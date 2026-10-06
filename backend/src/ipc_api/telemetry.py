"""Telemetria anônima das verificações (S21-01; FR-16, FR-17, NFR-12, C7 em 5.1).

Cada verificação vira um evento com período, lista, questão, versão do ruleset, resultado, as
regras violadas e o tempo de análise. Nunca código, IP, conta ou identificador de cliente.

O caminho da resposta só põe o evento numa fila limitada (``record`` não espera nada). Uma tarefa
de fundo grava em lote, a cada 100 eventos ou 2 s, com o usuário da API (membro de ``ipc_writer``,
que só insere). Se a fila encher ou o banco falhar, os eventos são descartados e contados: a
resposta à equipe nunca depende da telemetria. A mesma tarefa chama o expurgo de 12 meses (P-06)
ao subir e uma vez por dia.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

logger = logging.getLogger(__name__)

Outcome = Literal["valid", "invalid", "syntax_error", "rejected", "analysis_limit"]


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    enabled: bool = True
    queue_size: int = 10_000
    batch_size: int = 100
    flush_interval_s: float = 2.0
    purge_interval_s: float = 24 * 3600

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> TelemetryConfig:
        defaults = cls()
        return cls(
            enabled=env.get("IPC_TELEMETRY", "1") != "0",
            queue_size=int(env.get("IPC_TELEMETRY_QUEUE_SIZE", defaults.queue_size)),
            batch_size=int(env.get("IPC_TELEMETRY_BATCH_SIZE", defaults.batch_size)),
            flush_interval_s=float(
                env.get("IPC_TELEMETRY_FLUSH_INTERVAL_S", defaults.flush_interval_s)
            ),
            purge_interval_s=float(
                env.get("IPC_TELEMETRY_PURGE_INTERVAL_S", defaults.purge_interval_s)
            ),
        )


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    #: Período do ruleset (``2026.2``): a identidade de uma questão é (período, questão), P-07.
    semester: str
    list_number: int
    question_id: str | None
    ruleset_version: str
    outcome: Outcome
    violation_count: int
    analysis_ms: int
    #: Ocorrências por regra violada, em ordem de ``rule_id``.
    rules: tuple[tuple[str, int], ...] = ()

    @classmethod
    def from_result(
        cls,
        *,
        ruleset_version: str,
        list_number: int,
        outcome: Outcome,
        rule_ids: Iterable[str] = (),
        analysis_ms: int = 0,
        question_id: str | None = None,
    ) -> TelemetryEvent:
        counts = Counter(rule_ids)
        return cls(
            semester=semester_of(ruleset_version),
            list_number=list_number,
            question_id=question_id,
            ruleset_version=ruleset_version,
            outcome=outcome,
            violation_count=sum(counts.values()),
            analysis_ms=max(analysis_ms, 0),
            rules=tuple(sorted(counts.items())),
        )


def semester_of(ruleset_version: str) -> str:
    """``2026.2.1`` -> ``2026.2``: o período vem da versão do ruleset."""
    return ".".join(ruleset_version.split(".")[:2])


class TelemetrySink(Protocol):
    async def write(self, events: Sequence[TelemetryEvent]) -> None: ...

    async def purge_expired(self) -> int: ...

    async def close(self) -> None: ...


@dataclass(slots=True)
class TelemetryStats:
    written: int = 0
    dropped: int = 0
    failed_batches: int = 0
    purged: int = 0


@dataclass(slots=True)
class Telemetry:
    """A fila e a tarefa que grava. Sem ``sink`` (testes e telemetria desligada), não faz nada."""

    sink: TelemetrySink | None
    config: TelemetryConfig = field(default_factory=TelemetryConfig)
    stats: TelemetryStats = field(default_factory=TelemetryStats)
    #: Última versão do ruleset vista, para os eventos recusados antes da análise.
    ruleset_version: str | None = None
    _queue: asyncio.Queue[TelemetryEvent] | None = None
    _task: asyncio.Task[None] | None = None
    #: Eventos já tirados da fila, à espera de completar o lote; o ``stop`` também os grava.
    _pending: list[TelemetryEvent] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.sink is not None and self.config.enabled

    @property
    def queued(self) -> int:
        return 0 if self._queue is None else self._queue.qsize()

    def start(self) -> None:
        if not self.active or self._task is not None:
            return
        self._queue = asyncio.Queue(maxsize=self.config.queue_size)
        self._task = asyncio.create_task(self._run(self._queue), name="telemetria")

    def record(self, event: TelemetryEvent) -> None:
        """Põe o evento na fila sem esperar; se ela estiver cheia, o evento é descartado."""
        self.ruleset_version = event.ruleset_version
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.stats.dropped += 1
            if self.stats.dropped == 1 or self.stats.dropped % 1000 == 0:
                logger.warning("telemetria: fila cheia, eventos descartados")

    async def stop(self) -> None:
        """Grava o que ainda está na fila e encerra a tarefa e a conexão."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._queue is not None:
            queue = self._queue
            self._pending.extend(queue.get_nowait() for _ in range(queue.qsize()))
        await self._flush(self._take_pending())
        if self.sink is not None:
            await self.sink.close()

    async def _run(self, queue: asyncio.Queue[TelemetryEvent]) -> None:
        loop = asyncio.get_running_loop()
        next_purge = loop.time()
        while True:
            if loop.time() >= next_purge:
                await self._purge()
                next_purge = loop.time() + self.config.purge_interval_s
            await self._collect(queue)
            await self._flush(self._take_pending())

    async def _collect(self, queue: asyncio.Queue[TelemetryEvent]) -> None:
        """Junta até ``batch_size`` eventos ou espera ``flush_interval_s`` segundos."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.config.flush_interval_s
        while len(self._pending) < self.config.batch_size:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                self._pending.append(await asyncio.wait_for(queue.get(), remaining))
            except TimeoutError:
                break

    def _take_pending(self) -> list[TelemetryEvent]:
        batch, self._pending = self._pending, []
        return batch

    async def _flush(self, batch: list[TelemetryEvent]) -> None:
        if not batch or self.sink is None:
            return
        try:
            await self.sink.write(batch)
        except Exception as exc:  # o banco pode falhar de muitos jeitos; a resposta nunca
            self.stats.failed_batches += 1
            self.stats.dropped += len(batch)
            logger.warning("telemetria: lote descartado (%s)", type(exc).__name__)
        else:
            self.stats.written += len(batch)

    async def _purge(self) -> None:
        if self.sink is None:
            return
        try:
            self.stats.purged += await self.sink.purge_expired()
        except Exception as exc:  # tenta de novo no próximo ciclo
            logger.warning("telemetria: expurgo falhou (%s)", type(exc).__name__)


_INSERT_EVENT = (
    "INSERT INTO telemetry.validation_event (id, semester, list_number, question_id, "
    "ruleset_version, outcome, violation_count, analysis_ms) "
    "VALUES ($1, $2, $3, $4, $5, $6::telemetry.outcome, $7, $8)"
)
_INSERT_RULE = (
    "INSERT INTO telemetry.validation_event_rule (event_id, rule_id, occurrences) "
    "VALUES ($1, $2, $3)"
)


class PostgresTelemetrySink:
    """Grava os eventos com o usuário da API; o id vem daqui, porque ele não pode ler a tabela."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, dsn: str) -> PostgresTelemetrySink:
        import asyncpg  # só a produção precisa do driver

        pool = await asyncpg.create_pool(dsn, min_size=0, max_size=1, command_timeout=10)
        return cls(pool)

    async def write(self, events: Sequence[TelemetryEvent]) -> None:
        rows: list[tuple[Any, ...]] = []
        rules: list[tuple[Any, ...]] = []
        for event in events:
            event_id = uuid.uuid4()
            rows.append(
                (
                    event_id,
                    event.semester,
                    event.list_number,
                    event.question_id,
                    event.ruleset_version,
                    event.outcome,
                    min(event.violation_count, 200),
                    event.analysis_ms,
                )
            )
            rules.extend((event_id, rule_id, min(count, 200)) for rule_id, count in event.rules)
        async with self._pool.acquire() as connection, connection.transaction():
            await connection.executemany(_INSERT_EVENT, rows)
            if rules:
                await connection.executemany(_INSERT_RULE, rules)

    async def purge_expired(self) -> int:
        return int(await self._pool.fetchval("SELECT telemetry.purge_expired()"))

    async def close(self) -> None:
        await self._pool.close()

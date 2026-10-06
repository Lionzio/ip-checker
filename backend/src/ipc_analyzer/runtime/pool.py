"""Pool isolado de workers (ADR-01, S5-01).

Cada análise roda num processo filho do pool, nunca no processo que recebe a requisição:

- o worker nasce por ``forkserver`` (Linux) ou ``spawn`` (Windows), sem herdar sockets nem estado do
  processo principal, carrega o ruleset e então aplica os limites de recursos (``limits.py``);
- cada tarefa tem tempo de parede máximo; ao estourar, o Pebble mata o worker e cria outro;
- o worker é reciclado a cada ``max_tasks`` tarefas, para limitar vazamentos de memória;
- timeout, falta de memória e morte do worker viram ``AnalysisLimitError`` (422), nunca erro 5xx;
- com um prazo (S25-04), o pedido que vence na fila nem chega a ser analisado, e a análise que
  já começou não passa do prazo: nenhuma análise continua depois que a API desistiu.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import time
from collections.abc import Callable
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pebble import ProcessExpired, ProcessPool

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.feedback import FeedbackInput, feedback_input
from ipc_analyzer.engine.guards import AnalysisLimitError
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from ipc_analyzer.engine.similarity import (
    ClassMatch,
    ClassRejected,
    InvalidSide,
    Similarity,
    compare_class,
    compare_sources,
)
from ipc_analyzer.runtime.limits import ResourceLimits, apply_limits, forbid_new_processes
from ipc_analyzer.runtime.sandbox import SandboxMode, enforce

logger = logging.getLogger(__name__)


class DeadlineExpired(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """O prazo de quem pediu a análise venceu antes de ela terminar (S25-04)."""


@dataclass(frozen=True, slots=True)
class PoolConfig:
    workers: int = 2
    #: Tarefas por worker antes de ele ser substituído por um novo.
    max_tasks: int = 500
    #: Tempo de parede máximo de uma análise, em segundos.
    timeout_s: float = 2.0
    #: A comparação com a turma (S27-02) analisa até 101 códigos de uma vez.
    class_timeout_s: float = 10.0
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    #: Filtro seccomp do worker (S11-01). As imagens usam REQUIRED.
    sandbox: SandboxMode = SandboxMode.OPTIONAL


# ---------------------------------------------------------------------------
# Código que roda dentro do worker.
# ---------------------------------------------------------------------------

_RULESET: CompiledRuleset | None = None


def _init_worker(ruleset_path: str, limits: ResourceLimits, sandbox: SandboxMode) -> None:
    """Carrega o ruleset e só então se fecha: limites de recursos e, por fim, o seccomp.

    A ordem importa: depois dos limites, abrir arquivos falha; depois do seccomp, criar
    sockets e executar programas falha; por fim, nenhum processo novo nasce (o seccomp precisa
    de um subprocesso para achar a libseccomp). Com ``SandboxMode.REQUIRED``, um sistema que não
    permite o filtro impede o worker de nascer, e o serviço não fica pronto.
    """
    global _RULESET
    _RULESET = load_ruleset(Path(ruleset_path))
    if not apply_limits(limits):
        logger.warning("limites de recursos indisponíveis neste sistema; use Linux em produção")
    if not enforce(sandbox) and sandbox is SandboxMode.OPTIONAL:
        logger.warning("filtro seccomp indisponível neste sistema; use Linux em produção")
    forbid_new_processes()


def _before_deadline[T](deadline: float, function: Callable[..., T], *args: Any) -> T:
    """No worker: um pedido que esperou na fila além do prazo é descartado sem ser analisado.

    O prazo é de relógio de parede (``time.time``), comparável entre os processos da máquina.
    """
    if time.time() >= deadline:
        raise DeadlineExpired
    return function(*args)


def _analyze_in_worker(source: str, list_number: int, question_id: str | None) -> AnalysisResult:
    if _RULESET is None:
        raise RuntimeError("worker sem ruleset carregado")
    return analyze_source(
        source, list_number=list_number, ruleset=_RULESET, question_id=question_id
    )


def _feedback_in_worker(source: str, list_number: int, question_id: str | None) -> FeedbackInput:
    if _RULESET is None:
        raise RuntimeError("worker sem ruleset carregado")
    return feedback_input(
        source, list_number=list_number, ruleset=_RULESET, question_id=question_id
    )


def _compare_in_worker(first: str, second: str) -> Similarity | InvalidSide:
    if _RULESET is None:
        raise RuntimeError("worker sem ruleset carregado")
    return compare_sources(first, second, target=_RULESET.target_version)


def _compare_class_in_worker(
    code: str, others: list[str]
) -> SyntaxProblem | list[ClassMatch | SyntaxProblem | ClassRejected]:
    if _RULESET is None:
        raise RuntimeError("worker sem ruleset carregado")
    return compare_class(code, others, target=_RULESET.target_version)


# ---------------------------------------------------------------------------
# Lado do processo principal.
# ---------------------------------------------------------------------------


def _start_method() -> str:
    return "forkserver" if "forkserver" in multiprocessing.get_all_start_methods() else "spawn"


class AnalyzerPool:
    def __init__(self, ruleset_path: Path, config: PoolConfig | None = None) -> None:
        self.config = config or PoolConfig()
        self._pool = ProcessPool(
            max_workers=self.config.workers,
            max_tasks=self.config.max_tasks,
            initializer=_init_worker,
            initargs=(str(ruleset_path), self.config.limits, self.config.sandbox),
            # O Pebble anota o contexto como módulo, mas aceita um contexto de multiprocessing.
            context=multiprocessing.get_context(_start_method()),  # type: ignore[arg-type]
        )

    @property
    def active(self) -> bool:
        return bool(self._pool.active)

    async def run[T](
        self,
        function: Callable[..., T],
        *args: Any,
        deadline: float | None = None,
        timeout_s: float | None = None,
    ) -> T:
        """Executa ``function(*args)`` num worker, com tempo limite e tradução de falhas.

        ``deadline`` (``time.time``) é quando quem pediu desiste: sem tempo, o pedido é recusado
        com ``DeadlineExpired`` antes, durante a fila ou no meio da análise.
        """
        timeout = timeout_s if timeout_s is not None else self.config.timeout_s
        if deadline is None:
            future = self._pool.schedule(function, args=args, timeout=timeout)
        else:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise DeadlineExpired
            timeout = min(timeout, remaining)
            future = self._pool.schedule(
                _before_deadline, args=(deadline, function, *args), timeout=timeout
            )
        try:
            return await asyncio.wrap_future(future)
        except FuturesTimeoutError:
            if deadline is not None and time.time() >= deadline:
                logger.warning("análise interrompida no prazo de quem pediu; worker substituído")
                raise DeadlineExpired from None
            logger.warning("análise excedeu %.1f s; worker substituído", timeout)
            raise AnalysisLimitError(
                f"A análise excedeu o tempo limite de {timeout:g} s."
            ) from None
        except MemoryError:
            logger.warning("análise excedeu o limite de memória do worker")
            raise AnalysisLimitError("O código exige memória demais para ser analisado.") from None
        except ProcessExpired as exc:
            logger.warning("worker encerrado durante a análise (código %s)", exc.exitcode)
            raise AnalysisLimitError(
                "A análise foi interrompida e não pôde ser concluída."
            ) from None

    async def analyze(
        self,
        source: str,
        list_number: int,
        question_id: str | None = None,
        *,
        deadline: float | None = None,
    ) -> AnalysisResult:
        return await self.run(
            _analyze_in_worker, source, list_number, question_id, deadline=deadline
        )

    async def feedback_input(
        self,
        source: str,
        list_number: int,
        question_id: str | None = None,
        *,
        deadline: float | None = None,
    ) -> FeedbackInput:
        """Feedback (S18-02): o resultado com os nomes legíveis e o código sem comentários."""
        return await self.run(
            _feedback_in_worker, source, list_number, question_id, deadline=deadline
        )

    async def compare(
        self, first: str, second: str, *, deadline: float | None = None
    ) -> Similarity | InvalidSide:
        """Plágio (S17-02): os dois códigos são comparados no worker, com o mesmo isolamento."""
        return await self.run(_compare_in_worker, first, second, deadline=deadline)

    async def compare_class(
        self, code: str, others: list[str], *, deadline: float | None = None
    ) -> SyntaxProblem | list[ClassMatch | SyntaxProblem | ClassRejected]:
        """Uma solução contra a turma (S27-02), num worker só, com prazo próprio."""
        return await self.run(
            _compare_class_in_worker,
            code,
            others,
            deadline=deadline,
            timeout_s=self.config.class_timeout_s,
        )

    def close(self) -> None:
        self._pool.close()  # type: ignore[no-untyped-call]
        self._pool.join(timeout=10)
        if self._pool.active:
            self._pool.stop()  # type: ignore[no-untyped-call]
            self._pool.join()

"""Limpeza diária do banco (S25-03; Q-19 d, REC-06): roda ao subir a API e a cada intervalo.

Uma tarefa só, fora do caminho das requisições, chama ``AccountStore.housekeeping``. Uma falha
(banco fora do ar) fica no log e nas contagens do ``/health/slo``, e a tarefa tenta de novo no
próximo ciclo. Nenhuma contagem identifica alguém.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime

from ipc_api.accounts.models import HousekeepingCounts
from ipc_api.accounts.store import AccountStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HousekeepingConfig:
    enabled: bool = True
    #: Uma vez por dia, a partir da subida da API.
    interval_s: float = 24 * 3600

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> HousekeepingConfig:
        defaults = cls()
        return cls(
            enabled=env.get("IPC_HOUSEKEEPING", "1") != "0",
            interval_s=float(env.get("IPC_HOUSEKEEPING_INTERVAL_S", defaults.interval_s)),
        )


@dataclass(slots=True)
class HousekeepingStats:
    runs: int = 0
    failures: int = 0
    #: O que a limpeza apagou desde que a API subiu, somado.
    removed: HousekeepingCounts = field(default_factory=HousekeepingCounts)


class Housekeeping:
    def __init__(
        self,
        store: AccountStore,
        config: HousekeepingConfig,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self.store = store
        self.config = config
        self.clock = clock
        self.stats = HousekeepingStats()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self.config.enabled and self._task is None:
            self._task = asyncio.create_task(self._run(), name="limpeza-diaria")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        # Um servidor de testes pode encerrar a API em outro loop: aí basta o cancelamento.
        if task.get_loop() is asyncio.get_running_loop():
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def run_once(self) -> HousekeepingCounts | None:
        """Uma rodada; ``None`` se o banco falhou (a próxima rodada tenta de novo)."""
        try:
            counts = await self.store.housekeeping(self.clock())
        except Exception as exc:  # o banco pode falhar de muitos jeitos; a API segue no ar
            self.stats.failures += 1
            logger.warning("limpeza diária falhou (%s)", type(exc).__name__)
            return None
        self.stats.runs += 1
        total = self.stats.removed
        self.stats.removed = replace(
            total,
            sessions=total.sessions + counts.sessions,
            tokens=total.tokens + counts.tokens,
            unverified=total.unverified + counts.unverified,
            inactive=total.inactive + counts.inactive,
            log=total.log + counts.log,
        )
        logger.info(
            "limpeza diária: %s sessões, %s links, %s cadastros não confirmados, %s contas "
            "sem atividade e %s ações do registro apagados",
            counts.sessions,
            counts.tokens,
            counts.unverified,
            counts.inactive,
            counts.log,
        )
        return counts

    async def _run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.config.interval_s)

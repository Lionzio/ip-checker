"""Adoção da ferramenta pela equipe (S28-02; critério 2 da P-09, Q-15).

A primeira verificação de uma conta numa lista, em cada período, vira um registro em
``app.list_adoption``: só (conta, período, lista), sem data, código nem resultado, apagado junto
com a conta. A view ``telemetry.v_team_adoption_by_list`` devolve só a porcentagem de membros
ativos que usaram cada lista; a telemetria continua anônima (NFR-12).

O registro sai do caminho da resposta: a verificação nunca espera o banco por causa dele, e uma
falha só é tentada de novo na próxima verificação daquela conta e lista. Cada combinação já
gravada fica na memória (até ``max_keys``), para não repetir a escrita a cada verificação.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from ipc_api.accounts.models import StoreUnavailable
from ipc_api.accounts.store import AccountStore

logger = logging.getLogger(__name__)

_Key = tuple[UUID, str, int]


class Adoption:
    def __init__(self, store: AccountStore, *, max_keys: int = 10_000) -> None:
        self._store = store
        self._max_keys = max_keys
        self._seen: set[_Key] = set()
        self._tasks: set[asyncio.Task[None]] = set()

    def record(self, account_id: UUID, semester: str, list_number: int) -> None:
        """Agenda o registro, se esta conta ainda não foi vista nesta lista e período."""
        key = (account_id, semester, list_number)
        if key in self._seen:
            return
        if len(self._seen) >= self._max_keys:
            # Esquecer só custa uma escrita repetida, que o banco ignora (ON CONFLICT).
            self._seen.clear()
        self._seen.add(key)
        task = asyncio.create_task(self._write(key), name="adocao")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _write(self, key: _Key) -> None:
        try:
            await self._store.record_adoption(*key)
        except StoreUnavailable as exc:
            self._seen.discard(key)
            logger.warning("adoção: registro adiado (%s)", exc)

    async def drain(self) -> None:
        """Espera as escritas em andamento (ao desligar e nos testes)."""
        while self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

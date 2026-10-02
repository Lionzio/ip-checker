"""Gerenciamento da equipe (S15-02, FR-27): fila de pedidos, membros, cargos e remoções.

Cada ação é conferida na política (``auth/policy.py``) contra o estado atual da conta e aplicada
por uma transição condicional no banco: se outra pessoa agiu antes, a segunda recebe 409 em vez de
sobrescrever a primeira. Recusar, alterar o cargo, remover e reativar encerram as sessões da conta
(Q-19 c).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from ipc_api.accounts.models import REMOVED, Account, Role, Status
from ipc_api.accounts.store import AccountStore
from ipc_api.auth.policy import Action, can, can_manage, removal_status, state_allows
from ipc_api.errors import ApiError, ErrorCode


def forbidden() -> ApiError:
    return ApiError(403, ErrorCode.FORBIDDEN, "Você não tem permissão para esta ação.")


def not_found() -> ApiError:
    return ApiError(404, ErrorCode.ACCOUNT_NOT_FOUND, "Conta não encontrada.")


def state_changed() -> ApiError:
    return ApiError(
        409,
        ErrorCode.ACCOUNT_STATE_CHANGED,
        "Esta conta mudou desde que a lista foi carregada. Atualize a página e tente de novo.",
    )


class Management:
    def __init__(
        self, store: AccountStore, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self.store = store
        self.clock = clock

    async def requests(self, actor: Account) -> list[Account]:
        self._require_manager(actor)
        return await self.store.list_accounts({Status.AGUARDANDO_APROVACAO})

    async def members(self, actor: Account) -> tuple[list[Account], list[Account]]:
        self._require_manager(actor)
        active = await self.store.list_accounts({Status.ATIVO})
        removed = await self.store.list_accounts(REMOVED)
        return active, removed

    async def act(
        self, actor: Account, action: Action, target_id: UUID, role: Role | None = None
    ) -> Account:
        self._require_manager(actor)
        target = await self.store.get_account(target_id)
        if target is None:
            raise not_found()
        if target.id == actor.id or target.role is Role.DESENVOLVEDOR:
            raise forbidden()
        if not state_allows(action, target):
            raise state_changed()
        if not can(actor, action, target, role):
            raise forbidden()
        status, new_role = self._result(action, target, role)
        updated = await self.store.transition(
            target.id,
            expected=(target.status, target.role),
            status=status,
            role=new_role,
            decided_by=actor.id if action in (Action.APPROVE, Action.REJECT) else None,
            now=self.clock(),
            end_sessions=action is not Action.APPROVE,
        )
        if updated is None:
            raise state_changed()
        return updated

    @staticmethod
    def _result(action: Action, target: Account, role: Role | None) -> tuple[Status, Role | None]:
        if action is Action.REJECT:
            return Status.RECUSADO, None
        if action is Action.REMOVE:
            # A conta guarda o último cargo, como histórico (Q-19 d).
            return removal_status(target), target.role
        return Status.ATIVO, role

    @staticmethod
    def _require_manager(actor: Account) -> None:
        if not can_manage(actor):
            raise forbidden()

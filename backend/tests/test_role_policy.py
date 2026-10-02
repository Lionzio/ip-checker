"""Matriz completa da política de cargos (S15-01, FR-27): é a especificação de quem pode o quê.

O esperado é reescrito aqui a partir do texto do FR-27, sem usar as tabelas de ``policy.py``:
se as duas divergirem, este teste falha.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ipc_api.accounts.models import Account, Role, SignupMethod, Status, Treatment
from ipc_api.auth.policy import (
    Action,
    allowed_actions,
    assignable_roles,
    can,
    can_manage,
    removal_status,
    roles_for,
)

DEV, PROF, CHEFE, MON = Role.DESENVOLVEDOR, Role.PROFESSOR, Role.MONITOR_CHEFE, Role.MONITOR

#: "Atribui cargo, altera cargo e remove contas de", linha a linha da tabela do FR-27.
SPEC: dict[Role, set[Role]] = {
    DEV: {PROF, CHEFE, MON},
    PROF: {PROF, CHEFE, MON},
    CHEFE: {CHEFE, MON},
    MON: set(),
}
REMOVED = {Status.EX_MONITOR, Status.CONSELHEIRO, Status.INATIVO}


def account(
    role: Role | None, status: Status = Status.ATIVO, *, ja_foi_monitor_chefe: bool = False
) -> Account:
    return Account(
        id=uuid.uuid4(),
        name=f"Pessoa {uuid.uuid4().hex[:6]}",
        course="Ciência da Computação",
        treatment=Treatment.NEUTRO,
        role=role,
        status=status,
        ja_foi_monitor_chefe=ja_foi_monitor_chefe,
        password_hash=None,
        signup_method=SignupMethod.SENHA,
        emails=(f"{uuid.uuid4().hex[:8]}@cin.ufpe.br",),
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
    )


def expected(
    actor_role: Role,
    action: Action,
    target_role: Role | None,
    target_status: Status,
    requested: Role | None,
) -> bool:
    gives = SPEC[actor_role]
    if not gives or target_role is DEV:
        return False
    if action is Action.APPROVE:
        return target_status is Status.AGUARDANDO_APROVACAO and requested in gives
    if action is Action.REJECT:
        return target_status is Status.AGUARDANDO_APROVACAO and requested is None
    if action is Action.CHANGE_ROLE:
        return (
            target_status is Status.ATIVO
            and target_role in gives
            and requested in gives
            and requested is not target_role
        )
    if action is Action.REMOVE:
        return target_status is Status.ATIVO and target_role in gives and requested is None
    return target_status in REMOVED and requested in gives


def test_the_whole_matrix_follows_fr27() -> None:
    wrong = []
    for actor_role, action, target_role, target_status, requested in itertools.product(
        Role, Action, [*Role, None], Status, [*Role, None]
    ):
        actor = account(actor_role)
        target = account(target_role, target_status)
        got = can(actor, action, target, requested)
        if got != expected(actor_role, action, target_role, target_status, requested):
            wrong.append((actor_role, action, target_role, target_status, requested, got))

    assert wrong == []


@pytest.mark.parametrize("action", list(Action))
@pytest.mark.parametrize("role", list(Role))
def test_nobody_acts_on_the_own_account(action: Action, role: Role) -> None:
    for status in Status:
        actor = account(role)
        own = replace(actor, status=status)
        for requested in [*Role, None]:
            assert not can(actor, action, own, requested)


@pytest.mark.parametrize("status", [s for s in Status if s is not Status.ATIVO])
@pytest.mark.parametrize("role", [DEV, PROF, CHEFE])
def test_an_account_that_is_not_active_manages_nobody(role: Role, status: Status) -> None:
    actor = account(role, status)
    target = account(MON)

    assert not can_manage(actor)
    assert assignable_roles(actor) == ()
    assert allowed_actions(actor, target) == ()


def test_only_developer_professor_and_head_monitor_manage() -> None:
    assert [r for r in Role if can_manage(account(r))] == [DEV, PROF, CHEFE]


@pytest.mark.parametrize("role", list(Role))
def test_nobody_touches_the_developer_account(role: Role) -> None:
    developer = account(DEV)
    actor = account(role)

    assert allowed_actions(actor, developer) == ()
    assert not can(actor, Action.REMOVE, developer)
    assert all(not can(actor, Action.CHANGE_ROLE, developer, r) for r in Role)


def test_the_developer_role_is_never_assigned() -> None:
    pending = account(None, Status.AGUARDANDO_APROVACAO)
    for role in Role:
        assert DEV not in roles_for(account(role), Action.APPROVE, pending)


def test_head_monitor_approves_only_as_head_monitor_or_monitor() -> None:
    pending = account(None, Status.AGUARDANDO_APROVACAO)

    assert roles_for(account(CHEFE), Action.APPROVE, pending) == (CHEFE, MON)
    assert not can(account(CHEFE), Action.APPROVE, pending, PROF)


def test_head_monitor_does_not_act_on_professors() -> None:
    professor = account(PROF)

    assert allowed_actions(account(CHEFE), professor) == ()
    assert not can(account(CHEFE), Action.REMOVE, professor)


def test_changing_the_role_offers_the_other_roles_only() -> None:
    monitor = account(MON)

    assert roles_for(account(PROF), Action.CHANGE_ROLE, monitor) == (PROF, CHEFE)
    assert roles_for(account(CHEFE), Action.CHANGE_ROLE, monitor) == (CHEFE,)


@pytest.mark.parametrize(
    ("target", "result"),
    [
        (account(PROF), Status.INATIVO),
        (account(PROF, ja_foi_monitor_chefe=True), Status.INATIVO),
        (account(CHEFE, ja_foi_monitor_chefe=True), Status.CONSELHEIRO),
        (account(MON, ja_foi_monitor_chefe=True), Status.CONSELHEIRO),
        (account(MON), Status.EX_MONITOR),
    ],
)
def test_removal_keeps_the_record_with_the_right_status(target: Account, result: Status) -> None:
    assert removal_status(target) is result


def test_the_actions_shown_in_each_list() -> None:
    developer = account(DEV)

    assert allowed_actions(developer, account(None, Status.AGUARDANDO_APROVACAO)) == (
        Action.APPROVE,
        Action.REJECT,
    )
    assert allowed_actions(developer, account(MON)) == (Action.CHANGE_ROLE, Action.REMOVE)
    assert allowed_actions(developer, account(MON, Status.EX_MONITOR)) == (Action.REACTIVATE,)
    assert allowed_actions(developer, account(None, Status.AGUARDANDO_VERIFICACAO)) == ()
    assert allowed_actions(developer, account(None, Status.RECUSADO)) == ()
    assert allowed_actions(account(MON), account(MON)) == ()


def test_a_removed_professor_is_reactivated_by_who_gives_the_new_role() -> None:
    former = account(PROF, Status.INATIVO)

    assert roles_for(account(CHEFE), Action.REACTIVATE, former) == (CHEFE, MON)
    assert can(account(PROF), Action.REACTIVATE, former, PROF)
    assert not can(account(CHEFE), Action.REACTIVATE, former, PROF)

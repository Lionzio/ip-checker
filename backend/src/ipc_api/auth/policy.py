"""Política de cargos (S15-01; FR-27, P-14): quem pode fazer o quê sobre quem.

Funções puras, sem banco nem requisição: a API consulta esta tabela a cada ação, e o teste da
matriz completa (``tests/test_role_policy.py``) é a especificação.

| Cargo | Aprova cadastros | Atribui cargo, altera cargo e remove contas de |
|---|---|---|
| Desenvolvedor | Sim | Professores, monitores-chefe e monitores |
| Professor | Sim | Professores, monitores-chefe e monitores (nunca o desenvolvedor) |
| Monitor-chefe | Sim | Monitores-chefe e monitores |
| Monitor | Não | Ninguém, nem a si mesmo |

Além da tabela:

- ninguém age sobre a própria conta: ninguém altera o próprio cargo (FR-26), e ninguém remove a
  própria conta (Q-19 a);
- só o desenvolvedor altera a conta do desenvolvedor, e nenhuma ação daqui a altera (P-14);
- ao aprovar, o cargo é um dos que quem aprova pode atribuir;
- remover não apaga o registro: professor fica ``inativo``; quem já foi monitor-chefe vira
  ``conselheiro``; os demais, ``ex_monitor``;
- uma conta removida é reativada por quem pode atribuir o cargo que ela vai receber;
- o registro das ações de gerenciamento só é visto pelo desenvolvedor e pelos professores
  (REC-06).
"""

from __future__ import annotations

from enum import StrEnum

from ipc_api.accounts.models import REMOVED, Account, Role, Status


class Action(StrEnum):
    APPROVE = "aprovar"
    REJECT = "recusar"
    CHANGE_ROLE = "alterar_cargo"
    REMOVE = "remover"
    REACTIVATE = "reativar"


#: Os cargos que cada cargo atribui, altera e remove (tabela do FR-27).
ASSIGNABLE: dict[Role, tuple[Role, ...]] = {
    Role.DESENVOLVEDOR: (Role.PROFESSOR, Role.MONITOR_CHEFE, Role.MONITOR),
    Role.PROFESSOR: (Role.PROFESSOR, Role.MONITOR_CHEFE, Role.MONITOR),
    Role.MONITOR_CHEFE: (Role.MONITOR_CHEFE, Role.MONITOR),
    Role.MONITOR: (),
}

#: As ações que levam um cargo: aprovar, alterar e reativar.
ROLE_ACTIONS = frozenset({Action.APPROVE, Action.CHANGE_ROLE, Action.REACTIVATE})

#: O status em que a conta precisa estar para cada ação.
_FROM_STATUS: dict[Action, frozenset[Status]] = {
    Action.APPROVE: frozenset({Status.AGUARDANDO_APROVACAO}),
    Action.REJECT: frozenset({Status.AGUARDANDO_APROVACAO}),
    Action.CHANGE_ROLE: frozenset({Status.ATIVO}),
    Action.REMOVE: frozenset({Status.ATIVO}),
    Action.REACTIVATE: REMOVED,
}


def assignable_roles(actor: Account) -> tuple[Role, ...]:
    """Os cargos que a pessoa pode atribuir; vazio se ela não gerencia a equipe."""
    if actor.status is not Status.ATIVO or actor.role is None:
        return ()
    return ASSIGNABLE[actor.role]


def can_manage(actor: Account) -> bool:
    """Acesso à tela de gerenciamento: desenvolvedor, professor e monitor-chefe ativos."""
    return bool(assignable_roles(actor))


def can_view_log(actor: Account) -> bool:
    """O registro das ações de gerenciamento (REC-06): desenvolvedor e professores ativos."""
    return actor.status is Status.ATIVO and actor.role in (Role.DESENVOLVEDOR, Role.PROFESSOR)


#: Quem vê os indícios de uso de IA com ``IPC_AI_INDICATORS=chefia`` (S42-05, Q-35): a chefia,
#: durante a primeira lista, antes de toda a equipe.
INDICATORS_LEADERSHIP = frozenset({Role.DESENVOLVEDOR, Role.PROFESSOR, Role.MONITOR_CHEFE})
#: Quem cria o token de importação da extensão do Dikastis (S50-04): a chefia e o desenvolvedor.
IMPORT_ROLES = INDICATORS_LEADERSHIP


def sees_indicators(actor: Account, mode: str) -> bool:
    """Os indícios na verificação: ninguém com ``0``, a chefia com ``chefia``, todos com ``1``."""
    if actor.status is not Status.ATIVO or actor.role is None:
        return False
    if mode == "1":
        return True
    return mode == "chefia" and actor.role in INDICATORS_LEADERSHIP


def state_allows(action: Action, target: Account) -> bool:
    """A conta está no status de onde a ação parte (senão, 409: outra pessoa já agiu)."""
    return target.status in _FROM_STATUS[action]


def roles_for(actor: Account, action: Action, target: Account) -> tuple[Role, ...]:
    """Os cargos que ``actor`` pode dar a ``target`` com ``action`` (só nas ações com cargo)."""
    if action not in ROLE_ACTIONS or not _may_touch(actor, action, target):
        return ()
    roles = assignable_roles(actor)
    if action is Action.CHANGE_ROLE:
        return tuple(role for role in roles if role is not target.role)
    return roles


def can(actor: Account, action: Action, target: Account, role: Role | None = None) -> bool:
    """A ação é permitida? ``role`` é o cargo pedido, obrigatório só nas ações com cargo."""
    if action in ROLE_ACTIONS:
        return role is not None and role in roles_for(actor, action, target)
    return role is None and _may_touch(actor, action, target)


def allowed_actions(actor: Account, target: Account) -> tuple[Action, ...]:
    """As ações que a interface mostra para ``target`` a quem está logado."""
    return tuple(
        action
        for action in Action
        if (
            roles_for(actor, action, target)
            if action in ROLE_ACTIONS
            else can(actor, action, target)
        )
    )


def removal_status(target: Account) -> Status:
    """O status de quem é removido (FR-27). Professor fica inativo."""
    if target.role is Role.PROFESSOR:
        return Status.INATIVO
    if target.ja_foi_monitor_chefe or target.role is Role.MONITOR_CHEFE:
        return Status.CONSELHEIRO
    return Status.EX_MONITOR


def _may_touch(actor: Account, action: Action, target: Account) -> bool:
    roles = assignable_roles(actor)
    if not roles or target.id == actor.id or target.role is Role.DESENVOLVEDOR:
        return False
    if not state_allows(action, target):
        return False
    if action in (Action.CHANGE_ROLE, Action.REMOVE):
        # Altera e remove só quem tem um cargo da sua alçada.
        return target.role in roles
    return True

"""Gerenciamento da equipe (S15-02; FR-27, FR-28): só desenvolvedor, professor e monitor-chefe.

Um monitor recebe 403 em todas as rotas, inclusive por chamada direta. Cada item das listas traz
as ações que quem consulta pode fazer, calculadas pela mesma política que confere as ações. O
registro das ações (REC-06) só é visto pelo desenvolvedor e pelos professores.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from ipc_api.accounts.models import (
    ROLE_LABELS,
    STATUS_LABELS,
    Account,
    ManagementRecord,
    Role,
    StoreUnavailable,
)
from ipc_api.auth.deps import require_active_account
from ipc_api.auth.management import Management, forbidden
from ipc_api.auth.policy import (
    ROLE_ACTIONS,
    Action,
    allowed_actions,
    can,
    can_manage,
    removal_status,
    roles_for,
)
from ipc_api.deps import get_telemetry
from ipc_api.errors import database_unavailable
from ipc_api.routes import error_docs
from ipc_api.routes.auth import FORBIDDEN_ORIGIN, UNAVAILABLE
from ipc_api.schemas import (
    ListPanelResponse,
    ManagedAccount,
    ManagementLogEntry,
    ManagementLogResponse,
    MembersResponse,
    PanelRule,
    RequestsResponse,
    RoleChoice,
)
from ipc_api.telemetry import Telemetry, semester_of


def require_manager(account: Annotated[Account, Depends(require_active_account)]) -> Account:
    if not can_manage(account):
        raise forbidden()
    return account


def get_management(request: Request) -> Management:
    management: Management = request.app.state.management
    return management


router = APIRouter(
    prefix="/api/v1/admin", tags=["gerenciamento"], dependencies=[Depends(require_manager)]
)

Manager = Annotated[Account, Depends(require_manager)]
Service = Annotated[Management, Depends(get_management)]

UNAUTHENTICATED = "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe."
FORBIDDEN = "FORBIDDEN: o cargo de quem chama não permite a ação (FR-27)"
READ_ERRORS = {401: UNAUTHENTICATED, 403: FORBIDDEN + ".", 503: UNAVAILABLE}
ACTION_ERRORS = {
    401: UNAUTHENTICATED,
    403: FORBIDDEN + ", ou " + FORBIDDEN_ORIGIN,
    404: "ACCOUNT_NOT_FOUND: não há conta com esse identificador.",
    409: "ACCOUNT_STATE_CHANGED: a conta mudou desde que a lista foi carregada.",
    422: "INVALID_INPUT: identificador ou cargo inválido.",
    503: UNAVAILABLE,
}


def managed(actor: Account, account: Account) -> ManagedAccount:
    """A conta como quem consulta a vê: sem o tratamento, com as ações permitidas."""
    actions = allowed_actions(actor, account)
    role_action = next((a for a in actions if a in ROLE_ACTIONS), None)
    roles = roles_for(actor, role_action, account) if role_action is not None else ()
    return ManagedAccount(
        id=account.id,
        name=account.name,
        email=account.primary_email,
        course=account.course,
        signup_method=account.signup_method.value,
        requested_at=account.created_at,
        role=account.role.value if account.role is not None else None,
        role_label=ROLE_LABELS[account.role] if account.role is not None else None,
        status=account.status.value,
        status_label=STATUS_LABELS[account.status],
        actions=[action.value for action in actions],
        roles=[role.value for role in roles],
        removal_status=(
            removal_status(account).value if can(actor, Action.REMOVE, account) else None
        ),
    )


#: Como cada ação aparece no registro (REC-06), antes do nome da conta: "Aprovou Bia Souza".
ACTION_LABELS = {
    Action.APPROVE: "Aprovou",
    Action.REJECT: "Recusou",
    Action.CHANGE_ROLE: "Alterou o cargo de",
    Action.REMOVE: "Removeu",
    Action.REACTIVATE: "Reativou",
}


def _role_label(role: Role | None) -> str | None:
    return ROLE_LABELS[role] if role is not None else None


def log_entry(record: ManagementRecord) -> ManagementLogEntry:
    action = Action(record.action)
    return ManagementLogEntry(
        at=record.at,
        action=action.value,
        action_label=ACTION_LABELS[action],
        actor_name=record.actor_name,
        actor_role_label=_role_label(record.actor_role),
        target_name=record.target_name,
        from_status=record.from_status.value,
        from_status_label=STATUS_LABELS[record.from_status],
        to_status=record.to_status.value,
        to_status_label=STATUS_LABELS[record.to_status],
        from_role=record.from_role.value if record.from_role is not None else None,
        from_role_label=_role_label(record.from_role),
        to_role=record.to_role.value if record.to_role is not None else None,
        to_role_label=_role_label(record.to_role),
    )


async def _act(
    service: Management, actor: Account, action: Action, account_id: UUID, role: Role | None
) -> Response:
    try:
        await service.act(actor, action, account_id, role)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get(
    "/requests",
    summary="Fila de pedidos de cadastro com o e-mail confirmado",
    responses=error_docs(READ_ERRORS),
)
async def list_requests(actor: Manager, service: Service, response: Response) -> RequestsResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        items = await service.requests(actor)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return RequestsResponse(items=[managed(actor, account) for account in items])


@router.post(
    "/requests/{account_id}/approve",
    status_code=204,
    response_class=Response,
    summary="Aprova o pedido com um cargo que quem aprova pode atribuir",
    responses=error_docs(ACTION_ERRORS),
)
async def approve(account_id: UUID, body: RoleChoice, actor: Manager, service: Service) -> Response:
    return await _act(service, actor, Action.APPROVE, account_id, Role(body.role))


@router.post(
    "/requests/{account_id}/reject",
    status_code=204,
    response_class=Response,
    summary="Recusa o pedido",
    responses=error_docs(ACTION_ERRORS),
)
async def reject(account_id: UUID, actor: Manager, service: Service) -> Response:
    return await _act(service, actor, Action.REJECT, account_id, None)


@router.get(
    "/members",
    summary="Membros ativos e contas removidas (ex-monitores, conselheiros e inativos)",
    responses=error_docs(READ_ERRORS),
)
async def list_members(actor: Manager, service: Service, response: Response) -> MembersResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        active, removed = await service.members(actor)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return MembersResponse(
        active=[managed(actor, account) for account in active],
        removed=[managed(actor, account) for account in removed],
    )


@router.patch(
    "/members/{account_id}/role",
    status_code=204,
    response_class=Response,
    summary="Altera o cargo de um membro ativo; as sessões dele são encerradas",
    responses=error_docs(ACTION_ERRORS),
)
async def change_role(
    account_id: UUID, body: RoleChoice, actor: Manager, service: Service
) -> Response:
    return await _act(service, actor, Action.CHANGE_ROLE, account_id, Role(body.role))


@router.post(
    "/members/{account_id}/remove",
    status_code=204,
    response_class=Response,
    summary="Remove o membro da equipe sem apagar a conta (Ex-monitor, Conselheiro ou inativo)",
    responses=error_docs(ACTION_ERRORS),
)
async def remove(account_id: UUID, actor: Manager, service: Service) -> Response:
    return await _act(service, actor, Action.REMOVE, account_id, None)


@router.post(
    "/members/{account_id}/reactivate",
    status_code=204,
    response_class=Response,
    summary="Reativa uma conta removida com um cargo que quem reativa pode atribuir",
    responses=error_docs(ACTION_ERRORS),
)
async def reactivate(
    account_id: UUID, body: RoleChoice, actor: Manager, service: Service
) -> Response:
    return await _act(service, actor, Action.REACTIVATE, account_id, Role(body.role))


@router.get(
    "/log",
    summary="Registro das ações de gerenciamento dos últimos 12 meses (REC-06)",
    description=(
        "Quem aprovou, recusou, alterou o cargo, removeu ou reativou cada conta, e quando. "
        "Só o desenvolvedor e os professores veem; o monitor-chefe recebe 403."
    ),
    responses=error_docs(READ_ERRORS),
)
async def management_log(
    actor: Manager, service: Service, response: Response
) -> ManagementLogResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        records = await service.log(actor)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return ManagementLogResponse(items=[log_entry(record) for record in records])


@router.get(
    "/list-panel",
    summary="Regras mais violadas numa lista do período, só com dados anônimos (S40-03)",
    description=(
        "Para professores, monitores-chefes e o desenvolvedor: as contagens das views da "
        "telemetria (FR-17), sem código, conta, nome nem IP. Sem semestre, vale o período ativo."
    ),
    responses=error_docs(
        {**READ_ERRORS, 422: "INVALID_INPUT: lista fora de 1 a 6 ou semestre inválido."}
    ),
)
async def list_panel(
    actor: Manager,
    service: Service,
    response: Response,
    telemetry: Annotated[Telemetry, Depends(get_telemetry)],
    list_number: Annotated[int, Query(ge=1, le=6)],
    semester: Annotated[str | None, Query(pattern=r"^\d{4}\.[12]$")] = None,
) -> ListPanelResponse:
    response.headers["Cache-Control"] = "no-store"
    period = semester or (
        semester_of(telemetry.ruleset_version) if telemetry.ruleset_version else None
    )
    if period is None:
        return ListPanelResponse(
            semester="",
            list_number=list_number,
            top_rules=[],
            events=0,
            syntax_errors=0,
            adoption_pct=None,
        )
    try:
        panel = await service.store.list_panel(period, list_number)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return ListPanelResponse(
        semester=panel.semester,
        list_number=list_number,
        top_rules=[
            PanelRule(rule_id=rule.rule_id, events=rule.events, occurrences=rule.occurrences)
            for rule in panel.top_rules
        ],
        events=panel.events,
        syntax_errors=panel.syntax_errors,
        adoption_pct=panel.adoption_pct,
    )

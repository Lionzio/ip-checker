"""Perfil da conta logada (S14-03, FR-26): nome, curso, tratamento e senha; o cargo nunca."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.accounts.models import Account, StoreUnavailable, Treatment
from ipc_api.auth.accounts import AccountService
from ipc_api.auth.deps import get_accounts, get_authenticator, require_active_account
from ipc_api.auth.middleware import session_token
from ipc_api.auth.sessions import Authenticator, token_hash, valid_token
from ipc_api.deps import get_settings
from ipc_api.errors import database_unavailable
from ipc_api.routes import error_docs
from ipc_api.routes.auth import FORBIDDEN_ORIGIN, UNAVAILABLE, account_response
from ipc_api.schemas import AccountResponse, PasswordChange, ProfileUpdate
from ipc_api.settings import ApiSettings

router = APIRouter(
    prefix="/api/v1/profile", tags=["perfil"], dependencies=[Depends(require_active_account)]
)

UNAUTHENTICATED = "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe."


@router.patch(
    "",
    summary="Edita o próprio nome, curso e tratamento",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: FORBIDDEN_ORIGIN,
            409: "NAME_TAKEN: o nome já é usado por outra conta.",
            422: "INVALID_INPUT.",
            503: UNAVAILABLE,
        }
    ),
)
async def update_profile(
    body: ProfileUpdate,
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    accounts: Annotated[AccountService, Depends(get_accounts)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        updated = await accounts.update_profile(
            account,
            name=body.name,
            course=body.course,
            treatment=Treatment(body.treatment) if body.treatment is not None else None,
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return account_response(updated, settings.ai_indicators)


@router.post(
    "/password",
    status_code=204,
    response_class=Response,
    summary="Troca a senha (ou define uma, numa conta só do Google); as outras sessões caem",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: "INVALID_CREDENTIALS (senha atual incorreta) ou " + FORBIDDEN_ORIGIN,
            422: "WEAK_PASSWORD ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas tentativas com a senha atual errada. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def change_password(
    body: PasswordChange,
    request: Request,
    account: Annotated[Account, Depends(require_active_account)],
    accounts: Annotated[AccountService, Depends(get_accounts)],
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> Response:
    token = session_token(request.scope, authenticator.config.cookie_name)
    keep = token_hash(token) if token is not None and valid_token(token) else None
    try:
        await accounts.change_password(
            account, current=body.current_password, new=body.new_password, keep_session=keep
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=204, headers={"Cache-Control": "no-store"})

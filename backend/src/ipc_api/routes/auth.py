"""Entrar, sair e a conta logada (S13-02; FR-22 e FR-25)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.accounts.models import ROLE_LABELS, Account, StoreUnavailable
from ipc_api.auth.deps import get_authenticator, require_active_account
from ipc_api.auth.middleware import session_token
from ipc_api.auth.sessions import Authenticator
from ipc_api.errors import database_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas import AccountResponse, LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["autenticação"])

FORBIDDEN_ORIGIN = "ORIGIN_MISMATCH: a requisição veio de outro site."
UNAVAILABLE = "DATABASE_UNAVAILABLE: o banco de contas não respondeu. Veja retry_after_s."


def account_response(account: Account) -> AccountResponse:
    # Uma conta ativa sempre tem cargo (CHECK no banco).
    role = account.role
    assert role is not None  # noqa: S101 - invariante garantida pelo esquema
    return AccountResponse(
        name=account.name,
        email=account.primary_email,
        course=account.course,
        treatment=account.treatment.value,
        role=role.value,
        role_label=ROLE_LABELS[role],
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/login",
    summary="Entra com nome ou e-mail institucional e senha; abre a sessão no cookie",
    responses=error_docs(
        {
            401: "INVALID_CREDENTIALS: nome, e-mail ou senha incorretos (mensagem única).",
            403: (
                "ACCOUNT_PENDING_VERIFICATION, ACCOUNT_PENDING_APPROVAL, ACCOUNT_REJECTED ou "
                "ACCOUNT_REMOVED (só com a senha correta), ou " + FORBIDDEN_ORIGIN
            ),
            422: "DOMAIN_NOT_ALLOWED (e-mail fora de @cin.ufpe.br e @ufpe.br) ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas tentativas. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> AccountResponse:
    _no_store(response)
    try:
        account, token = await authenticator.login(body.login, body.password, request.scope)
        # Um identificador apresentado antes do login nunca é reaproveitado (fixação de sessão).
        await authenticator.logout(session_token(request.scope, authenticator.config.cookie_name))
    except StoreUnavailable:
        raise database_unavailable() from None
    config = authenticator.config
    response.set_cookie(
        config.cookie_name,
        token,
        max_age=config.absolute_timeout_s,
        path="/",
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return account_response(account)


@router.post(
    "/logout",
    status_code=204,
    summary="Sai: encerra a sessão no servidor e apaga o cookie",
    responses=error_docs({403: FORBIDDEN_ORIGIN, 503: UNAVAILABLE}),
)
async def logout(
    request: Request, authenticator: Annotated[Authenticator, Depends(get_authenticator)]
) -> Response:
    config = authenticator.config
    try:
        await authenticator.logout(session_token(request.scope, config.cookie_name))
    except StoreUnavailable:
        raise database_unavailable() from None
    response = Response(status_code=204)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        config.cookie_name, path="/", secure=config.cookie_secure, httponly=True, samesite="lax"
    )
    return response


@router.get(
    "/me",
    summary="A conta logada (o tratamento só aparece aqui, para o próprio titular)",
    responses=error_docs(
        {401: "UNAUTHENTICATED: sem sessão de uma conta ativa.", 503: UNAVAILABLE}
    ),
)
async def me(
    response: Response, account: Annotated[Account, Depends(require_active_account)]
) -> AccountResponse:
    _no_store(response)
    return account_response(account)

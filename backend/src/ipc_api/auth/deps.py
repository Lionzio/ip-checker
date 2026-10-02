"""Dependências do acesso restrito (FR-22): toda rota protegida exige uma conta ativa."""

from __future__ import annotations

from typing import Annotated

from fastapi import Request, Security
from fastapi.security import APIKeyCookie

from ipc_api.accounts.models import Account
from ipc_api.auth.accounts import AccountService
from ipc_api.auth.sessions import SECURE_COOKIE, Authenticator
from ipc_api.errors import database_unavailable, unauthenticated

#: Só documenta a sessão no OpenAPI; quem lê o cookie é o ``SessionMiddleware``.
session_cookie = APIKeyCookie(
    name=SECURE_COOKIE,
    auto_error=False,
    scheme_name="sessao",
    description=(
        "Sessão de uma conta ativa da equipe, criada por POST /api/v1/auth/login. HttpOnly, "
        "Secure e SameSite=Lax; o servidor guarda só o hash do identificador."
    ),
)


def get_authenticator(request: Request) -> Authenticator:
    authenticator: Authenticator = request.app.state.authenticator
    return authenticator


def get_accounts(request: Request) -> AccountService:
    accounts: AccountService = request.app.state.accounts
    return accounts


def require_active_account(
    request: Request, _cookie: Annotated[str | None, Security(session_cookie)] = None
) -> Account:
    if getattr(request.state, "session_error", False):
        raise database_unavailable()
    account: Account | None = getattr(request.state, "account", None)
    if account is None:
        raise unauthenticated()
    return account

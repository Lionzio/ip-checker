"""A dependência das rotas ``/api/v1/import/*`` (S50-04): o token de importação, não a sessão.

Lê ``Authorization: Bearer ipc_imp_…``, confere o token (ativo, da conta ativa, do cargo certo) e o
limite por minuto dele. Qualquer recusa de credencial é o mesmo 401, sem dizer o motivo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ipc_api.accounts.models import Account, StoreUnavailable
from ipc_api.accounts.store import AccountStore
from ipc_api.errors import ApiError, ErrorCode, database_unavailable, unauthenticated
from ipc_api.importing.service import ImportService, can_import

bearer = HTTPBearer(
    auto_error=False,
    scheme_name="ImportToken",
    description="O token de importação da extensão do Dikastis (Perfil → Token de importação).",
)


def get_importing(request: Request) -> ImportService:
    service: ImportService = request.app.state.importing
    return service


async def require_import_token(
    request: Request,
    service: Annotated[ImportService, Depends(get_importing)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)] = None,
) -> Account:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthenticated()
    store: AccountStore = request.app.state.authenticator.store
    try:
        token = await service.authenticate(credentials.credentials)
        account = await store.get_account(token.account_id) if token is not None else None
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    if token is None or account is None or not can_import(account):
        raise unauthenticated()
    wait = service.allow(token.id)
    if wait is not None:
        raise ApiError(
            429,
            ErrorCode.RATE_LIMITED,
            "Muitas sincronizações seguidas com este token: espere um minuto.",
            retry_after_s=wait,
        )
    request.state.account_id = account.id.bytes
    return account

"""Middlewares do acesso restrito: a sessão de cada requisição e a conferência do ``Origin``.

``SessionMiddleware`` lê o cookie e deixa a conta ativa em ``request.state.account``, antes do
limite de taxa, que passa a contar por conta. Ele não recusa nada: quem exige a sessão é a
dependência ``require_active_account`` de cada rota protegida, o que deixa a regra explícita no
código e no OpenAPI.

``OriginCheckMiddleware`` barra requisições que mudam estado vindas de outro site (CSRF), além do
``SameSite=Lax`` do cookie: um ``Origin`` presente precisa ser a própria origem da API (o ``Host``
pedido) ou uma das origens configuradas.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.requests import cookie_parser
from starlette.types import ASGIApp, Receive, Scope, Send

from ipc_api.accounts.models import StoreUnavailable
from ipc_api.errors import ErrorCode, error_response

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def session_token(scope: Scope, cookie_name: str) -> str | None:
    header = Headers(scope=scope).get("cookie")
    return cookie_parser(header).get(cookie_name) if header else None


class SessionMiddleware:
    def __init__(self, app: ASGIApp, cookie_name: str) -> None:
        self.app = app
        self.cookie_name = cookie_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        token = session_token(scope, self.cookie_name)
        if token is not None:
            state: dict[str, Any] = scope.setdefault("state", {})
            authenticator = scope["app"].state.authenticator
            try:
                account = await authenticator.resolve(token)
            except StoreUnavailable:
                state["session_error"] = True
            else:
                if account is not None:
                    state["account"] = account
                    state["account_id"] = account.id.bytes
        await self.app(scope, receive, send)


def _origin_allowed(origin: str, host: str | None, allowed: frozenset[str]) -> bool:
    normalized = origin.rstrip("/").lower()
    if normalized in allowed:
        return True
    parts = urlsplit(normalized)
    return parts.scheme in {"http", "https"} and host is not None and parts.netloc == host.lower()


class OriginCheckMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: tuple[str, ...]) -> None:
        self.app = app
        self.allowed = frozenset(origin.rstrip("/").lower() for origin in allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] not in UNSAFE_METHODS
            or not scope["path"].startswith("/api/")
        ):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin is None or _origin_allowed(origin, headers.get("host"), self.allowed):
            await self.app(scope, receive, send)
            return
        state: dict[str, Any] = scope.setdefault("state", {})
        state["outcome"] = ErrorCode.ORIGIN_MISMATCH
        # A recusa vem antes do roteamento, e o caminho pedido não vai para o log (S9-01).
        state["route_path"] = "outra"
        response = error_response(
            403,
            ErrorCode.ORIGIN_MISMATCH,
            "A requisição veio de outro site e foi recusada.",
        )
        await response(scope, receive, send)

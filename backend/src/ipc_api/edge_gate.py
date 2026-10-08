"""Só a página fala com a API do piloto (S30-03): o segredo que o middleware da Vercel acrescenta.

O Render é público e acrescenta ao ``X-Forwarded-For`` sem limpá-lo, e a Vercel não assina o que
repassa: quem chamasse o Render direto escolheria a própria chave do limite por IP. Com
``IPC_EDGE_SECRET`` configurada, toda requisição a ``/api/*`` precisa trazer o mesmo segredo no
cabeçalho que o middleware da página escreve (``frontend/scripts/edge-middleware.mjs``); sem ele,
403 ``ORIGIN_MISMATCH``. Com ele, o IP do cliente que a Vercel determinou passa a ser o IP da
requisição para os limites (``ratelimit.client_ip``).

As rotas de operação (``/health``, ``/ready``) ficam fora: o UptimeRobot e o pipeline as chamam
direto no Render. Sem o segredo configurado (compose, testes), nada muda.
"""

from __future__ import annotations

import hmac
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from ipc_api.errors import ErrorCode, error_response
from ipc_api.ratelimit import parse_ip

SECRET_HEADER = "x-ipc-edge-secret"  # noqa: S105 - o nome do cabeçalho, não o segredo
CLIENT_HEADER = "x-ipc-client-ip"
#: Um segredo curto seria adivinhável; ``openssl rand -hex 32`` gera 64 caracteres.
MIN_SECRET_LENGTH = 32


def validate_edge_secret(value: str | None) -> str | None:
    """Recusa na subida um ``IPC_EDGE_SECRET`` curto demais (falha visível no deploy)."""
    if not value:
        return None
    if len(value) < MIN_SECRET_LENGTH:
        raise ValueError(
            f"IPC_EDGE_SECRET curto demais: use pelo menos {MIN_SECRET_LENGTH} caracteres "
            "(por exemplo, openssl rand -hex 32)."
        )
    return value


class EdgeGateMiddleware:
    def __init__(self, app: ASGIApp, secret: str | None) -> None:
        self.app = app
        self.secret = secret.encode() if secret else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.secret is None or scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        state: dict[str, Any] = scope.setdefault("state", {})
        if hmac.compare_digest(headers.get(SECRET_HEADER, "").encode(), self.secret):
            state["edge_verified"] = True
            address = parse_ip(headers.get(CLIENT_HEADER))
            if address is not None:
                state["edge_client_ip"] = address
            await self.app(scope, receive, send)
            return
        state["outcome"] = ErrorCode.ORIGIN_MISMATCH
        # Como no OriginCheckMiddleware: a recusa vem antes do roteamento, sem o caminho no log.
        state["route_path"] = "outra"
        response = error_response(
            403,
            ErrorCode.ORIGIN_MISMATCH,
            "A API do IP-Checker só atende pela página.",
        )
        await response(scope, receive, send)

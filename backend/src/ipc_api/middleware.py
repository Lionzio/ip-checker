"""Middleware ASGI da API: identificador de requisição e limite de corpo antes da leitura."""

from __future__ import annotations

from fastapi import HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ipc_api.errors import ErrorCode, error_response
from ipc_api.ids import new_request_id


class RequestContextMiddleware:
    """Dá um ``request_id`` a cada requisição e recusa corpos acima do limite (DoD, item 1).

    Um ``Content-Length`` acima do limite é recusado sem ler um byte do corpo. Sem
    ``Content-Length`` (corpo em partes), a contagem acontece durante a leitura.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("X-Request-Id", request_id)
            await send(message)

        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self.max_body_bytes:
            response = error_response(413, ErrorCode.PAYLOAD_TOO_LARGE, self._too_large_message())
            await response(scope, receive, send_with_id)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    # O FastAPI repassa HTTPException da leitura do corpo ao tratador de erros.
                    raise HTTPException(413, self._too_large_message())
            return message

        await self.app(scope, limited_receive, send_with_id)

    def _too_large_message(self) -> str:
        return f"O corpo da requisição passa de {self.max_body_bytes // 1024} KB."

"""Middleware ASGI da API: identificador, limite de corpo, erro inesperado e a linha de log de
cada requisição."""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ipc_api.errors import ErrorCode, error_response
from ipc_api.ids import new_request_id
from ipc_api.logging import get_logger
from ipc_api.slo import SloMonitor

log = get_logger("ipc_api.access")
errors = get_logger("ipc_api.errors")


class RequestContextMiddleware:
    """Dá um ``request_id`` a cada requisição, recusa corpos acima do limite (DoD, item 1) e
    escreve uma linha de log ao final (S9-01).

    Um ``Content-Length`` acima do limite é recusado sem ler um byte do corpo. Sem
    ``Content-Length`` (corpo em partes), a contagem acontece durante a leitura. A linha de log
    traz o caminho da rota, nunca o caminho pedido: uma URL inventada pelo cliente não chega ao log.

    Uma exceção que escapa da aplicação vira um 500 ``INTERNAL_ERROR`` em JSON, com o
    ``request_id`` na mensagem e no cabeçalho (S25-04); o log guarda o tipo da exceção e o
    rastro, nunca o corpo da requisição.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int, slo: SloMonitor | None = None) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.slo = slo

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        request_id = new_request_id()
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id
        status = 500
        received = 0
        started_response = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, started_response
            if message["type"] == "http.response.start":
                started_response = True
                status = message["status"]
                MutableHeaders(scope=message).append("X-Request-Id", request_id)
            await send(message)

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    # O FastAPI repassa HTTPException da leitura do corpo ao tratador de erros.
                    raise HTTPException(413, self._too_large_message())
            return message

        try:
            declared = Headers(scope=scope).get("content-length", "")
            if declared.isdigit() and int(declared) > self.max_body_bytes:
                received = int(declared)
                state["outcome"] = ErrorCode.PAYLOAD_TOO_LARGE
                response = error_response(
                    413, ErrorCode.PAYLOAD_TOO_LARGE, self._too_large_message()
                )
                await response(scope, receive, send_with_id)
                return
            try:
                await self.app(scope, limited_receive, send_with_id)
            except Exception as exc:
                errors.error(
                    "erro inesperado",
                    request_id=request_id,
                    error_type=type(exc).__name__,
                    exc_info=True,
                )
                if started_response:
                    raise
                state["outcome"] = ErrorCode.INTERNAL_ERROR
                response = error_response(
                    500,
                    ErrorCode.INTERNAL_ERROR,
                    "Erro inesperado no serviço. Se continuar, informe à equipe o código "
                    f"{request_id}.",
                )
                await response(scope, receive, send_with_id)
        finally:
            route = scope.get("route")
            path = getattr(route, "path", state.get("route_path", "outra"))
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            if self.slo is not None:
                self.slo.observe(path, status, latency_ms)
            log.info(
                "request",
                request_id=request_id,
                method=scope["method"],
                path=path,
                status=status,
                latency_ms=latency_ms,
                payload_bytes=received,
                list_number=state.get("list_number"),
                ruleset_version=state.get("ruleset_version"),
                outcome=str(state.get("outcome") or status),
                **({"rate_limit": state["rate_limit"]} if "rate_limit" in state else {}),
            )

    def _too_large_message(self) -> str:
        return f"O corpo da requisição passa de {self.max_body_bytes // 1024} KB."

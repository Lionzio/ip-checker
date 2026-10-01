"""Linha de log de cada chamada ao analyzer (S9-01): sem código, sem IP, com o id da API."""

from __future__ import annotations

import re
import time
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ipc_analyzer.logging import get_logger

log = get_logger("ipc_analyzer.access")

#: Só um ULID vindo da API entra no log; qualquer outro valor do cabeçalho é ignorado.
_REQUEST_ID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        state: dict[str, Any] = scope.setdefault("state", {})
        status = 500

        async def send_and_record(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_and_record)
        finally:
            request_id = Headers(scope=scope).get("x-request-id", "")
            route = scope.get("route")
            log.info(
                "analysis" if getattr(route, "path", "") == "/internal/analyze" else "request",
                request_id=request_id if _REQUEST_ID.match(request_id) else None,
                method=scope["method"],
                path=getattr(route, "path", "outra"),
                status=status,
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
                payload_bytes=state.get("payload_bytes"),
                list_number=state.get("list_number"),
                ruleset_version=state.get("ruleset_version"),
                outcome=str(state.get("outcome") or status),
                violations=state.get("violations"),
            )

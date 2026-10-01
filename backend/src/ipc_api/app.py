"""Aplicação FastAPI da API pública (S8-01).

Para rodar localmente, com o analyzer em http://127.0.0.1:8001::

    uv run uvicorn ipc_api.app:create_app --factory --port 8101

Ordem de cada requisição (5.2.2): identificador e limite de corpo, limite de taxa (429),
validação (413/422), admissão (503) e chamada ao analyzer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ipc_api.admission import Admission
from ipc_api.clients.analyzer import AnalyzerClient
from ipc_api.errors import ApiError, ErrorCode, error_response
from ipc_api.logging import configure_logging
from ipc_api.middleware import RequestContextMiddleware
from ipc_api.ratelimit import RateLimitMiddleware, SlidingWindowLimiter
from ipc_api.routes import meta, validate
from ipc_api.settings import ApiSettings

API_VERSION = "1.0.0"

DESCRIPTION = """\
Confere, **sem executar o código**, se a solução em Python de um aluno de Introdução à
Programação respeita as permissões da lista antes do envio ao Dikastis.

Todo erro segue o formato `{"error": {"code", "message", "retry_after_s"}}`. Toda resposta traz
o cabeçalho `X-Request-Id`. As respostas 429 e 503 trazem também o cabeçalho `Retry-After`.
"""


def create_app(
    settings: ApiSettings | None = None,
    *,
    analyzer_transport: httpx2.AsyncBaseTransport | None = None,
) -> FastAPI:
    """``analyzer_transport`` só existe para os testes trocarem a rede pelo analyzer em memória."""
    config = settings or ApiSettings.from_env()
    if config.json_logs:
        configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = AnalyzerClient(
            config.analyzer_url, config.analyzer_timeout_s, transport=analyzer_transport
        )
        app.state.analyzer = client
        # O semáforo pertence ao laço de eventos que atende as requisições.
        app.state.admission = Admission(config.admission)
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(
        title="IP-Checker",
        version=API_VERSION,
        description=DESCRIPTION,
        # O contrato fica versionado em docs/openapi.json; o serviço não expõe documentação.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.rate_limiter = SlidingWindowLimiter(max_keys=config.rate_limit.max_keys)
    # O último middleware adicionado é o mais externo: o contexto (identificador, limite de
    # corpo e log) envolve o limite de taxa, e assim o 429 também aparece no log.
    app.add_middleware(
        RateLimitMiddleware, config=config.rate_limit, limiter=app.state.rate_limiter
    )
    app.add_middleware(RequestContextMiddleware, max_body_bytes=config.max_body_bytes)

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        request.state.outcome = exc.code
        return exc.response()

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
        request.state.outcome = ErrorCode.INVALID_INPUT
        return error_response(
            422,
            ErrorCode.INVALID_INPUT,
            "Requisição inválida: envie code (texto), list_number (1 a 6) e, se houver, "
            "question_id.",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Response:
        if exc.status_code == 413:
            request.state.outcome = ErrorCode.PAYLOAD_TOO_LARGE
            return error_response(413, ErrorCode.PAYLOAD_TOO_LARGE, str(exc.detail))
        # O FastAPI responde 400 genérico quando o corpo não é UTF-8 válido.
        if exc.status_code == 400:
            request.state.outcome = ErrorCode.INVALID_INPUT
            return error_response(
                422, ErrorCode.INVALID_INPUT, "O corpo da requisição não é JSON em UTF-8 válido."
            )
        return await http_exception_handler(request, exc)

    app.include_router(validate.router)
    app.include_router(meta.router)
    return app

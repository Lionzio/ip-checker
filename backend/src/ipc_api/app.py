"""Aplicação FastAPI da API pública (S8-01).

Para rodar localmente, com o analyzer em http://127.0.0.1:8001::

    uv run uvicorn ipc_api.app:create_app --factory --port 8101

Ordem de cada requisição (5.2.2): identificador e limite de corpo, ``Origin`` (403), sessão,
limite de taxa por conta (429), conta ativa (401), validação (413/422), admissão (503) e chamada
ao analyzer. O banco de contas vem de ``IPC_DATABASE_URL`` (S13-01).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx2
from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ipc_api.accounts.models import DeveloperSeed
from ipc_api.accounts.passwords import Passwords, password_problems
from ipc_api.accounts.store import AccountStore
from ipc_api.admission import Admission
from ipc_api.auth.middleware import OriginCheckMiddleware, SessionMiddleware
from ipc_api.auth.sessions import Authenticator
from ipc_api.clients.analyzer import AnalyzerClient
from ipc_api.edge import SecurityHeadersMiddleware
from ipc_api.errors import ApiError, ErrorCode, error_response
from ipc_api.logging import configure_logging
from ipc_api.middleware import RequestContextMiddleware
from ipc_api.ratelimit import RateLimitMiddleware, SlidingWindowLimiter
from ipc_api.routes import auth, meta, validate
from ipc_api.settings import ApiSettings, DeveloperSettings

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

DESCRIPTION = """\
Confere, **sem executar o código**, se a solução em Python de um aluno de Introdução à
Programação respeita as permissões da lista antes do envio ao Dikastis.

O acesso é restrito à equipe da disciplina: as rotas, exceto `/health`, `/ready` e as de
autenticação, exigem a sessão de uma conta ativa, aberta por `POST /api/v1/auth/login`.

Todo erro segue o formato `{"error": {"code", "message", "retry_after_s"}}`. Toda resposta traz
o cabeçalho `X-Request-Id`. As respostas 429 e 503 trazem também o cabeçalho `Retry-After`.
"""


async def _connect_store(settings: ApiSettings) -> AccountStore:
    # Importado aqui: só a produção precisa do driver do PostgreSQL.
    from ipc_api.accounts.postgres import PostgresAccountStore

    if settings.database_url is None:
        raise RuntimeError("Defina IPC_DATABASE_URL: a API não sobe sem o banco de contas.")
    return await PostgresAccountStore.connect(settings.database_url)


async def seed_developer(
    store: AccountStore, passwords: Passwords, developer: DeveloperSettings, now: datetime
) -> None:
    """Cria ou confirma a conta do desenvolvedor (P-14); a senha só vale na criação."""
    password_hash = None
    if developer.initial_password is not None:
        problems = password_problems(developer.initial_password)
        if problems:
            raise ValueError("IPC_DEV_INITIAL_PASSWORD precisa " + ", ".join(problems) + ".")
        password_hash = await passwords.hash(developer.initial_password)
    account = await store.ensure_developer(
        DeveloperSeed(developer.name, developer.course, developer.emails, password_hash), now
    )
    if account.password_hash is None:
        logger.warning("a conta do desenvolvedor não tem senha: defina IPC_DEV_INITIAL_PASSWORD")


def create_app(
    settings: ApiSettings | None = None,
    *,
    analyzer_transport: httpx2.AsyncBaseTransport | None = None,
    account_store: AccountStore | None = None,
    passwords: Passwords | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    """Os parâmetros depois de ``settings`` só existem para os testes: o analyzer em memória, um
    repositório de contas em memória, um Argon2 mais barato e um relógio controlável."""
    config = settings or ApiSettings.from_env()
    if config.json_logs:
        configure_logging()
    hasher = passwords or Passwords()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = account_store or await _connect_store(config)
        client = AnalyzerClient(
            config.analyzer_url, config.analyzer_timeout_s, transport=analyzer_transport
        )
        try:
            await seed_developer(store, hasher, config.developer, clock())
            app.state.authenticator = Authenticator(
                store,
                hasher,
                config.session,
                rate_limit=config.rate_limit,
                throttle_config=config.login_throttle,
                clock=clock,
            )
            app.state.analyzer = client
            # O semáforo pertence ao laço de eventos que atende as requisições.
            app.state.admission = Admission(config.admission)
            yield
        finally:
            await client.aclose()
            if account_store is None:
                await store.close()

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
    # corpo e log) envolve os demais, e assim o 403 e o 429 também aparecem no log. A sessão vem
    # antes do limite de taxa, que conta por conta.
    app.add_middleware(
        RateLimitMiddleware, config=config.rate_limit, limiter=app.state.rate_limiter
    )
    app.add_middleware(SessionMiddleware, cookie_name=config.session.cookie_name)
    app.add_middleware(
        OriginCheckMiddleware, allowed_origins=config.allowed_origins + config.cors_origins
    )
    app.add_middleware(RequestContextMiddleware, max_body_bytes=config.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware, hsts=config.hsts)
    if config.cors_origins:
        # O mais externo: até um 413 ou um 429 precisa dos cabeçalhos CORS, ou o navegador
        # esconde a resposta da página e o aluno vê "falha de rede" no lugar do motivo.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            expose_headers=["Retry-After", "X-Request-Id"],
            allow_credentials=False,
            max_age=600,
        )

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        request.state.outcome = exc.code
        return exc.response()

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
        request.state.outcome = ErrorCode.INVALID_INPUT
        if request.url.path == "/api/v1/auth/login":
            message = "Requisição inválida: envie login (nome ou e-mail) e password (senha)."
        else:
            message = (
                "Requisição inválida: envie code (texto), list_number (1 a 6) e, se houver, "
                "question_id."
            )
        return error_response(422, ErrorCode.INVALID_INPUT, message)

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

    app.include_router(auth.router)
    app.include_router(validate.router)
    app.include_router(meta.protected)
    app.include_router(meta.router)
    return app

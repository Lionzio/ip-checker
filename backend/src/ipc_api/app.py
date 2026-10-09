"""Aplicação FastAPI da API pública (S8-01).

Para rodar localmente, com o analyzer em http://127.0.0.1:8001::

    uv run uvicorn ipc_api.app:create_app --factory --port 8101

Ordem de cada requisição (5.2.2): identificador e limite de corpo, ``Origin`` (403), sessão,
limite de taxa por conta (429), conta ativa (401), validação (413/422), admissão (503) e chamada
ao analyzer. O banco de contas vem de ``IPC_DATABASE_URL`` (S13-01).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Sequence
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
from ipc_api.adoption import Adoption
from ipc_api.auth.accounts import AccountService
from ipc_api.auth.google import Expiring, GoogleOidc
from ipc_api.auth.google_accounts import GoogleAccounts
from ipc_api.auth.management import Management
from ipc_api.auth.middleware import OriginCheckMiddleware, SessionMiddleware
from ipc_api.auth.sessions import Authenticator
from ipc_api.auth.throttle import LoginThrottle
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.edge import SecurityHeadersMiddleware
from ipc_api.edge_gate import EdgeGateMiddleware
from ipc_api.errors import ApiError, ErrorCode, error_response
from ipc_api.feedback.providers import LlmConfig, Provider, Slot, build_provider
from ipc_api.feedback.service import Ai, FeedbackService
from ipc_api.gabaritos import Gabaritos
from ipc_api.gabaritos import load as load_gabaritos
from ipc_api.housekeeping import Housekeeping
from ipc_api.logging import configure_logging
from ipc_api.mail import EmailSender, email_sender_for
from ipc_api.middleware import RequestContextMiddleware
from ipc_api.ratelimit import (
    ApiGateMiddleware,
    FixedWindowCounter,
    RateLimitMiddleware,
    SlidingWindowLimiter,
)
from ipc_api.routes import admin, auth, feedback, google, meta, profile, similarity, validate
from ipc_api.settings import ApiSettings, DeveloperSettings
from ipc_api.slo import SloMonitor
from ipc_api.telemetry import PostgresTelemetrySink, Telemetry, TelemetrySink

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

DESCRIPTION = """\
Confere, **sem executar o código**, se a solução em Python de um aluno de Introdução à
Programação respeita as permissões da lista antes do envio ao Dikastis.

O acesso é restrito à equipe da disciplina: as rotas, exceto `/health`, `/ready`, `/health/slo`
e as de autenticação, exigem a sessão de uma conta ativa, aberta por `POST /api/v1/auth/login`.

Todo erro segue o formato `{"error": {"code", "message", "retry_after_s"}}`. Toda resposta traz
o cabeçalho `X-Request-Id`. As respostas 429 e 503 trazem também o cabeçalho `Retry-After`.

Além dos limites de cada rota, qualquer rota em `/api/*` responde 429 `RATE_LIMITED` quando um IP
passa de 600 requisições por minuto (6.000 nas faixas do campus). Uma falha inesperada responde
500 `INTERNAL_ERROR`, com o `X-Request-Id` na mensagem.
"""


#: Mensagem do 422 INVALID_INPUT de cada rota quando o corpo não segue o esquema.
VALIDATION_MESSAGES = {
    "/api/v1/validate": (
        "Requisição inválida: envie code (texto), list_number (1 a 6) e, se houver, question_id."
    ),
    "/api/v1/auth/login": "Requisição inválida: envie login (nome ou e-mail) e password (senha).",
    "/api/v1/similarity": "Requisição inválida: envie code_a e code_b, os dois códigos a comparar.",
    "/api/v1/feedback": (
        "Requisição inválida: envie code, list_number, student_name (até 120 caracteres) e, se "
        "quiser, annotation (até 1.000 caracteres)."
    ),
    "/api/v1/auth/register": (
        "Requisição inválida: envie name, email, password, course e treatment (masculino, "
        "feminino ou neutro)."
    ),
}

ADMIN_VALIDATION_MESSAGE = (
    "Requisição inválida: use o identificador de uma conta e, ao aprovar, alterar ou reativar, "
    "envie role (professor, monitor_chefe ou monitor)."
)


def _ais(config: ApiSettings, injected: Sequence[Provider] | None) -> list[Ai]:
    """A IA principal e a de reserva configuradas; nos testes, os provedores falsos dados."""
    configured = config.llm.configured
    if injected is not None:
        slots: tuple[Slot, ...] = ("primary", "fallback")
        return [
            Ai(
                slots[index],
                provider,
                configured[index][1] if index < len(configured) else LlmConfig(),
            )
            for index, provider in enumerate(injected[:2])
        ]
    ais = []
    for slot, llm in configured:
        provider = build_provider(llm)
        if provider is not None:
            ais.append(Ai(slot, provider, llm))
    return ais


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


async def _start_telemetry(
    config: ApiSettings,
    sink: TelemetrySink | None,
    analyzer: AnalyzerClient,
    *,
    production: bool,
) -> Telemetry:
    """Liga a telemetria (S21-01) quando há banco; nos testes, só com um ``sink`` injetado."""
    if sink is None and production and config.telemetry.enabled and config.database_url:
        sink = await PostgresTelemetrySink.connect(config.database_url)
    telemetry = Telemetry(sink, config.telemetry)
    telemetry.start()
    if telemetry.active:
        # A versão do ruleset também marca as recusas que acontecem antes de qualquer análise.
        try:
            telemetry.ruleset_version = (await analyzer.manifest()).ruleset_version
        except AnalyzerUnavailable:
            logger.info("telemetria: versão do ruleset fica para a primeira análise")
    return telemetry


def create_app(
    settings: ApiSettings | None = None,
    *,
    analyzer_transport: httpx2.AsyncBaseTransport | None = None,
    account_store: AccountStore | None = None,
    passwords: Passwords | None = None,
    email_sender: EmailSender | None = None,
    google_transport: httpx2.AsyncBaseTransport | None = None,
    llm_providers: Sequence[Provider] | None = None,
    telemetry_sink: TelemetrySink | None = None,
    gabaritos_transport: httpx2.AsyncBaseTransport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    """Os parâmetros depois de ``settings`` só existem para os testes: o analyzer em memória, um
    repositório de contas em memória, um Argon2 mais barato, um e-mail em memória e um relógio
    controlável."""
    config = settings or ApiSettings.from_env()
    config.check()
    if config.json_logs:
        configure_logging()
    hasher = passwords or Passwords()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = account_store or await _connect_store(config)
        client = AnalyzerClient(
            config.analyzer_url, config.analyzer_timeout_s, transport=analyzer_transport
        )
        gabaritos_task: asyncio.Task[None] | None = None
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
            app.state.accounts = AccountService(
                store,
                hasher,
                email_sender or email_sender_for(config.email),
                config.email,
                config.accounts,
                reserved_emails=config.developer.emails,
                throttle=LoginThrottle(max_keys=config.login_throttle.max_keys),
                clock=clock,
            )
            app.state.management = Management(store, clock=clock)
            app.state.feedback = FeedbackService(
                _ais(config, llm_providers),
                config.llm,
                config.feedback_limits,
                store=store,
                now=clock,
            )
            google_config = config.google
            app.state.google = google.GoogleLogin(
                oidc=GoogleOidc(google_config, transport=google_transport),
                accounts=GoogleAccounts(store, app.state.authenticator, clock=clock),
                flows=Expiring(google_config.flow_ttl_s),
                signups=Expiring(google_config.flow_ttl_s),
                redirect_uri=f"{config.accounts.public_base_url}/api/v1/auth/google/callback",
            )
            app.state.analyzer = client
            # Os gabaritos chegam em segundo plano (ADR-11): a API fica pronta sem esperar por eles.
            app.state.gabaritos = Gabaritos(
                status="loading" if config.gabaritos.enabled else "disabled"
            )
            gabaritos_task = asyncio.create_task(
                load_gabaritos(config.gabaritos, app.state.gabaritos, gabaritos_transport)
            )
            # O semáforo pertence ao laço de eventos que atende as requisições.
            app.state.admission = Admission(config.admission)
            app.state.telemetry = await _start_telemetry(
                config, telemetry_sink, client, production=account_store is None
            )
            app.state.adoption = Adoption(store)
            app.state.housekeeping = Housekeeping(store, config.housekeeping, clock=clock)
            app.state.housekeeping.start()
            yield
        finally:
            if gabaritos_task is not None and not gabaritos_task.done():
                gabaritos_task.cancel()
            adoption = getattr(app.state, "adoption", None)
            if adoption is not None:
                await adoption.drain()
            housekeeping = getattr(app.state, "housekeeping", None)
            if housekeeping is not None:
                await housekeeping.stop()
            telemetry = getattr(app.state, "telemetry", None)
            if telemetry is not None:
                await telemetry.stop()
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
    app.state.api_gate = FixedWindowCounter(max_keys=config.rate_limit.max_keys)
    app.state.slo = SloMonitor(config.slo)
    # O último middleware adicionado é o mais externo: o contexto (identificador, limite de
    # corpo e log) envolve os demais, e assim o 403 e o 429 também aparecem no log. A sessão vem
    # antes do limite de taxa, que conta por conta; o limite geral por IP vem antes da sessão.
    app.add_middleware(
        RateLimitMiddleware, config=config.rate_limit, limiter=app.state.rate_limiter
    )
    app.add_middleware(SessionMiddleware, cookie_name=config.session.cookie_name)
    app.add_middleware(ApiGateMiddleware, config=config.rate_limit, counter=app.state.api_gate)
    app.add_middleware(
        OriginCheckMiddleware,
        allowed_origins=(*config.allowed_origins, *config.cors_origins, config.page_origin),
    )
    # S30-03: no piloto, /api/* só pela página (segredo do middleware da Vercel).
    app.add_middleware(EdgeGateMiddleware, secret=config.edge_secret)
    app.add_middleware(
        RequestContextMiddleware, max_body_bytes=config.max_body_bytes, slo=app.state.slo
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=config.hsts)
    if config.cors_origins:
        # O mais externo: até um 413 ou um 429 precisa dos cabeçalhos CORS, ou o navegador
        # esconde a resposta da página e o aluno vê "falha de rede" no lugar do motivo.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_methods=["GET", "POST", "PATCH"],
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
        path = request.url.path
        message = (
            ADMIN_VALIDATION_MESSAGE
            if path.startswith("/api/v1/admin/")
            else VALIDATION_MESSAGES.get(path, "Requisição inválida: confira os campos enviados.")
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
    app.include_router(google.router)
    app.include_router(profile.router)
    app.include_router(admin.router)
    app.include_router(validate.router)
    app.include_router(similarity.router)
    app.include_router(feedback.router)
    app.include_router(meta.protected)
    app.include_router(meta.router)
    return app

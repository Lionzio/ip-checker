"""Serviço interno do analisador: ``POST /internal/analyze``, ``GET /internal/health`` (S5-01),
``GET /internal/ruleset/manifest`` (S8-01), ``POST /internal/similarity`` (S17-02) e
``POST /internal/feedback-input`` (S18-02).

Não tem documentação pública nem segredos e só deve ser alcançável pela API, numa rede interna
sem saída para a internet (NFR-07). A análise sempre acontece num worker do pool, nunca aqui.

Para rodar localmente::

    uv run uvicorn ipc_analyzer.service.app:create_app --factory --port 8001
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ipc_analyzer.engine.analysis import resolve_question
from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    InputError,
    PayloadTooLargeError,
    thousands,
)
from ipc_analyzer.engine.parse import require_runtime
from ipc_analyzer.engine.ruleset import (
    CompiledRuleset,
    LoadedRulesets,
    UnknownPeriod,
    load_rulesets,
)
from ipc_analyzer.logging import configure_logging
from ipc_analyzer.runtime.pool import AnalyzerPool, DeadlineExpired
from ipc_analyzer.service.access_log import AccessLogMiddleware
from ipc_analyzer.service.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClassRequest,
    ClassResponse,
    FeedbackInputResponse,
    HealthResponse,
    ListOut,
    ManifestResponse,
    MatrixRequest,
    MatrixResponse,
    PeriodOut,
    QuestionOut,
    SimilarityRequest,
    SimilarityResponse,
)
from ipc_analyzer.service.settings import AnalyzerSettings

logger = logging.getLogger(__name__)

#: Cabeçalho com o tempo, em milissegundos, que a API ainda espera pela resposta (S25-04).
BUDGET_HEADER = "X-IPC-Budget-Ms"
#: Um prazo acima disso é tratado como este (nenhuma análise dura tanto).
MAX_BUDGET_S = 60.0


def _deadline(request: Request) -> float | None:
    """Quando a API desiste deste pedido (``time.time``); ``None`` sem o cabeçalho."""
    raw = request.headers.get(BUDGET_HEADER)
    if raw is None:
        return None
    try:
        budget_s = int(raw) / 1000
    except ValueError:
        return None
    return time.time() + min(max(budget_s, 0.0), MAX_BUDGET_S)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _check_gabarito(gabarito: str | None) -> None:
    """O gabarito vem da API, que já limita o tamanho; um acima do limite é recusado do mesmo
    jeito que um código, sem citar o conteúdo."""
    if gabarito is None:
        return
    size = len(gabarito.encode("utf-8", errors="surrogatepass"))
    if size > DEFAULT_LIMITS.max_bytes:
        raise PayloadTooLargeError(
            f"O gabarito tem {thousands(size)} bytes; o limite é "
            f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
        )


def _pool(request: Request) -> AnalyzerPool:
    pool: AnalyzerPool = request.app.state.pool
    return pool


def _rulesets(request: Request) -> LoadedRulesets:
    rulesets: LoadedRulesets = request.app.state.rulesets
    return rulesets


def _lists(ruleset: CompiledRuleset) -> list[ListOut]:
    data = ruleset.ruleset
    return [
        ListOut(
            number=n,
            title=title,
            questions=[
                QuestionOut(id=q.id, title=q.question.title) for q in ruleset.questions_for(n)
            ],
        )
        for n, title in sorted(data.lists.items())
    ]


def create_app(settings: AnalyzerSettings | None = None) -> FastAPI:
    if (settings or AnalyzerSettings.from_env()).json_logs:
        configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings or AnalyzerSettings.from_env()
        # Fail-fast (FR-15, NFR-21): ruleset inválido ou Python errado impedem o serviço de subir.
        # O ativo e os anteriores da janela (S43-01); um inválido, de qualquer período, também.
        rulesets = load_rulesets(config.ruleset_path)
        for ruleset in rulesets.periods.values():
            require_runtime(ruleset.target_version)
        pool = AnalyzerPool(config.ruleset_path, config.pool)
        try:
            # Aquecimento: confirma que os workers carregam o ruleset e analisam antes de aceitar
            # requisições.
            await pool.analyze("x = 1\n", 1)
            app.state.rulesets = rulesets
            app.state.pool = pool
            yield
        finally:
            pool.close()

    app = FastAPI(
        title="IP-Checker analyzer (interno)",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(AccessLogMiddleware)

    @app.exception_handler(InputError)
    async def input_error(request: Request, exc: InputError) -> JSONResponse:
        request.state.outcome = exc.code
        status = 413 if isinstance(exc, PayloadTooLargeError) else 422
        return _error(status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
        request.state.outcome = "INVALID_INPUT"
        return _error(
            422,
            "INVALID_INPUT",
            "Requisição inválida: envie code, list_number (1 a 6) e, se houver, question_id.",
        )

    @app.exception_handler(UnknownPeriod)
    async def unknown_period(request: Request, exc: UnknownPeriod) -> JSONResponse:
        request.state.outcome = "UNKNOWN_PERIOD"
        loaded = ", ".join(exc.loaded)
        return _error(
            422,
            "UNKNOWN_PERIOD",
            f"O período {exc.period} não está carregado (carregados: {loaded}).",
        )

    @app.exception_handler(DeadlineExpired)
    async def deadline_expired(request: Request, _exc: DeadlineExpired) -> JSONResponse:
        # A API já desistiu: ninguém lê esta resposta, mas o log mostra a fila vencida.
        request.state.outcome = "DEADLINE_EXCEEDED"
        logger.warning("pedido descartado: o prazo da API venceu antes do fim da análise")
        return _error(503, "DEADLINE_EXCEEDED", "O prazo de quem pediu a análise venceu.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Response:
        # O FastAPI responde 400 genérico quando o corpo não é UTF-8 válido (DoD, item 3).
        if exc.status_code == 400:
            request.state.outcome = "INVALID_INPUT"
            return _error(422, "INVALID_INPUT", "O corpo da requisição não é JSON em UTF-8 válido.")
        return await http_exception_handler(request, exc)

    @app.post("/internal/analyze")
    async def analyze(
        body: AnalyzeRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        rulesets: Annotated[LoadedRulesets, Depends(_rulesets)],
    ) -> AnalyzeResponse:
        ruleset = rulesets.get(body.period)
        # Recusa cedo um texto que não cabe no limite, sem enviá-lo a um worker.
        size = len(body.code.encode("utf-8", errors="surrogatepass"))
        request.state.payload_bytes = size
        request.state.list_number = body.list_number
        request.state.ruleset_version = ruleset.version
        if size > DEFAULT_LIMITS.max_bytes:
            raise PayloadTooLargeError(
                f"O código tem {thousands(size)} bytes; o limite é "
                f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
            )
        _check_gabarito(body.gabarito)
        # A questão é conferida aqui, antes do worker: uma questão inexistente nem entra na fila.
        resolve_question(ruleset, body.list_number, body.question_id)
        result = await pool.analyze(
            body.code,
            body.list_number,
            body.question_id,
            deadline=_deadline(request),
            indicators=body.indicators,
            gabarito=body.gabarito,
            period=ruleset.ruleset.period,
        )
        request.state.outcome = result.status
        request.state.violations = len(result.violations)
        return AnalyzeResponse.from_result(result)

    @app.post("/internal/feedback-input")
    async def feedback_input(
        body: AnalyzeRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        rulesets: Annotated[LoadedRulesets, Depends(_rulesets)],
    ) -> FeedbackInputResponse:
        ruleset = rulesets.get(body.period)
        size = len(body.code.encode("utf-8", errors="surrogatepass"))
        request.state.payload_bytes = size
        request.state.list_number = body.list_number
        if size > DEFAULT_LIMITS.max_bytes:
            raise PayloadTooLargeError(
                f"O código tem {thousands(size)} bytes; o limite é "
                f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
            )
        resolve_question(ruleset, body.list_number, body.question_id)
        data = await pool.feedback_input(
            body.code,
            body.list_number,
            body.question_id,
            deadline=_deadline(request),
            period=ruleset.ruleset.period,
        )
        request.state.outcome = data.status
        return FeedbackInputResponse.from_input(data)

    @app.post("/internal/similarity")
    async def similarity(
        body: SimilarityRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        rulesets: Annotated[LoadedRulesets, Depends(_rulesets)],
    ) -> SimilarityResponse:
        period = rulesets.get(body.period).ruleset.period
        sizes = [
            len(code.encode("utf-8", errors="surrogatepass")) for code in (body.first, body.second)
        ]
        request.state.payload_bytes = sum(sizes)
        for label, size in zip("AB", sizes, strict=True):
            if size > DEFAULT_LIMITS.max_bytes:
                raise PayloadTooLargeError(
                    f"Código {label}: o código tem {thousands(size)} bytes; o limite é "
                    f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
                )
        _check_gabarito(body.gabarito)
        result, gabarito = await pool.compare(
            body.first,
            body.second,
            deadline=_deadline(request),
            gabarito=body.gabarito,
            period=period,
        )
        response = SimilarityResponse.from_result(result, gabarito)
        request.state.outcome = response.status
        return response

    @app.post("/internal/similarity/class")
    async def similarity_class(
        body: ClassRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
    ) -> ClassResponse:
        codes = [body.code, *body.others]
        request.state.payload_bytes = sum(
            len(code.encode("utf-8", errors="surrogatepass")) for code in codes
        )
        result = await pool.compare_class(body.code, body.others, deadline=_deadline(request))
        response = ClassResponse.from_result(result)
        request.state.outcome = response.status
        return response

    @app.post("/internal/similarity/matrix")
    async def similarity_matrix(
        body: MatrixRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
    ) -> MatrixResponse:
        request.state.payload_bytes = sum(
            len(code.encode("utf-8", errors="surrogatepass")) for code in body.codes
        )
        result = await pool.compare_all(body.codes, body.group_min, deadline=_deadline(request))
        request.state.outcome = "compared"
        return MatrixResponse.from_result(result)

    @app.get("/internal/ruleset/manifest")
    async def manifest(
        rulesets: Annotated[LoadedRulesets, Depends(_rulesets)],
    ) -> ManifestResponse:
        ruleset = rulesets.active_ruleset
        data = ruleset.ruleset
        return ManifestResponse(
            ruleset_version=data.ruleset_version,
            ruleset_sha256=ruleset.sha256,
            period=data.period,
            target_python=data.target_python,
            lists=_lists(ruleset),
            periods=[
                PeriodOut(
                    period=period,
                    active=period == rulesets.active,
                    ruleset_version=item.version,
                    ruleset_sha256=item.sha256,
                    lists=_lists(item),
                )
                for period, item in rulesets.periods.items()
            ],
        )

    @app.get("/internal/health", response_model=None)
    async def health(
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        rulesets: Annotated[LoadedRulesets, Depends(_rulesets)],
    ) -> JSONResponse:
        ruleset = rulesets.active_ruleset
        if not pool.active:
            return _error(503, "ANALYZER_UNAVAILABLE", "O pool de workers não está ativo.")
        body = HealthResponse(
            status="ok",
            ruleset_version=ruleset.version,
            ruleset_sha256=ruleset.sha256,
            target_python=ruleset.ruleset.target_python,
            workers=pool.config.workers,
        )
        return JSONResponse(body.model_dump())

    return app

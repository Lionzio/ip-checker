"""Serviço interno do analisador: ``POST /internal/analyze``, ``GET /internal/health`` (S5-01),
``GET /internal/ruleset/manifest`` (S8-01), ``POST /internal/similarity`` (S17-02) e
``POST /internal/feedback-input`` (S18-02).

Não tem documentação pública nem segredos e só deve ser alcançável pela API, numa rede interna
sem saída para a internet (NFR-07). A análise sempre acontece num worker do pool, nunca aqui.

Para rodar localmente::

    uv run uvicorn ipc_analyzer.service.app:create_app --factory --port 8001
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from ipc_analyzer.engine.feedback import FeedbackInput
from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    InputError,
    PayloadTooLargeError,
    thousands,
)
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import require_runtime
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from ipc_analyzer.engine.similarity import InvalidSide, Similarity
from ipc_analyzer.logging import configure_logging
from ipc_analyzer.runtime.pool import AnalyzerPool
from ipc_analyzer.service.access_log import AccessLogMiddleware
from ipc_analyzer.service.settings import AnalyzerSettings


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    list_number: int = Field(ge=1, le=6)


class ViolationOut(BaseModel):
    rule_id: str
    category: str
    line: int
    col: int
    end_line: int
    end_col: int
    # "construct" colide com um método do BaseModel; o nome no JSON continua sendo construct.
    construct_name: str = Field(serialization_alias="construct")
    allowed_from_list: int | None
    message: str


class SyntaxErrorOut(BaseModel):
    line: int
    col: int
    message: str


class AnalyzeResponse(BaseModel):
    ruleset_version: str
    status: Literal["valid", "invalid", "syntax_error"]
    list_number: int
    syntax_error: SyntaxErrorOut | None
    violations: list[ViolationOut]
    truncated: bool

    @classmethod
    def from_result(cls, result: AnalysisResult) -> AnalyzeResponse:
        problem = result.syntax_error
        return cls(
            ruleset_version=result.ruleset_version,
            status=result.status,
            list_number=result.list_number,
            syntax_error=(
                SyntaxErrorOut(line=problem.line, col=problem.col, message=problem.message)
                if problem is not None
                else None
            ),
            violations=[
                ViolationOut(
                    rule_id=v.rule_id,
                    category=v.category.value,
                    line=v.line,
                    col=v.col,
                    end_line=v.end_line,
                    end_col=v.end_col,
                    construct_name=v.construct,
                    allowed_from_list=v.allowed_from_list,
                    message=v.message,
                )
                for v in result.violations
            ],
            truncated=result.truncated,
        )


class SimilarityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first: str
    second: str


class SimilarityResponse(BaseModel):
    """Plágio (S17-02): a porcentagem, ou qual dos dois códigos tem erro de sintaxe."""

    status: Literal["compared", "syntax_error"]
    percent: float | None
    token_counts: list[int] | None
    syntax_error_side: Literal[1, 2] | None
    syntax_error: SyntaxErrorOut | None

    @classmethod
    def from_result(cls, result: Similarity | InvalidSide) -> SimilarityResponse:
        if isinstance(result, InvalidSide):
            problem = result.problem
            return cls(
                status="syntax_error",
                percent=None,
                token_counts=None,
                syntax_error_side=1 if result.side == 1 else 2,
                syntax_error=SyntaxErrorOut(
                    line=problem.line, col=problem.col, message=problem.message
                ),
            )
        return cls(
            status="compared",
            percent=result.percent,
            token_counts=list(result.token_counts),
            syntax_error_side=None,
            syntax_error=None,
        )


class FeedbackItemOut(BaseModel):
    kind: Literal["uso", "falta"]
    label: str


class FeedbackInputResponse(BaseModel):
    """Feedback (S18-02): o que o motor encontrou, pelos nomes legíveis, e o código sem
    comentários, que é o único texto do aluno que pode ir ao provedor de LLM."""

    status: Literal["valid", "invalid", "syntax_error"]
    items: list[FeedbackItemOut]
    code: str
    syntax_error: SyntaxErrorOut | None

    @classmethod
    def from_input(cls, data: FeedbackInput) -> FeedbackInputResponse:
        problem = data.syntax_error
        return cls(
            status=data.status,
            items=[FeedbackItemOut(kind=item.kind, label=item.label) for item in data.items],
            code=data.code,
            syntax_error=(
                SyntaxErrorOut(line=problem.line, col=problem.col, message=problem.message)
                if problem is not None
                else None
            ),
        )


class ListOut(BaseModel):
    number: int
    title: str


class ManifestResponse(BaseModel):
    """O que a API precisa saber do ruleset ativo sem carregá-lo (ela nunca lê regras)."""

    ruleset_version: str
    ruleset_sha256: str
    period: str
    target_python: str
    lists: list[ListOut]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    ruleset_version: str
    ruleset_sha256: str
    target_python: str
    workers: int


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _pool(request: Request) -> AnalyzerPool:
    pool: AnalyzerPool = request.app.state.pool
    return pool


def _ruleset(request: Request) -> CompiledRuleset:
    ruleset: CompiledRuleset = request.app.state.ruleset
    return ruleset


def create_app(settings: AnalyzerSettings | None = None) -> FastAPI:
    if (settings or AnalyzerSettings.from_env()).json_logs:
        configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config = settings or AnalyzerSettings.from_env()
        # Fail-fast (FR-15, NFR-21): ruleset inválido ou Python errado impedem o serviço de subir.
        ruleset = load_ruleset(config.ruleset_path)
        require_runtime(ruleset.target_version)
        pool = AnalyzerPool(config.ruleset_path, config.pool)
        try:
            # Aquecimento: confirma que os workers carregam o ruleset e analisam antes de aceitar
            # requisições.
            await pool.analyze("x = 1\n", 1)
            app.state.ruleset = ruleset
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
            422, "INVALID_INPUT", "Requisição inválida: envie code e list_number (1 a 6)."
        )

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
        ruleset: Annotated[CompiledRuleset, Depends(_ruleset)],
    ) -> AnalyzeResponse:
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
        result = await pool.analyze(body.code, body.list_number)
        request.state.outcome = result.status
        request.state.violations = len(result.violations)
        return AnalyzeResponse.from_result(result)

    @app.post("/internal/feedback-input")
    async def feedback_input(
        body: AnalyzeRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
    ) -> FeedbackInputResponse:
        size = len(body.code.encode("utf-8", errors="surrogatepass"))
        request.state.payload_bytes = size
        request.state.list_number = body.list_number
        if size > DEFAULT_LIMITS.max_bytes:
            raise PayloadTooLargeError(
                f"O código tem {thousands(size)} bytes; o limite é "
                f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
            )
        data = await pool.feedback_input(body.code, body.list_number)
        request.state.outcome = data.status
        return FeedbackInputResponse.from_input(data)

    @app.post("/internal/similarity")
    async def similarity(
        body: SimilarityRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
    ) -> SimilarityResponse:
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
        result = await pool.compare(body.first, body.second)
        response = SimilarityResponse.from_result(result)
        request.state.outcome = response.status
        return response

    @app.get("/internal/ruleset/manifest")
    async def manifest(
        ruleset: Annotated[CompiledRuleset, Depends(_ruleset)],
    ) -> ManifestResponse:
        data = ruleset.ruleset
        return ManifestResponse(
            ruleset_version=data.ruleset_version,
            ruleset_sha256=ruleset.sha256,
            period=data.period,
            target_python=data.target_python,
            lists=[ListOut(number=n, title=title) for n, title in sorted(data.lists.items())],
        )

    @app.get("/internal/health", response_model=None)
    async def health(
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        ruleset: Annotated[CompiledRuleset, Depends(_ruleset)],
    ) -> JSONResponse:
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

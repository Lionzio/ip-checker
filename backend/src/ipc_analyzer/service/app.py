"""Serviço interno do analisador (S5-01): ``POST /internal/analyze`` e ``GET /internal/health``.

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

from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    InputError,
    PayloadTooLargeError,
    thousands,
)
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import require_runtime
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from ipc_analyzer.runtime.pool import AnalyzerPool
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

    @app.exception_handler(InputError)
    async def input_error(_request: Request, exc: InputError) -> JSONResponse:
        status = 413 if isinstance(exc, PayloadTooLargeError) else 422
        return _error(status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return _error(
            422, "INVALID_INPUT", "Requisição inválida: envie code e list_number (1 a 6)."
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Response:
        # O FastAPI responde 400 genérico quando o corpo não é UTF-8 válido (DoD, item 3).
        if exc.status_code == 400:
            return _error(422, "INVALID_INPUT", "O corpo da requisição não é JSON em UTF-8 válido.")
        return await http_exception_handler(request, exc)

    @app.post("/internal/analyze")
    async def analyze(
        body: AnalyzeRequest, pool: Annotated[AnalyzerPool, Depends(_pool)]
    ) -> AnalyzeResponse:
        # Recusa cedo um texto que não cabe no limite, sem enviá-lo a um worker.
        size = len(body.code.encode("utf-8", errors="surrogatepass"))
        if size > DEFAULT_LIMITS.max_bytes:
            raise PayloadTooLargeError(
                f"O código tem {thousands(size)} bytes; o limite é "
                f"{thousands(DEFAULT_LIMITS.max_bytes)} bytes (50 KB)."
            )
        result = await pool.analyze(body.code, body.list_number)
        return AnalyzeResponse.from_result(result)

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

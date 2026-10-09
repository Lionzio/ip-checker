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
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException

from ipc_analyzer.engine.analysis import resolve_question
from ipc_analyzer.engine.feedback import FeedbackInput
from ipc_analyzer.engine.gabarito import GabaritoComparison
from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    InputError,
    PayloadTooLargeError,
    thousands,
)
from ipc_analyzer.engine.indicators import Indicators, LevelName, Signal
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import SyntaxProblem, require_runtime
from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset
from ipc_analyzer.engine.similarity import (
    MAX_CLASS,
    ClassMatch,
    ClassRejected,
    InvalidSide,
    Similarity,
)
from ipc_analyzer.engine.similarity_tree import TreeScores
from ipc_analyzer.logging import configure_logging
from ipc_analyzer.runtime.pool import AnalyzerPool, DeadlineExpired
from ipc_analyzer.service.access_log import AccessLogMiddleware
from ipc_analyzer.service.settings import AnalyzerSettings


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    list_number: int = Field(ge=1, le=6)
    #: Questão do período (R-01), como L3-Q2; sem ela, valem só as regras da lista.
    question_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,32}$")
    #: Calcula também os indícios de uso de IA (ADR-08); a API só pede quando estão ligados.
    indicators: bool = False
    #: O gabarito oficial da questão (ADR-11), vindo da memória da API; nunca volta na resposta.
    gabarito: str | None = None


class IndicatorOut(BaseModel):
    signal: Signal
    kind: str
    level: LevelName | None
    reason: str
    lines: list[int]


class IndicatorsOut(BaseModel):
    """Indícios de uso de IA (ADR-08, S29-01): nunca veredito, só para a equipe."""

    level: LevelName | None
    items: list[IndicatorOut]
    questions: list[str]

    @classmethod
    def of(cls, indicators: Indicators) -> IndicatorsOut:
        return cls(
            level=None if indicators.level is None else indicators.level.label,
            items=[
                IndicatorOut(
                    signal=item.signal,
                    kind=item.kind,
                    level=None if item.level is None else item.level.label,
                    reason=item.reason,
                    lines=list(item.lines),
                )
                for item in indicators.items
            ],
            questions=list(indicators.questions),
        )


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


class LinesOut(BaseModel):
    first: int
    last: int


class GabaritoOut(BaseModel):
    """Comparação com o gabarito (ADR-11): só nomes de construções e linhas do aluno."""

    percent: float
    token_counts: list[int]
    common: list[str]
    only_student: list[str]
    only_gabarito: list[str]
    student_lines: list[LinesOut]

    @classmethod
    def of(cls, comparison: GabaritoComparison) -> GabaritoOut:
        return cls(
            percent=comparison.percent,
            token_counts=list(comparison.token_counts),
            common=list(comparison.common),
            only_student=list(comparison.only_student),
            only_gabarito=list(comparison.only_gabarito),
            student_lines=[
                LinesOut(first=first, last=last) for first, last in comparison.student_lines
            ],
        )


class AnalyzeResponse(BaseModel):
    ruleset_version: str
    status: Literal["valid", "invalid", "syntax_error"]
    list_number: int
    syntax_error: SyntaxErrorOut | None
    violations: list[ViolationOut]
    truncated: bool
    indicators: IndicatorsOut | None = None
    gabarito: GabaritoOut | None = None

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
            indicators=(
                IndicatorsOut.of(result.indicators) if result.indicators is not None else None
            ),
            gabarito=GabaritoOut.of(result.gabarito) if result.gabarito is not None else None,
        )


class SimilarityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first: str
    second: str
    #: O gabarito da questão (ADR-11): cada código é comparado também com ele.
    gabarito: str | None = None


class MetricsOut(BaseModel):
    """As métricas por trás da porcentagem (S27-01), de 0 a 100, com uma casa."""

    sequence: float | None
    tree_dice: float
    tree_containment: float

    @classmethod
    def of(cls, sequence: float | None, tree: TreeScores) -> MetricsOut:
        return cls(
            sequence=None if sequence is None else round(100 * sequence, 1),
            tree_dice=round(100 * tree.dice, 1),
            tree_containment=round(100 * tree.containment, 1),
        )


class MatchOut(BaseModel):
    """Um trecho do código A com a mesma estrutura de um trecho do código B (S27-03)."""

    a_first: int
    a_last: int
    b_first: int
    b_last: int


class SimilarityResponse(BaseModel):
    """Plágio (S17-02): a porcentagem, ou qual dos dois códigos tem erro de sintaxe."""

    status: Literal["compared", "syntax_error"]
    percent: float | None
    token_counts: list[int] | None
    syntax_error_side: Literal[1, 2] | None
    syntax_error: SyntaxErrorOut | None
    metrics: MetricsOut | None = None
    matches: list[MatchOut] = []
    #: Com o gabarito: a semelhança de A e de B com ele, na ordem (ADR-11, item 5).
    gabarito: list[GabaritoOut | None] | None = None

    @classmethod
    def from_result(
        cls,
        result: Similarity | InvalidSide,
        gabarito: tuple[GabaritoComparison | None, ...] = (),
    ) -> SimilarityResponse:
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
            metrics=MetricsOut.of(result.sequence_score, result.tree),
            matches=[
                MatchOut(a_first=m.a.first, a_last=m.a.last, b_first=m.b.first, b_last=m.b.last)
                for m in result.matches
            ],
            gabarito=(
                [None if item is None else GabaritoOut.of(item) for item in gabarito]
                if gabarito
                else None
            ),
        )


class ClassRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    others: list[str] = Field(min_length=1, max_length=MAX_CLASS)


class ClassItemOut(BaseModel):
    status: Literal["compared", "syntax_error", "rejected"]
    percent: float | None = None
    token_count: int | None = None
    metrics: MetricsOut | None = None
    syntax_error: SyntaxErrorOut | None = None
    message: str | None = None


class ClassResponse(BaseModel):
    """Uma solução contra a turma (S27-02): um item por solução da turma, na ordem enviada."""

    status: Literal["compared", "syntax_error"]
    syntax_error: SyntaxErrorOut | None
    results: list[ClassItemOut]

    @classmethod
    def from_result(
        cls, result: SyntaxProblem | list[ClassMatch | SyntaxProblem | ClassRejected]
    ) -> ClassResponse:
        if isinstance(result, SyntaxProblem):
            problem = SyntaxErrorOut(line=result.line, col=result.col, message=result.message)
            return cls(status="syntax_error", syntax_error=problem, results=[])
        items: list[ClassItemOut] = []
        for item in result:
            if isinstance(item, SyntaxProblem):
                problem = SyntaxErrorOut(line=item.line, col=item.col, message=item.message)
                items.append(ClassItemOut(status="syntax_error", syntax_error=problem))
            elif isinstance(item, ClassRejected):
                items.append(ClassItemOut(status="rejected", message=item.message))
            else:
                items.append(
                    ClassItemOut(
                        status="compared",
                        percent=item.percent,
                        token_count=item.token_count,
                        metrics=MetricsOut.of(None, item.tree),
                    )
                )
        return cls(status="compared", syntax_error=None, results=items)


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


class QuestionOut(BaseModel):
    id: str
    title: str


class ListOut(BaseModel):
    number: int
    title: str
    #: Questões com regra específica cadastrada no período (R-01), em ordem.
    questions: list[QuestionOut] = []


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
            422,
            "INVALID_INPUT",
            "Requisição inválida: envie code, list_number (1 a 6) e, se houver, question_id.",
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
        )
        request.state.outcome = result.status
        request.state.violations = len(result.violations)
        return AnalyzeResponse.from_result(result)

    @app.post("/internal/feedback-input")
    async def feedback_input(
        body: AnalyzeRequest,
        request: Request,
        pool: Annotated[AnalyzerPool, Depends(_pool)],
        ruleset: Annotated[CompiledRuleset, Depends(_ruleset)],
    ) -> FeedbackInputResponse:
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
            body.code, body.list_number, body.question_id, deadline=_deadline(request)
        )
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
        _check_gabarito(body.gabarito)
        result, gabarito = await pool.compare(
            body.first, body.second, deadline=_deadline(request), gabarito=body.gabarito
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
            lists=[
                ListOut(
                    number=n,
                    title=title,
                    questions=[
                        QuestionOut(id=q.id, title=q.question.title)
                        for q in ruleset.questions_for(n)
                    ],
                )
                for n, title in sorted(data.lists.items())
            ],
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

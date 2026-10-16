"""Os modelos de entrada e saída da API interna do analisador (S5-01 em diante).

Só o contrato: o que cada rota recebe e devolve. As rotas estão em ``app.py`` (S39-02).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ipc_analyzer.engine.feedback import FeedbackInput
from ipc_analyzer.engine.gabarito import GabaritoComparison
from ipc_analyzer.engine.indicators import Indicators, LevelName, Signal
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.similarity import (
    MAX_CLASS,
    MAX_MATRIX,
    ClassMatch,
    ClassRejected,
    InvalidSide,
    MatrixResult,
    Similarity,
)
from ipc_analyzer.engine.similarity_tree import TreeScores


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
    #: O período das regras (S43-01), como 2026.2; sem ele, vale o ativo.
    period: str | None = Field(default=None, pattern=r"^\d{4}\.[12]$")


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
    explanation: str
    alternative: str


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
                    explanation=v.explanation,
                    alternative=v.alternative,
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
    #: O período das regras (S43-01), como 2026.2; sem ele, vale o ativo.
    period: str | None = Field(default=None, pattern=r"^\d{4}\.[12]$")


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


class MatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codes: list[str] = Field(min_length=2, max_length=MAX_MATRIX)
    #: A partir de quanto um par liga duas soluções num grupo (a faixa "Requer atenção", S40-02).
    group_min: float = Field(ge=0, le=100)


class MatrixSolutionOut(BaseModel):
    status: Literal["compared", "syntax_error", "rejected"]
    syntax_error: SyntaxErrorOut | None = None
    message: str | None = None


class MatrixPairOut(BaseModel):
    first: int
    second: int
    percent: float


#: Os pares que voltam à API: os mais parecidos, que é o que a tela mostra (S40-02).
MAX_MATRIX_PAIRS = 300


class MatrixResponse(BaseModel):
    """Todos contra todos (S40-02): cada solução, os pares mais parecidos e os grupos."""

    solutions: list[MatrixSolutionOut]
    pairs: list[MatrixPairOut]
    groups: list[list[int]]

    @classmethod
    def from_result(cls, result: MatrixResult) -> MatrixResponse:
        solutions = []
        for problem in result.problems:
            if problem is None:
                solutions.append(MatrixSolutionOut(status="compared"))
            elif isinstance(problem, ClassRejected):
                solutions.append(MatrixSolutionOut(status="rejected", message=problem.message))
            else:
                where = SyntaxErrorOut(line=problem.line, col=problem.col, message=problem.message)
                solutions.append(MatrixSolutionOut(status="syntax_error", syntax_error=where))
        return cls(
            solutions=solutions,
            pairs=[
                MatrixPairOut(first=pair.first, second=pair.second, percent=pair.percent)
                for pair in result.pairs[:MAX_MATRIX_PAIRS]
            ],
            groups=[list(group) for group in result.groups],
        )


class FeedbackItemOut(BaseModel):
    kind: Literal["uso", "falta"]
    label: str
    alternative: str


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
            items=[
                FeedbackItemOut(kind=item.kind, label=item.label, alternative=item.alternative)
                for item in data.items
            ],
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


class PeriodOut(BaseModel):
    """Um período carregado (S43-01): a versão, as listas e as questões dele."""

    period: str
    active: bool
    ruleset_version: str
    ruleset_sha256: str
    lists: list[ListOut]


class ManifestResponse(BaseModel):
    """O que a API precisa saber dos rulesets sem carregá-los (ela nunca lê regras). Os campos de
    cima são os do período ativo, como antes; ``periods`` traz todos os carregados (S43-01)."""

    ruleset_version: str
    ruleset_sha256: str
    period: str
    target_python: str
    lists: list[ListOut]
    periods: list[PeriodOut]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    ruleset_version: str
    ruleset_sha256: str
    target_python: str
    workers: int

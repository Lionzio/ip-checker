"""As respostas do analyzer, pela rede interna, validadas com rigor (``extra="forbid"``, limites
e coerência entre os campos) antes de qualquer dado chegar à página (TB-3, ameaça 2).

Parte do contrato da API (5.2.2), dividido em módulos na S39-02; importe de ``ipc_api.schemas``.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from .common import (
    MAX_VIOLATIONS,
    ListNumber,
    Message,
    Percent,
    Position,
    RulesetVersion,
    Status,
    SyntaxErrorInfo,
    _Strict,
)
from .responses import AnalyzerIndicators, Construct, ListInfo, Violation
from .verify import SimilarityMatch, SimilarityMetrics

# ---------------------------------------------------------------------------------------------
# Respostas do analyzer (rede interna)
# ---------------------------------------------------------------------------------------------


class AnalyzerFeedbackItem(_Strict):
    kind: Literal["uso", "falta"]
    label: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    #: O que usar no lugar (S38-02); vazio com um analisador anterior à Sprint 38.
    alternative: Annotated[str, StringConstraints(max_length=1000)] = ""


class AnalyzerFeedbackInput(_Strict):
    status: Literal["valid", "invalid", "syntax_error"]
    items: list[AnalyzerFeedbackItem] = Field(max_length=MAX_VIOLATIONS)
    code: Annotated[str, StringConstraints(max_length=60_000)]
    syntax_error: SyntaxErrorInfo | None

    @model_validator(mode="after")
    def _status_matches_content(self) -> Self:
        broken = self.status == "syntax_error"
        if broken != (self.syntax_error is not None) or (
            (self.status == "valid") == bool(self.items) and not broken
        ):
            raise ValueError(f"status {self.status!r} incoerente com o conteúdo da resposta")
        return self


class AnalyzerLines(_Strict):
    first: Position
    last: Position


class AnalyzerGabarito(_Strict):
    percent: Percent
    token_counts: list[Annotated[int, Field(ge=0)]] = Field(min_length=2, max_length=2)
    common: list[Construct] = Field(max_length=30)
    only_student: list[Construct] = Field(max_length=30)
    only_gabarito: list[Construct] = Field(max_length=30)
    student_lines: list[AnalyzerLines] = Field(max_length=100)


class AnalyzerSimilarity(_Strict):
    status: Literal["compared", "syntax_error"]
    percent: float | None = Field(ge=0, le=100)
    token_counts: list[Annotated[int, Field(ge=0)]] | None = Field(min_length=2, max_length=2)
    syntax_error_side: Literal[1, 2] | None
    syntax_error: SyntaxErrorInfo | None
    metrics: SimilarityMetrics | None = None
    matches: list[SimilarityMatch] = Field(default_factory=list, max_length=100)
    gabarito: list[AnalyzerGabarito | None] | None = Field(default=None, max_length=2)

    @model_validator(mode="after")
    def _status_matches_content(self) -> Self:
        compared = self.percent is not None and self.token_counts is not None
        broken = self.syntax_error is not None and self.syntax_error_side is not None
        if (self.status == "compared") != (compared and not broken) or (
            self.status == "syntax_error"
        ) != (broken and not compared):
            raise ValueError(f"status {self.status!r} incoerente com o conteúdo da resposta")
        return self


class AnalyzerClassItem(_Strict):
    status: Literal["compared", "syntax_error", "rejected"]
    percent: Percent | None = None
    token_count: Annotated[int, Field(ge=0)] | None = None
    metrics: SimilarityMetrics | None = None
    syntax_error: SyntaxErrorInfo | None = None
    message: Annotated[str, StringConstraints(max_length=500)] | None = None

    @model_validator(mode="after")
    def _status_matches_content(self) -> Self:
        expected = {
            "compared": self.percent is not None and self.token_count is not None,
            "syntax_error": self.syntax_error is not None,
            "rejected": self.message is not None,
        }
        if not expected[self.status]:
            raise ValueError(f"status {self.status!r} incoerente com o conteúdo do item")
        return self


class AnalyzerClass(_Strict):
    status: Literal["compared", "syntax_error"]
    syntax_error: SyntaxErrorInfo | None
    results: list[AnalyzerClassItem] = Field(max_length=100)


class AnalyzerMatrixSolution(_Strict):
    status: Literal["compared", "syntax_error", "rejected"]
    syntax_error: SyntaxErrorInfo | None = None
    message: Annotated[str, StringConstraints(max_length=500)] | None = None


class AnalyzerMatrixPair(_Strict):
    first: Annotated[int, Field(ge=0)]
    second: Annotated[int, Field(ge=0)]
    percent: Percent


class AnalyzerMatrix(_Strict):
    solutions: list[AnalyzerMatrixSolution] = Field(max_length=60)
    pairs: list[AnalyzerMatrixPair] = Field(max_length=300)
    groups: list[list[Annotated[int, Field(ge=0)]]] = Field(max_length=30)


class AnalyzerResult(_Strict):
    ruleset_version: RulesetVersion
    status: Status
    list_number: ListNumber
    syntax_error: SyntaxErrorInfo | None
    violations: list[Violation] = Field(max_length=MAX_VIOLATIONS)
    truncated: bool
    indicators: AnalyzerIndicators | None = None
    gabarito: AnalyzerGabarito | None = None

    @model_validator(mode="after")
    def _status_matches_content(self) -> Self:
        expected = {
            "valid": self.syntax_error is None and not self.violations,
            "invalid": self.syntax_error is None and bool(self.violations),
            "syntax_error": self.syntax_error is not None and not self.violations,
        }
        if not expected[self.status]:
            raise ValueError(f"status {self.status!r} incoerente com o conteúdo da resposta")
        return self


class AnalyzerErrorDetail(_Strict):
    code: Literal["PAYLOAD_TOO_LARGE", "INVALID_INPUT", "ANALYSIS_LIMIT"]
    message: Message


class AnalyzerErrorResponse(_Strict):
    error: AnalyzerErrorDetail


class AnalyzerPeriod(_Strict):
    """Um período carregado no analisador (S43-01)."""

    period: Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]$")]
    active: bool
    ruleset_version: RulesetVersion
    ruleset_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    lists: list[ListInfo] = Field(max_length=6)


class AnalyzerManifest(_Strict):
    ruleset_version: RulesetVersion
    ruleset_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    period: Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]$")]
    target_python: str
    lists: list[ListInfo] = Field(max_length=6)
    #: Todos os períodos carregados, o ativo e até 5 anteriores (S43-01; ADR-12, Q-34).
    periods: list[AnalyzerPeriod] = Field(default_factory=list, max_length=6)


class AnalyzerHealth(_Strict):
    status: Literal["ok"]
    ruleset_version: RulesetVersion
    ruleset_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    target_python: str
    workers: Annotated[int, Field(ge=1)]

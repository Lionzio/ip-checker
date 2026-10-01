"""Modelos do contrato público (5.2.2) e das respostas do analyzer.

As respostas do analyzer são validadas com rigor (``extra="forbid"``, limites e coerência entre
os campos) antes de qualquer dado chegar ao aluno: a API trata o analyzer como um processo que
pode ter sido comprometido por uma submissão (TB-3, ameaça 2).
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ipc_api.errors import ErrorCode

Category = Literal["ANULACAO", "PROIBIDO_NA_QUESTAO", "FORA_DA_LISTA", "NAO_CONSTA", "EXIGENCIA"]
Status = Literal["valid", "invalid", "syntax_error"]
Notice = Literal["QUESTION_RULES_NOT_APPLIED"]
ListNumber = Annotated[int, Field(ge=1, le=6)]
Position = Annotated[int, Field(ge=1, le=1_000_000)]
Message = Annotated[str, StringConstraints(min_length=1, max_length=1_000)]
RulesetVersion = Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]\.\d+$")]

#: Mesmo teto do analyzer: ele nunca devolve mais violações que isso.
MAX_VIOLATIONS = 200


class _Strict(BaseModel):
    # strict: "1" ou true não viram o número 1; o contrato pede inteiros de verdade.
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


# ---------------------------------------------------------------------------------------------
# Contrato público
# ---------------------------------------------------------------------------------------------


class ValidateRequest(_Strict):
    code: str = Field(description="Código Python do aluno. Nunca é executado.")
    list_number: ListNumber = Field(description="Lista de exercícios (1 a 6).")
    question_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")] | None = Field(
        default=None, description="Questão, como L3-Q2. Sem questão, valem só as regras da lista."
    )


class Violation(_Strict):
    rule_id: Annotated[str, StringConstraints(pattern=r"^R-\d{2}$")]
    category: Category
    line: Position
    col: Position
    end_line: Position
    end_col: Position
    # "construct" colide com um método do BaseModel; no JSON (entrada e saída) o nome é construct.
    construct_name: Annotated[str, StringConstraints(min_length=1, max_length=200)] = Field(
        alias="construct"
    )
    allowed_from_list: ListNumber | None
    message: Message


class SyntaxErrorInfo(_Strict):
    line: Position
    col: Position
    message: Message


class ValidateResponse(_Strict):
    request_id: str = Field(
        description="Identificador da requisição (ULID), também no X-Request-Id."
    )
    ruleset_version: RulesetVersion
    status: Status
    list_number: ListNumber
    question_id: str | None
    notices: list[Notice]
    syntax_error: SyntaxErrorInfo | None
    violations: list[Violation]
    truncated: bool = Field(description="Verdadeiro quando havia mais de 200 violações.")


class ListInfo(_Strict):
    number: ListNumber
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class ErrorDetail(_Strict):
    code: ErrorCode
    message: str
    retry_after_s: int | None


class ErrorResponse(_Strict):
    error: ErrorDetail


class HealthResponse(_Strict):
    status: Literal["ok"]


class ReadyResponse(_Strict):
    status: Literal["ready"]
    ruleset_version: RulesetVersion
    release: str | None = Field(
        default=None, description="Commit implantado, quando informado pelo ambiente."
    )


# ---------------------------------------------------------------------------------------------
# Respostas do analyzer (rede interna)
# ---------------------------------------------------------------------------------------------


class AnalyzerResult(_Strict):
    ruleset_version: RulesetVersion
    status: Status
    list_number: ListNumber
    syntax_error: SyntaxErrorInfo | None
    violations: list[Violation] = Field(max_length=MAX_VIOLATIONS)
    truncated: bool

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


class AnalyzerManifest(_Strict):
    ruleset_version: RulesetVersion
    ruleset_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    period: Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]$")]
    target_python: str
    lists: list[ListInfo] = Field(max_length=6)


class AnalyzerHealth(_Strict):
    status: Literal["ok"]
    ruleset_version: RulesetVersion
    ruleset_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    target_python: str
    workers: Annotated[int, Field(ge=1)]

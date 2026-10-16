"""O que a API responde à página: o resultado da verificação, as listas, os erros e a saúde.

Parte do contrato da API (5.2.2), dividido em módulos na S39-02; importe de ``ipc_api.schemas``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from ipc_api.errors import ErrorCode

from .common import (
    MAX_VIOLATIONS,
    Category,
    GabaritoStatus,
    ListNumber,
    Message,
    Notice,
    Percent,
    Position,
    QuestionId,
    RulesetVersion,
    SimilarityBand,
    Status,
    SyntaxErrorInfo,
    _Strict,
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
    #: Por que a construção não vale e o que usar no lugar, do ruleset (S38-01). Vazios só com um
    #: analisador anterior à Sprint 38.
    explanation: Annotated[str, StringConstraints(max_length=1000)] = ""
    alternative: Annotated[str, StringConstraints(max_length=1000)] = ""


IndicatorLevel = Literal["baixo", "medio", "alto"]


class Indicator(_Strict):
    signal: Literal["multiplas_violacoes", "referencia_ia", "gabarito", "estilo"] = Field(
        description=(
            "multiplas_violacoes (o padrão das violações), referencia_ia (semelhança com uma "
            "solução gerada por IA para a questão), gabarito (semelhança com o gabarito oficial, "
            "ADR-11) ou estilo (marcadores, sem peso na faixa)."
        )
    )
    kind: Annotated[str, StringConstraints(pattern=r"^[a-z_]{1,40}$")] = Field(
        description="O que foi observado, como variedade, salto_de_lista ou referencia."
    )
    level: IndicatorLevel | None = Field(
        description="Faixa deste indício; vazia nos marcadores de estilo, que não pesam."
    )
    reason: Message = Field(description="Por que é um indício, com as construções envolvidas.")
    lines: list[Position] = Field(max_length=MAX_VIOLATIONS)


class AnalyzerIndicators(_Strict):
    level: IndicatorLevel | None
    items: list[Indicator] = Field(min_length=1, max_length=20)
    questions: list[Message] = Field(max_length=3)


class Indicators(AnalyzerIndicators):
    """Indícios de uso de IA (ADR-08, S29): para a equipe decidir com quem conversar."""

    notice: Message = Field(description="Indícios não são prova; a confirmação é a conversa.")


class LineSpan(_Strict):
    first: Position
    last: Position


Construct = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class GabaritoComparison(_Strict):
    """Comparação com o gabarito oficial da questão (ADR-11, FR-32): só porcentagem, nomes de
    construções e linhas do aluno; nenhum texto do gabarito."""

    question_id: QuestionId
    status: GabaritoStatus = Field(
        description=(
            "compared; no_gabarito (a questão não tem gabarito); unavailable (gabaritos fora do "
            "ar neste servidor); not_compared (o código não pôde ser comparado)."
        )
    )
    similarity: Percent | None = Field(description="Semelhança com o gabarito (ADR-07).")
    band: SimilarityBand | None
    short_code: bool = Field(description="Código curto: soluções independentes se parecem.")
    common: list[Construct] = Field(max_length=30, description="Construções dos dois.")
    only_student: list[Construct] = Field(max_length=30, description="Só no código do aluno.")
    only_gabarito: list[Construct] = Field(max_length=30, description="Só no gabarito.")
    student_lines: list[LineSpan] = Field(
        max_length=100, description="Trechos do aluno com a estrutura de um trecho do gabarito."
    )
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
    indicators: Indicators | None = Field(
        default=None,
        description=(
            "Indícios de uso de IA (ADR-08), só quando estão ligados neste servidor "
            "(IPC_AI_INDICATORS) e há algum. Nunca prova; nunca vão para o feedback do aluno."
        ),
    )
    gabarito: GabaritoComparison | None = Field(
        default=None,
        description="Com uma questão escolhida: a comparação com o gabarito dela (ADR-11).",
    )


class PeriodInfo(_Strict):
    """Um período carregado no IP-Checker (S43-02): o ativo e os até 5 anteriores (ADR-12)."""

    period: str = Field(description="Período, como 2026.2.")
    active: bool = Field(description="É o período ativo (o padrão quando o pedido não diz).")
    ruleset_version: str = Field(description="A versão das regras do período.")


class QuestionInfo(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^L[1-6]-Q[1-9]\d?$")] = Field(
        description="Numeração oficial da questão no período (P-07), como L3-Q2."
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class ListInfo(_Strict):
    number: ListNumber
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    questions: list[QuestionInfo] = Field(
        default_factory=list,
        description=(
            "Questões com regra específica cadastrada no período (R-01), em ordem; vazio quando "
            "a lista não tem nenhuma."
        ),
    )
    gabaritos: list[QuestionId] = Field(
        default_factory=list,
        description=(
            "Questões do período ativo com gabarito para comparar (ADR-11), mesmo sem regra "
            "cadastrada; só os números, nunca o gabarito."
        ),
    )


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


class SloTelemetry(_Strict):
    written: int = Field(ge=0, description="Eventos gravados desde que a API subiu.")
    dropped: int = Field(ge=0, description="Eventos descartados (fila cheia ou banco fora).")
    failed_batches: int = Field(ge=0)
    queued: int = Field(ge=0)


class SloHousekeeping(_Strict):
    """A limpeza diária do banco desde que a API subiu (S25-03): só contagens."""

    runs: int = Field(ge=0)
    failures: int = Field(ge=0)
    sessions: int = Field(ge=0, description="Sessões vencidas apagadas.")
    tokens: int = Field(ge=0, description="Links de e-mail usados ou vencidos apagados.")
    unverified: int = Field(ge=0, description="Cadastros não confirmados em 48 horas apagados.")
    inactive: int = Field(
        ge=0, description="Contas fora do status ativo, 365 dias sem atividade, apagadas (Q-19 d)."
    )
    log: int = Field(ge=0, description="Ações do registro de gerenciamento com mais de 12 meses.")


class SloResponse(_Strict):
    """Latência e erros dos últimos minutos (S21-02, NFR-15), sem dado de ninguém."""

    status: Literal["ok", "degraded"]
    window_s: int
    requests: int = Field(ge=0)
    validations: int = Field(ge=0, description="Verificações com latência medida na janela.")
    p95_ms: float | None = Field(description="P95 do POST /api/v1/validate; nulo sem amostras.")
    error_rate_pct: float = Field(ge=0)
    reasons: list[Literal["latencia", "erros"]]
    telemetry: SloTelemetry
    housekeeping: SloHousekeeping
    warnings: list[Literal["ativo_defasado"]] = Field(
        default_factory=list,
        description=(
            "Avisos que não mudam o status: ativo_defasado quando o período ativo parece ter "
            "acabado há mais de 60 dias (S43-04); trocar o ATIVO é decisão da coordenação."
        ),
    )

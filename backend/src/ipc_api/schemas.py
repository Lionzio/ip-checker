"""Modelos do contrato público (5.2.2) e das respostas do analyzer.

As respostas do analyzer são validadas com rigor (``extra="forbid"``, limites e coerência entre
os campos) antes de qualquer dado chegar ao aluno: a API trata o analyzer como um processo que
pode ter sido comprometido por uma submissão (TB-3, ameaça 2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ipc_api.errors import ErrorCode

Category = Literal["ANULACAO", "PROIBIDO_NA_QUESTAO", "FORA_DA_LISTA", "NAO_CONSTA", "EXIGENCIA"]
Status = Literal["valid", "invalid", "syntax_error"]
Notice = Literal["QUESTION_RULES_NOT_APPLIED", "QUESTION_RULES_NOT_REGISTERED"]
QuestionId = Annotated[str, StringConstraints(pattern=r"^L[1-6]-Q[1-9]\d?$")]
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


class FeedbackRequest(_Strict):
    code: str = Field(description="Código do aluno. Nunca é executado.")
    list_number: ListNumber
    student_name: Annotated[str, StringConstraints(min_length=1, max_length=120)] = Field(
        description="Nome do aluno, digitado por quem avalia. Nunca vai ao provedor de LLM."
    )
    annotation: Annotated[str, StringConstraints(max_length=1_000)] | None = Field(
        default=None, description="Anotação para o aluno (opcional)."
    )
    question_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")] | None = Field(
        default=None,
        description="Questão verificada, como L3-Q2; o feedback usa as mesmas regras (R-01).",
    )


class FeedbackResponse(_Strict):
    request_id: str
    status: Literal["valid", "invalid"]
    text: str = Field(description="O texto para o aluno; a página o mostra como texto puro.")
    source: Literal["llm", "template"] = Field(
        description=(
            "llm: o trecho livre veio de uma IA e foi validado; template: montado por modelos de "
            "texto, sem IA (nenhuma configurada ou nenhuma respondeu a tempo)."
        )
    )
    provider: Literal["primary", "fallback"] | None = Field(
        description="Qual IA escreveu o trecho livre: a principal ou a de reserva."
    )


class SimilarityRequest(_Strict):
    code_a: str = Field(description="Código de um aluno. Nunca é executado.")
    code_b: str = Field(description="Código do outro aluno. Nunca é executado.")
    question_id: QuestionId | None = Field(
        default=None,
        description=(
            "Questão do período ativo (ADR-11): com o gabarito dela, A e B também são comparados "
            "com ele, e a resposta traz o alerta de possível vazamento."
        ),
    )


BandId = Literal[
    "plagio", "altas_chances", "requer_atencao", "ligeiramente_suspeito", "sem_suspeitas"
]


class SimilarityBand(_Strict):
    id: BandId
    label: str = Field(description="O nome da faixa, sempre escrito junto da cor (NFR-19).")
    minimum: float = Field(description="A faixa começa neste valor, inclusive (FR-29).")


class SimilaritySyntaxError(_Strict):
    code: Literal["a", "b"] = Field(description="Qual dos dois códigos tem o erro.")
    line: Position
    col: Position
    message: Message


Percent = Annotated[float, Field(ge=0, le=100)]
Line = Annotated[int, Field(ge=1)]


class SimilarityMetrics(_Strict):
    """As métricas por trás da similaridade (S27-01, ADR-07), em porcentagem."""

    sequence: Percent | None = Field(
        description="ADR-05: tokens e estrutura em sequência. Vazia na comparação com a turma."
    )
    tree_dice: Percent = Field(description="ADR-07: Dice das subárvores da árvore canonizada.")
    tree_containment: Percent = Field(
        description="ADR-07: quanto do menor código está no maior (denuncia código morto)."
    )


class SimilarityMatch(_Strict):
    """Linhas do código A com a mesma estrutura de linhas do código B (S27-03)."""

    a_first: Line
    a_last: Line
    b_first: Line
    b_last: Line


class SimilarityResponse(_Strict):
    request_id: str
    status: Literal["compared", "syntax_error"]
    similarity: float | None = Field(
        ge=0, le=100, description="Porcentagem com uma casa decimal; vazia com erro de sintaxe."
    )
    band: SimilarityBand | None
    short_code: bool = Field(
        description="Um dos códigos é curto: soluções independentes tendem a se parecer."
    )
    syntax_error: SimilaritySyntaxError | None
    notice: str = Field(description="O aviso de que o resultado é um indício (FR-29).")
    metrics: SimilarityMetrics | None = Field(
        default=None, description="Vazia com erro de sintaxe. A similaridade é a maior delas."
    )
    matches: list[SimilarityMatch] = Field(
        default_factory=list, description="Os trechos em comum, na ordem do código A."
    )
    gabarito: SimilarityGabarito | None = Field(
        default=None,
        description="Com a questão escolhida: A e B comparados com o gabarito (ADR-11, item 5).",
    )


GabaritoStatus = Literal["compared", "no_gabarito", "unavailable", "not_compared"]


class GabaritoSide(_Strict):
    similarity: Percent = Field(description="Semelhança com o gabarito, com uma casa decimal.")
    band: SimilarityBand


class SimilarityGabarito(_Strict):
    question_id: QuestionId
    status: GabaritoStatus = Field(
        description=(
            "compared; no_gabarito (a questão não tem gabarito); unavailable (gabaritos fora do "
            "ar neste servidor); not_compared (um dos códigos não pôde ser comparado)."
        )
    )
    a: GabaritoSide | None
    b: GabaritoSide | None
    leak_alert: bool = Field(
        description=(
            "Possível vazamento do gabarito: A com B, A com o gabarito e B com o gabarito acima "
            "do limiar, com os dois códigos acima do tamanho mínimo (ADR-11, item 5)."
        )
    )
    message: Message


class ClassSolution(_Strict):
    label: Annotated[str, StringConstraints(min_length=1, max_length=80)] = Field(
        description="Como a solução aparece no resultado (um nome ou um número)."
    )
    code: str = Field(description="Uma solução da turma. Nunca é executada nem guardada.")


class SimilarityClassRequest(_Strict):
    code: str = Field(description="A solução a comparar com a turma.")
    solutions: list[ClassSolution] = Field(
        min_length=1, max_length=100, description="Até 100 soluções da turma, somando até 128 KB."
    )


class SimilarityClassItem(_Strict):
    label: str
    status: Literal["compared", "syntax_error", "rejected"]
    similarity: Percent | None
    band: SimilarityBand | None
    short_code: bool
    metrics: SimilarityMetrics | None
    syntax_error: SyntaxErrorInfo | None
    message: str | None = Field(description="Por que a solução foi recusada (tamanho, linhas).")


class SimilarityClassResponse(_Strict):
    request_id: str
    status: Literal["compared", "syntax_error"]
    syntax_error: SyntaxErrorInfo | None = Field(description="Erro na solução comparada.")
    results: list[SimilarityClassItem] = Field(
        description="Da mais parecida para a menos; as recusadas e com erro de sintaxe no fim."
    )
    notice: str


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


# ---------------------------------------------------------------------------------------------
# Acesso restrito à equipe (Sprint 13)
# ---------------------------------------------------------------------------------------------

RoleName = Literal["desenvolvedor", "professor", "monitor_chefe", "monitor"]
TreatmentName = Literal["masculino", "feminino", "neutro"]
StatusName = Literal[
    "aguardando_verificacao",
    "aguardando_aprovacao",
    "ativo",
    "recusado",
    "ex_monitor",
    "conselheiro",
    "inativo",
]
ActionName = Literal["aprovar", "recusar", "alterar_cargo", "remover", "reativar"]


class LoginRequest(_Strict):
    login: Annotated[str, StringConstraints(min_length=1, max_length=254)] = Field(
        description="Nome ou e-mail institucional (@cin.ufpe.br ou @ufpe.br)."
    )
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)] = Field(
        description="Senha da conta. Nunca é registrada."
    )


Text120 = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Email = Annotated[str, StringConstraints(min_length=3, max_length=254)]
SessionToken = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{43}$")]


class RegisterRequest(_Strict):
    name: Text120 = Field(description="Nome; único sem diferenciar maiúsculas e usado para entrar.")
    email: Email = Field(description="E-mail institucional (@cin.ufpe.br ou @ufpe.br).")
    password: Password = Field(
        description="Pelo menos 9 caracteres, 1 letra maiúscula e 1 caractere especial."
    )
    course: Text120
    treatment: TreatmentName = Field(description="Como a pessoa quer ser tratada no feedback.")


class RegisterResponse(_Strict):
    status: Literal["aguardando_verificacao"]
    email: str = Field(description="Para onde o link de verificação foi enviado.")


class VerifyRequest(_Strict):
    token: SessionToken = Field(description="O token do link enviado por e-mail.")


class VerifyResponse(_Strict):
    status: Literal["aguardando_aprovacao"]


class AuthOptions(_Strict):
    google: bool = Field(description="A entrada pelo Google está configurada (FR-24).")
    feedback_ai: bool = Field(
        description="Há IA configurada para o feedback; sem ela, o texto é montado por modelos."
    )
    ai_indicators: bool = Field(
        description="Os indícios de uso de IA estão ligados neste servidor (ADR-08, S29)."
    )


class GooglePending(_Strict):
    email: str = Field(description="O e-mail confirmado pelo Google.")
    name: str = Field(description="O nome da conta Google, só como sugestão (pode vir vazio).")


class GoogleSignup(_Strict):
    name: Text120
    course: Text120
    treatment: TreatmentName = Field(description="Como a pessoa quer ser tratada no feedback.")


class GoogleSignupResponse(_Strict):
    status: Literal["aguardando_aprovacao"]
    email: str


class ResendRequest(_Strict):
    email: Email


class ForgotPasswordRequest(_Strict):
    email: Email


class ResetPasswordRequest(_Strict):
    token: SessionToken = Field(description="O token do link de redefinição enviado por e-mail.")
    new_password: Password


class ProfileUpdate(_Strict):
    name: Text120 | None = None
    course: Text120 | None = None
    treatment: TreatmentName | None = None


class PasswordChange(_Strict):
    current_password: Password | None = Field(
        default=None, description="Obrigatória, a não ser numa conta criada só pelo Google."
    )
    new_password: Password


class AccountResponse(_Strict):
    """A conta de quem está logado. O tratamento só aparece para o próprio titular (FR-26)."""

    name: str
    email: str = Field(description="E-mail principal.")
    course: str
    treatment: TreatmentName
    role: RoleName
    role_label: str = Field(
        description=(
            'Como o cargo aparece na interface; o desenvolvedor aparece como "Monitor e '
            'desenvolvedor".'
        )
    )
    has_password: bool = Field(
        description="Falso numa conta criada pelo Google que ainda não definiu uma senha."
    )
    can_manage: bool = Field(
        description="Verdadeiro para quem acessa o gerenciamento da equipe (FR-28)."
    )
    can_view_log: bool = Field(
        description=(
            "Verdadeiro para quem vê o registro das ações de gerenciamento: desenvolvedor e "
            "professores (REC-06)."
        )
    )


class ManagedAccount(_Strict):
    """Uma conta vista no gerenciamento (FR-28). Nunca traz o tratamento (FR-26)."""

    id: UUID
    name: str
    email: str = Field(description="E-mail principal.")
    course: str
    signup_method: Literal["senha", "google", "seed"]
    requested_at: datetime = Field(description="Data do pedido de cadastro.")
    role: RoleName | None = Field(description="Vazio num pedido; numa conta removida, o último.")
    role_label: str | None
    status: StatusName
    status_label: str
    actions: list[ActionName] = Field(description="O que quem consulta pode fazer com a conta.")
    roles: list[RoleName] = Field(
        description="Os cargos que quem consulta pode escolher ao aprovar, alterar ou reativar."
    )
    removal_status: StatusName | None = Field(
        description="O status que a conta recebe se for removida (ex_monitor, conselheiro ou "
        "inativo); vazio se quem consulta não pode removê-la."
    )


class RequestsResponse(_Strict):
    items: list[ManagedAccount]


class MembersResponse(_Strict):
    active: list[ManagedAccount]
    removed: list[ManagedAccount] = Field(description="Ex-monitores, conselheiros e inativos.")


class ManagementLogEntry(_Strict):
    """Uma ação de gerenciamento (REC-06). Nomes e cargos são os do momento da ação."""

    at: datetime = Field(description="Quando a ação foi aplicada.")
    action: ActionName
    action_label: str = Field(description='Como a ação aparece na tela, por exemplo "Aprovou".')
    actor_name: str = Field(description="Quem fez a ação.")
    actor_role_label: str | None = Field(description="O cargo de quem fez, na hora da ação.")
    target_name: str = Field(description="A conta sobre a qual a ação foi feita.")
    from_status: StatusName
    from_status_label: str
    to_status: StatusName
    to_status_label: str
    from_role: RoleName | None
    from_role_label: str | None
    to_role: RoleName | None
    to_role_label: str | None


class ManagementLogResponse(_Strict):
    items: list[ManagementLogEntry] = Field(
        description="As ações dos últimos 12 meses, da mais recente para a mais antiga (até 500)."
    )


class RoleChoice(_Strict):
    role: RoleName


# ---------------------------------------------------------------------------------------------
# Respostas do analyzer (rede interna)
# ---------------------------------------------------------------------------------------------


class AnalyzerFeedbackItem(_Strict):
    kind: Literal["uso", "falta"]
    label: Annotated[str, StringConstraints(min_length=1, max_length=200)]


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

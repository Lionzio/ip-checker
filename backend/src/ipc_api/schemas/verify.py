"""O que a página pede: verificar, corrigir em lote, gerar feedback, comparar e o painel por lista.

Parte do contrato da API (5.2.2), dividido em módulos na S39-02; importe de ``ipc_api.schemas``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from .common import (
    Category,
    GabaritoStatus,
    Line,
    ListNumber,
    Message,
    Percent,
    PeriodId,
    Position,
    QuestionId,
    SimilarityBand,
    SyntaxErrorInfo,
    _Strict,
)

# ---------------------------------------------------------------------------------------------
# Contrato público
# ---------------------------------------------------------------------------------------------


class ValidateRequest(_Strict):
    code: str = Field(description="Código Python do aluno. Nunca é executado.")
    list_number: ListNumber = Field(description="Lista de exercícios (1 a 6).")
    question_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")] | None = Field(
        default=None, description="Questão, como L3-Q2. Sem questão, valem só as regras da lista."
    )
    period: PeriodId | None = Field(
        default=None,
        description="Período das regras, como 2026.2 (S43-02); sem ele, vale o período ativo.",
    )


class BatchFile(_Strict):
    name: Annotated[str, StringConstraints(min_length=1, max_length=120)] = Field(
        description="O nome do arquivo, que identifica o aluno na tabela (nada é guardado)."
    )
    code: str = Field(description="O código do arquivo. Nunca é executado nem guardado.")


#: Arquivos por requisição do lote (S40-01): 20 de até 50 KB passam da barreira de 128 KB, então
#: a página manda partes menores; o limite garante que uma requisição não segure a admissão.
MAX_BATCH_FILES = 20


class ValidateBatchRequest(_Strict):
    list_number: ListNumber = Field(description="Lista de exercícios (1 a 6).")
    question_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,32}$")] | None = None
    files: list[BatchFile] = Field(
        min_length=1,
        max_length=MAX_BATCH_FILES,
        description="Até 20 arquivos por requisição; a página divide a turma em partes.",
    )
    period: PeriodId | None = Field(
        default=None,
        description="Período das regras, como 2026.2 (S43-02); sem ele, vale o período ativo.",
    )


class BatchResult(_Strict):
    name: str
    status: Literal["valid", "invalid", "syntax_error", "rejected"]
    #: Violações por categoria; vazio quando o código é válido ou não foi analisado.
    counts: dict[Category, int]
    rule_ids: list[str] = Field(description="As regras violadas, sem repetição, em ordem.")
    syntax_error: SyntaxErrorInfo | None = None
    message: str | None = Field(default=None, description="Por que o arquivo foi recusado.")
    gabarito_similarity: Percent | None = Field(
        default=None, description="Semelhança com o gabarito da questão, quando houver."
    )


class ValidateBatchResponse(_Strict):
    request_id: str
    ruleset_version: str
    results: list[BatchResult] = Field(description="Um por arquivo, na ordem enviada.")


class PanelRule(_Strict):
    rule_id: str
    events: int = Field(description="Em quantas verificações a regra apareceu.")
    occurrences: int = Field(description="Quantas vezes, no total, somando as verificações.")


class ListPanelResponse(_Strict):
    """O painel de uma lista do período (S40-03, US-16): só contagens anônimas da telemetria."""

    semester: str
    list_number: ListNumber
    top_rules: list[PanelRule] = Field(description="As 15 regras mais violadas na lista.")
    events: int = Field(description="Verificações da lista no período.")
    syntax_errors: int = Field(description="Quantas delas tiveram erro de sintaxe.")
    adoption_pct: float | None = Field(
        description="Porcentagem da equipe ativa que já usou a lista (P-09, critério 2)."
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
    period: PeriodId | None = Field(
        default=None,
        description="Período das regras, como 2026.2 (S43-02); sem ele, vale o período ativo.",
    )
    enhance: bool = Field(
        default=False,
        description=(
            "Aprimorar com IA (Q-16, S32-12): a versão sem IA vai às IAs configuradas, em ordem, "
            "para detalhar e exemplificar. Só este pedido gasta a cota diária de feedbacks."
        ),
    )


class FeedbackResponse(_Strict):
    request_id: str
    status: Literal["valid", "invalid"]
    text: str = Field(description="O texto para o aluno; a página o mostra como texto puro.")
    source: Literal["llm", "template"] = Field(
        description=(
            "llm: o trecho livre veio de uma IA e foi validado (Aprimorar com IA); template: "
            "montado por modelos de texto, sem IA (o padrão desde a Sprint 32, Q-16)."
        )
    )
    provider: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,19}$")] | None = Field(
        description="Qual IA da cadeia escreveu o trecho livre, quando foi uma."
    )
    can_enhance: bool = Field(
        default=False,
        description="Há IA configurada neste servidor: a página mostra o Aprimorar com IA.",
    )
    notice: Message | None = Field(
        default=None,
        description="Por que o texto ficou sem IA num pedido de aprimoramento.",
    )


class SimilarityRequest(_Strict):
    code_a: str = Field(description="Código de um aluno. Nunca é executado.")
    code_b: str = Field(description="Código do outro aluno. Nunca é executado.")
    question_id: QuestionId | None = Field(
        default=None,
        description=(
            "Questão do período (ADR-11): com o gabarito dela, A e B também são comparados com "
            "ele, e a resposta traz o alerta de possível vazamento."
        ),
    )
    period: PeriodId | None = Field(
        default=None,
        description="Período da questão, como 2026.2 (S43-02); sem ele, vale o período ativo.",
    )


class SimilaritySyntaxError(_Strict):
    code: Literal["a", "b"] = Field(description="Qual dos dois códigos tem o erro.")
    line: Position
    col: Position
    message: Message


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


class SimilarityMatrixRequest(_Strict):
    solutions: list[ClassSolution] = Field(
        min_length=2,
        max_length=60,
        description="De 2 a 60 soluções da turma, somando até 128 KB (S40-02).",
    )


class MatrixSolution(_Strict):
    label: str
    status: Literal["compared", "syntax_error", "rejected"]
    syntax_error: SyntaxErrorInfo | None = None
    message: str | None = None


class MatrixPair(_Strict):
    a: str = Field(description="O rótulo da primeira solução do par.")
    b: str = Field(description="O rótulo da segunda solução do par.")
    similarity: Percent
    band: SimilarityBand


class SimilarityMatrixResponse(_Strict):
    """Todos contra todos (S40-02): os pares mais parecidos primeiro e os grupos de soluções
    ligadas por pares a partir da faixa "Requer atenção"."""

    request_id: str
    solutions: list[MatrixSolution] = Field(description="Na ordem enviada.")
    pairs: list[MatrixPair] = Field(description="Até 200 pares, do mais parecido para o menos.")
    groups: list[list[str]] = Field(description="Grupos de 2 ou mais soluções, maiores primeiro.")
    notice: str

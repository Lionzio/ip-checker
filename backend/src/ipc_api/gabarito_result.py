"""O que a página recebe da comparação com o gabarito (ADR-11, FR-32; S32-04 e S32-05).

O analyzer devolve porcentagens, nomes de construções e linhas do aluno; aqui entram a faixa do
FR-29, os avisos e o alerta de possível vazamento do plágio. Nada do texto do gabarito passa por
aqui: ele só existe na memória da API e na chamada interna ao analyzer.
"""

from __future__ import annotations

from ipc_api.gabaritos import Gabaritos, GabaritosConfig
from ipc_api.schemas import (
    AnalyzerGabarito,
    AnalyzerSimilarity,
    GabaritoComparison,
    GabaritoSide,
    LineSpan,
    SimilarityBand,
    SimilarityGabarito,
)
from ipc_api.similarity import SHORT_CODE_TOKENS, classify, displayed

COMPARED = (
    "Semelhança com o gabarito oficial da questão, pela estrutura do código (a mesma medida do "
    "painel de plágio). É uma referência para a correção, não uma nota."
)
NO_GABARITO = "Esta questão não tem gabarito para comparar."
UNAVAILABLE = (
    "Os gabaritos não estão disponíveis neste servidor agora; a verificação segue normal, sem a "
    "comparação."
)
NOT_COMPARED = "O código não pôde ser comparado com o gabarito."
SYNTAX = "Com erro de sintaxe, o código não é comparado com o gabarito."
SIMILARITY_COMPARED = "A e B comparados também com o gabarito oficial da questão."
LEAK_ALERT = (
    "Possível vazamento do gabarito: os dois códigos coincidem entre si e com o gabarito oficial. "
    "Isto diz que os códigos coincidem com o gabarito, não quem o vazou; vale uma conversa."
)


def _band(percent: float) -> SimilarityBand:
    band = classify(percent)
    return SimilarityBand(id=band.id, label=band.label, minimum=band.minimum)


def _empty(question_id: str, status: str, message: str) -> GabaritoComparison:
    return GabaritoComparison.model_validate(
        {
            "question_id": question_id,
            "status": status,
            "similarity": None,
            "band": None,
            "short_code": False,
            "common": [],
            "only_student": [],
            "only_gabarito": [],
            "student_lines": [],
            "message": message,
        }
    )


def missing(question_id: str, gabaritos: Gabaritos) -> GabaritoComparison:
    """Sem o texto do gabarito: a questão não tem, ou os gabaritos estão fora do ar."""
    if gabaritos.status == "loaded":
        return _empty(question_id, "no_gabarito", NO_GABARITO)
    return _empty(question_id, "unavailable", UNAVAILABLE)


def for_validation(
    question_id: str, comparison: AnalyzerGabarito | None, *, syntax_error: bool
) -> GabaritoComparison:
    if comparison is None:
        return _empty(question_id, "not_compared", SYNTAX if syntax_error else NOT_COMPARED)
    return GabaritoComparison(
        question_id=question_id,
        status="compared",
        similarity=displayed(comparison.percent),
        band=_band(comparison.percent),
        short_code=min(comparison.token_counts) < SHORT_CODE_TOKENS,
        common=comparison.common,
        only_student=comparison.only_student,
        only_gabarito=comparison.only_gabarito,
        student_lines=[LineSpan(first=s.first, last=s.last) for s in comparison.student_lines],
        message=COMPARED,
    )


def for_similarity(
    question_id: str,
    result: AnalyzerSimilarity,
    gabaritos: Gabaritos,
    has_gabarito: bool,
    config: GabaritosConfig,
) -> SimilarityGabarito:
    def empty(status: str, message: str) -> SimilarityGabarito:
        return SimilarityGabarito.model_validate(
            {
                "question_id": question_id,
                "status": status,
                "a": None,
                "b": None,
                "leak_alert": False,
                "message": message,
            }
        )

    if not has_gabarito:
        if gabaritos.status == "loaded":
            return empty("no_gabarito", NO_GABARITO)
        return empty("unavailable", UNAVAILABLE)
    sides = result.gabarito or []
    a, b = (sides[0], sides[1]) if len(sides) == 2 else (None, None)
    if a is None or b is None or result.percent is None or result.token_counts is None:
        return empty("not_compared", NOT_COMPARED)
    shown = [displayed(result.percent), displayed(a.percent), displayed(b.percent)]
    tokens = [*result.token_counts, a.token_counts[0], b.token_counts[0]]
    alert = min(shown) >= config.alert_percent and min(tokens) >= config.alert_min_tokens
    return SimilarityGabarito(
        question_id=question_id,
        status="compared",
        a=GabaritoSide(similarity=shown[1], band=_band(a.percent)),
        b=GabaritoSide(similarity=shown[2], band=_band(b.percent)),
        leak_alert=alert,
        message=LEAK_ALERT if alert else SIMILARITY_COMPARED,
    )

"""Regras por questão do lado da API (R-01, FR-11): a questão pedida existe e é da lista?

A API nunca lê regras: confere a questão no manifesto do analisador, que lista as questões
cadastradas em cada período carregado (P-07; S43-02). O analisador confere de novo antes de
analisar. Desde a Sprint 32 (ADR-11, item 6), uma questão do período que só tem gabarito também
vale: a verificação usa as regras da lista e compara com o gabarito.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipc_api.errors import ApiError, ErrorCode
from ipc_api.gabaritos import Gabaritos
from ipc_api.periods import PeriodView


@dataclass(frozen=True, slots=True)
class QuestionCheck:
    #: O período do pedido, de onde vêm as questões e os gabaritos (P-07).
    period: str
    #: A questão tem regra cadastrada (R-01); sem isso, valem só as regras da lista.
    registered: bool


def check_question(
    view: PeriodView | None,
    list_number: int,
    question_id: str | None,
    gabaritos: Gabaritos | None = None,
) -> QuestionCheck | None:
    """Recusa com 422 ``UNKNOWN_QUESTION`` uma questão inexistente no período ou de outra lista;
    ``None`` sem questão. Com ``gabaritos``, aceita também uma questão que só tem gabarito."""
    if question_id is None or view is None:
        return None
    owner = next(
        (item.number for item in view.lists for q in item.questions if q.id == question_id),
        None,
    )
    registered = owner is not None
    if (
        owner is None
        and gabaritos is not None
        and gabaritos.get(view.period, question_id) is not None
    ):
        # A numeração oficial diz a lista: L3-Q2 é da Lista 3 (P-07).
        owner = int(question_id[1])
    if owner is None:
        where = "" if view.active else f" no período {view.period}"
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {question_id} não está cadastrada no IP-Checker{where}.",
        )
    if owner != list_number:
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {question_id} é da Lista {owner}, não da Lista {list_number}.",
        )
    return QuestionCheck(period=view.period, registered=registered)

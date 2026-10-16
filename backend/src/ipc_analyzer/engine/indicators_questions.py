"""As perguntas para a conversa com o aluno (ADR-08, item 4; S29-03).

Partem do que o painel de indícios achou e nunca acusam: pedem que o aluno explique ou mude o
próprio código. Saíram de ``indicators.py`` na S39-02.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.models import Violation
from ipc_analyzer.engine.ruleset import Category

if TYPE_CHECKING:
    from ipc_analyzer.engine.indicators import Indicator

#: Proibições gerais (R-05 a R-14): as que o sinal 1 conta pela variedade e pela repetição.
GENERAL_RULES = frozenset(f"R-{n:02d}" for n in range(5, 15))
MAX_QUESTIONS = 3


def suggested_questions(
    items: Sequence[Indicator], violations: Sequence[Violation]
) -> tuple[str, ...]:
    """De 2 a 3 perguntas para a conversa com o aluno, a partir do que o painel achou."""
    questions: list[str] = []
    kinds = {item.kind: item for item in items}
    if "salto_de_lista" in kinds:
        item = kinds["salto_de_lista"]
        questions.append(
            f"Na linha {item.lines[0]}, você usou uma construção que a disciplina só apresenta "
            "mais adiante. Onde você aprendeu e por que escolheu usá-la aqui?"
        )
    general = next(
        (v for v in violations if v.category is Category.ANULACAO and v.rule_id in GENERAL_RULES),
        None,
    )
    if general is not None and ("variedade" in kinds or "repeticao" in kinds):
        questions.append(
            f"O que o '{describe(general.construct)}' da linha {general.line} faz? Como você "
            "escreveria esse trecho sem ele?"
        )
    if "referencia" in kinds:
        item = kinds["referencia"]
        span = f"linhas {item.lines[0]} a {item.lines[-1]}" if item.lines else "o código"
        questions.append(
            f"Explique, com as suas palavras, o que acontece nas {span}, e o que mudaria se a "
            "entrada fosse diferente."
        )
    if "comentarios_em_ingles" in kinds or "identificadores_em_ingles" in kinds:
        questions.append(
            "Por que os nomes ou os comentários estão em inglês? Você pode explicar o que cada um "
            "deles significa no programa?"
        )
    if "docstring" in kinds or "anotacao_de_tipo" in kinds or "main_guard" in kinds:
        questions.append(
            "Algumas partes do código usam recursos que a disciplina não ensina. Você pode "
            "explicar para que servem e como funcionam?"
        )
    if len(questions) < 2:
        questions.append(
            "Faça uma pequena mudança no programa (por exemplo, outro formato de saída) e explique "
            "o que precisou alterar."
        )
    return tuple(questions[:MAX_QUESTIONS])

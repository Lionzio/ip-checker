"""As questões cadastradas no período ativo (R-01): cada uma tem o efeito que o enunciado pede.

A L3-Q9 é a questão do ensaio do cadastro (S31-13, ``docs/ensaio-cadastro.md``): libera ``map()``,
que o documento de permissões não cita, e proíbe ``sum()``, ``sort()`` e ``sorted()``, que a Lista 3
permite. A L4-Q3 é a primeira questão real: o enunciado libera ``eval()`` para ler listas da entrada.
"""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.ruleset import CompiledRuleset

SOLUTION = """\
notas = list(map(float, input().split()))
total = 0
aprovados = 0
for nota in notas:
    total += nota
    if nota >= 7:
        aprovados += 1
print(f"Média: {total / len(notas):.1f}")
print(f"Maior: {max(notas)}")
print(f"Menor: {min(notas)}")
print(f"Aprovados: {aprovados}")
"""


EVAL_SOLUTION = """def soma(cartas):
    total = 0
    for carta in cartas:
        total += carta
    return total

print(soma(eval(input())))
"""


def _violations(
    code: str, ruleset: CompiledRuleset, question: str | None, list_number: int = 3
) -> list[str]:
    result = analyze_source(code, list_number=list_number, ruleset=ruleset, question_id=question)
    return sorted(f"{v.rule_id} {v.category} {v.line}" for v in result.violations)


def test_the_rehearsal_question_is_registered(base_ruleset: CompiledRuleset) -> None:
    question = base_ruleset.questions["L3-Q9"]

    assert question.question.title.startswith("Ensaio")


def test_the_solution_passes_only_with_the_question(base_ruleset: CompiledRuleset) -> None:
    assert _violations(SOLUTION, base_ruleset, "L3-Q9") == []
    # Sem a questão, vale a Lista 3: map() não consta no documento.
    assert _violations(SOLUTION, base_ruleset, None) == ["R-04 NAO_CONSTA 1"]


@pytest.mark.parametrize(
    ("replacement", "line"),
    [("sum(notas)", 8), ("sorted(notas)[-1]", 9)],
    ids=["sum", "sorted"],
)
def test_what_the_statement_forbids_annuls_the_question(
    base_ruleset: CompiledRuleset, replacement: str, line: int
) -> None:
    original = "total / len(notas)" if line == 8 else "max(notas)"
    code = SOLUTION.replace(original, replacement if line == 9 else f"{replacement} / len(notas)")

    assert _violations(code, base_ruleset, "L3-Q9") == [f"R-01 PROIBIDO_NA_QUESTAO {line}"]
    # Sem a questão, a Lista 3 permite sum() e sorted() (só o map() aparece).
    assert _violations(code, base_ruleset, None) == ["R-04 NAO_CONSTA 1"]


def test_l4_q3_allows_eval_only_with_the_question(base_ruleset: CompiledRuleset) -> None:
    assert base_ruleset.questions["L4-Q3"].question.list_number == 4
    assert _violations(EVAL_SOLUTION, base_ruleset, "L4-Q3", list_number=4) == []
    # Sem a questão, vale a Lista 4: eval() não consta no documento.
    assert _violations(EVAL_SOLUTION, base_ruleset, None, list_number=4) == ["R-04 NAO_CONSTA 7"]

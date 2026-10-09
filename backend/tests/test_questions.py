"""As questões cadastradas no período ativo (R-01): cada uma tem o efeito que o enunciado pede.

A L3-Q9 é a questão do ensaio do cadastro (S31-13, ``docs/ensaio-cadastro.md``): libera ``map()``,
que o documento de permissões não cita, e proíbe ``sum()``, ``sort()`` e ``sorted()``, que a Lista 3
permite.
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


def _violations(code: str, ruleset: CompiledRuleset, question: str | None) -> list[str]:
    result = analyze_source(code, list_number=3, ruleset=ruleset, question_id=question)
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

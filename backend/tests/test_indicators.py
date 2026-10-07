"""Indícios de uso de IA (ADR-08, US-34; S29-01 e S29-02): o motor, as faixas e as referências.

Os casos da US-34 viram testes: ``break``, ``pass`` e ``continue`` juntos, vários ``pass`` e
construções de listas bem posteriores dão indício com as linhas; uma solução limpa não mostra nada.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from conftest import BASE_RULESET
from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.indicators import Indicators, Level
from ipc_analyzer.engine.ruleset import (
    MAX_REFERENCES_PER_QUESTION,
    CompiledRuleset,
    RulesetError,
    load_ruleset,
)


@pytest.fixture(scope="module")
def ruleset() -> CompiledRuleset:
    return load_ruleset(BASE_RULESET)


def indicators(code: str, ruleset: CompiledRuleset, list_number: int, **kw: object) -> Indicators:
    result = analyze_source(
        code,
        list_number=list_number,
        ruleset=ruleset,
        with_indicators=True,
        **kw,  # type: ignore[arg-type]
    )
    assert result.indicators is not None, "esperava algum indício"
    return result.indicators


def kinds(found: Indicators) -> dict[str, tuple[Level | None, tuple[int, ...]]]:
    return {item.kind: (item.level, item.lines) for item in found.items}


BREAK_PASS_CONTINUE = """numeros = []
for i in range(5):
    n = int(input())
    if n < 0:
        break
    if n == 0:
        continue
    if n > 100:
        pass
    numeros.append(n)
print(numeros)
"""

CLEAN = """nota = float(input())
if nota >= 7:
    print('Aprovado')
else:
    print('Reprovado')
"""


# --- Sinal 1: múltiplas violações ----------------------------------------------------------------


def test_break_pass_and_continue_together_are_high(ruleset: CompiledRuleset) -> None:
    found = indicators(BREAK_PASS_CONTINUE, ruleset, 3)

    assert found.level is Level.ALTO
    level, lines = kinds(found)["variedade"]
    assert level is Level.ALTO
    assert lines == (5, 7, 9)
    variety = next(item for item in found.items if item.kind == "variedade")
    # break e continue são a mesma regra (R-11), mas duas construções diferentes.
    assert "'break', 'continue' e 'pass'" in variety.reason


def test_two_different_prohibitions_are_medium(ruleset: CompiledRuleset) -> None:
    code = "for i in range(3):\n    if i:\n        break\n    pass\n"

    assert kinds(indicators(code, ruleset, 2))["variedade"][0] is Level.MEDIO


@pytest.mark.parametrize(("times", "level"), [(2, Level.BAIXO), (3, Level.ALTO)])
def test_the_same_prohibition_repeated(ruleset: CompiledRuleset, times: int, level: Level) -> None:
    code = "for i in range(3):\n" + "".join(
        f"    if i == {n}:\n        pass\n" for n in range(times)
    )

    found = kinds(indicators(code, ruleset, 2))

    assert found["repeticao"][0] is level
    assert len(found["repeticao"][1]) == times
    assert "variedade" not in found


def test_a_single_prohibition_is_not_an_indicator(ruleset: CompiledRuleset) -> None:
    result = analyze_source(
        "for i in range(3):\n    if i == 2:\n        break\n",
        list_number=2,
        ruleset=ruleset,
        with_indicators=True,
    )

    assert result.status == "invalid"
    assert result.indicators is None


def test_constructions_from_much_later_lists_are_a_jump(ruleset: CompiledRuleset) -> None:
    # Dicionário e lambda (Lista 5) numa solução da Lista 3: dois saltos de 2 listas.
    code = "notas = {'ana': 9}\ndobro = lambda x: x * 2\nprint(dobro(notas['ana']))\n"

    found = indicators(code, ruleset, 3)

    level, lines = kinds(found)["salto_de_lista"]
    assert level is Level.ALTO
    assert lines == (1, 2)
    reason = next(item.reason for item in found.items if item.kind == "salto_de_lista")
    assert "Lista 3" in reason
    assert "(Lista 5)" in reason
    assert any("linha 1" in question for question in found.questions)


def test_one_jump_is_medium_and_the_next_list_is_not_a_jump(ruleset: CompiledRuleset) -> None:
    one = "notas = {'ana': 9}\nprint(notas)\n"
    next_list = "x = int(input())\nfor i in range(x):\n    print(i)\n"

    assert kinds(indicators(one, ruleset, 3))["salto_de_lista"][0] is Level.MEDIO
    # for na Lista 1 é da Lista 2: um erro comum de quem está aprendendo, não um salto.
    assert (
        analyze_source(next_list, list_number=1, ruleset=ruleset, with_indicators=True).indicators
        is None
    )


def test_constructions_outside_the_document(ruleset: CompiledRuleset) -> None:
    few = "x = int(input())\nif x:\n    print(abs(x).bit_length())\n"
    many = (
        "x = int(input())\n"
        "if x:\n"
        "    print(x.bit_length(), x.to_bytes(2), x.as_integer_ratio(), x.conjugate())\n"
    )

    assert kinds(indicators(few, ruleset, 1))["fora_do_documento"][0] is Level.BAIXO
    assert kinds(indicators(many, ruleset, 1))["fora_do_documento"][0] is Level.MEDIO


def test_a_clean_solution_shows_nothing(ruleset: CompiledRuleset) -> None:
    result = analyze_source(CLEAN, list_number=1, ruleset=ruleset, with_indicators=True)

    assert result.status == "valid"
    assert result.indicators is None


def test_a_syntax_error_has_no_indicators(ruleset: CompiledRuleset) -> None:
    result = analyze_source("if x\n", list_number=1, ruleset=ruleset, with_indicators=True)

    assert result.status == "syntax_error"
    assert result.indicators is None


def test_without_asking_nothing_is_computed(ruleset: CompiledRuleset) -> None:
    result = analyze_source(BREAK_PASS_CONTINUE, list_number=3, ruleset=ruleset)

    assert result.indicators is None


def test_there_are_always_two_or_three_questions(ruleset: CompiledRuleset) -> None:
    for code, list_number in ((BREAK_PASS_CONTINUE, 3), ("x = {}\nprint(x)\n", 3)):
        found = indicators(code, ruleset, list_number)
        assert 2 <= len(found.questions) <= 3


def test_long_reasons_and_line_lists_are_capped(ruleset: CompiledRuleset) -> None:
    calls = ", ".join(f"x.{name}()" for name in ("bit_length", "to_bytes", "conjugate", "hex"))
    code = "x = 1\nif x:\n" + "".join(f"    print({calls})\n" for _ in range(300))

    found = indicators(code, ruleset, 1)

    assert all(len(item.lines) <= 200 for item in found.items)
    assert all(len(item.reason) <= 1_000 for item in found.items)


# --- Sinal 3: marcadores de estilo ---------------------------------------------------------------

ENGLISH_STYLE = '''def calculate_average(numbers: list) -> float:
    """Return the average of the numbers."""
    # calculate the sum of all values
    total = 0
    for value in numbers:
        total = total + value
    return total / len(numbers)


if __name__ == "__main__":
    print(calculate_average([1, 2, 3]))
'''


def test_style_markers_are_facts_without_weight(ruleset: CompiledRuleset) -> None:
    found = kinds(indicators(ENGLISH_STYLE, ruleset, 4))

    assert found["docstring"] == (None, (2,))
    assert found["anotacao_de_tipo"] == (None, (1,))
    assert found["main_guard"] == (None, (10,))
    assert found["identificadores_em_ingles"][0] is None
    assert found["comentarios_em_ingles"] == (None, (3,))


def test_portuguese_code_has_no_style_marker(ruleset: CompiledRuleset) -> None:
    code = (
        "def media(notas):\n"
        "    # soma todas as notas da lista\n"
        "    soma = 0\n"
        "    for nota in notas:\n"
        "        soma = soma + nota\n"
        "    return soma / len(notas)\n\n"
        "print(media([7, 8]))\n"
    )

    result = analyze_source(code, list_number=4, ruleset=ruleset, with_indicators=True)

    assert result.indicators is None


def test_only_style_markers_have_no_level(ruleset: CompiledRuleset) -> None:
    code = (
        "def media(notas):\n"
        '    """Calcula a média."""\n'
        "    return sum(notas) / len(notas)\n\n"
        "print(media([7, 8]))\n"
    )

    found = indicators(code, ruleset, 4)

    assert found.level is None
    assert [item.kind for item in found.items] == ["docstring"]


# --- Sinal 2: referências geradas por IA (S29-02) ------------------------------------------------

QUESTION = {
    "question_id": "L3-Q1",
    "list": 3,
    "title": "Média das notas",
    "source": "Enunciado da L3-Q1: leia as notas e mostre a média.",
    "allow_facts": ["builtin:map"],
}
REFERENCE = """quantidade = int(input())
notas = []
for i in range(quantidade):
    notas.append(float(input()))
soma = 0
for nota in notas:
    soma = soma + nota
print(soma / quantidade)
"""
RENAMED = """n = int(input())
valores = []
for k in range(n):
    valores.append(float(input()))
total = 0
for v in valores:
    total = total + v
print(total / n)
"""
INDEPENDENT = """n = int(input())
maior = 0
for k in range(n):
    x = float(input())
    if x > maior:
        maior = x
print(maior)
"""


def ruleset_with_references(tmp_path: Path, files: dict[str, str]) -> CompiledRuleset:
    shutil.copy(BASE_RULESET, tmp_path / "base.yaml")
    (tmp_path / "questions").mkdir()
    (tmp_path / "questions" / "L3-Q1.yaml").write_text(
        yaml.safe_dump(QUESTION, allow_unicode=True), encoding="utf-8"
    )
    for relative, content in files.items():
        path = tmp_path / "referencias" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return load_ruleset(tmp_path / "base.yaml")


def test_a_solution_like_an_ai_reference_is_an_indicator(tmp_path: Path) -> None:
    ruleset = ruleset_with_references(tmp_path, {"L3-Q1/assistente-a.py": REFERENCE})

    found = indicators(RENAMED, ruleset, 3, question_id="L3-Q1")

    level, lines = kinds(found)["referencia"]
    assert level is Level.ALTO
    assert lines
    reason = next(item.reason for item in found.items if item.kind == "referencia")
    assert "L3-Q1" in reason
    assert "assistente-a" in reason
    assert any("linhas" in question for question in found.questions)


def test_an_independent_solution_is_not_like_the_reference(tmp_path: Path) -> None:
    ruleset = ruleset_with_references(tmp_path, {"L3-Q1/assistente-a.py": REFERENCE})

    result = analyze_source(
        INDEPENDENT, list_number=3, ruleset=ruleset, question_id="L3-Q1", with_indicators=True
    )

    assert result.indicators is None


def test_the_most_similar_reference_is_the_one_shown(tmp_path: Path) -> None:
    ruleset = ruleset_with_references(
        tmp_path,
        {"L3-Q1/assistente-a.py": INDEPENDENT, "L3-Q1/assistente-b.py": REFERENCE},
    )

    found = indicators(RENAMED, ruleset, 3, question_id="L3-Q1")

    reason = next(item.reason for item in found.items if item.kind == "referencia")
    assert "assistente-b" in reason


def test_without_question_the_references_are_not_used(tmp_path: Path) -> None:
    ruleset = ruleset_with_references(tmp_path, {"L3-Q1/assistente-a.py": REFERENCE})

    result = analyze_source(RENAMED, list_number=3, ruleset=ruleset, with_indicators=True)

    assert result.indicators is None


def test_references_load_with_the_ruleset_and_change_its_fingerprint(tmp_path: Path) -> None:
    ruleset = ruleset_with_references(tmp_path, {"L3-Q1/assistente-a.py": REFERENCE})
    without = load_ruleset(BASE_RULESET)

    assert [r.label for r in ruleset.references["L3-Q1"]] == ["assistente-a"]
    assert ruleset.sha256 != without.sha256


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({"L9-Q9/a.py": REFERENCE}, "não está cadastrada"),
        ({"L3-Q1/a.py": "if x\n"}, "referência inválida"),
        ({"L3-Q1/a.py": "x" * 60_000}, "referência inválida"),
        (
            {f"L3-Q1/r{n}.py": REFERENCE for n in range(MAX_REFERENCES_PER_QUESTION + 1)},
            "o limite é",
        ),
    ],
)
def test_invalid_references_stop_the_ruleset(
    tmp_path: Path, files: dict[str, str], message: str
) -> None:
    with pytest.raises(RulesetError, match=message):
        ruleset_with_references(tmp_path, files)

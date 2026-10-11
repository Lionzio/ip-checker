"""Entrada do feedback no motor (S18-02; Q-16, Q-18): comentários fora, nomes legíveis."""

from __future__ import annotations

import ast

import pytest

from ipc_analyzer.engine.feedback import feedback_input, strip_comments, strip_docstrings
from ipc_analyzer.engine.guards import AnalysisLimitError
from ipc_analyzer.engine.ruleset import CompiledRuleset


def test_comments_go_and_strings_with_hashes_stay() -> None:
    code = "# cabeçalho\nx = '# não é comentário'  # é\n\n    # recuado\nprint(x)\n"

    assert strip_comments(code) == "x = '# não é comentário'\n\n\nprint(x)\n"


def test_a_code_with_only_comments_becomes_empty() -> None:
    assert strip_comments("# só comentário\n") == "\n"


def test_an_untokenizable_text_is_an_analysis_limit() -> None:
    with pytest.raises(AnalysisLimitError):
        strip_comments("x = (\n")


def test_items_keep_the_order_and_are_not_repeated(base_ruleset: CompiledRuleset) -> None:
    code = "for a in range(2):\n    for b in range(3):\n        print(a, b)\nif a:\n    pass\n"

    result = feedback_input(code, list_number=1, ruleset=base_ruleset)

    assert [(item.kind, item.label) for item in result.items] == [
        ("uso", "for"),
        ("uso", "range()"),
        ("uso", "pass"),
    ]


def test_the_missing_topic_is_named_by_the_list(base_ruleset: CompiledRuleset) -> None:
    code = "x = int(input())\nprint(x)\n"

    first = feedback_input(code, list_number=1, ruleset=base_ruleset).items
    second = feedback_input(code, list_number=2, ruleset=base_ruleset).items

    assert [(item.kind, item.label) for item in first] == [("falta", "if ou operador ternário")]
    assert [(item.kind, item.label) for item in second] == [("falta", "for ou while")]


def test_zip_outside_the_for_is_named_in_the_feedback(base_ruleset: CompiledRuleset) -> None:
    code = "a = input()\nb = input()\nz = zip(a, b)\nfor par in z:\n    print(par)\n"

    result = feedback_input(code, list_number=2, ruleset=base_ruleset)

    assert [(item.kind, item.label) for item in result.items] == [("uso", "zip()")]


def test_docstrings_and_loose_strings_leave_the_code() -> None:
    """S25-05: o texto solto é onde o aluno escreve nome e matrícula, como nos comentários."""
    code = (
        '"""Isabella, 20231234567"""\n'
        "def f(x):\n"
        '    """Soma.\n'
        '    Linha 2."""\n'
        "    return x\n"
        "class C:\n"
        "    'só a docstring'\n"
        's = "isto é dado e fica"; "solto"; y = "ção"\n'
    )

    out = strip_docstrings(code)

    assert out == (
        "...\n"
        "def f(x):\n"
        "    ...\n"
        "    return x\n"
        "class C:\n"
        "    ...\n"
        's = "isto é dado e fica"; ...; y = "ção"\n'
    )
    ast.parse(out)


def test_a_code_without_text_stays_the_same() -> None:
    code = 'x = 1\nprint(f"{x}")\n'

    assert strip_docstrings(code) == code


def test_feedback_input_has_no_docstrings(base_ruleset: CompiledRuleset) -> None:
    data = feedback_input(
        '"""Ana Lima"""\nx = int(input())  # Ana\nif x > 0:\n    print(x)\n',
        list_number=1,
        ruleset=base_ruleset,
    )

    assert "Ana" not in data.code
    assert data.code.startswith("...\n")


def test_a_lone_carriage_return_is_a_line_break() -> None:
    assert strip_comments("Ý = 1  # comentário\rØ = Ý\r") == "Ý = 1\nØ = Ý\n"

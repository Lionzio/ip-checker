"""Entrada do feedback no motor (S18-02; Q-16, Q-18): comentários fora, nomes legíveis."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.feedback import feedback_input, strip_comments
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

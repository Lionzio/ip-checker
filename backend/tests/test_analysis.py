"""Ponto de entrada do motor (analyze_source) e módulos de apoio: predicados e nomes legíveis."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.conditions import PREDICATES, holds
from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.facts import Fact
from ipc_analyzer.engine.guards import InvalidInputError
from ipc_analyzer.engine.ruleset import KNOWN_PREDICATES, CompiledRuleset, Condition


def test_valid_code(base_ruleset: CompiledRuleset) -> None:
    # Lista 1: precisa de um if ou de um ternário (R-02).
    source = "x = int(input())\nprint('par' if x % 2 == 0 else 'ímpar')\n"
    result = analyze_source(source, list_number=1, ruleset=base_ruleset)

    assert result.status == "valid"
    assert result.violations == ()
    assert result.ruleset_version == "2026.2.1"
    assert result.list_number == 1
    assert not result.truncated


def test_invalid_code(base_ruleset: CompiledRuleset) -> None:
    result = analyze_source("x = None\n", list_number=1, ruleset=base_ruleset)

    assert result.status == "invalid"
    assert [v.rule_id for v in result.violations] == ["R-02", "R-13"]


def test_syntax_error_skips_the_rules(base_ruleset: CompiledRuleset) -> None:
    result = analyze_source("try:\n    x = (\n", list_number=1, ruleset=base_ruleset)

    assert result.status == "syntax_error"
    assert result.violations == ()
    assert result.syntax_error is not None
    assert result.syntax_error.line == 2


@pytest.mark.parametrize("list_number", [0, 7])
def test_unknown_list_is_rejected(base_ruleset: CompiledRuleset, list_number: int) -> None:
    with pytest.raises(InvalidInputError, match=f"Lista {list_number} não existe"):
        analyze_source("x = 1\n", list_number=list_number, ruleset=base_ruleset)


def test_input_errors_propagate(base_ruleset: CompiledRuleset) -> None:
    with pytest.raises(InvalidInputError, match="vazio"):
        analyze_source("\n", list_number=1, ruleset=base_ruleset)


# --- Predicados ---------------------------------------------------------------------------


def test_predicate_library_matches_the_ruleset_vocabulary() -> None:
    assert set(PREDICATES) == KNOWN_PREDICATES


@pytest.mark.parametrize(
    ("call_args", "params", "expected"),
    [
        (3, {"min": 3}, True),
        (2, {"min": 3}, False),
        (1, {"min": 1, "max": 1}, True),
        (2, {"max": 1}, False),
        (None, {"min": 0}, False),  # referência sem chamada
    ],
)
def test_call_args_predicate(call_args: int | None, params: dict[str, int], expected: bool) -> None:
    fact = Fact("builtin:type", 1, 1, 1, 5, call_args=call_args)

    assert holds(Condition(predicate="call_args", params=params), fact) is expected


@pytest.mark.parametrize(
    ("zip_header_args", "expected"),
    [
        (2, True),
        (3, True),
        (1, False),  # uma sequência só não varia mais de um índice
        (None, False),  # fora do cabeçalho do for
    ],
)
def test_zip_in_for_header_predicate(zip_header_args: int | None, expected: bool) -> None:
    fact = Fact("builtin:zip", 1, 13, 1, 16, call_args=2, zip_header_args=zip_header_args)
    condition = Condition(predicate="zip_in_for_header", params={"min": 2})

    assert holds(condition, fact) is expected


def test_missing_condition_always_holds() -> None:
    assert holds(None, Fact("node:For", 1, 1, 1, 4))


# --- Nomes legíveis -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fact", "text"),
    [
        ("node:Lambda", "lambda"),
        ("node:Assert", "assert"),
        ("node:Await", "await"),
        ("node:Desconhecido", "Desconhecido"),
        ("op:FloorDiv", "//"),
        ("op:Invert", "~"),
        ("cmp:NotIn", "not in"),
        ("builtin:eval", "eval()"),
        ("method:split", ".split()"),
        ("kwarg:print.sep", "sep= em print()"),
        ("kwarg:_.end", "end="),
        ("kwarg:**", "** em chamada"),
        ("const:complex", "número complexo"),
        ("const:int", "int"),
        ("param:vararg", "*args"),
        ("target:for_unpack", "desempacotamento no for"),
        ("derived:recursion", "recursão"),
        ("outro:x", "outro:x"),
    ],
)
def test_describe(fact: str, text: str) -> None:
    assert describe(fact) == text

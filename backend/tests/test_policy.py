"""Avaliador de política v1 (S4-01): precedência, categorias, deduplicação e corte."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.facts import Fact, extract_facts
from ipc_analyzer.engine.models import Violation
from ipc_analyzer.engine.parse import ParsedSource, parse_source
from ipc_analyzer.engine.policy import evaluate, judge
from ipc_analyzer.engine.ruleset import Category, CompiledRuleset, load_ruleset


def violations(source: str, list_number: int, ruleset: CompiledRuleset) -> list[Violation]:
    """Violações dos fatos. As exigências (R-02) têm testes próprios, no fim do arquivo."""
    result = analyze_source(source, list_number=list_number, ruleset=ruleset)
    return [v for v in result.violations if v.category is not Category.EXIGENCIA]


def summary(found: list[Violation]) -> list[tuple[str, str, int]]:
    return [(v.rule_id, v.category.value, v.line) for v in found]


# --- Precedência com o ruleset real ---------------------------------------------------------


@pytest.mark.parametrize("list_number", [1, 6])
def test_general_prohibition_annuls_in_every_list(
    base_ruleset: CompiledRuleset, list_number: int
) -> None:
    found = violations("try:\n    x = 1\nexcept:\n    x = 2\n", list_number, base_ruleset)

    assert summary(found) == [("R-06", "ANULACAO", 1)]


def test_permission_of_the_list_is_accepted(base_ruleset: CompiledRuleset) -> None:
    source = "x = int(input())\nif x > 0:\n    print(f'{x}', end='')\n"

    assert violations(source, 1, base_ruleset) == []


def test_permissions_are_cumulative(base_ruleset: CompiledRuleset) -> None:
    source = "for i in range(3):\n    if i % 2 == 0:\n        print(abs(i))\n"

    assert violations(source, 2, base_ruleset) == []


def test_construct_of_a_later_list_is_out_of_the_list(base_ruleset: CompiledRuleset) -> None:
    found = violations("x = 3\nwhile x > 0:\n    x -= 1\n", 1, base_ruleset)

    assert summary(found) == [("R-34", "FORA_DA_LISTA", 2)]
    assert found[0].allowed_from_list == 2
    assert found[0].message.endswith("a partir da Lista 2.")


def test_construct_absent_from_the_document_is_denied(base_ruleset: CompiledRuleset) -> None:
    found = violations("f = lambda x: x\n", 1, base_ruleset)

    assert summary(found) == [("R-04", "NAO_CONSTA", 1)]
    assert found[0].construct == "node:Lambda"
    assert found[0].message.startswith("'lambda' não consta no documento")


def test_eval_is_denied_by_default(base_ruleset: CompiledRuleset) -> None:
    found = violations("x = eval('1 + 1')\n", 1, base_ruleset)

    assert summary(found) == [("R-04", "NAO_CONSTA", 1)]
    assert found[0].construct == "builtin:eval"
    assert (found[0].col, found[0].end_col) == (5, 9)


def test_type_with_three_arguments_creates_a_class(base_ruleset: CompiledRuleset) -> None:
    found = violations("C = type('C', (), {})\n", 1, base_ruleset)

    assert ("R-09", "ANULACAO", 1) in summary(found)


def test_type_with_one_argument_is_allowed(base_ruleset: CompiledRuleset) -> None:
    assert violations("x = 1\nprint(type(x))\n", 1, base_ruleset) == []


def test_unmet_condition_uses_the_condition_message(base_ruleset: CompiledRuleset) -> None:
    found = violations("x = type(1, 2)\n", 1, base_ruleset)

    assert summary(found) == [("R-33", "NAO_CONSTA", 1)]
    assert found[0].message.startswith("type() só é permitido com 1 argumento")


def test_same_rule_at_the_same_position_is_reported_once(base_ruleset: CompiledRuleset) -> None:
    # node:With e node:withitem caem na R-04 na mesma posição.
    found = violations("with open('a') as f:\n    print(f)\n", 1, base_ruleset)

    assert summary(found) == [("R-04", "NAO_CONSTA", 1), ("R-04", "NAO_CONSTA", 1)]
    assert [v.construct for v in found] == ["node:With", "builtin:open"]


def test_violations_are_sorted_and_truncated(base_ruleset: CompiledRuleset) -> None:
    # Na Lista 2 não há exigência ativa: só as 5 violações R-13.
    parsed = parse_source("x = None\n" * 5, target=(3, 13))
    assert isinstance(parsed, ParsedSource)
    facts = extract_facts(parsed)

    found, truncated = evaluate(facts, base_ruleset, 2, max_violations=3)

    assert [v.line for v in found] == [1, 2, 3]
    assert truncated
    assert evaluate(facts, base_ruleset, 2)[1] is False


def test_structural_facts_are_accepted(base_ruleset: CompiledRuleset) -> None:
    fact = Fact("node:Module", 1, 1, 1, 1)

    assert judge(fact, base_ruleset, 1) is None


# --- Precedência com um ruleset sintético (until_list e condições) -------------------------


@pytest.fixture
def zip_ruleset(
    minimal_data: dict[str, Any], write_ruleset: Callable[[object], Path]
) -> CompiledRuleset:
    """Imita R-37 (zip condicional, Listas 2 a 4) e R-64 (zip livre a partir da Lista 5)."""
    minimal_data["rules"] += [
        {
            "id": "R-37",
            "name": "zip condicional",
            "effect": "allow",
            "since_list": 2,
            "until_list": 4,
            "match": [
                {
                    "fact": "builtin:zip",
                    "when": {
                        "predicate": "call_args",
                        "params": {"min": 2},
                        "message": "zip() só com duas ou mais sequências.",
                    },
                }
            ],
            "message": "zip() só a partir da Lista {allowed_from_list}.",
            "source": "Permissões, p.2",
        },
        {
            "id": "R-64",
            "name": "zip",
            "effect": "allow",
            "since_list": 5,
            "match": ["builtin:zip"],
            "message": "zip() livre só a partir da Lista {allowed_from_list}.",
            "source": "Permissões, p.3",
        },
    ]
    return load_ruleset(write_ruleset(minimal_data))


def _zip(args: int) -> Fact:
    return Fact("builtin:zip", 1, 1, 1, 4, call_args=args)


@pytest.mark.parametrize(
    ("args", "list_number", "expected"),
    [
        (2, 2, None),  # condição atendida na faixa da R-37
        (1, 2, ("R-37", Category.NAO_CONSTA, None)),  # regra atual com condição falha vence
        (1, 5, None),  # a R-64 libera a partir da Lista 5
        (2, 1, ("R-37", Category.FORA_DA_LISTA, 2)),  # primeira lista em que a condição vale
        (1, 1, ("R-64", Category.FORA_DA_LISTA, 5)),  # sem a condição, só a R-64 libera
    ],
)
def test_until_list_and_conditions(
    zip_ruleset: CompiledRuleset,
    args: int,
    list_number: int,
    expected: tuple[str, Category, int | None] | None,
) -> None:
    violation = judge(_zip(args), zip_ruleset, list_number)

    if expected is None:
        assert violation is None
    else:
        assert violation is not None
        assert (violation.rule_id, violation.category, violation.allowed_from_list) == expected


def test_condition_message_is_used_when_the_condition_fails(zip_ruleset: CompiledRuleset) -> None:
    violation = judge(_zip(1), zip_ruleset, 3)

    assert violation is not None
    assert violation.message == "zip() só com duas ou mais sequências."


# --- Exigências (R-02, Q-05; Sprint 12) ------------------------------------------------------


def all_violations(source: str, list_number: int, ruleset: CompiledRuleset) -> list[Violation]:
    return list(analyze_source(source, list_number=list_number, ruleset=ruleset).violations)


def test_missing_topic_of_the_list_is_a_requirement_violation(
    base_ruleset: CompiledRuleset,
) -> None:
    found = all_violations("n = int(input())\nprint(n * 2)\n", 1, base_ruleset)

    assert summary(found) == [("R-02", "EXIGENCIA", 1)]
    (requirement,) = found
    assert (requirement.line, requirement.col, requirement.end_line, requirement.end_col) == (
        1,
        1,
        1,
        1,
    )
    assert requirement.construct == "requirement:R-02"
    assert requirement.allowed_from_list is None
    assert requirement.message.startswith("A solução não usa o assunto da Lista 1")


@pytest.mark.parametrize(
    "source",
    [
        "n = int(input())\nif n > 0:\n    print(n)\n",
        "n = int(input())\nprint('par' if n % 2 == 0 else 'ímpar')\n",
    ],
    ids=["if", "ternario"],
)
def test_if_or_ternary_meets_the_requirement_of_list_1(
    base_ruleset: CompiledRuleset, source: str
) -> None:
    assert all_violations(source, 1, base_ruleset) == []


def test_requirement_comes_first_and_is_never_truncated(base_ruleset: CompiledRuleset) -> None:
    parsed = parse_source("x = None\n" * 5, target=(3, 13))
    assert isinstance(parsed, ParsedSource)

    found, truncated = evaluate(extract_facts(parsed), base_ruleset, 1, max_violations=1)

    assert [(v.rule_id, v.category) for v in found] == [("R-02", Category.EXIGENCIA)]
    assert truncated


def test_requirements_only_apply_to_their_list(base_ruleset: CompiledRuleset) -> None:
    # A Lista 2 ainda não tem exigência ativa (Sprint 20).
    assert all_violations("n = int(input())\nprint(n)\n", 2, base_ruleset) == []
    assert [r.id for r in base_ruleset.requirements_for(1)] == ["R-02"]
    assert base_ruleset.requirements_for(2) == ()

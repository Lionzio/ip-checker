"""Fidelidade do rulesets/2026.2/base.yaml ao catálogo R-xx e às decisões Q-02 a Q-07."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.ruleset import Category, CompiledRuleset, Effect, MetaKind


def _ids(first: int, last: int) -> set[str]:
    return {f"R-{number:02d}" for number in range(first, last + 1)}


def test_base_ruleset_metadata(base_ruleset: CompiledRuleset) -> None:
    ruleset = base_ruleset.ruleset

    assert ruleset.period == "2026.2"
    assert ruleset.target_python == "3.13"
    assert len(base_ruleset.sha256) == 64


def test_sprint_23_scope_is_the_whole_catalog(base_ruleset: CompiledRuleset) -> None:
    ruleset = base_ruleset.ruleset

    # R-01 (questão) fica para a Sprint 24; R-02 e R-68 são exigências, e R-03 e R-04, meta-regras.
    assert {rule.id for rule in ruleset.rules} == _ids(5, 67)
    assert {requirement.id for requirement in ruleset.requirements} == {"R-02", "R-68"}
    assert {meta.id for meta in ruleset.meta_rules} == {"R-03", "R-04"}
    assert {meta.kind for meta in ruleset.meta_rules} == {
        MetaKind.CUMULATIVE,
        MetaKind.DEFAULT_DENY,
    }


def test_general_prohibitions_annul_the_question(base_ruleset: CompiledRuleset) -> None:
    denied = {rule.id for rule in base_ruleset.ruleset.rules if rule.effect is Effect.DENY}

    assert denied == _ids(5, 14)
    for rule in base_ruleset.ruleset.rules:
        if rule.effect is Effect.DENY:
            assert rule.category is Category.ANULACAO


@pytest.mark.parametrize(
    ("first", "last", "since"), [(15, 33, 1), (34, 36, 2), (38, 58, 3), (59, 60, 4), (61, 67, 5)]
)
def test_permissions_start_at_their_list(
    base_ruleset: CompiledRuleset, first: int, last: int, since: int
) -> None:
    rules = {rule.id: rule for rule in base_ruleset.ruleset.rules}

    for rule_id in _ids(first, last):
        assert rules[rule_id].since_list == since
        assert rules[rule_id].until_list is None


@pytest.mark.parametrize(
    ("fact", "rule_ids"),
    [
        ("node:Import", {"R-05"}),  # Q-06: toda biblioteca anula, inclusive math
        ("node:Global", {"R-14"}),  # Q-03: só a instrução global
        ("const:None", {"R-13"}),
        ("call:star_args", {"R-10"}),  # Q-02 (h)
        ("kwarg:**", {"R-10"}),  # Q-02 (h)
        ("method:format", {"R-28"}),  # Q-02 (a)
        ("builtin:format", {"R-28"}),
        ("cmp:IsNot", {"R-17"}),  # Q-02 (b)
        ("cmp:NotIn", {"R-30"}),  # Q-02 (b)
        ("cmp:In", {"R-30", "R-36", "R-44"}),
        ("node:List", {"R-38", "R-39"}),  # matriz = lista de listas (5.2.3)
        ("node:Tuple", {"R-40"}),  # inclusive a atribuição múltipla (Q-02 d)
        ("call:user", {"R-59"}),
        ("op:Add", {"R-18", "R-21"}),
        ("kwarg:print.end", {"R-32"}),
        ("node:For", {"R-34"}),
        ("builtin:zip", {"R-37", "R-64"}),  # Q-04: condicional até a Lista 4, livre depois
        ("target:for_unpack", {"R-37", "R-63", "R-64", "R-65"}),  # Q-02 (d): zip, enumerate, items
        ("node:Dict", {"R-61"}),
        ("node:Lambda", {"R-67"}),
        ("method:items", {"R-65"}),
    ],
)
def test_mapping_decisions(base_ruleset: CompiledRuleset, fact: str, rule_ids: set[str]) -> None:
    assert {rule.id for rule in base_ruleset.rules_for(fact)} == rule_ids


@pytest.mark.parametrize(
    "fact",
    [
        "kwarg:print.sep",  # Q-02 (c): só end= consta
        "node:AsyncFor",  # C-01
        "node:GeneratorExp",  # Q-02 (e)
        "node:DictComp",  # Q-02 (e)
        "builtin:eval",
        "builtin:getattr",
        "builtin:__import__",
        "kwarg:sorted.key",  # Q-02 (c): key= não consta, nem com lambda (R-67)
        "kwarg:enumerate.start",  # Q-02 (c): só end= consta
    ],
)
def test_not_yet_permitted_facts_fall_to_default_deny(
    base_ruleset: CompiledRuleset, fact: str
) -> None:
    assert base_ruleset.rules_for(fact) == ()
    assert not base_ruleset.is_structural(fact)


def test_every_rule_cites_the_permissions_document(base_ruleset: CompiledRuleset) -> None:
    for rule in base_ruleset.ruleset.rules:
        assert rule.source.startswith("Permissões, p."), rule.id
    for meta in base_ruleset.ruleset.meta_rules:
        assert meta.source.startswith("Permissões, p."), meta.id


def test_conditions_of_the_ruleset(base_ruleset: CompiledRuleset) -> None:
    conditional = {
        (rule.id, fact, condition.predicate)
        for rule in base_ruleset.ruleset.rules
        for fact, condition in rule.matches()
        if condition is not None
    }

    assert conditional == {
        ("R-09", "builtin:type", "call_args"),  # Q-07: type() com 3 argumentos cria classe
        ("R-33", "builtin:type", "call_args"),
        ("R-37", "builtin:zip", "zip_in_for_header"),  # Q-04
        ("R-37", "target:for_unpack", "zip_in_for_header"),  # Q-02 (d)
        ("R-63", "target:for_unpack", "enumerate_in_for_header"),
        ("R-64", "target:for_unpack", "zip_in_for_header"),
        ("R-65", "target:for_unpack", "items_in_for_header"),
    }


def test_zip_condition_holds_from_list_2_to_4(base_ruleset: CompiledRuleset) -> None:
    conditional, free = base_ruleset.rules_for("builtin:zip")

    assert (conditional.id, conditional.since_list, conditional.until_list) == ("R-37", 2, 4)
    assert all(condition is not None for _, condition in conditional.matches())
    assert all(c.params == {"min": 2} for _, c in conditional.matches() if c)
    # Q-04: a partir da Lista 5, zip() é livre; o alvo "a, b" ainda pede o zip no for.
    assert (free.id, free.since_list, free.until_list) == ("R-64", 5, None)
    assert dict(free.matches())["builtin:zip"] is None


def test_recursion_is_decided_by_the_function_rules(base_ruleset: CompiledRuleset) -> None:
    # derived:recursion só serve à exigência da R-68; o def e a chamada são da R-59.
    assert base_ruleset.is_structural("derived:recursion")
    assert {rule.id for rule in base_ruleset.rules_for("call:user")} == {"R-59"}


def test_requirements_follow_q05(base_ruleset: CompiledRuleset) -> None:
    requirements = {
        requirement.list_number: set(requirement.require_any)
        for requirement in base_ruleset.ruleset.requirements
    }

    assert requirements == {
        1: {"node:If", "node:IfExp"},
        2: {"node:For", "node:While"},
        3: {"node:List", "node:Tuple", "node:ListComp", "builtin:list", "builtin:tuple"},
        4: {"node:FunctionDef"},
        5: {"node:Dict", "builtin:dict"},
        6: {"derived:recursion"},  # R-68, recursão direta ou mútua (C-03)
    }

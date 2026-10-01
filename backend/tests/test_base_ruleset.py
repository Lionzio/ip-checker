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


def test_sprint_1_scope_is_r03_to_r36(base_ruleset: CompiledRuleset) -> None:
    ruleset = base_ruleset.ruleset

    assert {rule.id for rule in ruleset.rules} == _ids(5, 36)
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


@pytest.mark.parametrize(("first", "last", "since"), [(15, 33, 1), (34, 36, 2)])
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
        ("cmp:In", {"R-30", "R-36"}),
        ("op:Add", {"R-18", "R-21"}),
        ("kwarg:print.end", {"R-32"}),
        ("node:For", {"R-34"}),
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
        "node:Lambda",  # só a partir da Lista 5
        "builtin:zip",  # R-37 entra na Sprint 13
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


def test_only_type_has_conditions_so_far(base_ruleset: CompiledRuleset) -> None:
    conditional = {
        (rule.id, fact, condition.predicate)
        for rule in base_ruleset.ruleset.rules
        for fact, condition in rule.matches()
        if condition is not None
    }

    assert conditional == {
        ("R-09", "builtin:type", "call_args"),  # Q-07: type() com 3 argumentos cria classe
        ("R-33", "builtin:type", "call_args"),
    }

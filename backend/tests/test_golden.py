"""Corpus golden (S4-02, NFR-18): especificação executável do documento de permissões.

Cada caso traz o código, a lista e as violações esperadas no formato ``R-xx CATEGORIA linha``.
A comparação é exata: qualquer violação a mais é falso positivo; a menos, falso negativo.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.ruleset import CompiledRuleset

GOLDEN = Path(__file__).parent / "golden"
EVASION_FILE = "evasion.yaml"
_EXPECT = re.compile(
    r"R-\d{2} (ANULACAO|PROIBIDO_NA_QUESTAO|FORA_DA_LISTA|NAO_CONSTA|EXIGENCIA) \d+"
)
_KEYS = {"id", "rule", "list", "code", "expect"}


def _load() -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(GOLDEN.glob("*.yaml")):
        for case in yaml.safe_load(path.read_text(encoding="utf-8")):
            cases.append((path.name, case))
    return cases


CASES = _load()


def test_cases_are_well_formed() -> None:
    ids = Counter(case["id"] for _, case in CASES)
    assert [case_id for case_id, count in ids.items() if count > 1] == []
    for _, case in CASES:
        assert set(case) == _KEYS, case.get("id")
        assert re.fullmatch(r"R-\d{2}", case["rule"]), case["id"]
        assert case["list"] in range(1, 7), case["id"]
        assert all(_EXPECT.fullmatch(item) for item in case["expect"]), case["id"]


def test_every_rule_of_the_ruleset_has_at_least_three_cases(base_ruleset: CompiledRuleset) -> None:
    per_rule = Counter(case["rule"] for name, case in CASES if name != EVASION_FILE)

    # Regras e exigências (R-02, R-68): cada uma com pelo menos três casos (NFR-18).
    ids = [rule.id for rule in base_ruleset.ruleset.rules]
    ids += [requirement.id for requirement in base_ruleset.ruleset.requirements]
    missing = {rule_id: per_rule[rule_id] for rule_id in ids if per_rule[rule_id] < 3}

    assert missing == {}


def test_evasion_corpus_has_at_least_thirty_cases() -> None:
    assert sum(1 for name, _ in CASES if name == EVASION_FILE) >= 30


@pytest.mark.parametrize("case", [case for _, case in CASES], ids=[case["id"] for _, case in CASES])
def test_golden_case(case: dict[str, Any], base_ruleset: CompiledRuleset) -> None:
    result = analyze_source(case["code"], list_number=case["list"], ruleset=base_ruleset)

    found = sorted(f"{v.rule_id} {v.category} {v.line}" for v in result.violations)

    assert found == sorted(case["expect"]), [
        (v.rule_id, v.construct, v.line, v.col) for v in result.violations
    ]

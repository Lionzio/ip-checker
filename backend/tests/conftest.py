from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from ipc_analyzer.engine.ruleset import CompiledRuleset, load_ruleset

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_RULESET = REPO_ROOT / "rulesets" / "2026.2" / "base.yaml"

_MINIMAL: dict[str, Any] = {
    "schema_version": 2,
    "ruleset_version": "2026.2.0",
    "period": "2026.2",
    "source_document": "Permissões das listas (teste)",
    "target_python": "3.13",
    "lists": {1: "L1", 2: "L2", 3: "L3", 4: "L4", 5: "L5", 6: "L6"},
    "structural_facts": ["node:Module", "node:Expr"],
    "meta_rules": [
        {
            "id": "R-04",
            "kind": "default_deny",
            "message": "'{construct}' não consta no documento.",
            "source": "Permissões, p.1",
        }
    ],
    "rules": [
        {
            "id": "R-06",
            "name": "try/except",
            "effect": "deny",
            "category": "ANULACAO",
            "match": ["node:Try"],
            "message": "try/except é proibido.",
            "source": "Permissões, p.1",
        },
        {
            "id": "R-34",
            "name": "Laços",
            "effect": "allow",
            "since_list": 2,
            "match": ["node:For", "node:While"],
            "message": "Laços só a partir da Lista {allowed_from_list}.",
            "source": "Permissões, p.2",
        },
    ],
}


@pytest.fixture
def minimal_data() -> dict[str, Any]:
    """Um ruleset válido e pequeno, que cada teste pode alterar."""
    return copy.deepcopy(_MINIMAL)


@pytest.fixture
def write_ruleset(tmp_path: Path) -> Callable[[object], Path]:
    def write(data: object) -> Path:
        path = tmp_path / "ruleset.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    return write


@pytest.fixture(scope="session")
def base_ruleset() -> CompiledRuleset:
    return load_ruleset(BASE_RULESET)

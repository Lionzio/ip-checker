"""Gabaritos reais de períodos anteriores com zero violação (Q-14, S20).

Só roda com ``IPC_GABARITOS_DIR``, a pasta do repositório privado dos gabaritos (``harness.py``).
Na CI, o job "Gabaritos" baixa esse repositório quando a variável ``GABARITOS_REPO`` está
definida, com a chave só de leitura do segredo ``GABARITOS_SSH_KEY`` (ADR-10). Gabaritos de listas
ainda não habilitadas ficam de fora. Cada gabarito usa o ruleset do seu período, quando existe a
pasta ``rulesets/<período>/`` (S31-11).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import RULESETS
from ipc_analyzer.engine.ruleset import CompiledRuleset
from ipc_api.settings import ApiSettings
from official_answers.harness import (
    Gabarito,
    PeriodRulesets,
    discover,
    load_exceptions,
    unexpected,
)

_DIR = os.environ.get("IPC_GABARITOS_DIR", "")
ROOT = Path(_DIR) if _DIR else None
GABARITOS, MISPLACED = discover(ROOT) if ROOT is not None else ([], [])
ENABLED = ApiSettings().enabled_lists

pytestmark = pytest.mark.skipif(
    ROOT is None,
    reason="IPC_GABARITOS_DIR não definido: os gabaritos ficam num repositório privado",
)


def test_the_repository_is_organized() -> None:
    assert ROOT is not None
    assert ROOT.is_dir(), "IPC_GABARITOS_DIR não é uma pasta"
    assert GABARITOS, "nenhum gabarito em <período>/lista-<n>/*.py"
    assert MISPLACED == [], "arquivos .py fora de uma pasta lista-<n>"
    paths = {gabarito.path for gabarito in GABARITOS}
    assert sorted(set(load_exceptions(ROOT)) - paths) == [], "exceção para arquivo inexistente"


@pytest.fixture(scope="module")
def rulesets(base_ruleset: CompiledRuleset) -> PeriodRulesets:
    return PeriodRulesets(RULESETS, base_ruleset)


@pytest.mark.parametrize("gabarito", GABARITOS, ids=[gabarito.path for gabarito in GABARITOS])
def test_gabarito_has_no_violation(gabarito: Gabarito, rulesets: PeriodRulesets) -> None:
    assert ROOT is not None
    if gabarito.list_number not in ENABLED:
        pytest.skip(f"Lista {gabarito.list_number} ainda não habilitada")
    allowed = load_exceptions(ROOT).get(gabarito.path, frozenset())

    assert unexpected(gabarito, rulesets.for_gabarito(gabarito), allowed) == []

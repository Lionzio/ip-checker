"""Avaliação das condições das regras (5.2.3), com os predicados do registro ``predicates.py``."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ipc_analyzer.engine.facts import Fact
from ipc_analyzer.engine.predicates import REGISTRY, Check
from ipc_analyzer.engine.ruleset import Condition

#: Nome do predicado -> a função que o confere (o mesmo registro que o carregador usa).
PREDICATES: Mapping[str, Check] = MappingProxyType(
    {name: predicate.check for name, predicate in REGISTRY.items()}
)


def holds(condition: Condition | None, fact: Fact) -> bool:
    """Indica se a condição vale para o fato; sem condição, o fato casa sempre."""
    return condition is None or PREDICATES[condition.predicate](fact, condition.params)

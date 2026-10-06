"""Biblioteca fechada de predicados contextuais (5.2.3).

O ruleset só pode citar predicados daqui (``ruleset.KNOWN_PREDICATES``). Criar um predicado novo
exige código, teste e ADR; mudar parâmetros de um predicado existente é só dado.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType

from ipc_analyzer.engine.facts import Fact
from ipc_analyzer.engine.ruleset import Condition

Predicate = Callable[[Fact, Mapping[str, int]], bool]


def _call_args(fact: Fact, params: Mapping[str, int]) -> bool:
    """O fato é a função de uma chamada com número de argumentos entre ``min`` e ``max``."""
    if fact.call_args is None:
        return False
    low = params.get("min", 0)
    high = params.get("max")
    return fact.call_args >= low and (high is None or fact.call_args <= high)


def _zip_in_for_header(fact: Fact, params: Mapping[str, int]) -> bool:
    """O fato é o ``zip()`` que serve de iterável a um ``for`` (ou o alvo desse ``for``), com
    ``min`` ou mais sequências: "zip() somente para variar mais de um índice no comando for" (R-37).
    """
    return fact.zip_header_args is not None and fact.zip_header_args >= params["min"]


def _enumerate_in_for_header(fact: Fact, _params: Mapping[str, int]) -> bool:
    """O fato é o alvo de um ``for`` cujo iterável é ``enumerate(...)`` (R-63, Sprint 23)."""
    return fact.for_header == "enumerate"


def _items_in_for_header(fact: Fact, _params: Mapping[str, int]) -> bool:
    """O fato é o alvo de um ``for`` cujo iterável é ``x.items()`` (R-65, Sprint 23)."""
    return fact.for_header == "items"


PREDICATES: Mapping[str, Predicate] = MappingProxyType(
    {
        "call_args": _call_args,
        "zip_in_for_header": _zip_in_for_header,
        "enumerate_in_for_header": _enumerate_in_for_header,
        "items_in_for_header": _items_in_for_header,
    }
)


def holds(condition: Condition | None, fact: Fact) -> bool:
    """Indica se a condição vale para o fato; sem condição, o fato casa sempre."""
    return condition is None or PREDICATES[condition.predicate](fact, condition.params)

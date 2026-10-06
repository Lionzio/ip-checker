"""Registro único dos predicados contextuais (5.2.3, complemento da ADR-02; S24-02).

Cada predicado diz, para um fato, se a condição de uma regra vale (ex.: ``zip()`` como iterável do
``for``, R-37). O ruleset só pode citar predicados daqui, com os parâmetros declarados aqui: o
carregador (``ruleset.py``) valida contra este registro, e as condições (``conditions.py``) chamam
a função dele. Criar um predicado novo exige código, teste e ADR; mudar os parâmetros que uma regra
usa é só dado.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ipc_analyzer.engine.facts import Fact

Check = Callable[[Fact, Mapping[str, int]], bool]


@dataclass(frozen=True, slots=True)
class Predicate:
    #: Parâmetros que o ruleset pode passar (``params`` da condição).
    params: frozenset[str]
    check: Check


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


REGISTRY: Mapping[str, Predicate] = MappingProxyType(
    {
        "call_args": Predicate(frozenset({"min", "max"}), _call_args),
        "zip_in_for_header": Predicate(frozenset({"min"}), _zip_in_for_header),
        "enumerate_in_for_header": Predicate(frozenset(), _enumerate_in_for_header),
        "items_in_for_header": Predicate(frozenset(), _items_in_for_header),
    }
)

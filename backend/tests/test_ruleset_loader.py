"""Comportamento genérico do carregador de ruleset (FR-15): validação, fail-fast e imutabilidade."""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ipc_analyzer.engine.ruleset import (
    Category,
    Effect,
    Requirement,
    RulesetError,
    load_ruleset,
)

Writer = Callable[[object], Path]


def test_minimal_ruleset_loads_and_indexes_facts(
    minimal_data: dict[str, Any], write_ruleset: Writer
) -> None:
    path = write_ruleset(minimal_data)

    compiled = load_ruleset(path)

    assert compiled.version == "2026.2.0"
    assert compiled.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert [rule.id for rule in compiled.rules_for("node:For")] == ["R-34"]
    assert compiled.rules_for("node:Try")[0].effect is Effect.DENY
    assert compiled.rules_for("node:Try")[0].category is Category.ANULACAO
    assert compiled.rules_for("node:Lambda") == ()
    assert compiled.is_structural("node:Module")
    assert not compiled.is_structural("node:For")
    assert compiled.default_deny.id == "R-04"


def test_compiled_ruleset_is_immutable(minimal_data: dict[str, Any], write_ruleset: Writer) -> None:
    compiled = load_ruleset(write_ruleset(minimal_data))
    rule = compiled.rules_for("node:For")[0]

    with pytest.raises(TypeError):
        compiled.by_fact["node:For"] = ()  # type: ignore[index]
    with pytest.raises(ValidationError):
        rule.since_list = 1  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        compiled.sha256 = "x"  # type: ignore[misc]


def _first_rule(data: dict[str, Any]) -> dict[str, Any]:
    rule: dict[str, Any] = data["rules"][0]
    return rule


def _second_rule(data: dict[str, Any]) -> dict[str, Any]:
    rule: dict[str, Any] = data["rules"][1]
    return rule


def _conditional(
    fact: str, predicate: str = "call_args", params: dict[str, int] | None = None
) -> dict[str, Any]:
    when: dict[str, Any] = {"predicate": predicate}
    if params is not None:
        when["params"] = params
    return {"fact": fact, "when": when}


def test_conditional_facts_may_share_a_fact_between_allow_and_deny(
    minimal_data: dict[str, Any], write_ruleset: Writer
) -> None:
    _first_rule(minimal_data)["match"] = [
        "node:Try",
        _conditional("builtin:type", params={"min": 3}),
    ]
    _second_rule(minimal_data)["match"] = [_conditional("builtin:type", params={"max": 1})]

    compiled = load_ruleset(write_ruleset(minimal_data))

    matches = compiled.matches_for("builtin:type")
    assert [(m.rule.id, m.condition.params if m.condition else None) for m in matches] == [
        ("R-06", {"min": 3}),
        ("R-34", {"max": 1}),
    ]
    assert compiled.rules_for("node:Try")[0].unconditional_facts() == {"node:Try"}


INVALID_CASES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("id repetido", lambda d: _second_rule(d).update(id="R-06"), "id de regra repetido"),
    ("deny com since_list", lambda d: _first_rule(d).update(since_list=1), "não aceita since"),
    ("deny sem ANULACAO", lambda d: _first_rule(d).update(category="NAO_CONSTA"), "ANULACAO"),
    ("allow sem since_list", lambda d: _second_rule(d).pop("since_list"), "precisa de since_list"),
    (
        "allow com category",
        lambda d: _second_rule(d).update(category="ANULACAO"),
        "não tem category",
    ),
    ("until < since", lambda d: _second_rule(d).update(until_list=1), "until_list"),
    ("fato malformado", lambda d: _second_rule(d).update(match=["for"]), "fato malformado"),
    ("tipo desconhecido", lambda d: _second_rule(d).update(match=["foo:For"]), "tipo de fato"),
    ("nó inexistente", lambda d: _second_rule(d).update(match=["node:Fro"]), "fato inexistente"),
    ("nó obsoleto", lambda d: _second_rule(d).update(match=["node:Num"]), "fato inexistente"),
    ("nó abstrato", lambda d: _second_rule(d).update(match=["node:expr"]), "fato inexistente"),
    ("operador como nó", lambda d: _second_rule(d).update(match=["node:Add"]), "fato inexistente"),
    ("nó como operador", lambda d: _second_rule(d).update(match=["op:For"]), "fato inexistente"),
    ("built-in inexistente", lambda d: _second_rule(d).update(match=["builtin:lenn"]), "inexist"),
    ("constante inválida", lambda d: _second_rule(d).update(match=["const:list"]), "inexist"),
    ("kwarg sem função", lambda d: _second_rule(d).update(match=["kwarg:end"]), "inexist"),
    ("fato repetido", lambda d: _second_rule(d).update(match=["node:For", "node:For"]), "repetido"),
    (
        "predicado desconhecido",
        lambda d: _second_rule(d).update(match=[_conditional("builtin:zip", "zip_anywhere")]),
        "predicado desconhecido",
    ),
    (
        "zip_in_for_header sem min",
        lambda d: _second_rule(d).update(match=[_conditional("builtin:zip", "zip_in_for_header")]),
        "min maior ou igual a 1",
    ),
    (
        "zip_in_for_header com max",
        lambda d: _second_rule(d).update(
            match=[_conditional("builtin:zip", "zip_in_for_header", {"min": 2, "max": 3})]
        ),
        "parâmetro desconhecido",
    ),
    (
        "parâmetro desconhecido",
        lambda d: _second_rule(d).update(match=[_conditional("builtin:type", params={"n": 1})]),
        "parâmetro desconhecido",
    ),
    (
        "call_args sem limites",
        lambda d: _second_rule(d).update(match=[_conditional("builtin:type")]),
        "min ou max",
    ),
    (
        "call_args com min maior que max",
        lambda d: _second_rule(d).update(
            match=[_conditional("builtin:type", params={"min": 3, "max": 1})]
        ),
        "maior que max",
    ),
    (
        "condição no nível da regra",
        lambda d: _second_rule(d).update(when={"predicate": "call_args"}),
        "Extra inputs",
    ),
    ("marcador desconhecido", lambda d: _second_rule(d).update(message="Lista {x}"), "marcador"),
    ("mensagem vazia", lambda d: _second_rule(d).update(message="  "), "message"),
    (
        "allow e deny no mesmo fato",
        lambda d: _second_rule(d).update(match=["node:For", "node:Try"]),
        "permitidos e proibidos",
    ),
    (
        "fato estrutural numa regra",
        lambda d: _second_rule(d).update(match=["node:Expr"]),
        "fato estrutural",
    ),
    ("estrutural repetido", lambda d: d.update(structural_facts=["node:Expr"] * 2), "repetido"),
    ("sem default_deny", lambda d: d.update(meta_rules=[]), "default_deny"),
    (
        "default_deny sem mensagem",
        lambda d: d["meta_rules"][0].pop("message"),
        "default_deny",
    ),
    (
        "meta-regra repetida",
        lambda d: d["meta_rules"].append(dict(d["meta_rules"][0])),
        "meta-regra repetido",
    ),
    (
        "tipo de meta-regra repetido",
        lambda d: d["meta_rules"].append({**d["meta_rules"][0], "id": "R-03"}),
        "uma vez",
    ),
    (
        "id de regra e meta-regra",
        lambda d: _second_rule(d).update(id="R-04"),
        "regra e como meta-regra",
    ),
    ("listas incompletas", lambda d: d["lists"].pop(6), "Listas 1 a 6"),
    ("versão de outro período", lambda d: d.update(ruleset_version="2027.1.0"), "período"),
    ("chave desconhecida", lambda d: d.update(extra_key=1), "extra"),
    ("schema antigo", lambda d: d.update(schema_version=1), "schema_version"),
    ("sem regras", lambda d: d.update(rules=[]), "rules"),
]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [pytest.param(mutate, expected, id=name) for name, mutate, expected in INVALID_CASES],
)
def test_invalid_ruleset_fails_fast(
    minimal_data: dict[str, Any],
    write_ruleset: Writer,
    mutate: Callable[[dict[str, Any]], None],
    expected: str,
) -> None:
    mutate(minimal_data)

    with pytest.raises(RulesetError, match=expected):
        load_ruleset(write_ruleset(minimal_data))


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RulesetError, match="não foi possível ler"):
        load_ruleset(tmp_path / "nao-existe.yaml")


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "ruleset.yaml"
    path.write_text("rules: [unclosed", encoding="utf-8")

    with pytest.raises(RulesetError, match="YAML inválido"):
        load_ruleset(path)


def test_yaml_root_must_be_a_mapping(write_ruleset: Writer) -> None:
    with pytest.raises(RulesetError, match="mapeamento YAML"):
        load_ruleset(write_ruleset(["não", "é", "mapeamento"]))


def test_yaml_never_builds_python_objects(tmp_path: Path) -> None:
    path = tmp_path / "ruleset.yaml"
    path.write_text("!!python/object/apply:os.system ['echo invadido']\n", encoding="utf-8")

    with pytest.raises(RulesetError, match="YAML inválido"):
        load_ruleset(path)


def test_requirement_uses_list_alias() -> None:
    requirement = Requirement.model_validate(
        {
            "id": "R-68",
            "list": 6,
            "require_any": ["derived:recursion"],
            "message": "Toda questão da Lista 6 precisa de recursão.",
            "source": "Permissões, p.3",
        }
    )

    assert requirement.list_number == 6
    assert requirement.require_any == ("derived:recursion",)

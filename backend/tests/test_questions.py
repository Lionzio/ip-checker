"""Regras por questão (S24-01; R-01, FR-11, US-04, US-13): cadastro, validação e precedência.

Cada teste copia o ``base.yaml`` real para uma pasta temporária e escreve ao lado dela as
questões de ``questions/``; o ruleset do repositório não tem questões reais cadastradas.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from conftest import BASE_RULESET
from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import UnknownQuestionError
from ipc_analyzer.engine.ruleset import CompiledRuleset, RulesetError, load_ruleset
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings

Loader = Callable[..., CompiledRuleset]

L3_Q2: dict[str, Any] = {
    "question_id": "L3-Q2",
    "list": 3,
    "title": "Soma dos pares",
    "source": "Enunciado da L3-Q2: use map() para converter a entrada; não use append().",
    "allow_facts": ["builtin:map"],
    "deny": ["R-46"],
}


@pytest.fixture
def ruleset_dir(tmp_path: Path) -> Path:
    shutil.copy(BASE_RULESET, tmp_path / "base.yaml")
    (tmp_path / "questions").mkdir()
    return tmp_path


@pytest.fixture
def load(ruleset_dir: Path) -> Loader:
    def write_and_load(*questions: dict[str, Any], names: tuple[str, ...] = ()) -> CompiledRuleset:
        for index, question in enumerate(questions):
            name = names[index] if index < len(names) else question["question_id"]
            path = ruleset_dir / "questions" / f"{name}.yaml"
            path.write_text(yaml.safe_dump(question, allow_unicode=True), encoding="utf-8")
        return load_ruleset(ruleset_dir / "base.yaml")

    return write_and_load


def summary(
    code: str, ruleset: CompiledRuleset, list_number: int, question: str | None
) -> list[str]:
    result = analyze_source(code, list_number=list_number, ruleset=ruleset, question_id=question)
    return [f"{v.rule_id} {v.category} {v.line}" for v in result.violations]


# --- Cadastro e carga (US-13) --------------------------------------------------------------------


def test_questions_load_next_to_the_base_ruleset(load: Loader) -> None:
    ruleset = load(L3_Q2, {**L3_Q2, "question_id": "L3-Q10", "title": "Outra"})

    assert [q.id for q in ruleset.questions_for(3)] == ["L3-Q2", "L3-Q10"]
    assert ruleset.questions_for(4) == ()
    question = ruleset.questions["L3-Q2"]
    assert question.denied["method:append"] == "R-46"
    assert question.allowed["builtin:map"] == (None,)
    assert question.releases == ()


def test_a_question_changes_the_ruleset_fingerprint(load: Loader) -> None:
    without = load_ruleset(BASE_RULESET)

    assert load(L3_Q2).sha256 != without.sha256
    assert load(L3_Q2).version == without.version


def test_releasing_a_general_prohibition_is_flagged(load: Loader) -> None:
    question = {**L3_Q2, "allow": ["R-11"], "allow_facts": ["node:Try"], "deny": []}

    # C-02: liberar R-05 a R-14 exige professor; a CI e o ipc-rules mostram isso.
    assert load(question).questions["L3-Q2"].releases == ("R-06", "R-11")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"question_id": "L3-Q2", "list": 4}, "é da Lista 3"),
        ({"question_id": "Q2"}, "question_id"),
        ({"allow": ["R-99"]}, "R-99 não existe"),
        ({"allow": ["R-02"]}, "não é uma regra de permissão"),
        ({"allow": ["R-68"]}, "não é uma regra de permissão"),
        ({"deny": ["R-05"]}, "já é proibida em todas as listas"),
        ({"deny": ["node:Name"]}, "estrutural"),
        ({"allow_facts": ["node:Expr"], "deny": []}, "estrutural"),
        ({"allow_facts": ["builtin:mapp"]}, "fato inexistente"),
        ({"allow_facts": ["method:append"]}, "liberados e proibidos ao mesmo tempo"),
        ({"allow": [], "allow_facts": [], "deny": []}, "pelo menos um item"),
        ({"deny": ["R-46", "R-46"]}, "item repetido"),
        ({"source": "  "}, "source"),
        ({"message": "{allowed_from_list}"}, "marcador desconhecido"),
        ({"extra": 1}, "extra"),
    ],
)
def test_invalid_questions_stop_the_analyzer(
    load: Loader, change: dict[str, Any], message: str
) -> None:
    with pytest.raises(RulesetError, match=message) as error:
        load({**L3_Q2, **change})

    # O erro aponta o arquivo da questão.
    assert f"{(change.get('question_id') or 'L3-Q2')}.yaml" in str(error.value)


def test_the_file_name_must_be_the_question_id(load: Loader) -> None:
    with pytest.raises(RulesetError, match=r"precisa estar no arquivo L3-Q2.yaml"):
        load(L3_Q2, names=("questao-2",))


# --- Precedência (R-01, C-02) ---------------------------------------------------------------


CODE_L3 = "v = list(map(int, input().split()))\nv.append(1)\nprint(sum(v))\n"


def test_without_the_question_only_the_list_rules_apply(load: Loader) -> None:
    ruleset = load(L3_Q2)

    # map() não consta no documento (R-04); append() é permitido na Lista 3.
    assert summary(CODE_L3, ruleset, 3, None) == ["R-04 NAO_CONSTA 1"]


def test_the_question_allows_and_denies_over_the_list(load: Loader) -> None:
    ruleset = load(L3_Q2)

    assert summary(CODE_L3, ruleset, 3, "L3-Q2") == ["R-01 PROIBIDO_NA_QUESTAO 2"]
    result = analyze_source(CODE_L3, list_number=3, ruleset=ruleset, question_id="L3-Q2")
    assert (
        result.violations[0].message
        == "'.append()' é proibido nesta questão (L3-Q2), pelo enunciado."
    )


def test_a_custom_message_for_the_question(load: Loader) -> None:
    ruleset = load({**L3_Q2, "message": "A {question_id} pede outra forma: sem {construct}."})
    result = analyze_source(CODE_L3, list_number=3, ruleset=ruleset, question_id="L3-Q2")

    assert result.violations[0].message == "A L3-Q2 pede outra forma: sem .append()."


def test_allowing_a_rule_of_a_later_list_keeps_its_condition(load: Loader) -> None:
    question = {
        **L3_Q2,
        "question_id": "L1-Q1",
        "list": 1,
        "allow": ["R-37"],
        "allow_facts": [],
        "deny": [],
    }
    ruleset = load(question)
    in_header = "a = input()\nb = input()\nfor x, y in zip(a, b):\n    print(x if x else y)\n"
    outside = "a = input()\nz = zip(a, a)\nprint(z if z else a)\n"

    # A R-37 libera o zip no for (com a condição dela), não qualquer zip: fora do for, ele
    # continua sendo da Lista 5 (R-64). O for em si continua R-34.
    assert summary(in_header, ruleset, 1, "L1-Q1") == ["R-34 FORA_DA_LISTA 3"]
    assert "R-64 FORA_DA_LISTA 2" in summary(outside, ruleset, 1, "L1-Q1")


def test_a_question_can_release_a_general_prohibition(load: Loader) -> None:
    question = {
        **L3_Q2,
        "question_id": "L2-Q4",
        "list": 2,
        "allow": ["R-11"],
        "allow_facts": [],
        "deny": [],
    }
    ruleset = load(question)
    code = "for i in range(3):\n    if i == 1:\n        break\n    print(i)\n"

    assert summary(code, ruleset, 2, None) == ["R-11 ANULACAO 3"]
    assert summary(code, ruleset, 2, "L2-Q4") == []


def test_the_question_does_not_waive_the_topic_requirement(load: Loader) -> None:
    ruleset = load(L3_Q2)

    assert summary("print(1)\n", ruleset, 3, "L3-Q2") == ["R-02 EXIGENCIA 1"]


def test_unknown_question_or_question_of_another_list(load: Loader) -> None:
    ruleset = load(L3_Q2)

    with pytest.raises(UnknownQuestionError, match="não está cadastrada"):
        analyze_source("x = 1\n", list_number=3, ruleset=ruleset, question_id="L3-Q9")
    with pytest.raises(UnknownQuestionError, match="é da Lista 3, não da Lista 4"):
        analyze_source("x = 1\n", list_number=4, ruleset=ruleset, question_id="L3-Q2")


# --- Analisador (manifesto e análise com questão) ------------------------------------------


@pytest.fixture
def service(load: Loader, ruleset_dir: Path) -> Iterator[TestClient]:
    load(L3_Q2)
    settings = AnalyzerSettings(ruleset_path=ruleset_dir / "base.yaml", pool=PoolConfig(workers=1))
    with TestClient(create_app(settings)) as client:
        yield client


def test_the_manifest_lists_the_questions(service: TestClient) -> None:
    lists = service.get("/internal/ruleset/manifest").json()["lists"]

    assert lists[2]["questions"] == [{"id": "L3-Q2", "title": "Soma dos pares"}]
    assert all(item["questions"] == [] for item in lists if item["number"] != 3)


def test_the_analyzer_applies_the_question(service: TestClient) -> None:
    body = {"code": CODE_L3, "list_number": 3, "question_id": "L3-Q2"}

    response = service.post("/internal/analyze", json=body)

    assert response.status_code == 200
    assert [v["rule_id"] for v in response.json()["violations"]] == ["R-01"]
    refused = service.post("/internal/analyze", json={**body, "question_id": "L3-Q9"})
    assert (refused.status_code, refused.json()["error"]["code"]) == (422, "UNKNOWN_QUESTION")

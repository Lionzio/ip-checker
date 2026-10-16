"""O período na API pública (S43-02; ADR-12, US-39).

Sem período, tudo como antes: o ativo. Com um período anterior carregado, as regras, as questões e
as listas são as dele, e o pedido ao analisador leva o período. Fora da janela, 422
``UNKNOWN_PERIOD`` com os períodos disponíveis na mensagem.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from ipc_api.feedback.cache import result_key
from ipc_api.settings import ApiSettings
from ipc_api.telemetry import Telemetry, TelemetryEvent

#: Só as Listas 1 a 3 habilitadas no período ativo, para ver que um anterior não segue isso.
SETTINGS = ApiSettings(analyzer_url="http://analyzer.test", enabled_lists=frozenset({1, 2, 3}))


def _lists(question: dict[str, str] | None, at: int) -> list[dict[str, Any]]:
    return [
        {
            "number": n,
            "title": f"Lista {n}",
            "questions": [question] if question and n == at else [],
        }
        for n in range(1, 7)
    ]


ACTIVE_LISTS = _lists({"id": "L3-Q2", "title": "Soma dos pares"}, 3)
EARLIER_LISTS = _lists({"id": "L3-Q9", "title": "Maior de três"}, 3)
MANIFEST = {
    "ruleset_version": "2027.1.0",
    "ruleset_sha256": "a" * 64,
    "period": "2027.1",
    "target_python": "3.13",
    "lists": ACTIVE_LISTS,
    "periods": [
        {
            "period": "2027.1",
            "active": True,
            "ruleset_version": "2027.1.0",
            "ruleset_sha256": "a" * 64,
            "lists": ACTIVE_LISTS,
        },
        {
            "period": "2026.2",
            "active": False,
            "ruleset_version": "2026.2.7",
            "ruleset_sha256": "b" * 64,
            "lists": EARLIER_LISTS,
        },
    ],
}


class Analyzer:
    """O analisador simulado, que guarda o corpo de cada pedido."""

    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/internal/ruleset/manifest":
            return httpx2.Response(200, json=MANIFEST)
        body = json.loads(request.content)
        self.bodies.append(body)
        if request.url.path == "/internal/analyze":
            version = "2026.2.7" if body.get("period") == "2026.2" else "2027.1.0"
            return httpx2.Response(
                200,
                json={
                    "ruleset_version": version,
                    "status": "valid",
                    "list_number": body["list_number"],
                    "syntax_error": None,
                    "violations": [],
                    "truncated": False,
                },
            )
        if request.url.path == "/internal/similarity":
            return httpx2.Response(
                200,
                json={
                    "status": "compared",
                    "percent": 40.0,
                    "token_counts": [120, 130],
                    "syntax_error_side": None,
                    "syntax_error": None,
                },
            )
        raise AssertionError(request.url.path)


@pytest.fixture
def analyzer() -> Analyzer:
    return Analyzer()


@pytest.fixture
def api(analyzer: Analyzer) -> Iterator[TestClient]:
    app, store = make_app(SETTINGS, analyzer_transport=httpx2.MockTransport(analyzer))
    with authed_client(app, store) as client:
        yield client


def _validate(api: TestClient, **body: Any) -> httpx2.Response:
    return api.post("/api/v1/validate", json={"code": "x = 1\n", "list_number": 1, **body})


def test_without_a_period_everything_uses_the_active_one(
    api: TestClient, analyzer: Analyzer
) -> None:
    answer = _validate(api, question_id=None)

    assert answer.status_code == 200
    assert answer.json()["ruleset_version"] == "2027.1.0"
    assert "period" not in analyzer.bodies[-1]  # o pedido ao analisador é o mesmo de antes


def test_a_late_list_uses_the_rules_and_questions_of_its_period(
    api: TestClient, analyzer: Analyzer
) -> None:
    """Critério 1: com o ativo em 2027.1, a L3-Q9 de 2026.2 é verificada com as regras de 2026.2."""
    answer = api.post(
        "/api/v1/validate",
        json={"code": "x = 1\n", "list_number": 3, "question_id": "L3-Q9", "period": "2026.2"},
    )

    assert answer.status_code == 200, answer.json()
    assert answer.json()["ruleset_version"] == "2026.2.7"
    assert analyzer.bodies[-1]["period"] == "2026.2"
    assert analyzer.bodies[-1]["question_id"] == "L3-Q9"


def test_a_question_of_another_period_is_unknown(api: TestClient) -> None:
    answer = api.post(
        "/api/v1/validate", json={"code": "x = 1\n", "list_number": 3, "question_id": "L3-Q9"}
    )

    assert answer.status_code == 422
    assert answer.json()["error"]["code"] == "UNKNOWN_QUESTION"


def test_an_earlier_period_accepts_every_list_it_has(api: TestClient) -> None:
    assert _validate(api, list_number=5).json()["error"]["code"] == "LIST_NOT_ENABLED"
    assert _validate(api, list_number=5, period="2026.2").status_code == 200


@pytest.mark.parametrize("period", ["2025.2", "2027.2"])
def test_a_period_out_of_the_window_is_refused(
    api: TestClient, analyzer: Analyzer, period: str
) -> None:
    answer = _validate(api, period=period)

    assert answer.status_code == 422
    assert answer.json()["error"]["code"] == "UNKNOWN_PERIOD"
    assert "2027.1, 2026.2" in answer.json()["error"]["message"]
    assert analyzer.bodies == []  # nada chegou ao analisador


def test_a_malformed_period_is_invalid_input(api: TestClient) -> None:
    assert _validate(api, period="26.2").json()["error"]["code"] == "INVALID_INPUT"


def test_the_batch_uses_the_period_too(api: TestClient, analyzer: Analyzer) -> None:
    answer = api.post(
        "/api/v1/validate/batch",
        json={
            "list_number": 4,
            "period": "2026.2",
            "files": [{"name": "ana.py", "code": "x = 1\n"}],
        },
    )

    assert answer.status_code == 200, answer.json()
    assert answer.json()["ruleset_version"] == "2026.2.7"
    assert analyzer.bodies[-1]["period"] == "2026.2"


def test_the_pair_comparison_checks_the_period(api: TestClient, analyzer: Analyzer) -> None:
    pair = {"code_a": "a = 1\n", "code_b": "b = 1\n"}

    assert api.post("/api/v1/similarity", json=pair).status_code == 200
    assert "period" not in analyzer.bodies[-1]
    assert api.post("/api/v1/similarity", json={**pair, "period": "2026.2"}).status_code == 200
    assert analyzer.bodies[-1]["period"] == "2026.2"
    refused = api.post("/api/v1/similarity", json={**pair, "period": "2020.1"})
    assert refused.json()["error"]["code"] == "UNKNOWN_PERIOD"


def test_the_feedback_refuses_an_unknown_period(api: TestClient) -> None:
    answer = api.post(
        "/api/v1/feedback",
        json={"code": "x = 1\n", "list_number": 1, "student_name": "Ana", "period": "2019.1"},
    )

    assert answer.json()["error"]["code"] == "UNKNOWN_PERIOD"


def test_the_periods_route_lists_the_loaded_ones(api: TestClient) -> None:
    assert api.get("/api/v1/periods").json() == [
        {"period": "2027.1", "active": True, "ruleset_version": "2027.1.0"},
        {"period": "2026.2", "active": False, "ruleset_version": "2026.2.7"},
    ]


def test_the_lists_of_an_earlier_period_are_all_of_its_lists(api: TestClient) -> None:
    active = api.get("/api/v1/lists").json()
    earlier = api.get("/api/v1/lists", params={"period": "2026.2"}).json()

    assert [item["number"] for item in active] == [1, 2, 3]  # só as habilitadas
    assert [item["number"] for item in earlier] == [1, 2, 3, 4, 5, 6]
    assert earlier[2]["questions"] == [{"id": "L3-Q9", "title": "Maior de três"}]
    assert (
        api.get("/api/v1/lists", params={"period": "2020.1"}).json()["error"]["code"]
        == "UNKNOWN_PERIOD"
    )


def test_the_feedback_cache_does_not_mix_periods() -> None:
    assert result_key("x = 1\n", 3, "L3-Q9", "2026.2") != result_key(
        "x = 1\n", 3, "L3-Q9", "2027.1"
    )


def test_the_current_version_never_goes_back_to_an_earlier_period() -> None:
    """O painel por lista e as recusas usam a versão atual: uma verificação de 2026.2 não a muda."""
    telemetry = Telemetry(None)  # sem destino: só a versão atual importa aqui
    for version in ("2027.1.0", "2026.2.7", "2027.1.10", "2027.1.9"):
        telemetry.record(
            TelemetryEvent.from_result(ruleset_version=version, list_number=1, outcome="valid")
        )

    assert telemetry.ruleset_version == "2027.1.10"

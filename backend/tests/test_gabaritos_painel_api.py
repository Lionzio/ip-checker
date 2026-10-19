"""Os gabaritos pelo painel (Sprint 51, S51-02; ADR-17), pela API e com o analisador de verdade.

A chefia salva e lê o código; o analisador confere ao salvar e as regras acionadas ficam
registradas; a equipe vê só a existência, quem salvou e as regras; o monitor nunca recebe o
código, nem por chamada direta. O gabarito salvo passa a valer na verificação na hora.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import BASE_URL, COOKIE, make_app, member, open_session
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.accounts.models import Role
from ipc_api.accounts.store import MemoryAccountStore

BASE = "/api/v1/gabaritos"
ONE = f"{BASE}/2026.2/L1-Q1/notion"
#: Um texto que só existe no gabarito: nunca pode sair para um monitor, um log ou a lista.
CANARY = "CANARIO_GABARITO_51"
VALID = f"# {CANARY}\nnota = float(input())\nif nota >= 7:\n    print('Aprovado')\n"
#: Um laço na Lista 1: as regras R-34 e R-35 na linha 2 (e a R-02, sem if, na linha 1).
WITH_LOOP = f"# {CANARY}\nx = 1\nfor i in range(3):\n    print(i)\n"
LEADERSHIP = [Role.MONITOR_CHEFE, Role.PROFESSOR, Role.DESENVOLVEDOR]


@pytest.fixture(scope="module")
def analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as client:
        yield client


def _bridge(analyzer: TestClient) -> httpx2.MockTransport:
    def bridge(request: httpx2.Request) -> httpx2.Response:
        answer = analyzer.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={"Content-Type": "application/json"},
        )
        return httpx2.Response(
            answer.status_code,
            content=answer.content,
            headers={"Content-Type": answer.headers["content-type"]},
        )

    return httpx2.MockTransport(bridge)


@pytest.fixture
def api(analyzer: TestClient) -> Iterator[tuple[MemoryAccountStore, TestClient]]:
    app, store = make_app(analyzer_transport=_bridge(analyzer))
    with TestClient(app, base_url=BASE_URL) as client:
        yield store, client


def login(client: TestClient, store: MemoryAccountStore, role: Role | None) -> None:
    client.cookies.set(COOKIE, open_session(store, member(store, role=role, name=f"Conta {role}")))


def error_of(response: Any) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


@pytest.mark.parametrize("role", LEADERSHIP)
def test_leadership_saves_a_gabarito_checked_by_the_analyzer(api: Any, role: Role) -> None:
    store, client = api
    login(client, store, role)

    response = client.put(ONE, json={"code": VALID})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["violations"] == []
    assert (body["question_id"], body["kind"], body["source"]) == ("L1-Q1", "notion", "painel")
    assert body["updated_by_name"] == f"Conta {role}"
    assert "code" not in body
    assert client.get(ONE).json()["code"] == VALID


def test_the_rules_the_gabarito_triggers_are_recorded_with_their_lines(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)

    body = client.put(f"{BASE}/2026.2/L1-Q2/ip_cc", json={"code": WITH_LOOP}).json()

    hits = {(item["rule_id"], item["line"]) for item in body["violations"]}
    assert {("R-34", 3), ("R-35", 3)} <= hits
    assert CANARY not in str(body)


def test_the_team_sees_who_and_when_but_never_the_code(api: Any) -> None:
    store, client = api
    login(client, store, Role.MONITOR_CHEFE)
    client.put(ONE, json={"code": VALID})
    client.put(f"{BASE}/2026.2/L1-Q1/ip_cc", json={"code": WITH_LOOP})
    login(client, store, Role.MONITOR)

    listed = client.get(f"{BASE}/2026.2")

    assert listed.status_code == 200
    assert [(i["question_id"], i["kind"]) for i in listed.json()["items"]] == [
        ("L1-Q1", "notion"),
        ("L1-Q1", "ip_cc"),
    ]
    assert CANARY not in listed.text
    assert "print(" not in listed.text


@pytest.mark.parametrize("role", [Role.MONITOR, None])
def test_a_monitor_never_reads_saves_or_deletes(api: Any, role: Role | None) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)
    client.put(ONE, json={"code": VALID})
    login(client, store, role)

    for response in (
        client.get(ONE),
        client.put(ONE, json={"code": VALID}),
        client.delete(ONE),
    ):
        assert error_of(response) == (403, "FORBIDDEN")
        assert CANARY not in response.text


def test_without_a_session_nothing(api: Any) -> None:
    _, client = api

    for response in (client.get(f"{BASE}/2026.2"), client.get(ONE)):
        assert error_of(response) == (401, "UNAUTHENTICATED")


def test_deleting_removes_it_and_the_second_time_is_404(api: Any) -> None:
    store, client = api
    login(client, store, Role.DESENVOLVEDOR)
    client.put(ONE, json={"code": VALID})

    assert client.delete(ONE).status_code == 204
    assert error_of(client.delete(ONE)) == (404, "GABARITO_NOT_FOUND")
    assert error_of(client.get(ONE)) == (404, "GABARITO_NOT_FOUND")
    assert client.get(f"{BASE}/2026.2").json()["items"] == []


@pytest.mark.parametrize(
    ("path", "code", "expected"),
    [
        (ONE, "   \n", (422, "INVALID_INPUT")),
        (ONE, "if x\n    y = 1\n", (422, "INVALID_INPUT")),
        (ONE, "x = 1\x00\n", (422, "INVALID_INPUT")),
        (ONE, "#" + "a" * 51_200, (413, "PAYLOAD_TOO_LARGE")),
        (f"{BASE}/2025.1/L1-Q1/notion", VALID, (422, "UNKNOWN_PERIOD")),
        (f"{BASE}/2026.2/L7-Q1/notion", VALID, (422, "INVALID_INPUT")),
        (f"{BASE}/2026.2/L1-Q1/chatgpt", VALID, (422, "INVALID_INPUT")),
        (f"{BASE}/2026.3/L1-Q1/notion", VALID, (422, "INVALID_INPUT")),
    ],
    ids=["vazio", "sintaxe", "nulo", "grande", "periodo", "lista", "tipo", "formato"],
)
def test_what_is_not_a_gabarito_is_refused_and_nothing_is_saved(
    api: Any, path: str, code: str, expected: tuple[int, str]
) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)

    assert error_of(client.put(path, json={"code": code})) == expected
    assert client.get(f"{BASE}/2026.2").json()["items"] == []


def test_a_syntax_error_says_the_line(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)

    message = client.put(ONE, json={"code": "x = 1\nif x\n    y = 1\n"}).json()["error"]["message"]

    assert "linha 2" in message


def test_the_saved_gabarito_counts_in_the_verification_right_away(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)
    student = {"code": "nota = float(input())\nif nota > 6:\n    print('Ok')\n", "list_number": 1}

    before = client.post("/api/v1/validate", json={**student, "question_id": "L1-Q1"})
    client.put(ONE, json={"code": VALID})
    after = client.post("/api/v1/validate", json={**student, "question_id": "L1-Q1"})
    client.delete(ONE)
    gone = client.post("/api/v1/validate", json={**student, "question_id": "L1-Q1"})

    assert error_of(before) == (422, "UNKNOWN_QUESTION")
    assert after.json()["gabarito"]["status"] == "compared"
    assert CANARY not in after.text
    assert error_of(gone) == (422, "UNKNOWN_QUESTION")


def test_without_the_analyzer_nothing_is_saved() -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("analyzer parado", request=request)

    app, store = make_app(analyzer_transport=httpx2.MockTransport(refuse))
    with TestClient(app, base_url=BASE_URL) as client:
        login(client, store, Role.PROFESSOR)

        assert error_of(client.put(ONE, json={"code": VALID})) == (503, "ANALYZER_UNAVAILABLE")
        assert client.get(f"{BASE}/2026.2").json()["items"] == []


def test_the_code_never_reaches_the_logs(
    api: Any, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    store, client = api
    login(client, store, Role.PROFESSOR)

    client.put(ONE, json={"code": VALID})
    client.get(ONE)
    client.delete(ONE)

    out, err = capfd.readouterr()
    assert CANARY not in out + err + caplog.text
    assert "gabarito 2026.2 L1-Q1 notion salvo: 0 regra(s)" in caplog.text


# --- Os dois gabaritos na comparação (Sprint 51, S51-03) ------------------------------------------

#: Um gabarito "IP CC" bem diferente do aluno; o "Notion" (VALID) é quase igual.
FAR = f"# {CANARY}\nx = int(input())\nwhile x > 0:\n    print(x)\n    x -= 1\n"
STUDENT = "media = float(input())\nif media >= 7:\n    print('Ok')\n"


def test_with_two_gabaritos_the_verification_says_which_was_closer(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)
    client.put(f"{BASE}/2026.2/L1-Q1/ip_cc", json={"code": FAR})
    client.put(ONE, json={"code": VALID})

    body = client.post(
        "/api/v1/validate", json={"code": STUDENT, "list_number": 1, "question_id": "L1-Q1"}
    ).json()

    assert body["gabarito"]["status"] == "compared"
    assert body["gabarito"]["kind"] == "notion"
    assert body["gabarito"]["similarity"] >= 90
    assert CANARY not in str(body)


def test_with_only_ip_cc_the_comparison_says_ip_cc(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)
    client.put(f"{BASE}/2026.2/L1-Q1/ip_cc", json={"code": VALID})

    body = client.post(
        "/api/v1/validate", json={"code": STUDENT, "list_number": 1, "question_id": "L1-Q1"}
    ).json()

    assert body["gabarito"]["kind"] == "ip_cc"


def test_the_plagiarism_panel_says_which_gabarito_each_side_matched(api: Any) -> None:
    store, client = api
    login(client, store, Role.PROFESSOR)
    client.put(ONE, json={"code": VALID})
    client.put(f"{BASE}/2026.2/L1-Q1/ip_cc", json={"code": FAR})
    near_far = "y = int(input())\nwhile y > 0:\n    print(y)\n    y -= 1\n"

    body = client.post(
        "/api/v1/similarity",
        json={"code_a": STUDENT, "code_b": near_far, "question_id": "L1-Q1"},
    ).json()

    assert body["gabarito"]["status"] == "compared"
    assert (body["gabarito"]["a"]["kind"], body["gabarito"]["b"]["kind"]) == ("notion", "ip_cc")
    assert CANARY not in str(body)

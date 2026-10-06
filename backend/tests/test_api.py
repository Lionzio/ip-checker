"""API pública (S8-01): validação, mapeamento de erros e desconfiança da resposta do analyzer.

O analyzer é substituído por um transporte simulado, para provocar cada falha possível. Os testes
com o analyzer de verdade ficam em ``test_api_contract.py``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from ipc_api.settings import ApiSettings

Handler = Callable[[httpx2.Request], httpx2.Response]

SETTINGS = ApiSettings(analyzer_url="http://analyzer.test")
VALID = {
    "ruleset_version": "2026.2.0",
    "status": "valid",
    "list_number": 1,
    "syntax_error": None,
    "violations": [],
    "truncated": False,
}
VIOLATION = {
    "rule_id": "R-34",
    "category": "FORA_DA_LISTA",
    "line": 1,
    "col": 1,
    "end_line": 2,
    "end_col": 13,
    "construct": "node:For",
    "allowed_from_list": 2,
    "message": "Laços de repetição (for, while) só são permitidos a partir da Lista 2.",
}
INVALID = {**VALID, "status": "invalid", "violations": [VIOLATION]}
MANIFEST = {
    "ruleset_version": "2026.2.0",
    "ruleset_sha256": "a" * 64,
    "period": "2026.2",
    "target_python": "3.13",
    "lists": [{"number": n, "title": f"Lista {n}"} for n in range(1, 7)],
}
HEALTH = {
    "status": "ok",
    "ruleset_version": "2026.2.0",
    "ruleset_sha256": "a" * 64,
    "target_python": "3.13",
    "workers": 2,
}
REQUEST_ID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


class FakeAnalyzer:
    """Analyzer simulado: responde por rota e conta as chamadas."""

    def __init__(self, routes: dict[str, Handler]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.calls.append(request.url.path)
        return self.routes[request.url.path](request)


def reply(status: int, body: Any) -> Handler:
    return lambda _request: httpx2.Response(status, json=body)


def fail(error: type[httpx2.RequestError]) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error("simulado", request=request)

    return handler


@pytest.fixture
def analyzer() -> FakeAnalyzer:
    return FakeAnalyzer(
        {
            "/internal/analyze": reply(200, VALID),
            "/internal/health": reply(200, HEALTH),
            "/internal/ruleset/manifest": reply(200, MANIFEST),
        }
    )


def make_client(analyzer: FakeAnalyzer, settings: ApiSettings = SETTINGS) -> TestClient:
    app, store = make_app(settings, analyzer_transport=httpx2.MockTransport(analyzer))
    return authed_client(app, store)


@pytest.fixture
def client(analyzer: FakeAnalyzer) -> Iterator[TestClient]:
    with make_client(analyzer) as test_client:
        yield test_client


def validate(client: TestClient, **body: Any) -> httpx2.Response:
    payload = {"code": "x = 1\n", "list_number": 1, **body}
    # json.dumps escapa tudo em ASCII: assim até um surrogate sozinho (\ud800) chega à API.
    return client.post(
        "/api/v1/validate",
        content=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# --- Caminho feliz ----------------------------------------------------------------------------


def test_valid_code(client: TestClient, analyzer: FakeAnalyzer) -> None:
    response = validate(client)

    assert response.status_code == 200
    body = response.json()
    assert REQUEST_ID.match(body["request_id"])
    assert body | {"request_id": None} == {
        "request_id": None,
        "ruleset_version": "2026.2.0",
        "status": "valid",
        "list_number": 1,
        "question_id": None,
        "notices": ["QUESTION_RULES_NOT_APPLIED"],
        "syntax_error": None,
        "violations": [],
        "truncated": False,
    }
    assert response.headers["X-Request-Id"] == body["request_id"]
    assert response.headers["Cache-Control"] == "no-store"
    assert analyzer.calls == ["/internal/analyze"]


def test_violations_pass_through_unchanged(client: TestClient, analyzer: FakeAnalyzer) -> None:
    analyzer.routes["/internal/analyze"] = reply(200, INVALID)

    body = validate(client, code="for i in range(3):\n    print(i)\n").json()

    assert body["status"] == "invalid"
    assert body["violations"] == [VIOLATION]


def test_each_request_has_its_own_id(client: TestClient) -> None:
    first, second = validate(client), validate(client)

    assert first.headers["X-Request-Id"] != second.headers["X-Request-Id"]


# --- Validação da API, antes do analyzer -------------------------------------------------------


def test_list_not_enabled(analyzer: FakeAnalyzer) -> None:
    settings = ApiSettings(analyzer_url="http://analyzer.test", enabled_lists=frozenset({1, 2}))
    with make_client(analyzer, settings) as client:
        response = validate(client, list_number=5)

    assert error_of(response) == (422, "LIST_NOT_ENABLED")
    assert "Lista 5" in response.json()["error"]["message"]
    assert analyzer.calls == []


def test_enabled_lists_come_from_settings(analyzer: FakeAnalyzer) -> None:
    analyzer.routes["/internal/analyze"] = reply(200, {**VALID, "list_number": 5})
    settings = ApiSettings(analyzer_url="http://analyzer.test", enabled_lists=frozenset({1, 5}))

    with make_client(analyzer, settings) as client:
        assert validate(client, list_number=5).status_code == 200


def test_unknown_question(client: TestClient, analyzer: FakeAnalyzer) -> None:
    assert error_of(validate(client, question_id="L1-Q3")) == (422, "UNKNOWN_QUESTION")
    assert analyzer.calls == []


@pytest.mark.parametrize(
    ("code", "status", "code_name"),
    [
        ("#" + "a" * 51_200, 413, "PAYLOAD_TOO_LARGE"),
        ("#" + "é" * 25_600, 413, "PAYLOAD_TOO_LARGE"),
        ("   \n\t", 422, "INVALID_INPUT"),
        ("x = 1\x00", 422, "INVALID_INPUT"),
        ("x = 1\n" * 1_001, 422, "INVALID_INPUT"),
        ("x = 1\r\n" * 1_001, 422, "INVALID_INPUT"),
        ("x = '\ud800'", 422, "INVALID_INPUT"),
    ],
    ids=[
        "51201-bytes",
        "utf8-51201",
        "vazio",
        "nulo",
        "1001-linhas",
        "1001-linhas-crlf",
        "surrogate",
    ],
)
def test_code_limits_are_checked_before_the_analyzer(
    client: TestClient, analyzer: FakeAnalyzer, code: str, status: int, code_name: str
) -> None:
    assert error_of(validate(client, code=code)) == (status, code_name)
    assert analyzer.calls == []


@pytest.mark.parametrize(
    "code",
    ["x = 1\n" * 1_000, "#" + "a" * 51_199, "﻿#" + "a" * 51_199],
    ids=["1000-linhas", "51200-bytes", "bom-nao-conta"],
)
def test_code_at_the_limits_reaches_the_analyzer(
    client: TestClient, analyzer: FakeAnalyzer, code: str
) -> None:
    assert validate(client, code=code).status_code == 200
    assert analyzer.calls == ["/internal/analyze"]


@pytest.mark.parametrize(
    "payload",
    [
        {"list_number": 1},
        {"code": 1, "list_number": 1},
        {"code": "x = 1", "list_number": 0},
        {"code": "x = 1", "list_number": 7},
        {"code": "x = 1", "list_number": "1"},
        {"code": "x = 1", "list_number": True},
        {"code": "x = 1", "list_number": 1, "extra": True},
        {"code": "x = 1", "list_number": 1, "question_id": "../etc/passwd"},
        {"code": "x = 1", "list_number": 1, "question_id": "Q" * 33},
        [],
    ],
    ids=[
        "sem-code",
        "code-numerico",
        "lista-0",
        "lista-7",
        "lista-texto",
        "lista-booleana",
        "campo-extra",
        "questao-com-barra",
        "questao-longa",
        "lista-json",
    ],
)
def test_malformed_requests_are_invalid_input(client: TestClient, payload: Any) -> None:
    response = client.post("/api/v1/validate", json=payload)

    assert error_of(response) == (422, "INVALID_INPUT")
    assert response.json()["error"]["retry_after_s"] is None


@pytest.mark.parametrize(
    "body",
    [b'{"code": "x = \xff", "list_number": 1}', b'{"code": "x"', b""],
    ids=["utf8", "json", "vazio"],
)
def test_unparseable_bodies_are_invalid_input(client: TestClient, body: bytes) -> None:
    response = client.post(
        "/api/v1/validate", content=body, headers={"Content-Type": "application/json"}
    )

    assert error_of(response) == (422, "INVALID_INPUT")


# --- Limite de corpo (DoD, item 1) -------------------------------------------------------------


def test_declared_body_above_128kb_is_refused_before_reading(
    client: TestClient, analyzer: FakeAnalyzer
) -> None:
    body = json.dumps({"code": "#" + "a" * 140_000, "list_number": 1}).encode()

    response = client.post(
        "/api/v1/validate", content=body, headers={"Content-Type": "application/json"}
    )

    assert error_of(response) == (413, "PAYLOAD_TOO_LARGE")
    assert "128 KB" in response.json()["error"]["message"]
    assert REQUEST_ID.match(response.headers["X-Request-Id"])
    assert analyzer.calls == []


def test_streamed_body_above_128kb_is_cut_while_reading(
    client: TestClient, analyzer: FakeAnalyzer
) -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"code": "#'
        for _ in range(20):
            yield b"a" * 10_000
        yield b'", "list_number": 1}'

    # Sem Content-Length: o corpo chega em partes e o limite vale durante a leitura.
    response = client.post(
        "/api/v1/validate", content=chunks(), headers={"Content-Type": "application/json"}
    )

    assert error_of(response) == (413, "PAYLOAD_TOO_LARGE")
    assert analyzer.calls == []


# --- Respostas do analyzer ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("analyzer_status", "analyzer_code"),
    [(422, "ANALYSIS_LIMIT"), (422, "INVALID_INPUT"), (413, "PAYLOAD_TOO_LARGE")],
)
def test_analyzer_contract_errors_reach_the_student(
    client: TestClient, analyzer: FakeAnalyzer, analyzer_status: int, analyzer_code: str
) -> None:
    analyzer.routes["/internal/analyze"] = reply(
        analyzer_status, {"error": {"code": analyzer_code, "message": "explicação do analyzer"}}
    )

    response = validate(client)

    assert error_of(response) == (analyzer_status, analyzer_code)
    assert response.json()["error"]["message"] == "explicação do analyzer"


def _unavailable(response: httpx2.Response) -> None:
    assert error_of(response) == (503, "ANALYZER_UNAVAILABLE")
    assert response.json()["error"]["retry_after_s"] == 30
    assert response.headers["Retry-After"] == "30"


@pytest.mark.parametrize(
    "handler",
    [
        fail(httpx2.ConnectError),
        fail(httpx2.ReadTimeout),
        fail(httpx2.RemoteProtocolError),
        reply(500, {"detail": "Internal Server Error"}),
        reply(404, {"detail": "Not Found"}),
        reply(503, {"error": {"code": "ANALYZER_UNAVAILABLE", "message": "pool parado"}}),
        reply(422, {"error": {"code": "QUALQUER_OUTRO", "message": "x"}}),
        reply(422, {"detail": "formato do FastAPI"}),
        reply(200, {"status": "valid"}),
        reply(200, {**VALID, "status": "valid", "violations": [VIOLATION]}),
        reply(200, {**INVALID, "violations": []}),
        reply(200, {**VALID, "list_number": 2}),
        reply(200, {**VALID, "segredo": "campo a mais"}),
        reply(200, {**INVALID, "violations": [VIOLATION] * 201}),
        reply(200, {**INVALID, "violations": [{**VIOLATION, "rule_id": "<script>"}]}),
        lambda _request: httpx2.Response(200, content=b"isto nao e json"),
        lambda _request: httpx2.Response(200, content=b'{"x": "' + b"a" * 300_000 + b'"}'),
    ],
    ids=[
        "conexao-recusada",
        "tempo-esgotado",
        "protocolo",
        "500",
        "404",
        "503",
        "422-codigo-desconhecido",
        "422-sem-envelope",
        "200-incompleta",
        "valid-com-violacoes",
        "invalid-sem-violacoes",
        "outra-lista",
        "campo-a-mais",
        "201-violacoes",
        "rule-id-estranho",
        "nao-json",
        "acima-de-256kb",
    ],
)
def test_untrustworthy_analyzer_answers_become_unavailable(
    client: TestClient, analyzer: FakeAnalyzer, handler: Handler
) -> None:
    analyzer.routes["/internal/analyze"] = handler

    _unavailable(validate(client))


def test_stopped_analyzer_is_unavailable() -> None:
    # Critério da S8-01 com uma conexão de verdade: nada escuta na porta 9 desta máquina.
    settings = ApiSettings(analyzer_url="http://127.0.0.1:9", analyzer_timeout_s=3.0)

    app, store = make_app(settings)
    with authed_client(app, store) as client:
        _unavailable(validate(client))
        assert client.get("/health").status_code == 200
        _unavailable(client.get("/ready"))


# --- Listas, health e ready --------------------------------------------------------------------


def test_lists_show_only_enabled_lists(client: TestClient) -> None:
    response = client.get("/api/v1/lists")

    assert response.status_code == 200
    assert response.json() == [{"number": n, "title": f"Lista {n}"} for n in range(1, 7)]


def test_lists_follow_enabled_lists_setting(analyzer: FakeAnalyzer) -> None:
    settings = ApiSettings(analyzer_url="http://analyzer.test", enabled_lists=frozenset({1, 5}))

    with make_client(analyzer, settings) as client:
        numbers = [item["number"] for item in client.get("/api/v1/lists").json()]

    assert numbers == [1, 5]


def test_manifest_is_cached(client: TestClient, analyzer: FakeAnalyzer) -> None:
    client.get("/api/v1/lists")
    client.get("/api/v1/lists")

    assert analyzer.calls == ["/internal/ruleset/manifest"]


@pytest.mark.parametrize(
    "handler",
    [fail(httpx2.ConnectError), reply(500, {}), reply(200, {**MANIFEST, "lists": "todas"})],
    ids=["fora-do-ar", "500", "fora-do-esquema"],
)
def test_lists_unavailable_without_analyzer(
    client: TestClient, analyzer: FakeAnalyzer, handler: Handler
) -> None:
    analyzer.routes["/internal/ruleset/manifest"] = handler

    _unavailable(client.get("/api/v1/lists"))


def test_health_does_not_depend_on_the_analyzer(client: TestClient, analyzer: FakeAnalyzer) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert analyzer.calls == []


def test_ready_reports_the_ruleset(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "ruleset_version": "2026.2.0", "release": None}
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "handler",
    [fail(httpx2.ConnectError), reply(503, {}), reply(200, {"status": "ok"})],
    ids=["fora-do-ar", "503", "fora-do-esquema"],
)
def test_ready_is_unavailable_when_the_analyzer_is_not(
    client: TestClient, analyzer: FakeAnalyzer, handler: Handler
) -> None:
    analyzer.routes["/internal/health"] = handler

    _unavailable(client.get("/ready"))


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/internal/analyze"])
def test_no_documentation_or_internal_routes_are_exposed(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert REQUEST_ID.match(response.headers["X-Request-Id"])

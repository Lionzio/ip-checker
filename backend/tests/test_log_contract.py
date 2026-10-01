"""Contrato dos logs (S9-01, NFR-11, DoD item 13): esquema fixo e nenhum código ou IP gravado.

O teste canário manda à API, ligada ao analyzer de verdade, todo tipo de requisição com um
marcador escondido no código, na URL, nos cabeçalhos e na questão, e confere que o marcador e o
IP aparecem 0 vezes em tudo o que os dois serviços escreveram.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import BASE_RULESET
from ipc_analyzer import logging as analyzer_logging
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api import logging as api_logging
from ipc_api.app import create_app
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

CANARY = "CANARIO7F3A"
CLIENT_IP = "203.0.113.77"
#: Os testes daqui mandam centenas de requisições de um mesmo cliente; o limite de taxa tem
#: os próprios testes (test_api_rate_limit.py).
UNLIMITED = ApiSettings(rate_limit=RateLimitConfig(client_per_min=1_000_000, ip_per_min=1_000_000))
REQUEST_FIELDS = {
    "timestamp",
    "level",
    "logger",
    "event",
    "service",
    "request_id",
    "method",
    "path",
    "status",
    "latency_ms",
    "payload_bytes",
    "outcome",
}


def json_lines(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


@pytest.fixture(scope="module")
def analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as client:
        yield client


def bridged_api(analyzer: TestClient) -> FastAPI:
    def bridge(request: httpx2.Request) -> httpx2.Response:
        answer = analyzer.request(
            request.method, request.url.path, content=request.content, headers=request.headers
        )
        return httpx2.Response(
            answer.status_code,
            content=answer.content,
            headers={"Content-Type": answer.headers["content-type"]},
        )

    return create_app(UNLIMITED, analyzer_transport=httpx2.MockTransport(bridge))


def send_everything(api: TestClient) -> list[httpx2.Response]:
    """Toda forma de resposta do contrato, sempre com o marcador em algum lugar da requisição."""
    headers = {
        "X-Forwarded-For": CLIENT_IP,
        "X-Real-IP": CLIENT_IP,
        "User-Agent": f"{CANARY}-navegador",
        "X-Request-Id": CANARY,
        "Referer": f"http://{CANARY}.example/",
    }

    def validate(code: str, list_number: int = 1, **extra: Any) -> httpx2.Response:
        payload = {"code": code, "list_number": list_number, **extra}
        return api.post(
            "/api/v1/validate",
            content=json.dumps(payload).encode(),
            headers={**headers, "Content-Type": "application/json"},
        )

    return [
        validate(f"# {CANARY}\nx = '{CANARY}'\n"),
        validate(f"y = input().{CANARY}()\n"),
        validate(f"{CANARY} = (\n"),
        validate("(" * 1_000 + CANARY + ")" * 1_000),
        validate(f"# {CANARY}" + "a" * 51_200),
        validate(f"{CANARY}\x00"),
        validate(f"{CANARY}\x1b"),
        validate(f"x = '{CANARY}'\n", list_number=2),
        validate(f"x = '{CANARY}'\n", question_id=CANARY),
        validate(f"x = '{CANARY}'\n", extra=CANARY),
        api.post(
            "/api/v1/validate",
            content=b'{"code": "' + CANARY.encode() + b'", "x": "' + b"a" * 140_000 + b'"}',
            headers={**headers, "Content-Type": "application/json"},
        ),
        api.get(f"/api/v1/{CANARY}", headers=headers),
        api.get(f"/api/v1/lists?q={CANARY}", headers=headers),
        api.get("/ready", headers=headers),
        api.get("/health", headers=headers),
    ]


def test_canary_never_reaches_the_logs(
    analyzer: TestClient, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with TestClient(bridged_api(analyzer)) as api:
        responses = send_everything(api)

    # O marcador volta ao aluno quando faz parte do relatório dele (prova de que foi analisado)...
    assert CANARY in responses[1].text
    # ...mas não aparece em nada que os serviços escreveram.
    out, err = capfd.readouterr()
    written = out + err + caplog.text
    assert json_lines(out), "nenhuma linha de log JSON foi escrita"
    assert written.count(CANARY) == 0
    assert written.count(CLIENT_IP) == 0
    assert "testclient" not in written  # o "IP" que o TestClient informa ao servidor


def test_canary_never_reaches_the_logs_when_the_analyzer_is_down(
    capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(f"recusado {request.content!r}", request=request)

    app = create_app(ApiSettings(), analyzer_transport=httpx2.MockTransport(refuse))
    with TestClient(app) as api:
        response = api.post("/api/v1/validate", json={"code": f"x = '{CANARY}'", "list_number": 1})

    assert response.status_code == 503
    out, err = capfd.readouterr()
    assert (out + err + caplog.text).count(CANARY) == 0


def test_every_log_line_follows_the_schema(
    analyzer: TestClient, capfd: pytest.CaptureFixture[str]
) -> None:
    with TestClient(bridged_api(analyzer)) as api:
        response = api.post(
            "/api/v1/validate",
            json={"code": "for i in range(3):\n    print(i)\n", "list_number": 1},
        )
    lines = json_lines(capfd.readouterr().out)

    assert lines
    for line in lines:
        assert set(line) <= api_logging.LOG_FIELDS, line
        assert "dropped_fields" not in line, line

    request_id = response.headers["X-Request-Id"]
    (api_line,) = [x for x in lines if x["service"] == "api" and x.get("request_id") == request_id]
    assert set(api_line) >= REQUEST_FIELDS
    assert api_line | {"timestamp": None, "latency_ms": None} == {
        "timestamp": None,
        "level": "info",
        "logger": "ipc_api.access",
        "event": "request",
        "service": "api",
        "request_id": request_id,
        "method": "POST",
        "path": "/api/v1/validate",
        "status": 200,
        "latency_ms": None,
        "payload_bytes": len(b'{"code":"for i in range(3):\\n    print(i)\\n","list_number":1}'),
        "list_number": 1,
        "ruleset_version": "2026.2.0",
        "outcome": "invalid",
    }
    assert isinstance(api_line["latency_ms"], float)

    # O analyzer registra a mesma requisição com o mesmo id: os dois logs se ligam sem o código.
    (analysis,) = [x for x in lines if x["service"] == "analyzer" and x["event"] == "analysis"]
    assert analysis["request_id"] == request_id
    assert analysis["outcome"] == "invalid"
    assert analysis["violations"] == 3  # R-02 (sem if), R-34 e R-35
    assert analysis["payload_bytes"] == len(b"for i in range(3):\n    print(i)\n")


@pytest.mark.parametrize(
    ("payload", "outcome", "status"),
    [
        ({"code": "x = 1\n", "list_number": 2}, "LIST_NOT_ENABLED", 422),
        ({"code": "(" * 1_000 + ")" * 1_000, "list_number": 1}, "ANALYSIS_LIMIT", 422),
        ({"code": "#" + "a" * 51_200, "list_number": 1}, "PAYLOAD_TOO_LARGE", 413),
        ({"list_number": 1}, "INVALID_INPUT", 422),
    ],
    ids=["lista", "limite", "tamanho", "invalido"],
)
def test_errors_are_logged_with_their_code(
    analyzer: TestClient,
    capfd: pytest.CaptureFixture[str],
    payload: dict[str, Any],
    outcome: str,
    status: int,
) -> None:
    with TestClient(bridged_api(analyzer)) as api:
        response = api.post("/api/v1/validate", json=payload)

    request_id = response.headers["X-Request-Id"]
    (line,) = [
        x
        for x in json_lines(capfd.readouterr().out)
        if x.get("request_id") == request_id and x["service"] == "api"
    ]
    assert (line["outcome"], line["status"]) == (outcome, status)


def test_unknown_paths_are_not_logged_verbatim(capfd: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(ApiSettings())) as api:
        api.get(f"/{CANARY}/../etc/passwd")

    (line,) = [x for x in json_lines(capfd.readouterr().out) if x["event"] == "request"]
    assert line["path"] == "outra"
    assert line["status"] == 404


# --- Filtro de campos --------------------------------------------------------------------------


@pytest.mark.parametrize("module", [api_logging, analyzer_logging], ids=["api", "analyzer"])
def test_fields_outside_the_schema_are_dropped(module: Any) -> None:
    clean = module.keep_allowed_fields(
        None, "info", {"event": "x", "code": CANARY, "client_ip": CLIENT_IP, "status": 200}
    )

    assert clean == {"event": "x", "status": 200, "dropped_fields": ["client_ip", "code"]}


def test_structured_logger_cannot_leak_code(capfd: pytest.CaptureFixture[str]) -> None:
    api_logging.configure_logging()

    api_logging.get_logger("teste").info("descuido", code=CANARY, ip=CLIENT_IP, status=1)

    (line,) = json_lines(capfd.readouterr().out)
    assert line["dropped_fields"] == ["code", "ip"]
    assert CANARY not in json.dumps(line)


@pytest.mark.parametrize("module", [api_logging, analyzer_logging], ids=["api", "analyzer"])
def test_exceptions_keep_only_their_type(module: Any, capfd: pytest.CaptureFixture[str]) -> None:
    module.configure_logging()

    try:
        raise ValueError(f"mensagem com dados do aluno: {CANARY}")
    except ValueError:
        logging.getLogger("teste").exception("falhou")
        module.get_logger("teste").exception("falhou de novo")

    out = capfd.readouterr().out
    lines = json_lines(out)
    assert [line["error_type"] for line in lines] == ["ValueError", "ValueError"]
    assert CANARY not in out
    assert "Traceback" not in out


def test_configuration_is_idempotent_and_silences_uvicorn_access() -> None:
    api_logging.configure_logging()
    api_logging.configure_logging()
    analyzer_logging.configure_logging()

    handlers = [h for h in logging.getLogger().handlers if getattr(h, "ipc_json", False)]
    assert len(handlers) == 1
    assert logging.getLogger("uvicorn.access").disabled
    assert logging.getLogger("uvicorn.error").propagate


def test_both_services_share_the_log_schema() -> None:
    assert api_logging.LOG_FIELDS == analyzer_logging.LOG_FIELDS

"""Serviço interno do analisador (S5-01): contrato, erros e fail-fast na inicialização."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import BASE_RULESET
from ipc_analyzer.engine.ruleset import RulesetError
from ipc_analyzer.runtime.limits import MIB
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings

SETTINGS = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app(SETTINGS)) as test_client:
        yield test_client


def test_health_reports_the_loaded_ruleset(client: TestClient) -> None:
    response = client.get("/internal/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ruleset_version"] == "2026.2.0"
    assert body["target_python"] == "3.13"
    assert body["workers"] == 1
    assert len(body["ruleset_sha256"]) == 64


def test_manifest_describes_the_active_ruleset(client: TestClient) -> None:
    response = client.get("/internal/ruleset/manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["ruleset_version"] == "2026.2.0"
    assert body["period"] == "2026.2"
    assert len(body["ruleset_sha256"]) == 64
    assert [item["number"] for item in body["lists"]] == [1, 2, 3, 4, 5, 6]
    assert body["lists"][0] == {"number": 1, "title": "Comandos condicionais"}


def test_valid_code(client: TestClient) -> None:
    response = client.post("/internal/analyze", json={"code": "x = 1\n", "list_number": 1})

    assert response.status_code == 200
    assert response.json() == {
        "ruleset_version": "2026.2.0",
        "status": "valid",
        "list_number": 1,
        "syntax_error": None,
        "violations": [],
        "truncated": False,
    }


def test_violations_follow_the_contract(client: TestClient) -> None:
    code = "x = 3\nwhile x > 0:\n    x -= 1\n"

    response = client.post("/internal/analyze", json={"code": code, "list_number": 1})

    assert response.status_code == 200
    assert response.json()["violations"] == [
        {
            "rule_id": "R-34",
            "category": "FORA_DA_LISTA",
            "line": 2,
            "col": 1,
            "end_line": 3,
            "end_col": 11,
            "construct": "node:While",
            "allowed_from_list": 2,
            "message": "Laços de repetição (for, while) só são permitidos a partir da Lista 2.",
        }
    ]


def test_syntax_error(client: TestClient) -> None:
    response = client.post("/internal/analyze", json={"code": "x = (1\n", "list_number": 1})

    body = response.json()
    assert body["status"] == "syntax_error"
    assert body["syntax_error"] == {
        "line": 1,
        "col": 5,
        "message": "o '(' foi aberto e nunca fechado",
    }
    assert body["violations"] == []


@pytest.mark.parametrize(
    ("payload", "status", "code"),
    [
        ({"code": "  ", "list_number": 1}, 422, "INVALID_INPUT"),
        ({"code": "x = '\x00'", "list_number": 1}, 422, "INVALID_INPUT"),
        ({"code": "#" + "a" * 60_000, "list_number": 1}, 413, "PAYLOAD_TOO_LARGE"),
        ({"code": "#" + "é" * 25_600, "list_number": 1}, 413, "PAYLOAD_TOO_LARGE"),
        ({"code": "(" * 1_000 + ")" * 1_000, "list_number": 1}, 422, "ANALYSIS_LIMIT"),
        ({"code": "x = 1", "list_number": 7}, 422, "INVALID_INPUT"),
        ({"code": "x = 1", "list_number": 1, "extra": True}, 422, "INVALID_INPUT"),
        ({"list_number": 1}, 422, "INVALID_INPUT"),
    ],
    ids=[
        "vazio",
        "nulo",
        "60k",
        "utf8-51201",
        "1000-parenteses",
        "lista-7",
        "campo-extra",
        "sem-code",
    ],
)
def test_rejected_inputs_use_the_error_contract(
    client: TestClient, payload: dict[str, object], status: int, code: str
) -> None:
    response = client.post("/internal/analyze", json=payload)

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]


@pytest.mark.parametrize(
    "body",
    [b'{"code": "x = \xff\xfe", "list_number": 1}', b'{"code": "x = 1"', b""],
    ids=["utf8-invalido", "json-quebrado", "corpo-vazio"],
)
def test_malformed_bodies_are_invalid_input(client: TestClient, body: bytes) -> None:
    response = client.post(
        "/internal/analyze", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_internal_service_has_no_public_documentation(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_invalid_ruleset_prevents_startup(tmp_path: Path) -> None:
    broken = tmp_path / "base.yaml"
    broken.write_text("rules: []\n", encoding="utf-8")
    app = create_app(AnalyzerSettings(ruleset_path=broken, pool=PoolConfig(workers=1)))

    with pytest.raises(RulesetError), TestClient(app):
        pass


def test_settings_from_environment() -> None:
    settings = AnalyzerSettings.from_env(
        {
            "IPC_RULESET_PATH": "/app/rulesets/2026.2/base.yaml",
            "IPC_WORKERS": "3",
            "IPC_MAX_TASKS": "100",
            "IPC_TIMEOUT_S": "1.5",
            "IPC_MEMORY_MB": "300",
        }
    )

    assert settings.ruleset_path == Path("/app/rulesets/2026.2/base.yaml")
    assert settings.pool.workers == 3
    assert settings.pool.max_tasks == 100
    assert settings.pool.timeout_s == 1.5
    assert settings.pool.limits.memory_bytes == 300 * MIB


def test_settings_defaults_point_to_the_repository_ruleset() -> None:
    settings = AnalyzerSettings.from_env({})

    assert settings.ruleset_path == BASE_RULESET
    assert settings.pool == PoolConfig()

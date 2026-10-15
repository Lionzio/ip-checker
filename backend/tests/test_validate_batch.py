"""``POST /api/v1/validate/batch`` com o analyzer de verdade (S40-01; US-33)."""

from __future__ import annotations

from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

UNLIMITED = ApiSettings(rate_limit=RateLimitConfig(client_per_min=1_000_000, ip_per_min=1_000_000))
VALID = "nota = float(input())\nif nota >= 7:\n    print('aprovado')\n"
LOOP = "n = int(input())\nfor i in range(n):\n    print(i)\n"


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as analyzer:

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

        app = make_app(UNLIMITED, analyzer_transport=httpx2.MockTransport(bridge))
        with authed_client(*app) as client:
            yield client


def _batch(api: TestClient, files: list[dict[str, str]], list_number: int = 1) -> httpx2.Response:
    return api.post("/api/v1/validate/batch", json={"list_number": list_number, "files": files})


def test_each_file_gets_its_status_counts_and_rules(api: TestClient) -> None:
    files = [
        {"name": "ana.py", "code": VALID},
        {"name": "bruno.py", "code": LOOP},
        {"name": "carla.py", "code": "if x\n"},
        {"name": "davi.py", "code": "x = 1\n" * 1_100},
    ]

    response = _batch(api, files)

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    results = {item["name"]: item for item in body["results"]}
    assert [item["name"] for item in body["results"]] == [
        "ana.py",
        "bruno.py",
        "carla.py",
        "davi.py",
    ]
    assert results["ana.py"]["status"] == "valid"
    assert results["ana.py"]["counts"] == {}
    assert results["bruno.py"]["status"] == "invalid"
    assert results["bruno.py"]["counts"] == {"FORA_DA_LISTA": 2, "EXIGENCIA": 1}
    assert results["bruno.py"]["rule_ids"] == ["R-02", "R-34", "R-35"]
    assert results["carla.py"]["status"] == "syntax_error"
    assert results["carla.py"]["syntax_error"]["line"] == 1
    assert results["davi.py"]["status"] == "rejected"
    assert "o limite é 1.000" in results["davi.py"]["message"]
    assert body["ruleset_version"].startswith("2026.2.")


def test_a_batch_has_at_most_twenty_files(api: TestClient) -> None:
    files = [{"name": f"{n}.py", "code": VALID} for n in range(21)]

    assert _batch(api, files).status_code == 422


def test_a_list_that_is_not_enabled_refuses_the_whole_batch() -> None:
    settings = ApiSettings(enabled_lists=frozenset({1}))
    with authed_client(*make_app(settings)) as client:
        response = client.post(
            "/api/v1/validate/batch",
            json={"list_number": 2, "files": [{"name": "a.py", "code": LOOP}]},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LIST_NOT_ENABLED"


def test_the_batch_needs_a_session() -> None:
    app, _ = make_app(UNLIMITED)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/validate/batch",
            json={"list_number": 1, "files": [{"name": "a.py", "code": VALID}]},
        )

    assert response.status_code == 401

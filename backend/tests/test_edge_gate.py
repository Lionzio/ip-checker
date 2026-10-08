"""Só a página fala com a API do piloto (S30-03): o segredo do middleware da Vercel."""

from __future__ import annotations

from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import make_app
from ipc_api.edge_gate import CLIENT_HEADER, SECRET_HEADER, validate_edge_secret
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

SECRET = "s" * 64
PAGE = {SECRET_HEADER: SECRET}
#: Atrás da Vercel e do Render, como no piloto, com o diagnóstico ligado.
SETTINGS = ApiSettings(
    edge_secret=SECRET,
    rate_limit=RateLimitConfig(trusted_proxy_hops=4, trust_forwarded_header=True),
)


def _analyzer(request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, json={"status": "ok", "ruleset_version": "2026.2.0"})


@pytest.fixture
def client() -> Iterator[TestClient]:
    app, _ = make_app(SETTINGS, analyzer_transport=httpx2.MockTransport(_analyzer))
    with TestClient(app) as test_client:
        yield test_client


def test_without_the_secret_the_api_refuses_everything_under_api(client: TestClient) -> None:
    for response in (
        client.get("/api/v1/auth/options"),
        client.post("/api/v1/auth/login", json={"login": "x", "password": "y"}),
        client.get("/api/v1/auth/options", headers={SECRET_HEADER: "chute"}),
        client.get("/api/v1/auth/options", headers={SECRET_HEADER: SECRET[:-1]}),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ORIGIN_MISMATCH"


def test_with_the_secret_the_page_gets_through(client: TestClient) -> None:
    assert client.get("/api/v1/auth/options", headers=PAGE).status_code == 200


def test_operation_routes_stay_open_for_the_monitors(client: TestClient) -> None:
    # O UptimeRobot e o pipeline chamam o Render direto.
    assert client.get("/health").status_code == 200
    assert client.head("/health").status_code == 200
    assert client.head("/ready").status_code != 403  # o analisador falso não responde ao /ready


def test_the_client_ip_comes_from_the_page_once_the_secret_is_checked(client: TestClient) -> None:
    forged = {"Forwarded": "for=203.0.113.9", "X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    response = client.get(
        "/api/v1/proxy-check", headers={**PAGE, **forged, CLIENT_HEADER: "198.51.100.7"}
    )

    body = response.json()
    assert body["client_ip"] == "198.51.100.7"
    assert body["edge_verified"] is True
    assert "x-ipc-edge-secret" not in body["headers"]  # o segredo nunca volta
    assert SECRET not in response.text


def test_without_the_secret_configured_nothing_changes() -> None:
    app, _ = make_app(ApiSettings(), analyzer_transport=httpx2.MockTransport(_analyzer))
    with TestClient(app) as client:
        response = client.get("/api/v1/proxy-check", headers={CLIENT_HEADER: "198.51.100.7"})

    assert response.status_code == 200
    assert response.json()["edge_verified"] is False
    assert response.json()["client_ip"] != "198.51.100.7"


@pytest.mark.parametrize("value", [None, ""])
def test_an_empty_secret_turns_the_gate_off(value: str | None) -> None:
    assert validate_edge_secret(value) is None


def test_a_short_secret_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="IPC_EDGE_SECRET curto demais"):
        ApiSettings.from_env({"IPC_EDGE_SECRET": "curto"})
    assert ApiSettings.from_env({"IPC_EDGE_SECRET": SECRET}).edge_secret == SECRET
    assert SECRET not in repr(ApiSettings.from_env({"IPC_EDGE_SECRET": SECRET}))

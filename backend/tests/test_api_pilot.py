"""API no piloto (S11-02, NFR-10): CORS só para a página, cabeçalhos de segurança e versão.

No piloto a página (Vercel) e a API (Render) ficam em origens diferentes. Nas Fases 0 e 2 a origem
é a mesma, e a API não pode mandar nenhum cabeçalho CORS.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from ipc_api.app import create_app
from ipc_api.edge import HSTS_VALUE, parse_origins
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

SPA = "https://ip-checker.vercel.app"
EVIL = "https://ip-checker.vercel.app.evil.example"
VALID = {
    "ruleset_version": "2026.2.0",
    "status": "valid",
    "list_number": 1,
    "syntax_error": None,
    "violations": [],
    "truncated": False,
}
HEALTH = {
    "status": "ok",
    "ruleset_version": "2026.2.0",
    "ruleset_sha256": "a" * 64,
    "target_python": "3.13",
    "workers": 2,
}


def analyzer(request: httpx2.Request) -> httpx2.Response:
    body = HEALTH if request.url.path == "/internal/health" else VALID
    return httpx2.Response(200, json=body)


def make_client(settings: ApiSettings) -> TestClient:
    return TestClient(create_app(settings, analyzer_transport=httpx2.MockTransport(analyzer)))


PILOT = ApiSettings(cors_origins=(SPA,), hsts=True, release="abc1234")


@pytest.fixture
def pilot() -> Iterator[TestClient]:
    with make_client(PILOT) as client:
        yield client


@pytest.fixture
def same_origin() -> Iterator[TestClient]:
    with make_client(ApiSettings()) as client:
        yield client


def preflight(
    client: TestClient, origin: str, headers: str = "content-type,x-client-id"
) -> httpx2.Response:
    return client.options(
        "/api/v1/validate",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": headers,
        },
    )


def validate(client: TestClient, origin: str | None = SPA) -> httpx2.Response:
    headers = {"Origin": origin} if origin else {}
    return client.post(
        "/api/v1/validate", json={"code": "x = 1\n", "list_number": 1}, headers=headers
    )


# --- CORS --------------------------------------------------------------------------------------


def test_preflight_from_the_spa_is_allowed(pilot: TestClient) -> None:
    response = preflight(pilot, SPA)

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == SPA
    assert set(response.headers["Access-Control-Allow-Methods"].replace(" ", "").split(",")) >= {
        "GET",
        "POST",
    }
    allowed = response.headers["Access-Control-Allow-Headers"].lower()
    assert "content-type" in allowed
    assert "x-client-id" in allowed
    assert response.headers["Access-Control-Max-Age"] == "600"
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.parametrize(
    "origin",
    [EVIL, "http://ip-checker.vercel.app", "https://evil.example", "null"],
    ids=["sufixo", "http", "outro-site", "null"],
)
def test_other_origins_are_not_allowed(pilot: TestClient, origin: str) -> None:
    assert "Access-Control-Allow-Origin" not in preflight(pilot, origin).headers
    assert "Access-Control-Allow-Origin" not in validate(pilot, origin).headers


def test_only_the_needed_headers_are_allowed(pilot: TestClient) -> None:
    response = preflight(pilot, SPA, headers="content-type,authorization")

    assert response.status_code == 400


def test_responses_to_the_spa_expose_retry_after_and_request_id(pilot: TestClient) -> None:
    response = validate(pilot)

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == SPA
    exposed = response.headers["Access-Control-Expose-Headers"].lower()
    assert "retry-after" in exposed
    assert "x-request-id" in exposed


def test_errors_also_carry_cors_headers() -> None:
    # Sem CORS no 429, o navegador esconderia a resposta e o aluno veria "falha de rede".
    settings = ApiSettings(cors_origins=(SPA,), rate_limit=RateLimitConfig(client_per_min=1))
    with make_client(settings) as client:
        validate(client)
        limited = validate(client)
        too_large = client.post(
            "/api/v1/validate",
            content=b"x" * 140_000,
            headers={"Origin": SPA, "Content-Type": "application/json"},
        )

    assert limited.status_code == 429
    assert limited.headers["Access-Control-Allow-Origin"] == SPA
    assert too_large.status_code == 413
    assert too_large.headers["Access-Control-Allow-Origin"] == SPA


def test_same_origin_phases_send_no_cors_headers(same_origin: TestClient) -> None:
    response = validate(same_origin)
    options = preflight(same_origin, SPA)

    assert not any(name.lower().startswith("access-control-") for name in response.headers)
    assert not any(name.lower().startswith("access-control-") for name in options.headers)


# --- Cabeçalhos de segurança e versão ----------------------------------------------------------


def test_pilot_sends_hsts_and_nosniff(pilot: TestClient) -> None:
    for response in (validate(pilot), pilot.get("/health"), pilot.get("/nao-existe")):
        assert response.headers["Strict-Transport-Security"] == HSTS_VALUE
        assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_same_origin_phases_leave_hsts_to_the_edge(same_origin: TestClient) -> None:
    response = same_origin.get("/health")

    assert "Strict-Transport-Security" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_ready_reports_the_deployed_release(pilot: TestClient, same_origin: TestClient) -> None:
    assert pilot.get("/ready").json() == {
        "status": "ready",
        "ruleset_version": "2026.2.0",
        "release": "abc1234",
    }
    assert same_origin.get("/ready").json()["release"] is None


# --- Configuração ------------------------------------------------------------------------------


def test_settings_from_environment() -> None:
    settings = ApiSettings.from_env(
        {
            "IPC_CORS_ORIGINS": f"{SPA}/, http://localhost:5180",
            "IPC_HSTS": "1",
            "RENDER_GIT_COMMIT": "def5678",
        }
    )

    assert settings.cors_origins == (SPA, "http://localhost:5180")
    assert settings.hsts is True
    assert settings.release == "def5678"
    assert ApiSettings.from_env({"IPC_RELEASE": "x", "RENDER_GIT_COMMIT": "y"}).release == "x"


def test_defaults_have_no_cors_no_hsts_and_no_release() -> None:
    settings = ApiSettings.from_env({})

    assert (settings.cors_origins, settings.hsts, settings.release) == ((), False, None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", ()),
        (" , ", ()),
        ("https://IP-Checker.Vercel.app", ("https://ip-checker.vercel.app",)),
        ("https://a.example:8443", ("https://a.example:8443",)),
        ("http://127.0.0.1:5180", ("http://127.0.0.1:5180",)),
        ("https://a.example,https://a.example/", ("https://a.example",)),
    ],
)
def test_parse_origins(value: str, expected: tuple[str, ...]) -> None:
    assert parse_origins(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://*.vercel.app",
        "http://ip-checker.vercel.app",
        "https://ip-checker.vercel.app/app",
        "https://ip-checker.vercel.app?x=1",
        "https://user@ip-checker.vercel.app",
        "ip-checker.vercel.app",
        "ftp://ip-checker.vercel.app",
    ],
)
def test_invalid_origins_prevent_startup(value: str) -> None:
    with pytest.raises(ValueError, match="IPC_CORS_ORIGINS"):
        parse_origins(value)

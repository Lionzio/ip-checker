"""O piloto no ar (S11-03; NFR-10, DoD item 15): conferido depois de cada deploy, de fora.

Roda no pipeline de deploy (``.github/workflows/deploy.yml``), contra os endereços públicos:

    PILOT_API_URL=https://ip-checker-api.onrender.com \\
    PILOT_WEB_URL=https://ip-checker.vercel.app \\
    PILOT_LOGIN=... PILOT_PASSWORD=... \\
    PILOT_RELEASE=<commit> uv run pytest tests/pilot --no-cov

Sem ``PILOT_API_URL`` e ``PILOT_WEB_URL``, os testes são pulados. Desde a Sprint 16, a página e a
API ficam na mesma origem (a Vercel repassa ``/api/*`` ao Render), e o login, a verificação e a
saída são conferidos pela origem da página com uma conta ativa de verificação.
"""

from __future__ import annotations

import os
import socket
import ssl
from urllib.parse import urlsplit

import httpx2
import pytest

API = os.environ.get("PILOT_API_URL", "").rstrip("/")
WEB = os.environ.get("PILOT_WEB_URL", "").rstrip("/")
RELEASE = os.environ.get("PILOT_RELEASE")
#: Conta ativa só para as verificações do piloto (secrets PILOT_CHECK_LOGIN e PILOT_CHECK_PASSWORD).
LOGIN = os.environ.get("PILOT_LOGIN", "")
PASSWORD = os.environ.get("PILOT_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not (API and WEB), reason="defina PILOT_API_URL e PILOT_WEB_URL para conferir o piloto"
)

EVIL = "https://evil.example"


@pytest.fixture(scope="module")
def http() -> httpx2.Client:
    return httpx2.Client(timeout=30, follow_redirects=False)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


# --- Versão no ar ------------------------------------------------------------------------------


def test_api_is_ready_with_this_release(http: httpx2.Client) -> None:
    response = http.get(f"{API}/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    if RELEASE:
        assert body["release"] == RELEASE


def test_web_serves_this_release(http: httpx2.Client) -> None:
    response = http.get(f"{WEB}/version.json")

    assert response.status_code == 200
    if RELEASE:
        assert response.json() == {"release": RELEASE}


# --- Página (Vercel) ---------------------------------------------------------------------------


def test_web_sends_the_security_headers(http: httpx2.Client) -> None:
    response = http.get(f"{WEB}/")
    csp = response.headers["content-security-policy"]

    assert response.status_code == 200
    assert f"connect-src 'self' {_origin(API)}" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_web_routes_every_path_to_the_page(http: httpx2.Client) -> None:
    response = http.get(f"{WEB}/qualquer/caminho")

    assert response.status_code == 200
    assert '<div id="root">' in response.text


# --- API (Render) ------------------------------------------------------------------------------


def test_the_page_origin_serves_the_api(http: httpx2.Client) -> None:
    # Mesma origem (S16-02): a Vercel repassa /api/* ao Render.
    response = http.get(f"{WEB}/api/v1/auth/options")

    assert response.status_code == 200
    assert set(response.json()) == {"google"}
    assert response.headers["content-type"].startswith("application/json")


def test_without_a_session_the_api_gives_nothing(http: httpx2.Client) -> None:
    response = http.get(f"{WEB}/api/v1/lists")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("origin", [EVIL, "WEB"])
def test_cors_is_off(http: httpx2.Client, origin: str) -> None:
    # Com a mesma origem, ninguém precisa de CORS; nem a página recebe permissão de outra origem.
    sender = _origin(WEB) if origin == "WEB" else origin
    preflight = http.options(
        f"{API}/api/v1/validate",
        headers={"Origin": sender, "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-allow-origin" not in preflight.headers


def test_state_changes_from_other_sites_are_refused(http: httpx2.Client) -> None:
    response = http.post(
        f"{WEB}/api/v1/auth/login",
        json={"login": "ninguem@cin.ufpe.br", "password": "Qualquer-1"},
        headers={"Origin": EVIL},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_MISMATCH"


@pytest.mark.skipif(
    not (LOGIN and PASSWORD),
    reason="defina PILOT_LOGIN e PILOT_PASSWORD (conta ativa de verificação)",
)
def test_login_validation_and_logout_through_the_page() -> None:
    with httpx2.Client(timeout=30, follow_redirects=False) as client:
        page = {"Origin": _origin(WEB)}
        login = client.post(
            f"{WEB}/api/v1/auth/login", json={"login": LOGIN, "password": PASSWORD}, headers=page
        )
        assert login.status_code == 200, login.text
        cookie = login.headers["set-cookie"]
        assert cookie.startswith("__Host-ipc_session=")
        lowered = cookie.lower()
        assert all(flag in lowered for flag in ("httponly", "secure", "samesite=lax", "path=/"))
        assert "domain=" not in lowered

        response = client.post(
            f"{WEB}/api/v1/validate",
            json={"code": "x = 1\nfor i in range(3):\n    print(i)\n", "list_number": 1},
            headers=page,
        )
        assert response.status_code == 200
        assert [v["rule_id"] for v in response.json()["violations"]] == ["R-34", "R-35"]

        assert (
            client.post(f"{WEB}/api/v1/auth/logout", content=b"", headers=page).status_code == 204
        )
        assert client.get(f"{WEB}/api/v1/auth/me").status_code == 401


def test_api_sends_hsts_and_nosniff(http: httpx2.Client) -> None:
    response = http.get(f"{API}/health")

    assert response.headers["strict-transport-security"].startswith("max-age=31536000")
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("path", ["/docs", "/openapi.json", "/internal/analyze"])
def test_api_exposes_nothing_else(http: httpx2.Client, path: str) -> None:
    assert http.get(f"{API}{path}").status_code == 404


# --- Transporte --------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [API, WEB], ids=["api", "web"])
def test_tls_is_at_least_1_2(url: str) -> None:
    parts = urlsplit(url)
    assert parts.scheme == "https"
    context = ssl.create_default_context()
    with (
        socket.create_connection((parts.hostname, parts.port or 443), timeout=10) as raw,
        context.wrap_socket(raw, server_hostname=parts.hostname) as tls,
    ):
        assert tls.version() in {"TLSv1.2", "TLSv1.3"}

    # Uma conexão limitada a TLS 1.1 precisa ser recusada.
    old = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    old.check_hostname = False
    old.verify_mode = ssl.CERT_NONE
    try:
        old.minimum_version = ssl.TLSVersion.TLSv1
        old.maximum_version = ssl.TLSVersion.TLSv1_1
    except ValueError:
        return  # o OpenSSL desta máquina nem oferece TLS < 1.2
    with (
        pytest.raises((ssl.SSLError, ConnectionError)),
        socket.create_connection((parts.hostname, parts.port or 443), timeout=10) as raw,
        old.wrap_socket(raw, server_hostname=parts.hostname),
    ):
        pass

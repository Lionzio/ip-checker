"""O piloto no ar (S11-03; NFR-10, DoD item 15): conferido depois de cada deploy, de fora.

Roda no pipeline de deploy (``.github/workflows/deploy.yml``), contra os endereços públicos:

    PILOT_API_URL=https://ip-checker-api.onrender.com \\
    PILOT_WEB_URL=https://ip-checker.vercel.app \\
    PILOT_RELEASE=<commit> uv run pytest tests/pilot --no-cov

Sem ``PILOT_API_URL`` e ``PILOT_WEB_URL``, os testes são pulados.
"""

from __future__ import annotations

import os
import socket
import ssl
import uuid
from urllib.parse import urlsplit

import httpx2
import pytest

API = os.environ.get("PILOT_API_URL", "").rstrip("/")
WEB = os.environ.get("PILOT_WEB_URL", "").rstrip("/")
RELEASE = os.environ.get("PILOT_RELEASE")

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


def test_api_allows_the_spa_and_only_the_spa(http: httpx2.Client) -> None:
    def preflight(origin: str) -> httpx2.Response:
        return http.options(
            f"{API}/api/v1/validate",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-client-id",
            },
        )

    allowed, denied = preflight(_origin(WEB)), preflight(EVIL)

    assert allowed.headers.get("access-control-allow-origin") == _origin(WEB)
    assert "access-control-allow-credentials" not in allowed.headers
    assert "access-control-allow-origin" not in denied.headers


def test_cross_origin_validation_works(http: httpx2.Client) -> None:
    response = http.post(
        f"{API}/api/v1/validate",
        json={"code": "x = 1\nfor i in range(3):\n    print(i)\n", "list_number": 1},
        headers={"Origin": _origin(WEB), "X-Client-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 200
    assert [v["rule_id"] for v in response.json()["violations"]] == ["R-34", "R-35"]
    assert response.headers["access-control-allow-origin"] == _origin(WEB)
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "retry-after" in exposed
    assert "x-request-id" in exposed


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

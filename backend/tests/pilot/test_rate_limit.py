"""O limite por IP no piloto pega o cliente certo, pela página e direto no Render (S30-03).

Confirma a P-12 (a) e a P-15 (b): sem sessão, cada IP faz até 30 requisições por minuto nas rotas
de conta. Até a S30-03, o ``IPC_TRUSTED_PROXY_HOPS`` apontava para um proxy interno do Render,
diferente a cada requisição, e 33 tentativas seguidas não recebiam nenhum 429 (08/10/2026).

Pela página, a chave vem do ``Forwarded: for=``, que a Vercel sempre reescreve com o IP real (o
``X-Forwarded-For`` e o ``X-Vercel-Forwarded-For`` às vezes chegam forjados, conforme o nó da
Vercel). Direto no Render, quem forja os cabeçalhos escolhe a chave do cliente, mas um segundo
limite, pelo IP que o Cloudflare do Render escreve (``cf-connecting-ip``), o segura em 60 por
minuto.

O diagnóstico ``/api/v1/proxy-check`` devolve o IP que o limite usaria. As requisições saem por
IPv4: uma máquina com IPv4 e IPv6 pode chegar à Vercel por um e ao Render pelo outro, e seriam
dois clientes de verdade.

Ele esgota o limite do IP de quem roda por 1 minuto, por isso só roda quando pedido
(``PILOT_CHECK_RATE_LIMIT=1``), no último passo do "Deploy do piloto", depois do smoke e2e.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from urllib.parse import urlsplit

import httpx2
import pytest

API = os.environ.get("PILOT_API_URL", "").rstrip("/")
WEB = os.environ.get("PILOT_WEB_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(
    not (API and WEB and os.environ.get("PILOT_CHECK_RATE_LIMIT") == "1"),
    reason="defina PILOT_API_URL, PILOT_WEB_URL e PILOT_CHECK_RATE_LIMIT=1 (gasta o limite do IP)",
)

#: Sem sessão, o cliente é o IP: 30 por minuto (RateLimitConfig.client_per_min).
LIMIT = 30
#: Sem sessão, pelo IP que a borda do Render viu (RateLimitConfig.edge_anonymous_per_min).
EDGE_LIMIT = 60
FORGED = "203.0.113.77"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


@pytest.fixture(scope="module")
def http() -> Iterator[httpx2.Client]:
    transport = httpx2.HTTPTransport(local_address="0.0.0.0")  # noqa: S104 - só sai por IPv4
    with httpx2.Client(transport=transport, timeout=30, follow_redirects=False) as client:
        yield client


def _forged(value: str) -> dict[str, str]:
    """Os três cabeçalhos com que um cliente tenta escolher a própria chave."""
    return {
        "X-Forwarded-For": value,
        "X-Vercel-Forwarded-For": value,
        "Forwarded": f"for={value}",
    }


def _client_ip(http: httpx2.Client, base: str, forged: str | None = None) -> str:
    # POST, como as rotas de conta: a Vercel não trata os cabeçalhos igual em todo método e nó.
    headers = {"Origin": _origin(WEB), **(_forged(forged) if forged else {})}
    response = http.post(f"{base}/api/v1/proxy-check", headers=headers, content=b"")
    assert response.status_code == 200, response.text
    ip: str = response.json()["client_ip"]
    return ip


def test_the_page_and_the_render_see_the_same_client(http: httpx2.Client) -> None:
    through_page = _client_ip(http, WEB)

    # A Vercel sempre reescreve o Forwarded com o IP real, que vem antes do X-Forwarded-For.
    for _ in range(4):  # nós diferentes da Vercel
        assert _client_ip(http, WEB, forged=FORGED) == through_page
    assert _client_ip(http, API) == through_page


def _attempts(http: httpx2.Client, base: str, limit: int) -> list[int]:
    """Tentativas sem sessão, cada uma com outros cabeçalhos forjados, até o 429."""
    codes: list[int] = []
    for attempt in range(limit + 1):
        # Um token bem formado e inexistente: 422 INVALID_TOKEN, sem efeito no banco.
        body = {"token": secrets.token_urlsafe(32)[:43]}
        headers = {"Origin": _origin(WEB), **_forged(f"203.0.113.{attempt + 1}")}
        response = http.post(f"{base}/api/v1/auth/verify", json=body, headers=headers)
        codes.append(response.status_code)
        if response.status_code == 429:
            assert response.json()["error"]["code"] == "RATE_LIMITED"
            break
    return codes


def test_through_the_page_the_31st_attempt_gets_429(http: httpx2.Client) -> None:
    codes = _attempts(http, WEB, LIMIT)

    assert codes[-1] == 429, codes
    assert set(codes[:-1]) <= {422}, codes


def test_forging_directly_on_the_render_still_hits_the_edge_limit(http: httpx2.Client) -> None:
    # Direto no Render, o valor forjado vira a chave do cliente (o Render acrescenta ao cabeçalho
    # sem limpá-lo), mas o limite pelo IP que o Cloudflare viu (60 por minuto) continua valendo.
    codes = _attempts(http, API, EDGE_LIMIT)

    assert codes[-1] == 429, codes
    assert set(codes[:-1]) <= {422}, codes

"""O limite por IP no piloto pega o cliente certo, pela página e direto no Render (S30-03).

Confirma a P-12 (a) e a P-15 (b): sem sessão, cada IP faz até 30 requisições por minuto nas rotas
de conta. Antes da S30-03, o ``IPC_TRUSTED_PROXY_HOPS`` apontava para um proxy interno do Render,
diferente a cada requisição, e 33 tentativas seguidas não recebiam nenhum 429 (08/10/2026).

O teste alterna requisições pela página (com um ``X-Forwarded-For`` forjado, que a Vercel precisa
descartar) e direto no Render (sem forjar): as duas formas têm de cair na mesma chave, o IP do
runner, e a 31ª tentativa (ou antes, se outra verificação já gastou parte do minuto) recebe 429.

Ele esgota o limite do IP do runner por 1 minuto, por isso só roda quando pedido
(``PILOT_CHECK_RATE_LIMIT=1``), no último passo do "Deploy do piloto", depois do smoke e2e.

Limite conhecido: quem chama o Render direto **e** forja o cabeçalho escolhe a própria chave,
porque o Render acrescenta ao ``X-Forwarded-For`` sem limpá-lo; o bloqueio de login por conta
(5 falhas em 15 min) continua valendo (registrado na P-15).
"""

from __future__ import annotations

import os
import secrets
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


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def test_the_ip_limit_counts_the_real_client_on_both_paths() -> None:
    page = {"Origin": _origin(WEB)}
    codes: list[int] = []
    with httpx2.Client(timeout=30, follow_redirects=False) as client:
        for attempt in range(LIMIT + 1):
            # Um token bem formado e inexistente: 422 INVALID_TOKEN, sem efeito no banco.
            body = {"token": secrets.token_urlsafe(32)[:43]}
            if attempt % 2 == 0:
                forged = {"X-Forwarded-For": f"203.0.113.{attempt + 1}"}
                url = f"{WEB}/api/v1/auth/verify"
                response = client.post(url, json=body, headers={**page, **forged})
            else:
                response = client.post(f"{API}/api/v1/auth/verify", json=body, headers=page)
            codes.append(response.status_code)
            if response.status_code == 429:
                assert response.json()["error"]["code"] == "RATE_LIMITED"
                break

    assert 429 in codes, codes
    assert set(codes[:-1]) <= {422}, codes

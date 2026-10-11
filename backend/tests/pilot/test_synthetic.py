"""Teste sintético diário da primeira verificação (S34-02; NFR-01, NFR-06).

Faz o que um monitor faz na primeira verificação do dia, pela página da Vercel: entra com a conta
de verificação do deploy (as verificações dela não entram na telemetria, S28-02), verifica uma
solução da Lista 1 e sai. Falha com qualquer erro ou se a verificação passar do limite medido no
servidor: o cabeçalho ``Server-Timing`` da ``/api/v1/validate`` traz o tempo dentro da API, o
mesmo do NFR-01 e do ``/health/slo``, sem a rede entre quem testa e a Vercel.

Roda no workflow "Sintético diário" (``.github/workflows/synthetic.yml``) e, sem a cota do
Actions, por ``scripts/sintetico-local.sh``:

    PILOT_SYNTHETIC=1 PILOT_WEB_URL=https://... PILOT_LOGIN=... PILOT_PASSWORD=... \\
    uv run pytest tests/pilot/test_synthetic.py --no-cov

Sem ``PILOT_SYNTHETIC=1``, fica de fora do ``pytest tests/pilot`` do deploy: logo depois de um
deploy, a primeira verificação ainda aquece o analisador e não representa o dia a dia.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import httpx2
import pytest

WEB = os.environ.get("PILOT_WEB_URL", "").rstrip("/")
LOGIN = os.environ.get("PILOT_LOGIN", "")
PASSWORD = os.environ.get("PILOT_PASSWORD", "")
#: Limite da S34-02 para a verificação no servidor (o NFR-01 é o P95 de 200 ms; aqui é uma só).
MAX_MS = float(os.environ.get("PILOT_SYNTHETIC_MAX_MS", "300"))

needs_pilot = pytest.mark.skipif(
    os.environ.get("PILOT_SYNTHETIC") != "1" or not (WEB and LOGIN and PASSWORD),
    reason="defina PILOT_SYNTHETIC=1, PILOT_WEB_URL, PILOT_LOGIN e PILOT_PASSWORD",
)

#: Uma solução típica da Lista 1, sem violações.
SOLUTION = (
    "nota = float(input())\n"
    "if nota >= 7:\n"
    "    print('Aprovado')\n"
    "elif nota >= 3:\n"
    "    print('Final')\n"
    "else:\n"
    "    print('Reprovado')\n"
)
TIMING = re.compile(r"(?:^|,)\s*app;dur=(\d+(?:\.\d+)?)")


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def server_ms(header: str | None) -> float | None:
    """O tempo da API no ``Server-Timing``; a Vercel pode acrescentar as próprias entradas."""
    match = TIMING.search(header or "")
    return float(match.group(1)) if match else None


@needs_pilot
def test_the_first_validation_of_the_day() -> None:
    page = {"Origin": _origin(WEB)}
    with httpx2.Client(timeout=30, follow_redirects=False) as client:
        login = client.post(
            f"{WEB}/api/v1/auth/login", json={"login": LOGIN, "password": PASSWORD}, headers=page
        )
        assert login.status_code == 200, f"o login falhou com {login.status_code}"
        try:
            response = client.post(
                f"{WEB}/api/v1/validate", json={"code": SOLUTION, "list_number": 1}, headers=page
            )
        finally:
            client.post(f"{WEB}/api/v1/auth/logout", content=b"", headers=page)

    request_id = response.headers.get("X-Request-Id", "?")
    assert response.status_code == 200, (
        f"a verificação respondeu {response.status_code} (request_id {request_id})"
    )
    assert response.json()["status"] == "valid", f"resultado inesperado (request_id {request_id})"
    elapsed = server_ms(response.headers.get("Server-Timing"))
    assert elapsed is not None, "a resposta não trouxe o Server-Timing da API"
    print(f"verificação no servidor: {elapsed:.1f} ms (limite {MAX_MS:.0f} ms)")
    assert elapsed <= MAX_MS, (
        f"a verificação levou {elapsed:.1f} ms no servidor, acima de {MAX_MS:.0f} ms "
        f"(request_id {request_id})"
    )


@pytest.mark.parametrize(
    ("header", "expected"),
    [("app;dur=42.5", 42.5), ("cdn;dur=3, app;dur=118.0", 118.0), (None, None), ("x;dur=1", None)],
)
def test_server_timing_is_read_even_with_other_entries(
    header: str | None, expected: float | None
) -> None:
    assert server_ms(header) == expected

"""Tempo das entradas grandes no piloto (S36-06; NFR-02, ADR-03).

Verifica pela página da Vercel, com a conta de verificação do deploy, a entrada de cerca de 50 KB
do benchmark do motor (``tests/benchmark/test_engine_benchmark.py``, ``grande_50kb``) e frações
dela (10, 20, 30 e 40 KB), e lê o tempo dentro da API no ``Server-Timing``. Serve para saber se o
prazo do analisador (``IPC_TIMEOUT_S``) tem folga no plano gratuito do Render (0,1 CPU): nenhuma
entrada legítima de até 50 KB pode receber 422 ``ANALYSIS_LIMIT`` por prazo.

    PILOT_LARGE=1 PILOT_WEB_URL=https://... PILOT_LOGIN=... PILOT_PASSWORD=... \\
    uv run pytest tests/pilot/test_large_input.py --no-cov -s

As verificações da conta de verificação não entram na telemetria (S28-02). São 10 requisições,
espaçadas, abaixo do limite de 30 por minuto da conta.
"""

from __future__ import annotations

import os
import time
from urllib.parse import urlsplit

import httpx2
import pytest

from .test_synthetic import server_ms

WEB = os.environ.get("PILOT_WEB_URL", "").rstrip("/")
LOGIN = os.environ.get("PILOT_LOGIN", "")
PASSWORD = os.environ.get("PILOT_PASSWORD", "")
#: As frações da entrada de 50 KB medidas, e quantas vezes cada uma.
FRACTIONS = (0.2, 0.4, 0.6, 0.8, 1.0)
RUNS = int(os.environ.get("PILOT_LARGE_RUNS", "2"))
#: Folga pedida pela S36-06: a maior entrada leva no máximo metade do prazo do analisador.
TIMEOUT_S = float(os.environ.get("PILOT_ANALYSIS_TIMEOUT_S", "2"))

needs_pilot = pytest.mark.skipif(
    os.environ.get("PILOT_LARGE") != "1" or not (WEB and LOGIN and PASSWORD),
    reason="defina PILOT_LARGE=1, PILOT_WEB_URL, PILOT_LOGIN e PILOT_PASSWORD",
)

LINES = 960


def large_input(fraction: float = 1.0) -> str:
    """A entrada ``grande_50kb`` do benchmark (perto de 50 KB e de 1.000 linhas), ou uma fração."""
    lines = [
        f"x{i} = (a{i % 7} + b{i % 5}) * c{i % 3} - d{i % 11} // 2 if a{i % 7} > b{i % 5} else {i}"
        for i in range(round(LINES * fraction))
    ]
    return "\n".join(lines) + "\n"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def test_the_large_input_is_the_benchmark_one() -> None:
    assert 45_000 < len(large_input().encode()) <= 51_200
    assert len(large_input(0.2).encode()) < 11_000


@needs_pilot
def test_the_largest_input_has_room_in_the_pilot() -> None:
    page = {"Origin": _origin(WEB)}
    rows: list[tuple[int, int, float | None]] = []
    with httpx2.Client(timeout=60, follow_redirects=False) as client:
        login = client.post(
            f"{WEB}/api/v1/auth/login", json={"login": LOGIN, "password": PASSWORD}, headers=page
        )
        assert login.status_code == 200, f"o login falhou com {login.status_code}"
        try:
            for fraction in FRACTIONS:
                code = large_input(fraction)
                for _ in range(RUNS):
                    response = client.post(
                        f"{WEB}/api/v1/validate",
                        json={"code": code, "list_number": 1},
                        headers=page,
                    )
                    elapsed = server_ms(response.headers.get("Server-Timing"))
                    rows.append((len(code.encode()), response.status_code, elapsed))
                    size = len(code.encode())
                    print(f"{size:>6} bytes: HTTP {response.status_code}, {elapsed} ms")
                    time.sleep(3)
        finally:
            client.post(f"{WEB}/api/v1/auth/logout", content=b"", headers=page)

    refused = [row for row in rows if row[1] != 200]
    slowest = max((row[2] or 0.0) for row in rows)
    print(f"mais lenta: {slowest:.0f} ms; recusadas: {len(refused)} de {len(rows)}")
    assert refused == [], f"entradas legítimas recusadas no piloto: {refused}"
    assert slowest <= TIMEOUT_S * 1000 / 2, (
        f"a maior entrada levou {slowest:.0f} ms, mais que metade do prazo de {TIMEOUT_S} s"
    )

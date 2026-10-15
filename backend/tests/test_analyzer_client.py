"""O cliente do analyzer e as conexões que o analyzer fecha (sprint-38.1)."""

from __future__ import annotations

import httpx2
import pytest

from ipc_api.clients.analyzer import KEEPALIVE_EXPIRY_S, AnalyzerClient, AnalyzerUnavailable

HEALTH = {
    "status": "ok",
    "ruleset_version": "2026.2.7",
    "ruleset_sha256": "a" * 64,
    "target_python": "3.13",
    "workers": 1,
}

pytestmark = pytest.mark.anyio


def _client(failures: list[Exception]) -> tuple[AnalyzerClient, list[str]]:
    """Um analyzer que falha com cada exceção da lista, em ordem, e depois responde."""
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        if failures:
            raise failures.pop(0)
        return httpx2.Response(200, json=HEALTH)

    return AnalyzerClient("http://analyzer", 3.0, transport=httpx2.MockTransport(handler)), calls


@pytest.mark.parametrize(
    "stale",
    [
        httpx2.RemoteProtocolError("Server disconnected"),
        httpx2.ReadError("closed"),
        httpx2.WriteError("closed"),
    ],
    ids=["RemoteProtocolError", "ReadError", "WriteError"],
)
async def test_a_connection_the_analyzer_closed_is_retried_once(stale: Exception) -> None:
    client, calls = _client([stale])

    health = await client.health()

    assert health.status == "ok"
    assert len(calls) == 2
    await client.aclose()


async def test_two_failures_in_a_row_still_mean_unavailable() -> None:
    client, calls = _client([httpx2.ReadError("closed"), httpx2.ReadError("closed")])

    with pytest.raises(AnalyzerUnavailable, match="ReadError"):
        await client.health()
    assert len(calls) == 2
    await client.aclose()


async def test_a_refused_connection_is_not_retried() -> None:
    """Analyzer fora do ar não é conexão velha: 503 na hora, sem outra tentativa."""
    client, calls = _client([httpx2.ConnectError("refused")])

    with pytest.raises(AnalyzerUnavailable, match="ConnectError"):
        await client.health()
    assert len(calls) == 1
    await client.aclose()


def test_idle_connections_expire_before_the_analyzer_closes_them() -> None:
    """O uvicorn do analyzer fecha a conexão parada em 5 s; o cliente a descarta antes."""
    assert KEEPALIVE_EXPIRY_S < 5

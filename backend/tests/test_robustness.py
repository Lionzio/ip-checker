"""Robustez no plano gratuito (S25-04): prazos, banco, limite geral por IP, HTTPS e o 500 em JSON.

O seccomp e os rlimits ampliados ficam em ``test_sandbox.py`` e ``test_pool.py``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from api_support import BASE_URL, COOKIE, authed_client, make_app
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import AnalyzerPool, DeadlineExpired, PoolConfig
from ipc_analyzer.service import app as service
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.accounts.models import StoreUnavailable
from ipc_api.accounts.postgres import _guard
from ipc_api.auth.accounts import AccountsConfig
from ipc_api.auth.sessions import SessionConfig, new_token
from ipc_api.clients.analyzer import BUDGET_HEADER
from ipc_api.ratelimit import FixedWindowCounter, RateLimitConfig
from ipc_api.settings import ANALYSIS_TIMEOUT_S, ApiSettings
from test_api import MANIFEST, VALID, FakeAnalyzer, reply

SETTINGS = ApiSettings(analyzer_url="http://analyzer.test")


def _sleep(seconds: float) -> str:
    time.sleep(seconds)
    return "acordou"


# --- O prazo da API chega ao analisador ----------------------------------------------------------


def test_the_api_timeout_follows_the_pool_timeout() -> None:
    assert PoolConfig().timeout_s == ANALYSIS_TIMEOUT_S
    assert ApiSettings.from_env({}).analyzer_timeout_s == ANALYSIS_TIMEOUT_S + 1
    assert ApiSettings.from_env({"IPC_TIMEOUT_S": "5"}).analyzer_timeout_s == 6
    explicit = {"IPC_TIMEOUT_S": "5", "IPC_ANALYZER_TIMEOUT_S": "4"}
    assert ApiSettings.from_env(explicit).analyzer_timeout_s == 4


def test_the_api_sends_its_budget_to_the_analyzer() -> None:
    seen: list[str | None] = []

    def analyze(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.headers.get(BUDGET_HEADER))
        return httpx2.Response(200, json=VALID)

    analyzer = FakeAnalyzer(
        {"/internal/analyze": analyze, "/internal/ruleset/manifest": reply(200, MANIFEST)}
    )
    app, store = make_app(SETTINGS, analyzer_transport=httpx2.MockTransport(analyzer))
    with authed_client(app, store) as client:
        response = client.post("/api/v1/validate", json={"code": "x = 1\n", "list_number": 1})

    assert response.status_code == 200
    assert seen == ["3000"]


@pytest.mark.timing
def test_the_api_gives_up_at_the_deadline_even_if_the_analyzer_trickles() -> None:
    async def slow(request: httpx2.Request) -> httpx2.Response:
        # O manifesto responde na hora; só a análise demora mais que o prazo.
        if request.url.path == "/internal/analyze":
            await asyncio.sleep(2)
            return httpx2.Response(200, json=VALID)
        return httpx2.Response(200, json=MANIFEST)

    settings = ApiSettings(analyzer_url="http://analyzer.test", analyzer_timeout_s=0.2)
    app, store = make_app(settings, analyzer_transport=httpx2.MockTransport(slow))
    with authed_client(app, store) as client:
        started = time.monotonic()
        response = client.post("/api/v1/validate", json={"code": "x = 1\n", "list_number": 1})
        elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ANALYZER_UNAVAILABLE"
    assert elapsed < 1.5


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw})


def test_the_analyzer_reads_the_budget() -> None:
    before = time.time()
    deadline = service._deadline(_request({BUDGET_HEADER: "1500"}))

    assert deadline is not None
    assert before + 1.5 <= deadline <= time.time() + 1.5
    assert service._deadline(_request({})) is None
    assert service._deadline(_request({BUDGET_HEADER: "muito"})) is None
    huge = service._deadline(_request({BUDGET_HEADER: "999999999"}))
    assert huge is not None
    assert huge <= time.time() + service.MAX_BUDGET_S


@pytest.fixture(scope="module")
def pool() -> Iterator[AnalyzerPool]:
    analyzer_pool = AnalyzerPool(BASE_RULESET, PoolConfig(workers=1, timeout_s=2.0))
    yield analyzer_pool
    analyzer_pool.close()


def test_an_expired_request_never_reaches_a_worker(pool: AnalyzerPool) -> None:
    with pytest.raises(DeadlineExpired):
        asyncio.run(pool.analyze("x = 1\n", 1, deadline=time.time() - 1))


def test_a_request_that_expires_in_the_queue_is_dropped(pool: AnalyzerPool) -> None:
    async def scenario() -> tuple[str, BaseException | None]:
        busy = asyncio.create_task(pool.run(_sleep, 0.6))
        await asyncio.sleep(0.1)  # o único worker está ocupado
        queued = pool.analyze("x = 1\n", 1, deadline=time.time() + 0.2)
        outcome = await asyncio.gather(queued, return_exceptions=True)
        return await busy, outcome[0] if isinstance(outcome[0], BaseException) else None

    first, error = asyncio.run(scenario())

    assert first == "acordou"
    assert isinstance(error, DeadlineExpired)


@pytest.mark.timing
def test_an_analysis_stops_at_the_deadline(pool: AnalyzerPool) -> None:
    # O worker sobe antes de medir: rodando sozinho ou só com os testes de tempo (S39-03), o pool
    # chega frio, e a subida entraria na conta do prazo.
    assert asyncio.run(pool.analyze("x = 1\n", 1, deadline=time.time() + 5)).status
    started = time.monotonic()
    with pytest.raises(DeadlineExpired):
        asyncio.run(pool.run(_sleep, 5.0, deadline=time.time() + 0.3))

    # Quem parou a análise foi o prazo de 0,3 s: a exceção é DeadlineExpired, e não a do tempo
    # limite do pool. O tempo só precisa ficar longe do fim do sono de 5 s. Matar e trocar o worker
    # leva de 1 a 2,6 s no Windows, conforme a carga da máquina: os limites de 1,2 s (até a S39-03)
    # e de 1,9 s (S43-01) reprovavam sem nenhuma mudança no pool.
    assert time.monotonic() - started < 4.0
    # O worker substituído continua atendendo.
    assert asyncio.run(pool.analyze("x = 1\n", 1, deadline=time.time() + 5)).status


def test_the_analyzer_answers_503_when_the_budget_is_gone() -> None:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(service.create_app(settings)) as client:
        expired = client.post(
            "/internal/analyze",
            json={"code": "x = 1\n", "list_number": 1},
            headers={BUDGET_HEADER: "0"},
        )
        fine = client.post(
            "/internal/analyze",
            json={"code": "x = 1\n", "list_number": 1},
            headers={BUDGET_HEADER: "3000"},
        )

    assert expired.status_code == 503
    assert expired.json()["error"]["code"] == "DEADLINE_EXCEEDED"
    assert fine.status_code == 200


# --- Banco ---------------------------------------------------------------------------------------


@pytest.mark.timing
@pytest.mark.anyio
async def test_a_slow_database_becomes_unavailable() -> None:
    started = time.monotonic()
    with pytest.raises(StoreUnavailable, match="TimeoutError"):
        async with _guard(0.05):
            await asyncio.sleep(5)

    assert time.monotonic() - started < 1


# --- Limite geral por IP antes da sessão -------------------------------------------------------


class Clock:
    def __init__(self, now: float = 6000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_the_counter_resets_each_minute() -> None:
    clock = Clock()
    counter = FixedWindowCounter(clock=clock)

    assert [counter.acquire(b"a", 2) for _ in range(2)] == [None, None]
    rejected = counter.acquire(b"a", 2)
    assert rejected is not None
    assert (rejected.scope, rejected.retry_after_s) == ("ip", 60)
    assert counter.acquire(b"b", 2) is None  # outra chave tem a própria conta

    clock.now += 45
    again = counter.acquire(b"a", 2)
    assert again is not None
    assert again.retry_after_s == 15
    clock.now += 15
    assert counter.acquire(b"a", 2) is None
    assert len(counter) == 1


def test_the_counter_has_a_key_ceiling() -> None:
    counter = FixedWindowCounter(max_keys=1, clock=Clock())

    assert counter.acquire(b"a", 5) is None
    full = counter.acquire(b"b", 5)
    assert full is not None
    assert full.scope == "capacity"
    assert counter.acquire(b"a", 5) is None


def test_random_session_tokens_stop_at_the_ip_limit() -> None:
    settings = ApiSettings(
        analyzer_url="http://analyzer.test", rate_limit=RateLimitConfig(api_ip_per_min=3)
    )
    app, store = make_app(settings)
    lookups: list[bytes] = []
    original = store.get_session

    async def counted(token_hash: bytes) -> Any:
        lookups.append(token_hash)
        return await original(token_hash)

    store.get_session = counted  # type: ignore[method-assign]

    with TestClient(app, base_url=BASE_URL) as client:
        statuses = []
        for _ in range(5):
            client.cookies.set(COOKIE, new_token())
            statuses.append(client.get("/api/v1/auth/me").status_code)
        limited = client.get("/api/v1/auth/me")
        health = client.get("/health")

    assert statuses == [401, 401, 401, 429, 429]
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) >= 1
    assert len(lookups) == 3  # o banco não viu os chutes recusados
    assert health.status_code == 200  # o monitoramento fica de fora


def test_the_ip_limit_reads_its_settings() -> None:
    env = {"IPC_RATE_LIMIT_API_IP_PER_MIN": "50", "IPC_RATE_LIMIT_API_CAMPUS_PER_MIN": "500"}

    config = ApiSettings.from_env(env).rate_limit

    assert (config.api_ip_per_min, config.api_campus_per_min) == (50, 500)
    assert (RateLimitConfig().api_ip_per_min, RateLimitConfig().api_campus_per_min) == (600, 6000)


# --- HTTPS do endereço público -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "secure", "accepted"),
    [
        ("https://ip-checker.vercel.app", True, True),
        ("http://ip-checker.vercel.app", True, False),
        ("http://ip-checker.vercel.app", False, True),
        ("http://127.0.0.1:8180", True, True),
        ("http://localhost:5173", True, True),
        ("http://[::1]:8180", True, True),
    ],
)
def test_a_secure_cookie_needs_an_https_public_address(
    url: str, secure: bool, accepted: bool
) -> None:
    settings = ApiSettings(
        accounts=AccountsConfig(public_base_url=url),
        session=SessionConfig(cookie_secure=secure),
    )

    if accepted:
        settings.check()
    else:
        with pytest.raises(ValueError, match="https://"):
            settings.check()


def test_the_api_refuses_to_start_with_an_insecure_public_address() -> None:
    settings = ApiSettings(accounts=AccountsConfig(public_base_url="http://ip-checker.example"))

    with pytest.raises(ValueError, match="IPC_PUBLIC_BASE_URL"):
        make_app(settings)


# --- 500 em JSON ---------------------------------------------------------------------------------


def test_an_unexpected_error_is_a_json_500_with_the_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, _ = make_app(SETTINGS)

    async def boom() -> None:
        raise RuntimeError("segredo-que-nao-pode-vazar")

    app.add_api_route("/api/v1/boom", boom)
    with TestClient(app, base_url=BASE_URL, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/boom")

    request_id = response.headers["X-Request-Id"]
    body = response.json()
    assert response.status_code == 500
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert request_id in body["error"]["message"]
    assert "segredo" not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "RuntimeError" in caplog.text

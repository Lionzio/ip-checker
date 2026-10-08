"""Limite de taxa e admissão na API (S10-01): critérios da US-17 e da US-18, ponta a ponta.

Desde a S13-02, o limite por cliente é por conta (30 verificações por minuto, C-04): cada
"aluno" destes testes é uma conta da equipe com a própria sessão. Sem sessão, o cliente é o IP, e
a rota responde 401. O analyzer é simulado, para os testes controlarem quanto tempo cada análise
leva.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_support import COOKIE, make_app, member, open_session
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.admission import AdmissionConfig
from ipc_api.ratelimit import RateLimitConfig, parse_networks
from ipc_api.settings import ApiSettings

VALID = {
    "ruleset_version": "2026.2.0",
    "status": "valid",
    "list_number": 1,
    "syntax_error": None,
    "violations": [],
    "truncated": False,
}
BODY = {"code": "x = 1\n", "list_number": 1}
CAMPUS_IP = "150.161.2.10"
EXTERNAL_IP = "203.0.113.9"
#: Atrás de um proxy confiável (Caddy no compose, proxy do Render no piloto).
BEHIND_PROXY = ApiSettings(rate_limit=RateLimitConfig(trusted_proxy_hops=1))
#: Verificações por minuto por conta (S13-02).
LIMIT = RateLimitConfig().client_per_min


class Analyzer:
    """Analyzer simulado: conta as chamadas e pode demorar."""

    def __init__(self, delay_s: float = 0.0) -> None:
        self.calls = 0
        self.delay_s = delay_s

    async def __call__(self, _request: httpx2.Request) -> httpx2.Response:
        self.calls += 1
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        return httpx2.Response(200, json=VALID)


@pytest.fixture
def analyzer() -> Analyzer:
    return Analyzer()


def make_client(analyzer: Analyzer, settings: ApiSettings | None = None) -> TestClient:
    app, _store = make_app(settings, analyzer_transport=httpx2.MockTransport(analyzer))
    return TestClient(app)


@pytest.fixture
def client(analyzer: Analyzer) -> Iterator[TestClient]:
    with make_client(analyzer) as test_client:
        yield test_client


@pytest.fixture
def proxied(analyzer: Analyzer) -> Iterator[TestClient]:
    with make_client(analyzer, BEHIND_PROXY) as test_client:
        yield test_client


def new_student(client: TestClient) -> str:
    """Uma conta nova da equipe, com sessão aberta; devolve o identificador do cookie."""
    app = cast(FastAPI, client.app)
    store = cast(MemoryAccountStore, app.state.authenticator.store)
    return open_session(store, member(store))


def validate(
    client: TestClient,
    session: str | None = None,
    forwarded: str | None = None,
    body: Any = BODY,
) -> httpx2.Response:
    headers = {"Content-Type": "application/json"}
    if session is not None:
        headers["Cookie"] = f"{COOKIE}={session}"
    if forwarded is not None:
        headers["X-Forwarded-For"] = forwarded
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return client.post("/api/v1/validate", content=content, headers=headers)


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# --- US-17: limite por conta -------------------------------------------------------------------


def test_request_over_the_account_limit_in_a_minute_is_rate_limited(
    client: TestClient, analyzer: Analyzer
) -> None:
    student = new_student(client)

    responses = [validate(client, student) for _ in range(LIMIT + 1)]

    assert [r.status_code for r in responses[:LIMIT]] == [200] * LIMIT
    limited = responses[LIMIT]
    assert error_of(limited) == (429, "RATE_LIMITED")
    error = limited.json()["error"]
    assert 1 <= error["retry_after_s"] <= 60
    assert limited.headers["Retry-After"] == str(error["retry_after_s"])
    assert error["message"] == "Você fez muitas requisições em pouco tempo."
    assert limited.headers["X-Request-Id"]
    assert analyzer.calls == LIMIT  # a requisição recusada não chega ao analyzer


def test_default_limit_per_account_is_thirty() -> None:
    # S13-02 (C-04): a correção em lote passa das 10 por minuto do aluno anônimo.
    assert LIMIT == 30


def test_each_account_has_its_own_limit(client: TestClient) -> None:
    first, second = new_student(client), new_student(client)
    for _ in range(LIMIT):
        validate(client, first)

    assert validate(client, first).status_code == 429
    assert validate(client, second).status_code == 200


def test_two_sessions_of_one_account_share_its_limit(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    store = cast(MemoryAccountStore, app.state.authenticator.store)
    account = member(store)
    first, second = open_session(store, account), open_session(store, account)
    for _ in range(LIMIT):
        validate(client, first)

    # Entrar de novo não rende um limite maior: a chave é a conta, não a sessão.
    assert validate(client, second).status_code == 429


@pytest.mark.parametrize("session", [None, "nao-e-sessao", ""], ids=["sem", "invalida", "vazia"])
def test_requests_without_a_session_are_refused_and_share_the_limit_of_their_ip(
    proxied: TestClient, session: str | None
) -> None:
    for _ in range(LIMIT):
        assert error_of(validate(proxied, session, EXTERNAL_IP)) == (401, "UNAUTHENTICATED")

    assert validate(proxied, session, EXTERNAL_IP).status_code == 429
    assert validate(proxied, None, EXTERNAL_IP).status_code == 429
    assert validate(proxied, session, "198.51.100.20").status_code == 401  # outro IP
    assert validate(proxied, new_student(proxied), EXTERNAL_IP).status_code == 200  # com sessão


# --- US-17: limite por IP ----------------------------------------------------------------------


def test_sixty_members_behind_one_campus_ip_are_never_rate_limited(
    proxied: TestClient, analyzer: Analyzer
) -> None:
    students = [new_student(proxied) for _ in range(60)]

    statuses = {
        validate(proxied, student, CAMPUS_IP).status_code for _ in range(5) for student in students
    }

    assert statuses == {200}
    assert analyzer.calls == 300


def test_external_ip_is_limited_to_120_per_minute(proxied: TestClient, analyzer: Analyzer) -> None:
    # 130 contas de um mesmo IP externo, cada uma com 1 verificação.
    responses = [validate(proxied, new_student(proxied), EXTERNAL_IP) for _ in range(130)]

    assert [r.status_code for r in responses] == [200] * 120 + [429] * 10
    message = responses[-1].json()["error"]["message"]
    assert message == "Muitas requisições vieram da sua rede em pouco tempo."
    assert analyzer.calls == 120
    assert validate(proxied, new_student(proxied), "198.51.100.20").status_code == 200


def test_campus_limit_is_configurable(analyzer: Analyzer) -> None:
    settings = ApiSettings(
        rate_limit=RateLimitConfig(
            trusted_proxy_hops=1,
            campus_per_min=3,
            campus_networks=parse_networks("198.51.100.0/24"),
        )
    )
    with make_client(analyzer, settings) as client:
        statuses = [
            validate(client, new_student(client), "198.51.100.20").status_code for _ in range(4)
        ]

    assert statuses == [200, 200, 200, 429]


def test_an_account_over_its_limit_does_not_use_up_the_ip_of_its_colleagues(
    analyzer: Analyzer,
) -> None:
    settings = ApiSettings(rate_limit=RateLimitConfig(trusted_proxy_hops=1, ip_per_min=LIMIT + 2))
    with make_client(analyzer, settings) as client:
        abusive = new_student(client)
        for _ in range(100):
            validate(client, abusive, EXTERNAL_IP)  # 30 aceitas, 70 recusadas

        colleagues = [
            validate(client, new_student(client), EXTERNAL_IP).status_code for _ in range(3)
        ]

    assert colleagues == [200, 200, 429]  # só as aceitas contaram para o IP


# --- De onde vem o IP --------------------------------------------------------------------------


def test_spoofed_forwarded_address_does_not_earn_the_campus_limit(proxied: TestClient) -> None:
    # O cliente manda um X-Forwarded-For falso; o proxy acrescenta o endereço verdadeiro no fim.
    spoofed = f"{CAMPUS_IP}, {EXTERNAL_IP}"

    statuses = [validate(proxied, new_student(proxied), spoofed).status_code for _ in range(121)]

    assert statuses == [200] * 120 + [429]


def test_forwarded_header_is_ignored_without_a_trusted_proxy(client: TestClient) -> None:
    # Sem proxy configurado, trocar o X-Forwarded-For a cada requisição não muda nada.
    student = new_student(client)
    statuses = [validate(client, student, f"198.51.100.{n}").status_code for n in range(LIMIT + 1)]

    assert statuses == [200] * LIMIT + [429]


# --- Ordem: limite de corpo, limite de taxa, validação -----------------------------------------


def test_rate_limit_comes_before_validation_and_after_the_size_guard(
    client: TestClient, analyzer: Analyzer
) -> None:
    student = new_student(client)
    # Requisições inválidas também gastam o limite: ele é conferido antes de o corpo ser lido.
    for _ in range(LIMIT):
        assert validate(client, student, body={"code": ""}).status_code == 422

    assert validate(client, student, body=b'{"code": "x"').status_code == 429
    oversized = json.dumps({"code": "#" + "a" * 140_000, "list_number": 1}).encode()
    assert error_of(validate(client, student, body=oversized)) == (413, "PAYLOAD_TOO_LARGE")
    assert analyzer.calls == 0


def test_only_validation_and_login_are_rate_limited(client: TestClient) -> None:
    student = new_student(client)
    for _ in range(LIMIT + 1):
        validate(client, student)

    cookie = {"Cookie": f"{COOKIE}={student}"}
    for path in ("/api/v1/lists", "/api/v1/auth/me", "/health", "/ready"):
        statuses = {client.get(path, headers=cookie).status_code for _ in range(LIMIT + 5)}
        assert 429 not in statuses, path


# --- Log (NFR-11) ------------------------------------------------------------------------------


def test_rate_limited_requests_are_logged_without_ip_or_session(
    proxied: TestClient, capfd: pytest.CaptureFixture[str]
) -> None:
    student = new_student(proxied)
    for _ in range(LIMIT + 1):
        response = validate(proxied, student, EXTERNAL_IP)

    out = capfd.readouterr().out
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    (line,) = [x for x in lines if x.get("request_id") == response.headers["X-Request-Id"]]
    assert (line["status"], line["outcome"], line["rate_limit"]) == (429, "RATE_LIMITED", "client")
    assert line["path"] == "/api/v1/validate"
    assert "rate_limit" not in lines[0]
    assert student not in out
    assert EXTERNAL_IP not in out


# --- Admissão (NFR-05, US-18) ------------------------------------------------------------------


def test_saturated_service_answers_overloaded_quickly(capfd: pytest.CaptureFixture[str]) -> None:
    analyzer = Analyzer(delay_s=0.8)
    settings = ApiSettings(
        admission=AdmissionConfig(capacity=1, max_waiting=1, max_wait_s=0.2),
        rate_limit=RateLimitConfig(client_per_min=1_000, ip_per_min=1_000),
    )

    with make_client(analyzer, settings) as api, ThreadPoolExecutor(max_workers=3) as pool:
        sessions = [new_student(api) for _ in range(4)]

        def timed(index: int) -> tuple[httpx2.Response, float]:
            start = time.perf_counter()
            response = validate(api, sessions[index])
            return response, time.perf_counter() - start

        results = list(pool.map(timed, range(3)))
        after = validate(api, sessions[3])  # passada a rajada, o serviço se recupera

    served = [response for response, _ in results if response.status_code == 200]
    refused = [(response, elapsed) for response, elapsed in results if response.status_code != 200]
    assert len(served) == 1
    assert len(refused) == 2
    for response, elapsed in refused:
        assert error_of(response) == (503, "OVERLOADED")
        assert response.json()["error"]["retry_after_s"] == 10
        assert response.headers["Retry-After"] == "10"
        assert elapsed < 0.6  # recusada sem esperar a análise em curso (0,8 s)
    assert analyzer.calls == 2  # as recusadas não chegaram ao analyzer
    assert after.status_code == 200

    lines = [json.loads(x) for x in capfd.readouterr().out.splitlines() if x.startswith("{")]
    assert [x["outcome"] for x in lines if x.get("status") == 503] == ["OVERLOADED"] * 2


def test_invalid_requests_do_not_take_a_slot() -> None:
    settings = ApiSettings(
        admission=AdmissionConfig(capacity=0, max_waiting=0),
        enabled_lists=frozenset({1, 2, 3, 4, 5}),
    )
    with make_client(Analyzer(), settings) as client:
        student = new_student(client)
        # Sem nenhuma vaga, o que é recusado na validação continua recebendo o próprio erro.
        assert error_of(validate(client, student, body={"code": "x", "list_number": 6})) == (
            422,
            "LIST_NOT_ENABLED",
        )
        assert error_of(validate(client, student)) == (503, "OVERLOADED")
        assert client.get("/health").status_code == 200


# --- Configuração ------------------------------------------------------------------------------


def test_settings_from_environment() -> None:
    settings = ApiSettings.from_env(
        {
            "IPC_RATE_LIMIT_CLIENT_PER_MIN": "20",
            "IPC_RATE_LIMIT_IP_PER_MIN": "240",
            "IPC_RATE_LIMIT_CAMPUS_PER_MIN": "2000",
            "IPC_RATE_LIMIT_CAMPUS_CIDRS": "150.161.0.0/16,2001:db8::/32",
            "IPC_TRUSTED_PROXY_HOPS": "1",
            "IPC_RATE_LIMIT_MAX_KEYS": "1000",
            "IPC_RATE_LIMIT_EDGE_HEADER": "CF-Connecting-IP",
            "IPC_TRUST_FORWARDED_HEADER": "1",
            "IPC_RATE_LIMIT_EDGE_ANONYMOUS_PER_MIN": "45",
            "IPC_ADMISSION_CAPACITY": "8",
            "IPC_ADMISSION_MAX_WAITING": "32",
            "IPC_ADMISSION_MAX_WAIT_S": "0.5",
        }
    )

    assert settings.rate_limit == RateLimitConfig(
        client_per_min=20,
        ip_per_min=240,
        campus_per_min=2_000,
        campus_networks=parse_networks("150.161.0.0/16,2001:db8::/32"),
        trusted_proxy_hops=1,
        max_keys=1_000,
        trust_forwarded_header=True,
        edge_ip_header="cf-connecting-ip",
        edge_anonymous_per_min=45,
    )
    assert settings.admission == AdmissionConfig(capacity=8, max_waiting=32, max_wait_s=0.5)


def test_default_limits_follow_the_blueprint() -> None:
    settings = ApiSettings.from_env({})

    # FR-19, P-04 e C-04: 30/min por conta, 120/min por IP externo, 1.000/min na faixa da UFPE.
    assert settings.rate_limit == RateLimitConfig(
        client_per_min=30,
        ip_per_min=120,
        campus_per_min=1_000,
        campus_networks=parse_networks("150.161.0.0/16"),
        trusted_proxy_hops=0,
    )
    # C3: 2 análises por worker do analyzer e espera de até 1 s.
    assert settings.admission == AdmissionConfig(capacity=4, max_waiting=64, max_wait_s=1.0)


def test_invalid_campus_cidrs_prevent_startup() -> None:
    with pytest.raises(ValueError, match="IPC_RATE_LIMIT_CAMPUS_CIDRS"):
        ApiSettings.from_env({"IPC_RATE_LIMIT_CAMPUS_CIDRS": "campus"})


def test_proxy_check_shows_only_proxy_headers_and_the_client_ip(analyzer: Analyzer) -> None:
    # S30-03: diagnóstico do piloto; devolve a quem chama só os cabeçalhos de proxy e a chave.
    with make_client(analyzer, BEHIND_PROXY) as client:
        response = client.get(
            "/api/v1/proxy-check",
            headers={
                "X-Forwarded-For": "203.0.113.9, 198.51.100.7",
                "Cookie": "segredo=1",
                "Authorization": "Bearer segredo",
            },
        )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "headers": {"x-forwarded-for": ["203.0.113.9, 198.51.100.7"]},
        "client_ip": "198.51.100.7",
        "trusted_proxy_hops": 1,
        "trust_forwarded_header": False,
    }


def test_proxy_check_also_answers_post(analyzer: Analyzer) -> None:
    with make_client(analyzer, BEHIND_PROXY) as client:
        response = client.post(
            "/api/v1/proxy-check", headers={"X-Forwarded-For": "198.51.100.7"}, content=b""
        )

    assert response.status_code == 200
    assert response.json()["client_ip"] == "198.51.100.7"

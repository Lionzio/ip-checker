"""Acesso restrito à equipe (S13-02; FR-22, FR-25, NFR-22, NFR-23; DoD itens 16, 19 e 20).

A API roda com o repositório em memória e um relógio controlável. Os mesmos fluxos contra o
compose de verdade estão na suíte de segurança (``tests/security``).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import (
    BASE_URL,
    DEV_EMAIL,
    DEV_NAME,
    FAST_PASSWORDS,
    PASSWORD,
    cookie_header,
    make_app,
    member,
    open_session,
)
from conftest import REPO_ROOT
from ipc_api.accounts.models import AccountConflict, Role, Status, Treatment
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.app import create_app
from ipc_api.auth.accounts import AccountsConfig
from ipc_api.auth.sessions import PLAIN_COOKIE, SECURE_COOKIE, SessionConfig, token_hash
from ipc_api.auth.throttle import LoginThrottle, LoginThrottleConfig
from ipc_api.ratelimit import RateLimitConfig, parse_networks
from ipc_api.settings import ApiSettings, DeveloperSettings

SECONDARY_EMAIL = "vinicius.leoncio@ufpe.br"
VALID = {
    "ruleset_version": "2026.2.0",
    "status": "valid",
    "list_number": 1,
    "syntax_error": None,
    "violations": [],
    "truncated": False,
}
MANIFEST = {
    "ruleset_version": "2026.2.0",
    "ruleset_sha256": "a" * 64,
    "period": "2026.2",
    "target_python": "3.13",
    "lists": [{"number": 1, "title": "Comandos condicionais"}],
}
HEALTH = {
    "status": "ok",
    "ruleset_version": "2026.2.0",
    "ruleset_sha256": "a" * 64,
    "target_python": "3.13",
    "workers": 2,
}
INVALID_CREDENTIALS = (
    "Nome, e-mail ou senha incorretos. Se você criou a conta pelo Google, entre pelo Google ou "
    "defina uma senha no perfil."
)


def analyzer(request: httpx2.Request) -> httpx2.Response:
    body = {"/internal/health": HEALTH, "/internal/ruleset/manifest": MANIFEST}
    return httpx2.Response(200, json=body.get(request.url.path, VALID))


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store() -> MemoryAccountStore:
    return MemoryAccountStore()


def start(
    store: MemoryAccountStore, clock: Clock | None = None, settings: ApiSettings | None = None
) -> TestClient:
    app, _ = make_app(
        settings, analyzer_transport=httpx2.MockTransport(analyzer), store=store, clock=clock
    )
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def api(store: MemoryAccountStore, clock: Clock) -> Iterator[TestClient]:
    with start(store, clock) as client:
        yield client


def login(client: TestClient, login: str = DEV_EMAIL, password: str = PASSWORD) -> httpx2.Response:
    return client.post("/api/v1/auth/login", json={"login": login, "password": password})


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def hashed(password: str = PASSWORD) -> str:
    return FAST_PASSWORDS.hash_sync(password)


# --- FR-22: nada sem sessão --------------------------------------------------------------------

OPEN_ROUTES = {
    ("GET", "/health"),
    ("GET", "/ready"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/verify"),
    ("POST", "/api/v1/auth/verify/resend"),
    # Sprint 16: as formas de entrar e o Google, que abrem a sessão em vez de exigi-la.
    ("GET", "/api/v1/auth/options"),
    ("GET", "/api/v1/auth/google/start"),
    ("GET", "/api/v1/auth/google/callback"),
    ("GET", "/api/v1/auth/google/pending"),
    ("POST", "/api/v1/auth/google/complete"),
}


def _documented_routes() -> list[tuple[str, str]]:
    contract = json.loads((REPO_ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    return [
        (method.upper(), path)
        for path, operations in contract["paths"].items()
        for method in operations
    ]


@pytest.mark.parametrize("route", _documented_routes(), ids=lambda r: f"{r[0]} {r[1]}")
def test_every_route_but_health_ready_and_auth_requires_a_session(
    api: TestClient, route: tuple[str, str]
) -> None:
    method, path = route
    for headers in ({}, cookie_header("x" * 43), cookie_header("lixo")):
        response = api.request(method, path, json={}, headers=headers)
        if route in OPEN_ROUTES:
            assert response.status_code != 401, route
        else:
            assert error_of(response) == (401, "UNAUTHENTICATED"), (route, headers)
            assert set(response.json()) == {"error"}  # nenhum dado sem sessão


def test_the_open_routes_are_exactly_the_expected_ones() -> None:
    documented = set(_documented_routes())

    assert documented >= OPEN_ROUTES
    assert ("GET", "/api/v1/auth/me") in documented - OPEN_ROUTES


def test_unauthenticated_message(api: TestClient) -> None:
    response = api.get("/api/v1/lists")

    assert response.json()["error"]["message"] == (
        "Entre com a sua conta da equipe para usar o IP-Checker."
    )


# --- Conta do desenvolvedor (P-14) -------------------------------------------------------------


def test_developer_enters_with_either_email_or_the_name(api: TestClient) -> None:
    for identifier in (DEV_EMAIL, SECONDARY_EMAIL, "VLACG@CIN.UFPE.BR", DEV_NAME.upper()):
        response = login(api, identifier)
        assert response.status_code == 200, identifier
        assert response.json() == {
            "name": DEV_NAME,
            "email": DEV_EMAIL,
            "course": "Ciência da Computação",
            "treatment": "masculino",
            "role": "desenvolvedor",
            # Pedido do autor (02/10/2026); no feedback, a linha "Monitor" do FR-30.
            "role_label": "Monitor e desenvolvedor",
            "has_password": True,
            "can_manage": True,
        }


def test_seed_is_idempotent_and_the_initial_password_only_counts_at_creation(
    store: MemoryAccountStore,
) -> None:
    with start(store):
        pass
    (developer,) = store.accounts.values()

    other = ApiSettings(developer=DeveloperSettings(initial_password="Outra-senha-1"))
    with start(store, settings=other) as client:
        assert len(store.accounts) == 1
        assert next(iter(store.accounts.values())).id == developer.id
        assert login(client).status_code == 200
        assert login(client, password="Outra-senha-1").status_code == 401


def test_weak_initial_password_prevents_startup(store: MemoryAccountStore) -> None:
    weak = ApiSettings(developer=DeveloperSettings(initial_password="fraca"))

    with (
        pytest.raises(ValueError, match="IPC_DEV_INITIAL_PASSWORD precisa"),
        start(store, settings=weak),
    ):
        pass


def test_without_initial_password_the_developer_has_no_password(
    store: MemoryAccountStore, caplog: pytest.LogCaptureFixture
) -> None:
    # Sem make_app: ele daria à conta a senha de teste.
    plain = create_app(ApiSettings(json_logs=False), account_store=store, passwords=FAST_PASSWORDS)
    with TestClient(plain, base_url=BASE_URL) as client:
        assert error_of(login(client)) == (401, "INVALID_CREDENTIALS")
    (developer,) = store.accounts.values()
    assert developer.password_hash is None
    assert "IPC_DEV_INITIAL_PASSWORD" in caplog.text


def test_developer_emails_in_two_accounts_prevent_startup(store: MemoryAccountStore) -> None:
    member(store, email=SECONDARY_EMAIL)
    member(store, email=DEV_EMAIL)

    with pytest.raises(AccountConflict), start(store):
        pass


def test_startup_without_database_url_fails() -> None:
    with (
        pytest.raises(RuntimeError, match="IPC_DATABASE_URL"),
        TestClient(create_app(ApiSettings())),
    ):
        pass


# --- FR-25: entrar -----------------------------------------------------------------------------


def test_login_opens_a_session_with_a_secure_cookie(
    api: TestClient, store: MemoryAccountStore
) -> None:
    response = login(api)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    cookie = SimpleCookie(response.headers["set-cookie"])[SECURE_COOKIE]
    assert len(cookie.value) == 43  # 256 bits em base64url
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert cookie["max-age"] == str(7 * 24 * 3600)
    # O banco guarda só o hash do identificador.
    assert token_hash(cookie.value) in store.sessions
    assert cookie.value.encode() not in b"".join(store.sessions)
    assert api.get("/api/v1/auth/me").json()["email"] == DEV_EMAIL


def test_cookie_without_secure_only_when_configured(store: MemoryAccountStore) -> None:
    settings = ApiSettings(session=SessionConfig(cookie_secure=False))
    with start(store, settings=settings) as client:
        response = login(client)

    cookie = SimpleCookie(response.headers["set-cookie"])[PLAIN_COOKIE]
    assert cookie["secure"] == ""
    assert cookie["httponly"] is True


def test_wrong_password_and_unknown_account_get_the_same_answer(api: TestClient) -> None:
    wrong = login(api, password="Senha-errada-1")
    unknown = login(api, "ninguem@cin.ufpe.br")
    unknown_name = login(api, "Ninguém Mesmo")

    for response in (wrong, unknown, unknown_name):
        assert error_of(response) == (401, "INVALID_CREDENTIALS")
        assert response.json()["error"]["message"] == INVALID_CREDENTIALS
        assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "email",
    [
        "x@xcin.ufpe.br",
        "x@ee.ufpe.br",
        "x@gmail.com",
        "x@cin.ufpe.br.exemplo.com",
        "a@b@cin.ufpe.br",
    ],
)
def test_email_outside_the_allowed_domains_is_refused(api: TestClient, email: str) -> None:
    response = login(api, email)

    assert error_of(response) == (422, "DOMAIN_NOT_ALLOWED")
    assert response.json()["error"]["message"] == (
        "Só e-mails @cin.ufpe.br e @ufpe.br têm acesso ao IP-Checker."
    )


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (
            Status.AGUARDANDO_VERIFICACAO,
            "ACCOUNT_PENDING_VERIFICATION",
            "Confirme o seu e-mail pelo link que enviamos antes de entrar.",
        ),
        (
            Status.AGUARDANDO_APROVACAO,
            "ACCOUNT_PENDING_APPROVAL",
            "O seu cadastro está aguardando a aprovação de um monitor-chefe, de um professor ou "
            "do desenvolvedor.",
        ),
        (Status.RECUSADO, "ACCOUNT_REJECTED", "O seu cadastro foi recusado."),
        (
            Status.EX_MONITOR,
            "ACCOUNT_REMOVED",
            "Esta conta foi removida da equipe e não tem mais acesso.",
        ),
        (
            Status.CONSELHEIRO,
            "ACCOUNT_REMOVED",
            "Esta conta foi removida da equipe e não tem mais acesso.",
        ),
        (
            Status.INATIVO,
            "ACCOUNT_REMOVED",
            "Esta conta foi removida da equipe e não tem mais acesso.",
        ),
    ],
)
def test_account_status_is_revealed_only_with_the_right_password(
    api: TestClient, store: MemoryAccountStore, status: Status, code: str, message: str
) -> None:
    role = Role.MONITOR if status is not Status.AGUARDANDO_APROVACAO else None
    account = member(store, status=status, role=role, password_hash=hashed())

    wrong = login(api, account.primary_email, "Senha-errada-1")
    right = login(api, account.primary_email)

    assert error_of(wrong) == (401, "INVALID_CREDENTIALS")
    assert error_of(right) == (403, code)
    assert right.json()["error"]["message"] == message
    assert "set-cookie" not in right.headers
    assert not store.sessions


def test_account_without_password_cannot_enter_with_a_password(
    api: TestClient, store: MemoryAccountStore
) -> None:
    google_only = member(store, password_hash=None)

    assert error_of(login(api, google_only.primary_email, "")) == (422, "INVALID_INPUT")
    assert error_of(login(api, google_only.primary_email, "Qualquer-1")) == (
        401,
        "INVALID_CREDENTIALS",
    )


def test_each_login_gets_a_new_identifier_and_drops_the_one_presented(
    api: TestClient, store: MemoryAccountStore
) -> None:
    first = SimpleCookie(login(api).headers["set-cookie"])[SECURE_COOKIE].value
    second = SimpleCookie(login(api).headers["set-cookie"])[SECURE_COOKIE].value

    assert first != second
    # O identificador que o navegador apresentou no segundo login não vale mais (fixação).
    assert token_hash(first) not in store.sessions
    assert token_hash(second) in store.sessions


def test_invalid_login_body(api: TestClient) -> None:
    response = api.post("/api/v1/auth/login", json={"login": DEV_EMAIL})

    assert error_of(response) == (422, "INVALID_INPUT")
    assert "envie login" in response.json()["error"]["message"]


# --- Bloqueio por tentativas (NFR-22, DoD item 20) ---------------------------------------------


def test_sixth_attempt_after_five_failures_waits_even_with_the_right_password(
    api: TestClient,
) -> None:
    for _ in range(5):
        assert login(api, password="Senha-errada-1").status_code == 401

    blocked = login(api)

    assert error_of(blocked) == (429, "RATE_LIMITED")
    retry = blocked.json()["error"]["retry_after_s"]
    assert 1 <= retry <= 15 * 60
    assert blocked.headers["Retry-After"] == str(retry)


def test_name_and_email_of_the_same_account_share_the_failures(api: TestClient) -> None:
    for identifier in (DEV_EMAIL, SECONDARY_EMAIL, DEV_NAME, DEV_EMAIL, DEV_NAME):
        assert login(api, identifier, "Senha-errada-1").status_code == 401

    assert login(api, DEV_NAME).status_code == 429


def test_a_right_login_clears_the_failures(api: TestClient) -> None:
    for _ in range(4):
        login(api, password="Senha-errada-1")
    assert login(api).status_code == 200

    for _ in range(4):
        assert login(api, password="Senha-errada-1").status_code == 401
    assert login(api).status_code == 200


def test_failures_from_one_ip_are_limited_across_accounts(store: MemoryAccountStore) -> None:
    settings = ApiSettings(login_throttle=LoginThrottleConfig(ip_failures=3))
    with start(store, settings=settings) as client:
        for index in range(3):
            assert login(client, f"ninguem{index}@cin.ufpe.br").status_code == 401

        assert login(client).status_code == 429


def test_campus_has_a_higher_limit_of_failures(store: MemoryAccountStore) -> None:
    settings = ApiSettings(
        rate_limit=RateLimitConfig(
            trusted_proxy_hops=1, campus_networks=parse_networks("150.161.0.0/16")
        ),
        login_throttle=LoginThrottleConfig(ip_failures=2, campus_ip_failures=4),
    )
    with start(store, settings=settings) as client:
        campus = {"X-Forwarded-For": "150.161.2.10"}
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"login": f"ninguem{index}@cin.ufpe.br", "password": "x"},
                headers=campus,
            ).status_code
            for index in range(5)
        ]

    assert statuses == [401, 401, 401, 401, 429]


def test_failures_expire_after_the_window() -> None:
    now = [0.0]
    throttle = LoginThrottle(clock=lambda: now[0])
    key = throttle.key("a", "alguem")
    for _ in range(5):
        throttle.fail([key])

    assert throttle.retry_after([(key, 5)]) == 15 * 60
    now[0] = 15 * 60 - 1
    assert throttle.retry_after([(key, 5)]) == 1
    now[0] = 15 * 60
    assert throttle.retry_after([(key, 5)]) is None


def test_throttle_keys_are_opaque() -> None:
    throttle = LoginThrottle()
    key = throttle.key("a", DEV_EMAIL)

    assert DEV_EMAIL.encode() not in key
    assert key != LoginThrottle().key("a", DEV_EMAIL)  # sal por processo


def test_full_throttle_still_records_known_keys() -> None:
    throttle = LoginThrottle(max_keys=1)
    first, second = throttle.key("a", "1"), throttle.key("a", "2")

    throttle.fail([first])
    throttle.fail([second])  # tabela cheia: a chave nova não entra
    throttle.fail([first])

    assert throttle.retry_after([(first, 2)]) is not None
    assert throttle.retry_after([(second, 1)]) is None


# --- Sessão: uso, expiração e saída ------------------------------------------------------------


def test_me_shows_the_treatment_only_to_its_owner(
    api: TestClient, store: MemoryAccountStore
) -> None:
    account = member(store, name="Ana Lima", treatment=Treatment.NEUTRO)
    response = api.get("/api/v1/auth/me", headers=cookie_header(open_session(store, account)))

    assert response.json() == {
        "name": "Ana Lima",
        "email": account.primary_email,
        "course": "Ciência da Computação",
        "treatment": "neutro",
        "role": "monitor",
        "role_label": "Monitor",
        "has_password": False,
        # Monitor não gerencia a equipe (FR-27).
        "can_manage": False,
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_session_expires_after_twelve_idle_hours(
    api: TestClient, store: MemoryAccountStore, clock: Clock
) -> None:
    login(api)
    clock.now += timedelta(hours=11, minutes=59)
    assert api.get("/api/v1/auth/me").status_code == 200  # renova o "último uso"

    clock.now += timedelta(hours=11, minutes=59)
    assert api.get("/api/v1/auth/me").status_code == 200

    clock.now += timedelta(hours=12)
    assert error_of(api.get("/api/v1/auth/me")) == (401, "UNAUTHENTICATED")
    assert not store.sessions  # a sessão vencida é apagada


def test_session_lasts_at_most_seven_days(
    api: TestClient, store: MemoryAccountStore, clock: Clock
) -> None:
    login(api)
    for _ in range(14):  # usada a cada 12 h menos 1 min: nunca ociosa
        clock.now += timedelta(hours=11, minutes=59)
        assert api.get("/api/v1/auth/me").status_code == 200

    clock.now += timedelta(minutes=15)  # 7 dias e 1 minuto depois do login
    assert clock.now > datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    assert error_of(api.get("/api/v1/auth/me")) == (401, "UNAUTHENTICATED")


def test_last_use_is_written_at_most_every_five_minutes(
    api: TestClient, store: MemoryAccountStore, clock: Clock
) -> None:
    login(api)
    (session,) = store.sessions.values()
    start_time = session.last_seen_at

    clock.now += timedelta(minutes=4)
    api.get("/api/v1/auth/me")
    assert session.last_seen_at == start_time
    clock.now += timedelta(minutes=2)
    api.get("/api/v1/auth/me")
    assert session.last_seen_at == clock.now


def test_an_account_that_stops_being_active_loses_its_sessions(
    api: TestClient, store: MemoryAccountStore
) -> None:
    account = member(store)
    token = open_session(store, account)
    assert api.get("/api/v1/auth/me", headers=cookie_header(token)).status_code == 200

    store.accounts[account.id] = replace(account, status=Status.EX_MONITOR)

    assert api.get("/api/v1/auth/me", headers=cookie_header(token)).status_code == 401
    assert token_hash(token) not in store.sessions


def test_logout_ends_the_session_and_clears_the_cookie(
    api: TestClient, store: MemoryAccountStore
) -> None:
    login(api)

    response = api.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert not store.sessions
    cookie = SimpleCookie(response.headers["set-cookie"])[SECURE_COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert api.get("/api/v1/auth/me").status_code == 401
    assert api.post("/api/v1/auth/logout").status_code == 204  # sem sessão também


# --- Origin (CSRF, ADR-04) ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "null", "https://testserver.evil.example", "file://"]
)
def test_state_changes_from_other_sites_are_refused(api: TestClient, origin: str) -> None:
    for path, body in (
        ("/api/v1/auth/login", {"login": DEV_EMAIL, "password": PASSWORD}),
        ("/api/v1/auth/logout", None),
        ("/api/v1/validate", {"code": "x = 1\n", "list_number": 1}),
    ):
        response = api.post(path, json=body, headers={"Origin": origin})
        assert error_of(response) == (403, "ORIGIN_MISMATCH"), (path, origin)
        assert response.json()["error"]["message"] == (
            "A requisição veio de outro site e foi recusada."
        )


def test_same_origin_and_configured_origins_are_accepted(store: MemoryAccountStore) -> None:
    settings = ApiSettings(allowed_origins=("https://ip-checker.vercel.app/",))
    with start(store, settings=settings) as client:
        for origin in ("https://testserver", "https://ip-checker.vercel.app", "HTTPS://TESTSERVER"):
            response = client.post(
                "/api/v1/auth/login",
                json={"login": DEV_EMAIL, "password": PASSWORD},
                headers={"Origin": origin},
            )
            assert response.status_code == 200, origin


def test_the_page_origin_is_accepted_behind_a_rewrite(store: MemoryAccountStore) -> None:
    # Piloto (S16-02): a Vercel repassa /api/* ao Render, então o Host é o do Render e o Origin é
    # o da página, que é o endereço público configurado.
    settings = ApiSettings(accounts=AccountsConfig(public_base_url="https://ip-checker.vercel.app"))
    with start(store, settings=settings) as client:
        headers = {"Host": "ip-checker-api.onrender.com"}
        page = client.post(
            "/api/v1/auth/login",
            json={"login": DEV_EMAIL, "password": PASSWORD},
            headers={**headers, "Origin": "https://ip-checker.vercel.app"},
        )
        evil = client.post(
            "/api/v1/auth/login",
            json={"login": DEV_EMAIL, "password": PASSWORD},
            headers={**headers, "Origin": "https://ip-checker.vercel.app.evil.example"},
        )

    assert page.status_code == 200
    assert error_of(evil) == (403, "ORIGIN_MISMATCH")


def test_reading_from_another_origin_is_not_blocked_here(
    api: TestClient, store: MemoryAccountStore
) -> None:
    # GET não muda estado; quem impede outro site de ler a resposta é o CORS do navegador.
    token = open_session(store, member(store))
    response = api.get(
        "/api/v1/lists", headers={"Origin": "https://evil.example", **cookie_header(token)}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


# --- Banco fora do ar --------------------------------------------------------------------------


def test_database_outage_is_a_503_not_a_401(api: TestClient, store: MemoryAccountStore) -> None:
    token = open_session(store, member(store))
    store.available = False

    for response in (
        api.get("/api/v1/auth/me", headers=cookie_header(token)),
        api.get("/api/v1/lists", headers=cookie_header(token)),
        login(api),
        api.post("/api/v1/auth/logout", headers=cookie_header(token)),
        api.get("/ready"),
    ):
        assert error_of(response) == (503, "DATABASE_UNAVAILABLE")
        assert response.headers["Retry-After"] == "30"
    assert api.get("/health").status_code == 200


# --- Configuração ------------------------------------------------------------------------------


def test_auth_settings_from_environment() -> None:
    settings = ApiSettings.from_env(
        {
            "IPC_DATABASE_URL": "postgresql://ipc_api:x@db:5432/ipchecker",
            "IPC_SESSION_COOKIE_SECURE": "0",
            "IPC_SESSION_IDLE_TIMEOUT_S": "600",
            "IPC_SESSION_ABSOLUTE_TIMEOUT_S": "3600",
            "IPC_LOGIN_ACCOUNT_FAILURES": "3",
            "IPC_LOGIN_IP_FAILURES": "10",
            "IPC_LOGIN_CAMPUS_IP_FAILURES": "50",
            "IPC_ALLOWED_ORIGINS": "https://ip-checker.vercel.app",
            "IPC_DEV_NAME": " Fulano de Tal ",
            "IPC_DEV_COURSE": "Engenharia da Computação",
            "IPC_DEV_EMAILS": "Fulano@CIN.ufpe.br, fulano@ufpe.br",
            "IPC_DEV_INITIAL_PASSWORD": "Senha-forte-1",
        }
    )

    assert settings.database_url == "postgresql://ipc_api:x@db:5432/ipchecker"
    assert settings.session == SessionConfig(
        cookie_secure=False, idle_timeout_s=600, absolute_timeout_s=3600
    )
    assert settings.login_throttle == LoginThrottleConfig(
        account_failures=3, ip_failures=10, campus_ip_failures=50
    )
    assert settings.allowed_origins == ("https://ip-checker.vercel.app",)
    assert settings.developer == DeveloperSettings(
        name="Fulano de Tal",
        course="Engenharia da Computação",
        emails=("fulano@cin.ufpe.br", "fulano@ufpe.br"),
        initial_password="Senha-forte-1",
    )
    # Segredos fora da representação (logs de depuração, tracebacks).
    assert "Senha-forte-1" not in repr(settings)
    assert "ipc_api:x" not in repr(settings)


def test_auth_defaults() -> None:
    settings = ApiSettings.from_env({})

    assert settings.database_url is None
    assert settings.session == SessionConfig()
    assert settings.session.cookie_name == SECURE_COOKIE
    assert (settings.session.idle_timeout_s, settings.session.absolute_timeout_s) == (
        12 * 3600,
        7 * 24 * 3600,
    )
    assert settings.login_throttle == LoginThrottleConfig(
        account_failures=5, ip_failures=30, campus_ip_failures=200
    )
    assert settings.developer.emails == (DEV_EMAIL, SECONDARY_EMAIL)
    assert settings.developer.initial_password is None


@pytest.mark.parametrize("value", ["", "fulano@gmail.com", "fulano@xcin.ufpe.br,x@ufpe.br"])
def test_invalid_developer_emails_prevent_startup(value: str) -> None:
    with pytest.raises(ValueError, match="IPC_DEV_EMAILS"):
        ApiSettings.from_env({"IPC_DEV_EMAILS": value})

"""Entrada e registro pelo Google com um provedor OIDC falso (S16-01; FR-24, FR-25, US-25).

O provedor falso assina ID tokens RS256 de verdade com uma chave gerada no teste, publica o JWKS e
confere, no endpoint de token, o ``code_verifier`` contra o ``code_challenge`` que a API mandou na
URL de autorização (PKCE). Cada recusa do FR-24 é provocada: domínio fora (inclusive com ``hd``
adulterado), ``email_verified`` falso, ``state`` trocado ou reutilizado, ``nonce``, emissor,
audiência e assinatura errados, e o pré-sequestro de conta.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from api_support import (
    BASE_URL,
    COOKIE,
    DEV_EMAIL,
    FAST_PASSWORDS,
    PASSWORD,
    cookie_header,
    make_app,
    member,
    open_session,
)
from ipc_api.accounts.models import Role, SignupMethod, Status
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.auth.google import Expiring, GoogleConfig
from ipc_api.auth.sessions import token_hash
from ipc_api.settings import ApiSettings

CLIENT_ID = "cliente-de-teste.apps.googleusercontent.com"
GOOGLE = GoogleConfig(client_id=CLIENT_ID, client_secret="segredo-de-teste")
SETTINGS = ApiSettings(google=GOOGLE)
CALLBACK = "http://127.0.0.1:8180/api/v1/auth/google/callback"
OAUTH_COOKIE = "__Host-ipc_oauth"
SIGNUP_COOKIE = "__Host-ipc_google"


@dataclass
class FakeGoogle:
    """O provedor OIDC falso: endpoint de token e JWKS, por um transporte em memória."""

    key: RSAKey = field(default_factory=lambda: RSAKey.generate_key(2048, parameters={"kid": "k1"}))
    published: list[RSAKey] = field(default_factory=list)
    codes: dict[str, tuple[dict[str, Any], str, RSAKey | None]] = field(default_factory=dict)
    token_status: int = 200
    jwks_down: bool = False
    network_down: bool = False
    received: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.published = [self.key]

    def claims(self, expected_nonce: str, **changes: Any) -> dict[str, Any]:
        now = int(time.time())
        base = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "azp": CLIENT_ID,
            "sub": "google-sub-1",
            "email": "gabi@cin.ufpe.br",
            "email_verified": True,
            "name": "Gabi Google",
            "nonce": expected_nonce,
            "iat": now,
            "exp": now + 3600,
        }
        base.update(changes)
        return {k: v for k, v in base.items() if v is not None}

    def issue(
        self, code: str, claims: dict[str, Any], challenge: str, key: RSAKey | None = None
    ) -> None:
        self.codes[code] = (claims, challenge, key)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if self.network_down:
            raise httpx2.ConnectError("sem rede", request=request)
        if request.url.path == "/oauth2/v3/certs":
            if self.jwks_down:
                return httpx2.Response(503)
            keys: list[Any] = list(self.published)
            return httpx2.Response(200, json=KeySet(keys).as_dict(private=False))
        assert request.url.path == "/token"
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.received.append(form)
        if self.token_status != 200:
            return httpx2.Response(self.token_status, json={"error": "invalid_grant"})
        claims, challenge, key = self.codes.pop(form["code"], ({}, "", None))
        valid = (
            form.get("grant_type") == "authorization_code"
            and form.get("client_id") == CLIENT_ID
            and form.get("client_secret") == GOOGLE.client_secret
            and form.get("redirect_uri") == CALLBACK
            and create_s256_code_challenge(form.get("code_verifier", "")) == challenge
        )
        if not claims or not valid:
            return httpx2.Response(400, json={"error": "invalid_grant"})
        signer = key or self.key
        token = jwt.encode({"alg": "RS256", "kid": signer.kid}, claims, signer)
        return httpx2.Response(
            200, json={"id_token": token, "access_token": "a", "token_type": "Bearer"}
        )


@pytest.fixture
def fake() -> FakeGoogle:
    return FakeGoogle()


@pytest.fixture
def store() -> MemoryAccountStore:
    return MemoryAccountStore()


@pytest.fixture
def api(fake: FakeGoogle, store: MemoryAccountStore) -> Iterator[TestClient]:
    app, _ = make_app(SETTINGS, store=store, google_transport=httpx2.MockTransport(fake.handle))
    with TestClient(app, base_url=BASE_URL, follow_redirects=False) as client:
        yield client


def start(api: TestClient) -> dict[str, str]:
    response = api.get("/api/v1/auth/google/start")
    assert response.status_code == 303
    return {k: v[0] for k, v in parse_qs(urlsplit(response.headers["location"]).query).items()}


def sign_in(
    api: TestClient, fake: FakeGoogle, key: RSAKey | None = None, **claims: Any
) -> httpx2.Response:
    """Começa pelo /start, emite um código no provedor falso e volta pelo /callback."""
    query = start(api)
    fake.issue("codigo", fake.claims(query["nonce"], **claims), query["code_challenge"], key)
    return api.get(
        "/api/v1/auth/google/callback", params={"code": "codigo", "state": query["state"]}
    )


def landing(response: httpx2.Response) -> str:
    assert response.status_code == 303
    return response.headers["location"]


def complete(api: TestClient, **body: str) -> httpx2.Response:
    data = {"name": "Gabi Google", "course": "Ciência da Computação", "treatment": "feminino"}
    return api.post("/api/v1/auth/google/complete", json={**data, **body})


# --- Configuração e início -----------------------------------------------------------------------


def test_google_settings_come_in_pairs() -> None:
    assert not GoogleConfig.from_env({}).enabled
    config = GoogleConfig.from_env(
        {"IPC_GOOGLE_CLIENT_ID": CLIENT_ID, "IPC_GOOGLE_CLIENT_SECRET": "segredo-env"}
    )
    assert config.enabled
    assert "segredo-env" not in repr(ApiSettings(google=config))
    with pytest.raises(ValueError, match="IPC_GOOGLE_CLIENT_SECRET"):
        GoogleConfig.from_env({"IPC_GOOGLE_CLIENT_ID": CLIENT_ID})


def test_without_configuration_google_is_off(store: MemoryAccountStore) -> None:
    app, _ = make_app(store=store)
    with TestClient(app, base_url=BASE_URL, follow_redirects=False) as api:
        assert api.get("/api/v1/auth/options").json() == {"google": False}
        assert landing(api.get("/api/v1/auth/google/start")) == "/entrar?google=indisponivel"
        callback = api.get("/api/v1/auth/google/callback", params={"code": "c", "state": "s"})
        assert landing(callback) == "/entrar?google=indisponivel"


def test_start_sends_state_nonce_pkce_and_hd_only_as_a_hint(api: TestClient) -> None:
    assert api.get("/api/v1/auth/options").json() == {"google": True}
    response = api.get("/api/v1/auth/google/start")
    location = urlsplit(response.headers["location"])
    query = {k: v[0] for k, v in parse_qs(location.query).items()}

    assert f"{location.scheme}://{location.netloc}{location.path}" == GOOGLE.authorization_endpoint
    assert query["response_type"] == "code"
    assert query["client_id"] == CLIENT_ID
    # O retorno vem do endereço público configurado, nunca do Host da requisição.
    assert query["redirect_uri"] == CALLBACK
    assert query["scope"] == "openid email profile"
    assert query["code_challenge_method"] == "S256"
    assert len(query["code_challenge"]) == 43
    assert query["hd"] == "*"
    assert len(query["state"]) >= 43
    assert len(query["nonce"]) >= 43
    assert query["state"] != query["nonce"]
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{OAUTH_COOKIE}={query['state']};")
    assert all(flag in cookie for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"))
    assert response.headers["Cache-Control"] == "no-store"


def test_the_pkce_verifier_goes_only_to_the_token_endpoint(
    api: TestClient, fake: FakeGoogle
) -> None:
    response = sign_in(api, fake)

    [form] = fake.received
    assert 43 <= len(form["code_verifier"]) <= 128
    assert form["code_verifier"] not in response.headers["location"]
    assert landing(response) == "/google/concluir"


# --- Registro pelo Google (formulário complementar) ---------------------------------------------


def test_a_new_person_fills_the_form_and_waits_for_approval(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    assert landing(sign_in(api, fake)) == "/google/concluir"

    pending = api.get("/api/v1/auth/google/pending")
    created = complete(api, name="Gabriela Lima")
    again = api.get("/api/v1/auth/google/pending")
    retry = sign_in(api, fake)

    assert pending.json() == {"email": "gabi@cin.ufpe.br", "name": "Gabi Google"}
    assert created.status_code == 201
    assert created.json() == {"status": "aguardando_aprovacao", "email": "gabi@cin.ufpe.br"}
    [account] = [a for a in store.accounts.values() if a.google_sub == "google-sub-1"]
    assert (account.name, account.status, account.password_hash, account.signup_method) == (
        "Gabriela Lima",
        Status.AGUARDANDO_APROVACAO,
        None,
        SignupMethod.GOOGLE,
    )
    assert again.status_code == 422  # o cadastro em andamento foi consumido
    # Sem aprovação, nada de sessão: o Google já confirmou quem é, então o status aparece.
    assert landing(retry) == "/entrar?google=ACCOUNT_PENDING_APPROVAL"
    assert COOKIE not in api.cookies


def test_an_approved_google_account_signs_in(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    sign_in(api, fake)
    complete(api)
    [account] = [a for a in store.accounts.values() if a.google_sub == "google-sub-1"]
    store.accounts[account.id] = replace(account, status=Status.ATIVO, role=Role.MONITOR)

    response = sign_in(api, fake)
    me = api.get("/api/v1/auth/me")

    assert landing(response) == "/"
    assert response.headers["Cache-Control"] == "no-store"
    assert me.status_code == 200
    assert (me.json()["email"], me.json()["has_password"]) == ("gabi@cin.ufpe.br", False)


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"name": "Vinícius Leôncio de Andrade Corrêa Gondim"}, 409, "NAME_TAKEN"),
        ({"name": "a@b"}, 422, "INVALID_INPUT"),
        ({"course": "X"}, 422, "INVALID_INPUT"),
        ({"treatment": "outro"}, 422, "INVALID_INPUT"),
    ],
)
def test_the_form_is_validated(
    api: TestClient, fake: FakeGoogle, body: dict[str, str], status: int, code: str
) -> None:
    sign_in(api, fake)
    response = complete(api, **body)

    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert api.get("/api/v1/auth/google/pending").status_code == 200  # dá para corrigir


def test_the_form_needs_a_google_sign_in_in_this_browser(api: TestClient) -> None:
    pending = api.get("/api/v1/auth/google/pending")
    created = complete(api)
    api.cookies.set(SIGNUP_COOKIE, "inventado")
    forged = api.post(
        "/api/v1/auth/google/complete", json={"name": "X Y", "course": "CC", "treatment": "neutro"}
    )

    for response in (pending, created, forged):
        assert (response.status_code, response.json()["error"]["code"]) == (422, "INVALID_TOKEN")


def test_the_form_refuses_another_site(api: TestClient, fake: FakeGoogle) -> None:
    sign_in(api, fake)
    response = api.post(
        "/api/v1/auth/google/complete",
        json={"name": "Gabi", "course": "CC", "treatment": "neutro"},
        headers={"Origin": "https://evil.example"},
    )

    assert (response.status_code, response.json()["error"]["code"]) == (403, "ORIGIN_MISMATCH")


# --- Mesmo e-mail, mesma conta (FR-25) ------------------------------------------------------------


def test_the_same_email_with_password_and_google_is_the_same_account(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    ana = member(store, email="ana@ufpe.br", password_hash=FAST_PASSWORDS.hash_sync(PASSWORD))

    response = sign_in(api, fake, sub="sub-ana", email="ANA@ufpe.br")

    assert landing(response) == "/"
    assert store.accounts[ana.id].google_sub == "sub-ana"
    assert api.get("/api/v1/auth/me").json()["email"] == "ana@ufpe.br"
    # A senha continua valendo.
    login = api.post("/api/v1/auth/login", json={"login": "ana@ufpe.br", "password": PASSWORD})
    assert login.status_code == 200


def test_both_developer_emails_reach_the_developer_account(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    first = sign_in(api, fake, sub="sub-dev", email=DEV_EMAIL)
    api.cookies.clear()
    second = sign_in(api, fake, sub="sub-dev", email="vinicius.leoncio@ufpe.br")

    assert landing(first) == landing(second) == "/"
    assert api.get("/api/v1/auth/me").json()["role"] == "desenvolvedor"


def test_another_google_account_cannot_take_a_linked_email(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    ana = member(store, email="ana@ufpe.br")
    store.accounts[ana.id] = replace(ana, google_sub="sub-original")

    response = sign_in(api, fake, sub="sub-impostor", email="ana@ufpe.br")

    assert landing(response) == "/entrar?google=outra_conta"
    assert store.accounts[ana.id].google_sub == "sub-original"


def test_pre_hijacking_an_unverified_email_does_not_work(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    # Quem não é dono do e-mail pede o cadastro com senha e nunca o confirma.
    squat = api.post(
        "/api/v1/auth/register",
        json={
            "name": "Impostor",
            "email": "gabi@cin.ufpe.br",
            "password": "Senha-do-impostor-1",
            "course": "CC",
            "treatment": "neutro",
        },
    )
    assert squat.status_code == 201
    [squatted] = [a for a in store.accounts.values() if a.name == "Impostor"]

    # A dona do e-mail entra pelo Google e completa o cadastro.
    assert landing(sign_in(api, fake)) == "/google/concluir"
    assert complete(api).status_code == 201

    account = store.accounts[squatted.id]
    assert (account.name, account.password_hash, account.google_sub) == (
        "Gabi Google",
        None,
        "google-sub-1",
    )
    store.accounts[account.id] = replace(account, status=Status.ATIVO, role=Role.MONITOR)
    login = api.post(
        "/api/v1/auth/login", json={"login": "gabi@cin.ufpe.br", "password": "Senha-do-impostor-1"}
    )
    assert (login.status_code, login.json()["error"]["code"]) == (401, "INVALID_CREDENTIALS")


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (Status.RECUSADO, "ACCOUNT_REJECTED"),
        (Status.EX_MONITOR, "ACCOUNT_REMOVED"),
        (Status.AGUARDANDO_APROVACAO, "ACCOUNT_PENDING_APPROVAL"),
    ],
)
def test_accounts_that_are_not_active_see_their_status(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore, status: Status, reason: str
) -> None:
    member(store, email="ana@ufpe.br", status=status, role=None)

    response = sign_in(api, fake, sub="sub-ana", email="ana@ufpe.br")

    assert landing(response) == f"/entrar?google={reason}"
    assert COOKIE not in api.cookies


def test_signing_in_with_google_replaces_a_previous_session(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    ana = member(store, email="ana@ufpe.br")
    old = open_session(store, ana)
    api.cookies.set(COOKIE, old)

    response = sign_in(api, fake, sub="sub-ana", email="ana@ufpe.br")

    assert landing(response) == "/"
    # O identificador apresentado antes do login morreu, e outro foi emitido (fixação de sessão).
    assert token_hash(old) not in store.sessions
    assert [s.account_id for s in store.sessions.values()] == [ana.id]
    api.cookies.clear()
    assert api.get("/api/v1/auth/me", headers=cookie_header(old)).status_code == 401


# --- Recusas do Google (FR-24) -------------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    ["gabi@gmail.com", "gabi@xcin.ufpe.br", "gabi@ee.ufpe.br", "gabi@cin.ufpe.br.evil.com"],
)
def test_domains_outside_are_refused_even_with_hd_tampered(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore, email: str
) -> None:
    before = dict(store.accounts)

    response = sign_in(api, fake, email=email, hd="cin.ufpe.br")

    assert landing(response) == "/entrar?google=dominio"
    assert store.accounts == before


@pytest.mark.parametrize("verified", [False, None, "true", 1])
def test_unverified_google_emails_are_refused(
    api: TestClient, fake: FakeGoogle, verified: object
) -> None:
    response = sign_in(api, fake, email_verified=verified)

    assert landing(response) == "/entrar?google=email_nao_verificado"


@pytest.mark.parametrize(
    "claims",
    [
        {"nonce": "outro-nonce"},
        {"aud": "outro-cliente.apps.googleusercontent.com"},
        {"azp": "outro-cliente.apps.googleusercontent.com"},
        {"iss": "https://evil.example"},
        {"exp": 1_000_000_000, "iat": 999_999_000},
        {"iat": None},
        {"email": None},
        {"sub": None},
    ],
)
def test_id_tokens_with_wrong_claims_are_refused(
    api: TestClient, fake: FakeGoogle, claims: dict[str, Any]
) -> None:
    assert landing(sign_in(api, fake, **claims)) == "/entrar?google=token"


def test_both_google_issuer_spellings_are_accepted(api: TestClient, fake: FakeGoogle) -> None:
    assert landing(sign_in(api, fake, iss="accounts.google.com")) == "/google/concluir"


def test_a_token_signed_by_another_key_is_refused(api: TestClient, fake: FakeGoogle) -> None:
    impostor = RSAKey.generate_key(2048, parameters={"kid": "k1"})

    assert landing(sign_in(api, fake, key=impostor)) == "/entrar?google=token"


def test_new_google_keys_are_fetched_once(api: TestClient, fake: FakeGoogle) -> None:
    assert landing(sign_in(api, fake)) == "/google/concluir"
    rotated = RSAKey.generate_key(2048, parameters={"kid": "k2"})
    fake.published = [fake.key, rotated]

    assert landing(sign_in(api, fake, key=rotated)) == "/google/concluir"


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        ({"token_status": 400}, "token"),
        ({"token_status": 503}, "indisponivel"),
        ({"network_down": True}, "indisponivel"),
        ({"jwks_down": True}, "indisponivel"),
    ],
)
def test_google_failures_send_the_person_back_with_a_reason(
    api: TestClient, fake: FakeGoogle, setup: dict[str, Any], reason: str
) -> None:
    for name, value in setup.items():
        setattr(fake, name, value)

    assert landing(sign_in(api, fake)) == f"/entrar?google={reason}"


# --- state e cookie (CSRF de login) --------------------------------------------------------------


def test_a_callback_without_the_state_of_this_browser_is_refused(
    api: TestClient, fake: FakeGoogle
) -> None:
    query = start(api)
    fake.issue("codigo", fake.claims(query["nonce"]), query["code_challenge"])
    api.cookies.clear()
    # O atacante leva a vítima ao retorno com o código e o state dele, sem o cookie dela.
    forged = api.get(
        "/api/v1/auth/google/callback", params={"code": "codigo", "state": query["state"]}
    )

    assert landing(forged) == "/entrar?google=estado"
    assert fake.received == []  # o código nem chegou a ser trocado


def test_a_state_that_differs_from_the_cookie_is_refused(api: TestClient, fake: FakeGoogle) -> None:
    query = start(api)
    other = start(api)  # o cookie agora tem o state do segundo início

    response = api.get(
        "/api/v1/auth/google/callback", params={"code": "c", "state": query["state"]}
    )

    assert landing(response) == "/entrar?google=estado"
    assert other["state"] != query["state"]


def test_a_state_is_used_only_once(api: TestClient, fake: FakeGoogle) -> None:
    query = start(api)
    fake.issue("codigo", fake.claims(query["nonce"]), query["code_challenge"])
    params = {"code": "codigo", "state": query["state"]}

    first = api.get("/api/v1/auth/google/callback", params=params)
    api.cookies.set(OAUTH_COOKIE, query["state"])
    second = api.get("/api/v1/auth/google/callback", params=params)

    assert landing(first) == "/google/concluir"
    assert landing(second) == "/entrar?google=estado"


@pytest.mark.parametrize(
    "params",
    [{"error": "access_denied"}, {"state": "s"}, {"code": "c"}],
)
def test_cancelled_or_incomplete_callbacks(api: TestClient, params: dict[str, str]) -> None:
    start(api)
    response = api.get("/api/v1/auth/google/callback", params=params)

    expected = "cancelado" if "error" in params else "estado"
    assert landing(response) == f"/entrar?google={expected}"
    assert f'{OAUTH_COOKIE}=""' in response.headers["set-cookie"]


def test_short_lived_values_expire_and_are_used_once() -> None:
    now = [0.0]
    values: Expiring[str] = Expiring(600, max_items=2, monotonic=lambda: now[0])
    first = values.put("a")
    second = values.put("b")

    assert values.peek(first) == "a"
    assert values.pop(first) == "a"
    assert values.pop(first) is None
    third = values.put("c")
    fourth = values.put("d")  # cheio: o mais antigo sai
    assert values.peek(second) is None
    assert (values.peek(third), values.peek(fourth)) == ("c", "d")
    now[0] = 601
    assert values.peek(third) is None
    assert values.peek(None) is None


@pytest.mark.parametrize("body", [b"nao e json", b'{"access_token": "sem id_token"}', b'["lista"]'])
def test_token_answers_without_an_id_token_are_refused(
    api: TestClient, fake: FakeGoogle, body: bytes
) -> None:
    original = fake.handle

    def broken(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/token":
            return httpx2.Response(200, content=body)
        return original(request)

    fake.handle = broken  # type: ignore[method-assign]
    app, _ = make_app(SETTINGS, google_transport=httpx2.MockTransport(fake.handle))
    with TestClient(app, base_url=BASE_URL, follow_redirects=False) as client:
        assert landing(sign_in(client, fake)) == "/entrar?google=token"


def test_cached_keys_keep_working_when_the_jwks_is_down(api: TestClient, fake: FakeGoogle) -> None:
    assert landing(sign_in(api, fake)) == "/google/concluir"
    fake.jwks_down = True
    unknown = RSAKey.generate_key(2048, parameters={"kid": "k9"})

    # A chave conhecida segue valendo; a desconhecida não tem como ser conferida.
    assert landing(sign_in(api, fake)) == "/google/concluir"
    assert landing(sign_in(api, fake, key=unknown)) == "/entrar?google=token"


def test_a_database_outage_sends_the_person_back(
    api: TestClient, fake: FakeGoogle, store: MemoryAccountStore
) -> None:
    sign_in(api, fake)
    store.available = False

    assert landing(sign_in(api, fake)) == "/entrar?google=indisponivel"
    response = complete(api)
    assert (response.status_code, response.json()["error"]["code"]) == (503, "DATABASE_UNAVAILABLE")

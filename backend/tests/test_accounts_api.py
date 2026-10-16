"""Registro, verificação de e-mail e perfil (Sprint 14; FR-23, FR-25, FR-26; DoD itens 18 e 20).

A API roda com repositório e e-mail em memória e um relógio controlável: cada mensagem enviada
fica no ``MemorySender``, de onde os testes tiram o link de verificação.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from urllib.parse import parse_qs, urlsplit

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
from ipc_api.accounts.models import Status, Treatment
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.auth.accounts import AccountsConfig, AccountService
from ipc_api.auth.sessions import token_hash
from ipc_api.auth.throttle import LoginThrottle
from ipc_api.mail import (
    BREVO_URL,
    BrevoSender,
    EmailConfig,
    EmailUnavailable,
    MemorySender,
    SmtpSender,
    email_sender_for,
    verification_message,
)
from ipc_api.settings import ApiSettings

STRONG = "Senha-forte-1"
NEW_MEMBER = {
    "name": "Ana Beatriz Lima",
    "email": "ana.lima@cin.ufpe.br",
    "password": STRONG,
    "course": "Ciência da Computação",
    "treatment": "feminino",
}


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


@pytest.fixture
def sender() -> MemorySender:
    return MemorySender()


def start(
    store: MemoryAccountStore,
    sender: MemorySender,
    clock: Clock | None = None,
    settings: ApiSettings | None = None,
) -> TestClient:
    app, _ = make_app(settings, store=store, clock=clock, sender=sender)
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def api(store: MemoryAccountStore, sender: MemorySender, clock: Clock) -> Iterator[TestClient]:
    with start(store, sender, clock) as client:
        yield client


def register(api: TestClient, **overrides: Any) -> httpx2.Response:
    return api.post("/api/v1/auth/register", json={**NEW_MEMBER, **overrides})


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def link_of(message: EmailMessage) -> str:
    body = message.get_body(("plain",))
    assert body is not None
    match = re.search(r"https?://\S+/verificar\?token=\S+", body.get_content())
    assert match is not None
    return match.group(0)


def token_of(message: EmailMessage) -> str:
    return parse_qs(urlsplit(link_of(message)).query)["token"][0]


def login(api: TestClient, login: str, password: str = STRONG) -> httpx2.Response:
    return api.post("/api/v1/auth/login", json={"login": login, "password": password})


# --- S14-01: registro --------------------------------------------------------------------------


def test_registration_waits_for_the_email_verification(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    response = register(api, email="  Ana.Lima@CIN.ufpe.br ")

    assert response.status_code == 201
    assert response.json() == {"status": "aguardando_verificacao", "email": "ana.lima@cin.ufpe.br"}
    (account,) = [a for a in store.accounts.values() if a.name == "Ana Beatriz Lima"]
    assert (account.status, account.role) == (Status.AGUARDANDO_VERIFICACAO, None)
    assert account.treatment is Treatment.FEMININO
    assert account.password_hash is not None
    assert STRONG not in account.password_hash
    # Com a senha certa, a mensagem do status (FR-25); nada de sessão.
    assert error_of(login(api, "ana.lima@cin.ufpe.br")) == (403, "ACCOUNT_PENDING_VERIFICATION")
    (message,) = sender.messages
    assert message["To"] == "ana.lima@cin.ufpe.br"
    assert message["Subject"] == "Confirme o seu cadastro no IP-Checker"


def test_verification_email_has_the_required_text_and_a_one_time_link(
    api: TestClient, sender: MemorySender
) -> None:
    register(api)
    (message,) = sender.messages

    html = message.get_body(("html",))
    assert html is not None
    assert "Clique aqui para verificar seu acesso." in html.get_content()
    link = link_of(message)
    assert link.startswith("http://127.0.0.1:8180/verificar?token=")
    assert len(token_of(message)) == 43  # 256 bits em base64url


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
    assert error_of(register(api, email=email)) == (422, "DOMAIN_NOT_ALLOWED")


@pytest.mark.parametrize(
    ("password", "missing"),
    [
        ("Curta-1!", "ter pelo menos 9 caracteres"),
        ("sem-maiuscula-1", "ter pelo menos 1 letra maiúscula"),
        ("SemEspecial123", "ter pelo menos 1 caractere especial"),
    ],
)
def test_weak_passwords_are_refused_by_the_backend(
    api: TestClient, store: MemoryAccountStore, password: str, missing: str
) -> None:
    response = register(api, password=password)

    assert error_of(response) == (422, "WEAK_PASSWORD")
    assert missing in response.json()["error"]["message"]
    assert len(store.accounts) == 1  # só a conta do desenvolvedor


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "A", "O nome precisa ter entre 2 e 120 caracteres."),
        ("name", "ana@lima", "O nome não pode ter @."),
        ("name", "Ana​Lima", "O texto tem caracteres de controle."),
        ("course", " ", "O curso precisa ter entre 2 e 120 caracteres."),
    ],
)
def test_name_and_course_are_validated(
    api: TestClient, field: str, value: str, message: str
) -> None:
    response = register(api, **{field: value})

    assert error_of(response) == (422, "INVALID_INPUT")
    assert response.json()["error"]["message"] == message


def test_treatment_is_required_and_closed(api: TestClient) -> None:
    body = {key: value for key, value in NEW_MEMBER.items() if key != "treatment"}

    assert error_of(api.post("/api/v1/auth/register", json=body)) == (422, "INVALID_INPUT")
    assert error_of(register(api, treatment="outro")) == (422, "INVALID_INPUT")


def test_names_are_unique_ignoring_case_and_spaces(api: TestClient) -> None:
    assert register(api).status_code == 201

    response = register(api, name="  ana   BEATRIZ lima ", email="outra@ufpe.br")

    assert error_of(response) == (409, "NAME_TAKEN")


def test_developer_emails_are_reserved(api: TestClient) -> None:
    for email in (DEV_EMAIL, "Vinicius.Leoncio@ufpe.br"):
        assert error_of(register(api, email=email)) == (409, "EMAIL_TAKEN")


def test_email_of_a_verified_account_is_taken(api: TestClient, store: MemoryAccountStore) -> None:
    member(store, email="ativa@cin.ufpe.br")

    assert error_of(register(api, email="ativa@cin.ufpe.br")) == (409, "EMAIL_TAKEN")


def test_an_unverified_email_can_be_registered_again_and_the_old_link_dies(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    # Alguém registra o e-mail de outra pessoa sem conseguir abrir a caixa dela (ameaça 16).
    register(api, name="Impostor", password="Senha-do-impostor-1")
    first = token_of(sender.messages[0])

    response = register(api)  # a dona do e-mail se registra de verdade

    assert response.status_code == 201
    (account,) = [a for a in store.accounts.values() if "ana.lima@cin.ufpe.br" in a.emails]
    assert account.name == "Ana Beatriz Lima"
    assert error_of(api.post("/api/v1/auth/verify", json={"token": first})) == (
        422,
        "INVALID_TOKEN",
    )
    second = token_of(sender.messages[1])
    assert api.post("/api/v1/auth/verify", json={"token": second}).status_code == 200


def test_email_outage_keeps_the_registration_and_the_link_can_be_resent(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    sender.available = False

    response = register(api)

    assert error_of(response) == (503, "EMAIL_UNAVAILABLE")
    assert response.headers["Retry-After"] == "60"
    assert any(a.status is Status.AGUARDANDO_VERIFICACAO for a in store.accounts.values())
    sender.available = True
    assert (
        api.post("/api/v1/auth/verify/resend", json={"email": NEW_MEMBER["email"]}).status_code
        == 202
    )
    assert len(sender.messages) == 1


def test_link_comes_from_the_public_address_never_from_the_host_header(
    store: MemoryAccountStore, sender: MemorySender
) -> None:
    settings = ApiSettings(accounts=AccountsConfig(public_base_url="https://ip-checker.example/"))
    with start(store, sender, settings=settings) as client:
        client.post("/api/v1/auth/register", json=NEW_MEMBER, headers={"Host": "evil.example"})

    assert link_of(sender.messages[0]).startswith("https://ip-checker.example/verificar?token=")


# --- S14-02: verificação -----------------------------------------------------------------------


def test_verified_registration_goes_to_the_approval_queue(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    register(api)

    response = api.post("/api/v1/auth/verify", json={"token": token_of(sender.messages[0])})

    assert response.status_code == 200
    assert response.json() == {"status": "aguardando_aprovacao"}
    assert error_of(login(api, "Ana Beatriz Lima")) == (403, "ACCOUNT_PENDING_APPROVAL")


def test_a_used_link_does_not_work_again(api: TestClient, sender: MemorySender) -> None:
    register(api)
    token = token_of(sender.messages[0])
    api.post("/api/v1/auth/verify", json={"token": token})

    assert error_of(api.post("/api/v1/auth/verify", json={"token": token})) == (
        422,
        "INVALID_TOKEN",
    )


def test_an_expired_link_does_not_work(api: TestClient, sender: MemorySender, clock: Clock) -> None:
    register(api)
    clock.now += timedelta(hours=24)

    response = api.post("/api/v1/auth/verify", json={"token": token_of(sender.messages[0])})

    assert error_of(response) == (422, "INVALID_TOKEN")
    assert response.json()["error"]["message"] == (
        "O link de verificação é inválido, já foi usado ou venceu. Peça um novo."
    )


def test_opening_the_link_with_get_does_not_spend_the_token(
    api: TestClient, sender: MemorySender
) -> None:
    # O antivírus do e-mail abre o link; só o POST da página confirma (ameaça 21).
    register(api)
    token = token_of(sender.messages[0])

    assert api.get(f"/api/v1/auth/verify?token={token}").status_code == 405
    assert api.post("/api/v1/auth/verify", json={"token": token}).status_code == 200


@pytest.mark.parametrize("token", ["", "curto", "x" * 44, "a" * 42 + "!"])
def test_malformed_tokens_are_invalid_input(api: TestClient, token: str) -> None:
    assert error_of(api.post("/api/v1/auth/verify", json={"token": token})) == (
        422,
        "INVALID_INPUT",
    )


def test_unknown_token_is_invalid(api: TestClient) -> None:
    assert error_of(api.post("/api/v1/auth/verify", json={"token": "a" * 43})) == (
        422,
        "INVALID_TOKEN",
    )


def test_token_is_stored_only_as_a_hash(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    register(api)
    token = token_of(sender.messages[0])

    assert token_hash(token) in store.email_tokens
    assert token.encode() not in b"".join(store.email_tokens)


# --- Reenvio -----------------------------------------------------------------------------------


def test_resend_answers_the_same_whether_the_account_exists_or_not(
    api: TestClient, sender: MemorySender
) -> None:
    for email in ("ninguem@cin.ufpe.br", DEV_EMAIL):
        response = api.post("/api/v1/auth/verify/resend", json={"email": email})
        assert response.status_code == 202
        assert response.content == b""
    assert sender.messages == []
    assert error_of(api.post("/api/v1/auth/verify/resend", json={"email": "x@gmail.com"})) == (
        422,
        "DOMAIN_NOT_ALLOWED",
    )


@pytest.mark.anyio
async def test_resend_is_limited_per_account() -> None:
    store, sender, now = MemoryAccountStore(), MemorySender(), [0.0]
    service = AccountService(
        store,
        FAST_PASSWORDS,
        sender,
        EmailConfig(),
        AccountsConfig(),
        reserved_emails=(),
        throttle=LoginThrottle(),
        clock=lambda: datetime(2026, 10, 2, tzinfo=UTC),
        monotonic=lambda: now[0],
    )
    await service.register(
        name="Ana",
        email="ana@cin.ufpe.br",
        password=STRONG,
        course="CC",
        treatment=Treatment.NEUTRO,
    )

    await service.resend("ana@cin.ufpe.br")
    await service.resend("ana@cin.ufpe.br")  # menos de 1 minuto depois: nada
    assert len(sender.messages) == 2
    for _ in range(10):
        now[0] += 61
        await service.resend("ana@cin.ufpe.br")
    assert len(sender.messages) == 1 + 5  # no máximo 5 reenvios por dia
    now[0] += 24 * 3600
    await service.resend("ana@cin.ufpe.br")
    assert len(sender.messages) == 7


# --- S14-03: perfil ----------------------------------------------------------------------------


@pytest.fixture
def ana(store: MemoryAccountStore) -> dict[str, str]:
    account = member(store, name="Ana Souza", password_hash=FAST_PASSWORDS.hash_sync(STRONG))
    return {**cookie_header(open_session(store, account)), "id": str(account.id)}


def _cookie(session: dict[str, str]) -> dict[str, str]:
    return {"Cookie": session["Cookie"]}


def test_profile_edits_name_course_and_treatment(api: TestClient, ana: dict[str, str]) -> None:
    response = api.patch(
        "/api/v1/profile",
        json={
            "name": "  Ana   Souza Lima ",
            "course": "Engenharia da Computação",
            "treatment": "neutro",
        },
        headers=_cookie(ana),
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["course"], body["treatment"]) == (
        "Ana Souza Lima",
        "Engenharia da Computação",
        "neutro",
    )
    assert api.get("/api/v1/auth/me", headers=_cookie(ana)).json() == body


def test_profile_keeps_what_is_not_sent(api: TestClient, ana: dict[str, str]) -> None:
    body = api.patch(
        "/api/v1/profile", json={"course": "Sistemas de Informação"}, headers=_cookie(ana)
    ).json()

    assert (body["name"], body["treatment"]) == ("Ana Souza", "feminino")


def test_profile_cannot_take_another_name_nor_change_the_role(
    api: TestClient, ana: dict[str, str]
) -> None:
    taken = api.patch("/api/v1/profile", json={"name": DEV_NAME.lower()}, headers=_cookie(ana))
    role = api.patch("/api/v1/profile", json={"role": "professor"}, headers=_cookie(ana))

    assert error_of(taken) == (409, "NAME_TAKEN")
    assert error_of(role) == (422, "INVALID_INPUT")
    assert api.get("/api/v1/auth/me", headers=_cookie(ana)).json()["role"] == "monitor"


def test_profile_requires_a_session(api: TestClient) -> None:
    assert error_of(api.patch("/api/v1/profile", json={"course": "X"})) == (401, "UNAUTHENTICATED")
    assert error_of(api.post("/api/v1/profile/password", json={"new_password": STRONG})) == (
        401,
        "UNAUTHENTICATED",
    )


# --- Troca de senha (pedido do autor em 02/10/2026) --------------------------------------------


def test_changing_the_password_keeps_this_session_and_ends_the_others(
    api: TestClient, store: MemoryAccountStore, ana: dict[str, str]
) -> None:
    account = store.accounts[next(a.id for a in store.accounts.values() if a.name == "Ana Souza")]
    other = open_session(store, account)

    response = api.post(
        "/api/v1/profile/password",
        json={"current_password": STRONG, "new_password": "Nova-senha-2"},
        headers=_cookie(ana),
    )

    assert response.status_code == 204
    assert api.get("/api/v1/auth/me", headers=_cookie(ana)).status_code == 200
    assert api.get("/api/v1/auth/me", headers=cookie_header(other)).status_code == 401
    assert login(api, "Ana Souza", STRONG).status_code == 401
    assert login(api, "Ana Souza", "Nova-senha-2").status_code == 200


def test_wrong_current_password_is_refused_and_eventually_blocked(
    api: TestClient, ana: dict[str, str]
) -> None:
    def attempt(current: str) -> httpx2.Response:
        return api.post(
            "/api/v1/profile/password",
            json={"current_password": current, "new_password": "Nova-senha-2"},
            headers=_cookie(ana),
        )

    for _ in range(5):
        response = attempt("Senha-errada-1")
        assert error_of(response) == (403, "INVALID_CREDENTIALS")
        assert response.json()["error"]["message"] == "A senha atual está incorreta."
    assert error_of(attempt(STRONG)) == (429, "RATE_LIMITED")


def test_new_password_must_follow_the_policy(api: TestClient, ana: dict[str, str]) -> None:
    response = api.post(
        "/api/v1/profile/password",
        json={"current_password": STRONG, "new_password": "fraca"},
        headers=_cookie(ana),
    )

    assert error_of(response) == (422, "WEAK_PASSWORD")


def test_current_password_is_required_when_the_account_has_one(
    api: TestClient, ana: dict[str, str]
) -> None:
    response = api.post(
        "/api/v1/profile/password", json={"new_password": "Nova-senha-2"}, headers=_cookie(ana)
    )

    assert error_of(response) == (403, "INVALID_CREDENTIALS")


def test_an_account_without_password_can_define_one(
    api: TestClient, store: MemoryAccountStore
) -> None:
    google_only = member(store, name="Só Google", password_hash=None)
    session = cookie_header(open_session(store, google_only))

    response = api.post(
        "/api/v1/profile/password", json={"new_password": "Nova-senha-2"}, headers=session
    )

    assert response.status_code == 204
    assert login(api, "Só Google", "Nova-senha-2").status_code == 200


def test_developer_seed_uses_the_author_data(api: TestClient) -> None:
    response = login(api, DEV_EMAIL, PASSWORD)

    assert response.json() == {
        "name": "Vinícius Leôncio de Andrade Corrêa Gondim",
        "email": DEV_EMAIL,
        "course": "Ciência da Computação",
        "treatment": "masculino",
        "role": "desenvolvedor",
        "role_label": "Monitor e desenvolvedor",
        "has_password": True,
        "can_manage": True,
        "can_view_log": True,
        "ai_indicators": False,
    }


# --- E-mail ------------------------------------------------------------------------------------


def test_email_settings_from_environment() -> None:
    settings = ApiSettings.from_env(
        {
            "IPC_SMTP_HOST": "smtp.exemplo.br",
            "IPC_SMTP_PORT": "465",
            "IPC_SMTP_SECURITY": "ssl",
            "IPC_SMTP_USERNAME": "ip-checker",
            "IPC_SMTP_PASSWORD": "segredo-smtp",
            "IPC_EMAIL_FROM": "IP-Checker <ip-checker@cin.ufpe.br>",
            "IPC_PUBLIC_BASE_URL": "https://ip-checker.example",
        }
    )

    assert settings.email == EmailConfig(
        host="smtp.exemplo.br",
        port=465,
        security="ssl",
        username="ip-checker",
        password="segredo-smtp",
        sender="IP-Checker <ip-checker@cin.ufpe.br>",
    )
    assert settings.accounts.public_base_url == "https://ip-checker.example"
    assert "segredo-smtp" not in repr(settings)


def test_invalid_smtp_security_prevents_startup() -> None:
    with pytest.raises(ValueError, match="IPC_SMTP_SECURITY"):
        ApiSettings.from_env({"IPC_SMTP_SECURITY": "talvez"})


@pytest.mark.anyio
async def test_smtp_without_host_is_unavailable() -> None:
    with pytest.raises(EmailUnavailable):
        await SmtpSender(EmailConfig()).send(
            verification_message("a@b", "c@cin.ufpe.br", "C", "http://x/verificar?token=t")
        )


@pytest.mark.anyio
async def test_smtp_connection_failure_is_unavailable() -> None:
    config = EmailConfig(host="127.0.0.1", port=9, security="none", timeout_s=2)
    with pytest.raises(EmailUnavailable):
        await SmtpSender(config).send(
            verification_message("a@b", "c@cin.ufpe.br", "C", "http://x/verificar?token=t")
        )


def test_message_escapes_the_name_in_html() -> None:
    message = verification_message("a@b", "c@cin.ufpe.br", "<b>Ana</b>", "http://x/v?token=t&a=1")

    html = message.get_body(("html",))
    assert html is not None
    content = html.get_content()
    assert "<b>Ana</b>" not in content
    assert "&lt;b&gt;Ana&lt;/b&gt;" in content
    assert 'href="http://x/v?token=t&amp;a=1"' in content


def test_store_entries_are_unchanged_by_failed_registrations(
    api: TestClient, store: MemoryAccountStore
) -> None:
    before = dict(store.accounts)
    register(api, password="fraca")
    register(api, email="x@gmail.com")

    assert store.accounts == before
    assert replace(next(iter(before.values()))) == next(iter(store.accounts.values()))


# --- Transporte HTTPS (Brevo) -------------------------------------------------------------------

BREVO_KEY = "chave-brevo-de-teste"


def link_message() -> EmailMessage:
    return verification_message(
        "IP-Checker <ip-checker@cin.ufpe.br>",
        "ana@cin.ufpe.br",
        "Ana",
        "https://ip-checker.example/verificar?token=abc",
    )


def test_brevo_transport_from_environment() -> None:
    settings = ApiSettings.from_env(
        {"IPC_EMAIL_TRANSPORT": "brevo", "IPC_EMAIL_API_KEY": BREVO_KEY}
    )

    assert settings.email.transport == "brevo"
    assert settings.email.api_key == BREVO_KEY
    assert BREVO_KEY not in repr(settings)
    assert isinstance(email_sender_for(settings.email), BrevoSender)
    assert isinstance(email_sender_for(EmailConfig()), SmtpSender)


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"IPC_EMAIL_TRANSPORT": "pombo"}, "IPC_EMAIL_TRANSPORT"),
        ({"IPC_EMAIL_TRANSPORT": "brevo"}, "IPC_EMAIL_API_KEY"),
        ({"IPC_EMAIL_TRANSPORT": "brevo", "IPC_EMAIL_API_KEY": ""}, "IPC_EMAIL_API_KEY"),
    ],
)
def test_invalid_email_transport_prevents_startup(env: dict[str, str], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ApiSettings.from_env(env)


@pytest.mark.anyio
async def test_brevo_posts_the_same_message_over_https() -> None:
    requests: list[httpx2.Request] = []

    def brevo(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(201, json={"messageId": "<1@brevo>"})

    config = EmailConfig(transport="brevo", api_key=BREVO_KEY)
    await BrevoSender(config, httpx2.MockTransport(brevo)).send(link_message())

    [request] = requests
    assert str(request.url) == BREVO_URL
    assert request.method == "POST"
    assert request.headers["api-key"] == BREVO_KEY
    body = json.loads(request.content)
    assert body["sender"] == {"name": "IP-Checker", "email": "ip-checker@cin.ufpe.br"}
    assert body["to"] == [{"email": "ana@cin.ufpe.br"}]
    assert body["subject"] == "Confirme o seu cadastro no IP-Checker"
    assert "https://ip-checker.example/verificar?token=abc" in body["textContent"]
    assert "Clique aqui para verificar seu acesso." in body["htmlContent"]


@pytest.mark.anyio
@pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
async def test_brevo_refusal_is_unavailable_without_the_response_body(status: int) -> None:
    def brevo(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json={"message": "ana@cin.ufpe.br recusado"})

    sender = BrevoSender(
        EmailConfig(transport="brevo", api_key=BREVO_KEY), httpx2.MockTransport(brevo)
    )
    with pytest.raises(EmailUnavailable) as caught:
        await sender.send(link_message())

    assert str(caught.value) == f"HTTP {status}"


@pytest.mark.anyio
@pytest.mark.parametrize("error", [httpx2.ConnectError, httpx2.ReadTimeout])
async def test_brevo_network_failure_is_unavailable(error: type[httpx2.RequestError]) -> None:
    def brevo(request: httpx2.Request) -> httpx2.Response:
        raise error("falha simulada", request=request)

    sender = BrevoSender(
        EmailConfig(transport="brevo", api_key=BREVO_KEY), httpx2.MockTransport(brevo)
    )
    with pytest.raises(EmailUnavailable):
        await sender.send(link_message())


@pytest.mark.anyio
async def test_brevo_without_key_is_unavailable() -> None:
    with pytest.raises(EmailUnavailable):
        await BrevoSender(EmailConfig(transport="brevo")).send(link_message())


# --- Tratamento só para o titular (S14-03) ------------------------------------------------------


def _refs(schema: Any, components: dict[str, Any], seen: set[str]) -> set[str]:
    """Os nomes de todos os schemas alcançáveis a partir de ``schema``."""
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str):
            name = ref.rsplit("/", 1)[-1]
            if name not in seen:
                seen.add(name)
                _refs(components[name], components, seen)
        for value in schema.values():
            _refs(value, components, seen)
    elif isinstance(schema, list):
        for value in schema:
            _refs(value, components, seen)
    return seen


def test_treatment_only_appears_in_answers_about_the_account_itself(api: TestClient) -> None:
    spec = api.app.openapi()  # type: ignore[attr-defined]
    components = spec["components"]["schemas"]
    with_treatment = {
        name for name, schema in components.items() if "treatment" in schema.get("properties", {})
    }
    answers_with_treatment = {
        (path, method)
        for path, operations in spec["paths"].items()
        for method, operation in operations.items()
        if _refs(operation.get("responses", {}), components, set()) & with_treatment
    }

    # Só as respostas sobre a própria conta. Listas de contas (S15) não trazem o tratamento.
    assert answers_with_treatment == {
        ("/api/v1/auth/me", "get"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/profile", "patch"),
    }

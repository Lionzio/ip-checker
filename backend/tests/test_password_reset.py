"""Esqueci minha senha (S24-04, Q-19 b): link por e-mail, uso único, 1 hora, sessões encerradas.

A API roda com repositório e e-mail em memória e um relógio controlável, como em
``test_accounts_api.py``; os links saem do ``MemorySender``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import BASE_URL, FAST_PASSWORDS, cookie_header, make_app, member, open_session
from ipc_api.accounts.models import Account, Status
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.mail import MemorySender

OLD = "Senha-antiga-1"
NEW = "Senha-nova-2!"
EMAIL = "bia.souza@cin.ufpe.br"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)

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


@pytest.fixture
def api(store: MemoryAccountStore, sender: MemorySender, clock: Clock) -> Iterator[TestClient]:
    app, _ = make_app(store=store, clock=clock, sender=sender)
    with TestClient(app, base_url=BASE_URL) as client:
        yield client


@pytest.fixture
async def bia(store: MemoryAccountStore) -> Account:
    return member(
        store,
        name="Bia Souza",
        email=EMAIL,
        password_hash=await FAST_PASSWORDS.hash(OLD),
    )


def forgot(api: TestClient, email: str = EMAIL) -> httpx2.Response:
    return api.post("/api/v1/auth/password/forgot", json={"email": email})


def reset(api: TestClient, token: str, password: str = NEW) -> httpx2.Response:
    return api.post("/api/v1/auth/password/reset", json={"token": token, "new_password": password})


def login(api: TestClient, password: str) -> httpx2.Response:
    return api.post("/api/v1/auth/login", json={"login": EMAIL, "password": password})


def link_of(message: EmailMessage) -> str:
    body = message.get_body(("plain",))
    assert body is not None
    match = re.search(r"https?://\S+/redefinir-senha\?token=\S+", body.get_content())
    assert match is not None
    return match.group(0)


def token_of(message: EmailMessage) -> str:
    return parse_qs(urlsplit(link_of(message)).query)["token"][0]


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


pytestmark = pytest.mark.anyio


async def test_the_link_sets_a_new_password_and_ends_every_session(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender, bia: Account
) -> None:
    session = cookie_header(open_session(store, bia))

    assert forgot(api).status_code == 202
    (message,) = sender.messages
    assert message["To"] == EMAIL
    assert message["Subject"] == "Redefina a sua senha do IP-Checker"
    body = message.get_body(("plain",))
    assert body is not None
    assert "vale por 1 hora e só uma vez" in body.get_content()

    assert reset(api, token_of(message)).status_code == 204
    # A sessão que existia caiu; a senha antiga não entra mais, e a nova entra.
    assert api.get("/api/v1/auth/me", headers=session).status_code == 401
    assert login(api, OLD).status_code == 401
    assert login(api, NEW).status_code == 200


@pytest.mark.parametrize(
    "email",
    ["ninguem@cin.ufpe.br", "pendente@cin.ufpe.br", "recusada@cin.ufpe.br"],
    ids=["sem-conta", "e-mail-nao-confirmado", "recusada"],
)
async def test_the_answer_never_reveals_who_has_an_account(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender, email: str
) -> None:
    member(store, email="pendente@cin.ufpe.br", role=None, status=Status.AGUARDANDO_VERIFICACAO)
    member(store, email="recusada@cin.ufpe.br", role=None, status=Status.RECUSADO)

    response = forgot(api, email)

    assert response.status_code == 202
    assert response.headers["cache-control"] == "no-store"
    assert sender.messages == []


async def test_removed_and_waiting_accounts_also_get_the_link(
    api: TestClient, store: MemoryAccountStore, sender: MemorySender
) -> None:
    member(store, email="ex@cin.ufpe.br", status=Status.EX_MONITOR)
    member(store, email="fila@cin.ufpe.br", role=None, status=Status.AGUARDANDO_APROVACAO)

    forgot(api, "ex@cin.ufpe.br")
    forgot(api, "fila@cin.ufpe.br")

    assert [message["To"] for message in sender.messages] == ["ex@cin.ufpe.br", "fila@cin.ufpe.br"]


async def test_other_domains_are_refused(api: TestClient) -> None:
    assert error_of(forgot(api, "bia@gmail.com")) == (422, "DOMAIN_NOT_ALLOWED")


async def test_the_link_works_once(api: TestClient, sender: MemorySender, bia: Account) -> None:
    forgot(api)
    token = token_of(sender.messages[0])

    assert reset(api, token).status_code == 204
    assert error_of(reset(api, token, "Outra-senha-3!")) == (422, "INVALID_TOKEN")


async def test_the_link_expires_after_one_hour(
    api: TestClient, sender: MemorySender, clock: Clock, bia: Account
) -> None:
    forgot(api)
    clock.now += timedelta(hours=1, seconds=1)

    assert error_of(reset(api, token_of(sender.messages[0]))) == (422, "INVALID_TOKEN")


async def test_a_weak_password_does_not_spend_the_link(
    api: TestClient, sender: MemorySender, bia: Account
) -> None:
    forgot(api)
    token = token_of(sender.messages[0])

    assert error_of(reset(api, token, "fraca")) == (422, "WEAK_PASSWORD")
    assert reset(api, token).status_code == 204


async def test_requests_respect_the_resend_limit(
    api: TestClient, sender: MemorySender, bia: Account
) -> None:
    forgot(api)
    forgot(api)  # menos de 1 minuto depois: nenhum e-mail novo, e a resposta é a mesma

    assert len(sender.messages) == 1


async def test_verification_and_reset_links_are_not_interchangeable(
    api: TestClient, sender: MemorySender, bia: Account
) -> None:
    forgot(api)
    token = token_of(sender.messages[0])

    assert error_of(api.post("/api/v1/auth/verify", json={"token": token})) == (
        422,
        "INVALID_TOKEN",
    )
    assert reset(api, token).status_code == 204


async def test_an_email_outage_keeps_the_same_answer(
    api: TestClient, sender: MemorySender, bia: Account
) -> None:
    sender.available = False

    assert forgot(api).status_code == 202


async def test_the_link_comes_from_the_public_address(
    api: TestClient, sender: MemorySender, bia: Account
) -> None:
    api.post(
        "/api/v1/auth/password/forgot", json={"email": EMAIL}, headers={"Host": "evil.example"}
    )

    assert link_of(sender.messages[0]).startswith("http://127.0.0.1:8180/redefinir-senha?token=")

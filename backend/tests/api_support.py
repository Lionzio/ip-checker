"""Contas e sessões nos testes da API (Sprint 13).

A API não sobe sem um repositório de contas: os testes usam o ``MemoryAccountStore``, que passa
pelos mesmos testes de contrato que o PostgreSQL (``test_account_store.py``), e um Argon2 barato.
Toda rota da equipe exige sessão, então os clientes de teste já nascem com o cookie de um membro.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ipc_api.accounts.models import Account, Role, SignupMethod, Status, Treatment
from ipc_api.accounts.passwords import Passwords
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.app import create_app
from ipc_api.auth.sessions import SECURE_COOKIE, new_token, token_hash
from ipc_api.settings import ApiSettings

#: Senha inicial da conta do desenvolvedor nos testes.
PASSWORD = "Senha-de-teste-1"
DEV_EMAIL = "vlacg@cin.ufpe.br"
DEV_NAME = "Vinícius Leôncio"
COOKIE = SECURE_COOKIE
#: HTTPS: o cookie é Secure, e o cliente de teste só o devolve numa conexão segura.
BASE_URL = "https://testserver"
#: Argon2 barato: a política de senha e o Argon2 de produção têm os próprios testes.
FAST_PASSWORDS = Passwords(memory_kib=1024, iterations=1)


def with_developer(settings: ApiSettings) -> ApiSettings:
    if settings.developer.initial_password is not None:
        return settings
    return replace(settings, developer=replace(settings.developer, initial_password=PASSWORD))


def make_app(
    settings: ApiSettings | None = None,
    *,
    analyzer_transport: httpx2.AsyncBaseTransport | None = None,
    store: MemoryAccountStore | None = None,
    clock: Callable[[], datetime] | None = None,
) -> tuple[FastAPI, MemoryAccountStore]:
    store = store if store is not None else MemoryAccountStore()
    app = create_app(
        with_developer(settings or ApiSettings()),
        analyzer_transport=analyzer_transport,
        account_store=store,
        passwords=FAST_PASSWORDS,
        **({"clock": clock} if clock is not None else {}),
    )
    return app, store


def member(
    store: MemoryAccountStore,
    *,
    name: str | None = None,
    email: str | None = None,
    role: Role | None = Role.MONITOR,
    status: Status = Status.ATIVO,
    password_hash: str | None = None,
    treatment: Treatment = Treatment.FEMININO,
) -> Account:
    """Uma conta pronta no repositório (por padrão, uma monitora ativa)."""
    suffix = uuid.uuid4().hex[:10]
    return store.add(
        Account(
            id=uuid.uuid4(),
            name=name or f"Membro {suffix}",
            course="Ciência da Computação",
            treatment=treatment,
            role=role,
            status=status,
            ja_foi_monitor_chefe=False,
            password_hash=password_hash,
            signup_method=SignupMethod.SENHA,
            emails=(email or f"m{suffix}@cin.ufpe.br",),
            created_at=datetime.now(UTC),
        )
    )


def open_session(store: MemoryAccountStore, account: Account, now: datetime | None = None) -> str:
    """Abre uma sessão direto no repositório e devolve o identificador do cookie."""
    token = new_token()
    start = now or datetime.now(UTC)
    store.add_session(token_hash(token), account.id, start, start + timedelta(days=7))
    return token


def cookie_header(token: str) -> dict[str, str]:
    return {"Cookie": f"{COOKIE}={token}"}


def authed_client(
    app: FastAPI, store: MemoryAccountStore, account: Account | None = None
) -> TestClient:
    """Cliente com o cookie da sessão de um membro (ou da conta indicada)."""
    client = TestClient(app, base_url=BASE_URL)
    client.cookies.set(COOKIE, open_session(store, account or member(store)))
    return client

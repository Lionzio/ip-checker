"""Contrato do repositório de contas (S13-01): a versão em memória e a do PostgreSQL.

Cada teste roda nos dois repositórios. A versão em memória serve aos testes da API; este arquivo
garante que ela se comporta como o banco. O PostgreSQL só entra com ``IPC_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from db_support import DATABASE_URL, fresh_schema
from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    DeveloperSeed,
    NewAccount,
    Role,
    SignupMethod,
    Status,
    StoreUnavailable,
    Treatment,
)
from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.accounts.store import VERIFICATION, AccountStore, MemoryAccountStore

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
DEV = DeveloperSeed(
    name="Vinícius Leôncio",
    course="Não informado",
    emails=("vlacg@cin.ufpe.br", "vinicius.leoncio@ufpe.br"),
    password_hash="$argon2id$hash-de-teste",
)

pytestmark = pytest.mark.anyio


@pytest.fixture(
    params=[
        "memoria",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not DATABASE_URL, reason="sem IPC_TEST_DATABASE_URL"),
        ),
    ]
)
async def store(request: pytest.FixtureRequest) -> AsyncIterator[AccountStore]:
    if request.param == "memoria":
        yield MemoryAccountStore()
        return
    await fresh_schema()
    postgres = await PostgresAccountStore.connect(DATABASE_URL)
    try:
        yield postgres
    finally:
        await postgres.close()


async def insert(
    store: AccountStore, name: str, email: str, status: Status = Status.ATIVO
) -> Account:
    """Insere uma conta comum. O registro chega na Sprint 14; até lá, só os testes inserem."""
    if isinstance(store, MemoryAccountStore):
        return store.add(
            Account(
                id=uuid.uuid4(),
                name=name,
                course="Ciência da Computação",
                treatment=Treatment.NEUTRO,
                role=Role.MONITOR if status is Status.ATIVO else None,
                status=status,
                ja_foi_monitor_chefe=False,
                password_hash=None,
                signup_method=SignupMethod.SENHA,
                emails=(email,),
                created_at=NOW,
            )
        )
    assert isinstance(store, PostgresAccountStore)
    pool: Any = store._pool
    role = "monitor" if status is Status.ATIVO else None
    account_id = await pool.fetchval(
        "INSERT INTO app.account (name, course, treatment, role, status, signup_method) "
        "VALUES ($1, 'Ciência da Computação', 'neutro', $2, $3, 'senha') RETURNING id",
        name,
        role,
        status.value,
    )
    await pool.execute(
        "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)", email, account_id
    )
    account = await store.get_account(account_id)
    assert account is not None
    return account


# --- Conta do desenvolvedor (P-14) -------------------------------------------------------------


async def test_developer_is_created_active_with_both_emails(store: AccountStore) -> None:
    account = await store.ensure_developer(DEV, NOW)

    assert account.name == "Vinícius Leôncio"
    assert (account.role, account.status) == (Role.DESENVOLVEDOR, Status.ATIVO)
    assert account.treatment is Treatment.MASCULINO
    assert account.signup_method is SignupMethod.SEED
    assert account.emails == DEV.emails  # o principal primeiro
    assert account.primary_email == "vlacg@cin.ufpe.br"
    assert account.password_hash == DEV.password_hash


async def test_seed_is_idempotent_and_never_touches_the_password(store: AccountStore) -> None:
    first = await store.ensure_developer(DEV, NOW)

    again = await store.ensure_developer(replace(DEV, password_hash="$argon2id$outra"), NOW)

    assert again.id == first.id
    assert again.password_hash == DEV.password_hash
    assert again.emails == DEV.emails


async def test_seed_links_a_new_developer_email_to_the_same_account(store: AccountStore) -> None:
    first = await store.ensure_developer(replace(DEV, emails=DEV.emails[:1]), NOW)

    second = await store.ensure_developer(DEV, NOW)

    assert second.id == first.id
    assert second.emails == DEV.emails


async def test_developer_emails_in_two_accounts_are_a_conflict(store: AccountStore) -> None:
    await store.ensure_developer(replace(DEV, emails=DEV.emails[:1]), NOW)
    await insert(store, "Outra Pessoa", DEV.emails[1])

    with pytest.raises(AccountConflict):
        await store.ensure_developer(DEV, NOW)


async def test_developer_name_taken_by_someone_else_is_a_conflict(store: AccountStore) -> None:
    await insert(store, "VINÍCIUS LEÔNCIO", "outra@cin.ufpe.br")

    with pytest.raises(AccountConflict):
        await store.ensure_developer(DEV, NOW)


# --- Busca para o login (FR-25) ----------------------------------------------------------------


async def test_login_finds_the_account_by_email_or_name_ignoring_case(store: AccountStore) -> None:
    account = await store.ensure_developer(DEV, NOW)

    for login in (
        "vlacg@cin.ufpe.br",
        "  VLACG@CIN.UFPE.BR ",
        "Vinicius.Leoncio@UFPE.br",
        "vinícius leôncio",
        "VINÍCIUS LEÔNCIO",
    ):
        found = await store.find_by_login(login)
        assert found is not None, login
        assert found.id == account.id, login


async def test_unknown_logins_find_nothing(store: AccountStore) -> None:
    await store.ensure_developer(DEV, NOW)

    for login in ("ninguem@cin.ufpe.br", "Ninguém", "vlacg@ufpe.br", "vlacg"):
        assert await store.find_by_login(login) is None, login


async def test_accounts_keep_their_status(store: AccountStore) -> None:
    waiting = await insert(store, "Aguardando", "espera@ufpe.br", Status.AGUARDANDO_APROVACAO)

    found = await store.get_account(waiting.id)

    assert found is not None
    assert (found.status, found.role) == (Status.AGUARDANDO_APROVACAO, None)
    assert await store.get_account(uuid.uuid4()) is None


# --- Sessões (NFR-22) --------------------------------------------------------------------------


async def test_session_lifecycle(store: AccountStore) -> None:
    account = await store.ensure_developer(DEV, NOW)
    token_hash = bytes(range(32))

    await store.create_session(token_hash, account.id, NOW, NOW + timedelta(days=7))
    session = await store.get_session(token_hash)
    assert session is not None
    assert session.account.id == account.id
    assert (session.created_at, session.last_seen_at) == (NOW, NOW)
    assert session.expires_at == NOW + timedelta(days=7)

    later = NOW + timedelta(minutes=10)
    await store.touch_session(token_hash, later)
    touched = await store.get_session(token_hash)
    assert touched is not None
    assert touched.last_seen_at == later

    await store.delete_session(token_hash)
    assert await store.get_session(token_hash) is None
    await store.delete_session(token_hash)  # apagar de novo não falha


async def test_unknown_session_is_none(store: AccountStore) -> None:
    assert await store.get_session(b"\x00" * 32) is None
    await store.touch_session(b"\x00" * 32, NOW)  # tocar uma sessão inexistente não falha


async def test_store_answers_ping(store: AccountStore) -> None:
    await store.ping()


# --- Banco fora do ar --------------------------------------------------------------------------


async def test_memory_store_can_simulate_an_outage() -> None:
    store = MemoryAccountStore()
    store.available = False

    with pytest.raises(StoreUnavailable):
        await store.ping()
    with pytest.raises(StoreUnavailable):
        await store.find_by_login("x@cin.ufpe.br")


async def test_unreachable_postgres_is_unavailable() -> None:
    with pytest.raises(StoreUnavailable):
        await PostgresAccountStore.connect("postgresql://ninguem:x@127.0.0.1:9/nada")


# --- Registro, verificação e perfil (Sprint 14) ------------------------------------------------

NEW = NewAccount(
    name="Ana Lima",
    email="ana@cin.ufpe.br",
    course="Ciência da Computação",
    treatment=Treatment.FEMININO,
    password_hash="$argon2id$ana",
)
LATER = NOW + timedelta(hours=1)


async def test_registration_creates_a_pending_account(store: AccountStore) -> None:
    account = await store.register(NEW, NOW)

    assert (account.status, account.role) == (Status.AGUARDANDO_VERIFICACAO, None)
    assert account.emails == ("ana@cin.ufpe.br",)
    assert account.signup_method is SignupMethod.SENHA
    assert account.password_hash == "$argon2id$ana"
    found = await store.find_by_login("ana lima")
    assert found is not None
    assert found.id == account.id


async def test_registration_conflicts(store: AccountStore) -> None:
    await store.ensure_developer(DEV, NOW)
    await insert(store, "Ativa", "ativa@ufpe.br")

    with pytest.raises(AccountConflict) as email:
        await store.register(replace(NEW, email="ativa@ufpe.br"), NOW)
    with pytest.raises(AccountConflict) as name:
        await store.register(replace(NEW, name="VINÍCIUS LEÔNCIO"), NOW)

    assert (email.value.field, name.value.field) == ("email", "nome")


async def test_pending_email_can_be_registered_again(store: AccountStore) -> None:
    first = await store.register(replace(NEW, name="Impostor"), NOW)
    await store.add_email_token(b"\x01" * 32, first.id, VERIFICATION, NOW, NOW + timedelta(days=1))

    again = await store.register(NEW, LATER)

    assert again.id == first.id
    assert again.name == "Ana Lima"
    assert await store.verify_email(b"\x01" * 32, LATER) is None  # o link antigo morreu


async def test_verification_token_lifecycle(store: AccountStore) -> None:
    account = await store.register(NEW, NOW)
    expires = NOW + timedelta(hours=24)
    await store.add_email_token(b"\x02" * 32, account.id, VERIFICATION, NOW, expires)
    await store.add_email_token(b"\x03" * 32, account.id, VERIFICATION, NOW, expires)

    assert await store.verify_email(b"\x02" * 32, LATER) is None  # substituído pelo mais novo
    assert await store.verify_email(b"\x03" * 32, expires) is None  # vencido no limite
    await store.add_email_token(b"\x04" * 32, account.id, VERIFICATION, NOW, expires)
    verified = await store.verify_email(b"\x04" * 32, LATER)

    assert verified is not None
    assert verified.status is Status.AGUARDANDO_APROVACAO
    assert await store.verify_email(b"\x04" * 32, LATER) is None  # uso único
    assert await store.verify_email(b"\x05" * 32, LATER) is None  # desconhecido


async def test_profile_and_password_updates(store: AccountStore) -> None:
    await store.ensure_developer(DEV, NOW)
    account = await insert(store, "Bia", "bia@ufpe.br")

    updated = await store.update_profile(account.id, "Beatriz", "Engenharia", Treatment.NEUTRO)
    await store.set_password(account.id, "$argon2id$nova")

    assert (updated.name, updated.course, updated.treatment) == (
        "Beatriz",
        "Engenharia",
        Treatment.NEUTRO,
    )
    reread = await store.get_account(account.id)
    assert reread is not None
    assert reread.password_hash == "$argon2id$nova"
    with pytest.raises(AccountConflict):
        await store.update_profile(account.id, "vinícius leôncio", "Outro", Treatment.NEUTRO)


async def test_deleting_the_other_sessions_keeps_one(store: AccountStore) -> None:
    account = await store.ensure_developer(DEV, NOW)
    for byte in (b"\x0a", b"\x0b", b"\x0c"):
        await store.create_session(byte * 32, account.id, NOW, NOW + timedelta(days=1))

    await store.delete_sessions(account.id, keep=b"\x0b" * 32)

    assert await store.get_session(b"\x0a" * 32) is None
    assert await store.get_session(b"\x0b" * 32) is not None
    assert await store.get_session(b"\x0c" * 32) is None
    await store.delete_sessions(account.id)
    assert await store.get_session(b"\x0b" * 32) is None

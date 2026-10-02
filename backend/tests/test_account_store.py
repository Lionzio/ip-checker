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
    NewGoogleAccount,
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


# --- Gerenciamento (S15-02) ---------------------------------------------------------------------


async def decision_of(store: AccountStore, account_id: uuid.UUID) -> tuple[Any, Any]:
    if isinstance(store, MemoryAccountStore):
        return store.decisions.get(account_id, (None, None))
    assert isinstance(store, PostgresAccountStore)
    row = await store._pool.fetchrow(
        "SELECT decided_by, decided_at FROM app.account WHERE id = $1", account_id
    )
    return row["decided_by"], row["decided_at"]


async def test_accounts_are_listed_by_status_oldest_first(store: AccountStore) -> None:
    developer = await store.ensure_developer(DEV, NOW)
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    bia = await insert(store, "Bia", "bia@cin.ufpe.br", Status.AGUARDANDO_APROVACAO)
    caio = await insert(store, "Caio", "caio@cin.ufpe.br", Status.AGUARDANDO_APROVACAO)
    await insert(store, "Duda", "duda@cin.ufpe.br", Status.AGUARDANDO_VERIFICACAO)

    pending = await store.list_accounts({Status.AGUARDANDO_APROVACAO})
    active = await store.list_accounts([Status.ATIVO])

    assert [a.id for a in pending] == [bia.id, caio.id]
    assert {a.id for a in active} == {developer.id, ana.id}
    assert await store.list_accounts({Status.CONSELHEIRO}) == []


async def test_transition_is_conditional_and_records_the_decision(store: AccountStore) -> None:
    developer = await store.ensure_developer(DEV, NOW)
    bia = await insert(store, "Bia", "bia@cin.ufpe.br", Status.AGUARDANDO_APROVACAO)
    approve: dict[str, Any] = {
        "expected": (Status.AGUARDANDO_APROVACAO, None),
        "status": Status.ATIVO,
        "role": Role.MONITOR,
        "decided_by": developer.id,
        "now": NOW,
        "end_sessions": False,
    }

    approved = await store.transition(bia.id, **approve)
    again = await store.transition(bia.id, **approve)

    assert approved is not None
    assert (approved.status, approved.role) == (Status.ATIVO, Role.MONITOR)
    assert again is None
    assert await decision_of(store, bia.id) == (developer.id, NOW)
    assert await store.transition(uuid.uuid4(), **approve) is None


async def test_role_changes_keep_the_first_decision(store: AccountStore) -> None:
    developer = await store.ensure_developer(DEV, NOW)
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")

    changed = await store.transition(
        ana.id,
        expected=(Status.ATIVO, Role.MONITOR),
        status=Status.ATIVO,
        role=Role.PROFESSOR,
        decided_by=None,
        now=NOW,
        end_sessions=False,
    )

    assert changed is not None
    assert changed.role is Role.PROFESSOR
    assert await decision_of(store, ana.id) == (None, None)
    assert developer.role is Role.DESENVOLVEDOR


async def test_having_been_head_monitor_is_permanent(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")

    async def move(old: tuple[Status, Role | None], status: Status, role: Role | None) -> Account:
        account = await store.transition(
            ana.id,
            expected=old,
            status=status,
            role=role,
            decided_by=None,
            now=NOW,
            end_sessions=False,
        )
        assert account is not None
        return account

    chefe = await move((Status.ATIVO, Role.MONITOR), Status.ATIVO, Role.MONITOR_CHEFE)
    back = await move((Status.ATIVO, Role.MONITOR_CHEFE), Status.ATIVO, Role.MONITOR)
    removed = await move((Status.ATIVO, Role.MONITOR), Status.CONSELHEIRO, Role.MONITOR)

    assert not ana.ja_foi_monitor_chefe
    assert chefe.ja_foi_monitor_chefe
    assert back.ja_foi_monitor_chefe
    assert (removed.status, removed.role, removed.ja_foi_monitor_chefe) == (
        Status.CONSELHEIRO,
        Role.MONITOR,
        True,
    )


@pytest.mark.parametrize("end_sessions", [True, False])
async def test_transition_can_end_the_sessions_of_the_account(
    store: AccountStore, end_sessions: bool
) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    await store.create_session(b"\x0d" * 32, ana.id, NOW, NOW + timedelta(days=1))

    await store.transition(
        ana.id,
        expected=(Status.ATIVO, Role.MONITOR),
        status=Status.EX_MONITOR,
        role=Role.MONITOR,
        decided_by=None,
        now=NOW,
        end_sessions=end_sessions,
    )

    assert (await store.get_session(b"\x0d" * 32) is None) is end_sessions


# --- Google (S16-01) ------------------------------------------------------------------------------

GOOGLE = NewGoogleAccount(
    name="Gabi Google",
    email="gabi@cin.ufpe.br",
    course="Ciência da Computação",
    treatment=Treatment.FEMININO,
    google_sub="1234567890",
)


async def test_google_registration_waits_for_approval_without_password(store: AccountStore) -> None:
    account = await store.register_google(GOOGLE, NOW)

    assert (account.status, account.role, account.password_hash) == (
        Status.AGUARDANDO_APROVACAO,
        None,
        None,
    )
    assert (account.signup_method, account.google_sub) == (SignupMethod.GOOGLE, "1234567890")
    found = await store.find_by_google_sub("1234567890")
    assert found is not None
    assert found.id == account.id
    assert await store.find_by_google_sub("outro") is None


async def test_google_takes_over_an_email_that_was_never_verified(store: AccountStore) -> None:
    squatter = await store.register(replace(NEW, name="Impostor", email="gabi@cin.ufpe.br"), NOW)
    await store.add_email_token(
        b"\x06" * 32, squatter.id, VERIFICATION, NOW, NOW + timedelta(days=1)
    )

    account = await store.register_google(GOOGLE, LATER)

    assert account.id == squatter.id
    assert (account.name, account.password_hash, account.status) == (
        "Gabi Google",
        None,
        Status.AGUARDANDO_APROVACAO,
    )
    # O link pedido por quem não provou ser dono do e-mail morreu.
    assert await store.verify_email(b"\x06" * 32, LATER) is None


async def test_google_registration_conflicts(store: AccountStore) -> None:
    await store.ensure_developer(DEV, NOW)
    await insert(store, "Ativa", "ativa@ufpe.br")
    await store.register_google(GOOGLE, NOW)

    with pytest.raises(AccountConflict) as email:
        await store.register_google(replace(GOOGLE, email="ativa@ufpe.br", google_sub="2"), NOW)
    with pytest.raises(AccountConflict) as name:
        await store.register_google(
            replace(GOOGLE, name="vinícius leôncio", email="v@ufpe.br", google_sub="3"), NOW
        )
    with pytest.raises(AccountConflict) as sub:
        await store.register_google(replace(GOOGLE, name="Outra", email="o@ufpe.br"), NOW)

    assert (email.value.field, name.value.field, sub.value.field) == ("email", "nome", "google")


async def test_linking_google_to_a_verified_account(store: AccountStore) -> None:
    developer = await store.ensure_developer(DEV, NOW)
    other = await insert(store, "Ativa", "ativa@ufpe.br")

    linked = await store.link_google(developer.id, "sub-dev")
    again = await store.link_google(developer.id, "sub-dev")

    assert (linked.google_sub, again.google_sub) == ("sub-dev", "sub-dev")
    with pytest.raises(AccountConflict) as different:
        await store.link_google(developer.id, "sub-outro")
    with pytest.raises(AccountConflict) as taken:
        await store.link_google(other.id, "sub-dev")
    assert (different.value.field, taken.value.field) == ("google", "google")
    reread = await store.find_by_login(DEV.emails[1])
    assert reread is not None
    assert reread.google_sub == "sub-dev"

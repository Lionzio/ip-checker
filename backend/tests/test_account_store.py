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
    HousekeepingCounts,
    ManagementRecord,
    NewAccount,
    NewGoogleAccount,
    Role,
    SignupMethod,
    Status,
    StoreUnavailable,
    Treatment,
)
from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.accounts.store import RESET, VERIFICATION, AccountStore, MemoryAccountStore

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


# --- Esqueci minha senha (S24-04) -----------------------------------------------------------------


async def test_reset_password_is_one_time_and_ends_the_sessions(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    await store.create_session(b"\x0e" * 32, ana.id, NOW, NOW + timedelta(days=1))
    expires = NOW + timedelta(hours=1)
    await store.add_email_token(b"\x01" * 32, ana.id, RESET, NOW, expires)
    # Um pedido novo invalida o anterior da mesma finalidade.
    await store.add_email_token(b"\x02" * 32, ana.id, RESET, NOW, expires)
    await store.add_email_token(b"\x03" * 32, ana.id, VERIFICATION, NOW, expires)

    assert await store.reset_password(b"\x01" * 32, "$argon2id$novo", NOW) is None
    assert await store.reset_password(b"\x03" * 32, "$argon2id$novo", NOW) is None
    changed = await store.reset_password(b"\x02" * 32, "$argon2id$novo", NOW)
    again = await store.reset_password(b"\x02" * 32, "$argon2id$outro", NOW)

    assert changed is not None
    assert changed.password_hash == "$argon2id$novo"
    assert again is None
    assert await store.get_session(b"\x0e" * 32) is None


async def test_an_expired_reset_token_does_nothing(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    await store.add_email_token(b"\x04" * 32, ana.id, RESET, NOW, NOW + timedelta(hours=1))

    later = NOW + timedelta(hours=1, seconds=1)
    assert await store.reset_password(b"\x04" * 32, "$argon2id$novo", later) is None
    unchanged = await store.get_account(ana.id)
    assert unchanged is not None
    assert unchanged.password_hash is None


# --- Registro de gerenciamento (S23-03, REC-06) ---------------------------------------------------


def record(at: datetime, action: str, target: Account, to_role: Role | None) -> ManagementRecord:
    return ManagementRecord(
        at=at,
        action=action,
        actor_id=None,
        actor_name="Professora Ana",
        actor_role=Role.PROFESSOR,
        target_id=target.id,
        target_name=target.name,
        from_status=target.status,
        to_status=Status.ATIVO,
        from_role=target.role,
        to_role=to_role,
    )


async def test_the_record_is_written_only_when_the_transition_happens(store: AccountStore) -> None:
    bia = await insert(store, "Bia", "bia@cin.ufpe.br", Status.AGUARDANDO_APROVACAO)
    approve: dict[str, Any] = {
        "expected": (Status.AGUARDANDO_APROVACAO, None),
        "status": Status.ATIVO,
        "role": Role.MONITOR,
        "decided_by": None,
        "now": NOW,
        "end_sessions": False,
        "record": record(NOW, "aprovar", bia, Role.MONITOR),
    }

    assert await store.transition(bia.id, **approve) is not None
    # Outra pessoa já agiu: a transição não acontece, e nada entra no registro.
    assert await store.transition(bia.id, **approve) is None

    assert await store.management_log(10, NOW) == [record(NOW, "aprovar", bia, Role.MONITOR)]


async def test_the_log_is_newest_first_limited_and_keeps_twelve_months(
    store: AccountStore,
) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    roles = [Role.MONITOR_CHEFE, Role.MONITOR, Role.MONITOR_CHEFE]
    moments = [NOW - timedelta(days=400), NOW - timedelta(days=300), NOW - timedelta(days=1)]
    current = ana
    for moment, role in zip(moments, roles, strict=True):
        changed = await store.transition(
            ana.id,
            expected=(Status.ATIVO, current.role),
            status=Status.ATIVO,
            role=role,
            decided_by=None,
            now=moment,
            end_sessions=False,
            record=record(moment, "alterar_cargo", current, role),
        )
        assert changed is not None
        current = changed

    log = await store.management_log(10, NOW)

    # A de 400 dias saiu pelo expurgo; as outras vêm da mais recente para a mais antiga.
    assert [entry.at for entry in log] == [moments[2], moments[1]]
    assert [entry.to_role for entry in log] == [Role.MONITOR_CHEFE, Role.MONITOR]
    assert [entry.at for entry in await store.management_log(1, NOW)] == [moments[2]]


# --- Limpeza diária (S25-03; Q-19 d) -------------------------------------------------------------


async def age(store: AccountStore, account_id: uuid.UUID, when: datetime) -> None:
    """Põe o cadastro e a última atividade da conta em ``when``, como se o tempo tivesse passado."""
    if isinstance(store, MemoryAccountStore):
        store.accounts[account_id] = replace(store.accounts[account_id], created_at=when)
        store.activity[account_id] = when
        return
    assert isinstance(store, PostgresAccountStore)
    pool: Any = store._pool
    await pool.execute(
        "UPDATE app.account SET created_at = $2, last_activity_at = $2 WHERE id = $1",
        account_id,
        when,
    )


async def test_housekeeping_drops_expired_sessions_and_spent_links(store: AccountStore) -> None:
    dev = await store.ensure_developer(DEV, NOW - timedelta(days=30))
    await store.create_session(
        b"\x0a" * 32, dev.id, NOW - timedelta(days=8), NOW - timedelta(days=1)
    )
    await store.create_session(b"\x0b" * 32, dev.id, NOW, NOW + timedelta(days=7))
    ana = await store.register(NEW, NOW)
    hour = timedelta(hours=1)
    await store.add_email_token(b"\x01" * 32, ana.id, VERIFICATION, NOW, NOW + hour)
    # O pedido novo invalida o anterior (usado); o de redefinição já venceu.
    await store.add_email_token(b"\x02" * 32, ana.id, VERIFICATION, NOW, NOW + hour)
    await store.add_email_token(b"\x03" * 32, ana.id, RESET, NOW - 2 * hour, NOW - hour)

    counts = await store.housekeeping(NOW)

    assert counts == HousekeepingCounts(sessions=1, tokens=2)
    assert await store.get_session(b"\x0a" * 32) is None
    assert await store.get_session(b"\x0b" * 32) is not None
    assert await store.verify_email(b"\x02" * 32, NOW) is not None  # o link vivo continua valendo
    assert await store.housekeeping(NOW) == HousekeepingCounts(tokens=1)  # agora usado


async def test_unconfirmed_signups_go_after_48_hours_and_free_the_email(
    store: AccountStore,
) -> None:
    old = await store.register(NEW, NOW - timedelta(hours=49))
    recent = await store.register(
        replace(NEW, name="Bia Recente", email="bia@cin.ufpe.br"), NOW - timedelta(hours=47)
    )
    # Pediu o cadastro de novo com o mesmo e-mail: o prazo recomeça.
    again = replace(NEW, name="Caio de Novo", email="caio@cin.ufpe.br")
    await store.register(again, NOW - timedelta(hours=60))
    await store.register(again, NOW - timedelta(hours=1))

    counts = await store.housekeeping(NOW)

    assert counts.unverified == 1
    assert await store.get_account(old.id) is None
    assert await store.get_account(recent.id) is not None
    assert await store.find_by_login("caio@cin.ufpe.br") is not None
    fresh = await store.register(NEW, NOW)  # nome e e-mail livres
    assert fresh.id != old.id


async def test_inactive_accounts_go_after_365_days_but_never_the_developer(
    store: AccountStore,
) -> None:
    dev = await store.ensure_developer(DEV, NOW - timedelta(days=800))
    # Mesmo inativa e esquecida, a conta do desenvolvedor fica (P-14).
    retired = await store.transition(
        dev.id,
        expected=(Status.ATIVO, Role.DESENVOLVEDOR),
        status=Status.INATIVO,
        role=Role.DESENVOLVEDOR,
        decided_by=None,
        now=NOW - timedelta(days=700),
        end_sessions=False,
    )
    assert retired is not None
    await age(store, dev.id, NOW - timedelta(days=700))
    gone = await insert(store, "Ex Antiga", "ex@cin.ufpe.br", Status.EX_MONITOR)
    kept = await insert(store, "Ex Recente", "recente@cin.ufpe.br", Status.EX_MONITOR)
    active = await insert(store, "Ativa Calada", "ativa@cin.ufpe.br")
    refused = await insert(store, "Recusada", "recusada@cin.ufpe.br", Status.RECUSADO)
    # A conta que some aprovou outra e aparece no registro: os dois ficam, sem o vínculo.
    bia = await insert(store, "Bia", "bia@cin.ufpe.br", Status.AGUARDANDO_APROVACAO)
    moment = NOW - timedelta(days=200)
    entry = replace(record(moment, "aprovar", bia, Role.MONITOR), actor_id=gone.id)
    approved = await store.transition(
        bia.id,
        expected=(Status.AGUARDANDO_APROVACAO, None),
        status=Status.ATIVO,
        role=Role.MONITOR,
        decided_by=gone.id,
        now=moment,
        end_sessions=False,
        record=entry,
    )
    assert approved is not None
    await age(store, gone.id, NOW - timedelta(days=366))
    await age(store, refused.id, NOW - timedelta(days=365))
    await age(store, kept.id, NOW - timedelta(days=364))
    await age(store, active.id, NOW - timedelta(days=900))

    counts = await store.housekeeping(NOW)

    assert counts.inactive == 2
    for account in (gone, refused):
        assert await store.get_account(account.id) is None
    for account in (dev, kept, active, bia):
        assert await store.get_account(account.id) is not None
    assert await store.find_by_login("ex@cin.ufpe.br") is None  # o e-mail ficou livre (Q-19 d)
    await store.register(replace(NEW, name="Ex Antiga", email="ex@cin.ufpe.br"), NOW)
    assert await store.management_log(10, NOW) == [replace(entry, actor_id=None)]


async def test_activity_keeps_an_account_from_the_purge(store: AccountStore) -> None:
    login = await insert(store, "Volta Sempre", "volta@cin.ufpe.br", Status.CONSELHEIRO)
    await age(store, login.id, NOW - timedelta(days=500))
    await store.create_session(
        b"\x0c" * 32, login.id, NOW - timedelta(days=10), NOW - timedelta(days=3)
    )
    moved = await insert(store, "Mudou", "mudou@cin.ufpe.br", Status.INATIVO)
    await age(store, moved.id, NOW - timedelta(days=500))
    changed = await store.transition(
        moved.id,
        expected=(Status.INATIVO, None),
        status=Status.AGUARDANDO_APROVACAO,
        role=None,
        decided_by=None,
        now=NOW - timedelta(days=5),
        end_sessions=False,
    )
    assert changed is not None
    reset = await insert(store, "Lembrou", "lembrou@cin.ufpe.br", Status.EX_MONITOR)
    await age(store, reset.id, NOW - timedelta(days=500))
    await store.add_email_token(b"\x06" * 32, reset.id, RESET, NOW - timedelta(days=2), NOW)
    assert await store.reset_password(b"\x06" * 32, "$argon2id$nova", NOW - timedelta(days=2))

    counts = await store.housekeeping(NOW)

    assert counts.inactive == 0
    for account in (login, moved, reset):
        assert await store.get_account(account.id) is not None


async def test_the_purge_keeps_twelve_months_of_log(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    old = NOW - timedelta(days=400)
    changed = await store.transition(
        ana.id,
        expected=(Status.ATIVO, Role.MONITOR),
        status=Status.ATIVO,
        role=Role.MONITOR_CHEFE,
        decided_by=None,
        now=old,
        end_sessions=False,
        record=record(old, "alterar_cargo", ana, Role.MONITOR_CHEFE),
    )
    assert changed is not None

    assert (await store.housekeeping(NOW)).log == 1
    assert await store.management_log(10, NOW) == []


async def test_the_feedback_quota_counts_per_account_and_per_day(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    bia = await insert(store, "Bia", "bia@cin.ufpe.br")
    today = NOW.date()

    taken = [await store.take_feedback_quota(ana.id, today, 2, 3) for _ in range(3)]
    other = await store.take_feedback_quota(bia.id, today, 2, 3)
    full = await store.take_feedback_quota(bia.id, today, 2, 3)
    tomorrow = await store.take_feedback_quota(ana.id, today + timedelta(days=1), 2, 3)

    assert taken == [None, None, "conta"]
    assert (other, full, tomorrow) == (None, "servidor", None)


async def test_old_quota_days_and_removed_accounts_leave_the_quota(store: AccountStore) -> None:
    ana = await insert(store, "Ana", "ana@cin.ufpe.br")
    gone = await insert(store, "Ex", "ex@cin.ufpe.br", Status.EX_MONITOR)
    for days in (0, 1, 2):
        await store.take_feedback_quota(ana.id, NOW.date() - timedelta(days=days), 1, 100)
    await store.take_feedback_quota(gone.id, NOW.date(), 1, 100)
    await age(store, gone.id, NOW - timedelta(days=400))

    await store.housekeeping(NOW)

    # Hoje e ontem ficam; anteontem saiu, e a conta apagada levou a dela.
    assert await store.take_feedback_quota(ana.id, NOW.date(), 1, 100) == "conta"
    assert (
        await store.take_feedback_quota(ana.id, NOW.date() - timedelta(days=1), 1, 100) == "conta"
    )
    assert await store.take_feedback_quota(ana.id, NOW.date() - timedelta(days=2), 1, 100) is None
    assert await store.take_feedback_quota(ana.id, NOW.date(), 1, 2) == "conta"


async def test_housekeeping_needs_the_database() -> None:
    store = MemoryAccountStore()
    store.available = False

    with pytest.raises(StoreUnavailable):
        await store.housekeeping(NOW)


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

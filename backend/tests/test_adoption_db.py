"""Adoção pela equipe no PostgreSQL (S28-02; critério 2 da P-09, Q-15).

A API grava um registro por (conta, período, lista) e não lê nada; quem consulta (``ipc_reader``)
vê só a porcentagem por período e lista; o registro some com a conta.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database
from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.db.migrate import ensure_login_role, mark_check_account

pytestmark = [pytest.mark.anyio, requires_database]

VIEW = "telemetry.v_team_adoption_by_list"


def as_user(role: str, password: str) -> str:
    parts = urlsplit(DATABASE_URL)
    return urlunsplit(parts._replace(netloc=f"{role}:{password}@{parts.hostname}:{parts.port}"))


@pytest.fixture
async def admin() -> AsyncIterator[Any]:
    await fresh_schema()
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        await connection.close()


@pytest.fixture
async def store(admin: Any) -> AsyncIterator[PostgresAccountStore]:
    password = secrets.token_urlsafe(16)
    await ensure_login_role(admin, "ipc_api_teste", password)
    store = await PostgresAccountStore.connect(as_user("ipc_api_teste", password))
    try:
        yield store
    finally:
        await store.close()


@pytest.fixture
async def reader(admin: Any) -> AsyncIterator[Any]:
    password = secrets.token_urlsafe(16)
    await admin.execute("DROP ROLE IF EXISTS ipc_leitura_teste")
    statement = await admin.fetchval(
        "SELECT format('CREATE ROLE ipc_leitura_teste LOGIN PASSWORD %L IN ROLE ipc_reader', "
        "$1::text)",
        password,
    )
    await admin.execute(statement)
    connection = await asyncpg.connect(as_user("ipc_leitura_teste", password))
    try:
        yield connection
    finally:
        await connection.close()
        await admin.execute("DROP ROLE ipc_leitura_teste")


async def account(
    admin: Any, name: str, role: str | None = "monitor", status: str = "ativo"
) -> Any:
    created = await admin.fetchval(
        "INSERT INTO app.account (name, course, treatment, role, status, signup_method) "
        "VALUES ($1, 'Ciência da Computação', 'neutro', $2, $3, 'senha') RETURNING id",
        name,
        role,
        status,
    )
    email = f"{name.lower().replace(' ', '.')}@cin.ufpe.br"
    await admin.execute(
        "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)", email, created
    )
    return created


async def adoption(reader: Any) -> dict[tuple[str, int], Decimal | None]:
    rows = await reader.fetch(f"SELECT * FROM {VIEW} ORDER BY 1, 2")  # noqa: S608
    return {(row["semester"], row["list_number"]): row["adoption_pct"] for row in rows}


async def test_the_view_gives_the_share_of_active_members_per_list(
    admin: Any, store: PostgresAccountStore, reader: Any
) -> None:
    ana, bia, caio, davi = [await account(admin, name) for name in ("Ana", "Bia", "Caio", "Davi")]
    developer = await account(admin, "Dev", role="desenvolvedor")
    check = await account(admin, "Verificacao")
    await mark_check_account(admin, "verificacao@cin.ufpe.br")
    former = await account(admin, "Ex Monitor", status="ex_monitor")

    for who in (ana, bia, caio):
        await store.record_adoption(who, "2027.1", 1)
    await store.record_adoption(ana, "2027.1", 1)  # repetir não muda nada
    await store.record_adoption(ana, "2027.1", 2)
    # O desenvolvedor, a conta de verificação e quem saiu da equipe não contam.
    for who in (developer, check, former):
        await store.record_adoption(who, "2027.1", 3)
    await store.record_adoption(davi, "2026.2", 6)

    found = await adoption(reader)

    assert found[("2027.1", 1)] == Decimal("75.0")
    assert found[("2027.1", 2)] == Decimal("25.0")
    assert found[("2027.1", 3)] == Decimal("0.0")
    assert found[("2027.1", 6)] == Decimal("0.0")
    assert found[("2026.2", 6)] == Decimal("25.0")
    # Cada período com uso aparece com as 6 listas.
    assert len(found) == 12


async def test_the_view_has_only_percentages(reader: Any) -> None:
    columns = await reader.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'telemetry' AND table_name = 'v_team_adoption_by_list'"
    )

    assert sorted(row["column_name"] for row in columns) == [
        "adoption_pct",
        "list_number",
        "semester",
    ]


async def test_without_members_the_share_is_empty(
    admin: Any, store: PostgresAccountStore, reader: Any
) -> None:
    developer = await account(admin, "Dev", role="desenvolvedor")
    await store.record_adoption(developer, "2027.1", 1)

    assert set((await adoption(reader)).values()) == {None}


async def test_the_api_only_inserts_and_the_reader_only_sees_the_view(
    admin: Any, store: PostgresAccountStore, reader: Any
) -> None:
    ana = await account(admin, "Ana")
    await store.record_adoption(ana, "2027.1", 1)
    api: Any = store._pool  # a mesma credencial da API

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await api.fetch("SELECT * FROM app.list_adoption")
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await api.execute("DELETE FROM app.list_adoption")
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.fetch("SELECT * FROM app.list_adoption")
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.fetch("SELECT name FROM app.account")


async def test_the_record_goes_away_with_the_account(
    admin: Any, store: PostgresAccountStore
) -> None:
    ana = await account(admin, "Ana")
    await store.record_adoption(ana, "2027.1", 1)

    await admin.execute("DELETE FROM app.account WHERE id = $1", ana)

    assert await admin.fetchval("SELECT count(*) FROM app.list_adoption") == 0


async def test_the_store_reads_the_check_account_flag(
    admin: Any, store: PostgresAccountStore
) -> None:
    await account(admin, "Verificacao")
    await account(admin, "Ana")
    await mark_check_account(admin, "Verificacao")

    check = await store.find_by_login("verificacao@cin.ufpe.br")
    other = await store.find_by_login("Ana")

    assert check is not None
    assert check.check_account
    assert other is not None
    assert not other.check_account

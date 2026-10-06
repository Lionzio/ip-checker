"""Registro de gerenciamento no PostgreSQL (S23-03, REC-06): só acrescentar, ler e expurgar.

O usuário da API insere e lê, mas não altera nem apaga um registro; o expurgo é uma função que
conta os 12 meses pelo relógio do banco, então nenhuma chamada apaga um registro recente.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database
from ipc_api.db.migrate import ensure_login_role

pytestmark = [pytest.mark.anyio, requires_database]

_INSERT = (
    "INSERT INTO app.management_log (at, action, actor_name, target_name, from_status, "
    "to_status) VALUES ($1, $2, 'Ana', 'Bia', 'aguardando_aprovacao', 'ativo') RETURNING id"
)


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
async def api(admin: Any) -> AsyncIterator[Any]:
    """O usuário da API, criado como no deploy: membro de ipc_app."""
    password = secrets.token_urlsafe(16)
    await ensure_login_role(admin, "ipc_api_teste", password)
    connection = await asyncpg.connect(as_user("ipc_api_teste", password))
    try:
        yield connection
    finally:
        await connection.close()


async def test_the_api_appends_and_reads_but_never_edits_the_log(api: Any) -> None:
    entry = await api.fetchval(_INSERT, datetime.now(UTC), "aprovar")

    assert await api.fetchval("SELECT count(*) FROM app.management_log") == 1
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await api.execute("UPDATE app.management_log SET actor_name = 'Outra' WHERE id = $1", entry)
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await api.execute("DELETE FROM app.management_log WHERE id = $1", entry)


async def test_only_known_actions_are_accepted(api: Any) -> None:
    with pytest.raises(asyncpg.CheckViolationError):
        await api.fetchval(_INSERT, datetime.now(UTC), "apagar")


async def test_the_purge_counts_twelve_months_by_the_database_clock(api: Any) -> None:
    now = datetime.now(UTC)
    await api.fetchval(_INSERT, now - timedelta(days=400), "aprovar")  # mais de 12 meses
    await api.fetchval(_INSERT, now - timedelta(days=300), "remover")
    await api.fetchval(_INSERT, now, "reativar")

    # Pedir um "agora" no futuro não adianta o prazo: vale o relógio do banco.
    future = now + timedelta(days=3650)

    assert await api.fetchval("SELECT app.purge_management_log($1)", future) == 1
    actions = await api.fetch("SELECT action FROM app.management_log ORDER BY at")
    assert [row["action"] for row in actions] == ["remover", "reativar"]


async def test_removing_an_account_keeps_its_history(admin: Any) -> None:
    account = await admin.fetchval(
        "INSERT INTO app.account (name, course, treatment, role, status, signup_method) "
        "VALUES ('Bia', 'CC', 'neutro', 'monitor', 'ativo', 'senha') RETURNING id"
    )
    await admin.execute(
        "INSERT INTO app.management_log (at, action, actor_name, target_id, target_name, "
        "from_status, to_status) VALUES (now(), 'aprovar', 'Ana', $1, 'Bia', "
        "'aguardando_aprovacao', 'ativo')",
        account,
    )

    # O expurgo de contas (Sprint 25) apaga a conta; o registro fica, só sem o identificador.
    await admin.execute("DELETE FROM app.account WHERE id = $1", account)

    row = await admin.fetchrow("SELECT target_id, target_name FROM app.management_log")
    assert (row["target_id"], row["target_name"]) == (None, "Bia")

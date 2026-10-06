"""Migrações do banco (S13-01; DoD: toda migração tem ida e volta testadas).

Os testes de descoberta rodam sempre; os demais precisam de ``IPC_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database
from ipc_api.db import migrate
from ipc_api.db.migrate import (
    DEFAULT_DIR,
    applied_versions,
    discover,
    ensure_login_role,
    migrate_down,
    migrate_up,
)

# --- Descoberta dos arquivos -------------------------------------------------------------------


def test_every_migration_has_up_and_down() -> None:
    migrations = discover(DEFAULT_DIR)

    assert [(m.version, m.name) for m in migrations][:1] == [("0001", "contas")]
    for migration in migrations:
        assert migration.up.name.endswith(".up.sql")
        assert migration.down.name.endswith(".down.sql")


def test_migration_without_down_is_refused(tmp_path: Path) -> None:
    (tmp_path / "0001_a.up.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.down\.sql"):
        discover(tmp_path)


def test_version_with_two_names_is_refused(tmp_path: Path) -> None:
    (tmp_path / "0001_a.up.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0001_b.down.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ValueError, match="dois nomes"):
        discover(tmp_path)


def test_other_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "LEIA-ME.md").write_text("x", encoding="utf-8")
    (tmp_path / "0002_b.up.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0002_b.down.sql").write_text("SELECT 1;", encoding="utf-8")

    assert [m.version for m in discover(tmp_path)] == ["0002"]


def test_cli_requires_the_admin_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("IPC_DATABASE_ADMIN_URL", raising=False)

    assert migrate.main(["status"]) == 2
    assert "IPC_DATABASE_ADMIN_URL" in capsys.readouterr().err


# --- Contra o PostgreSQL -----------------------------------------------------------------------


@pytest.fixture
async def admin() -> AsyncIterator[Any]:
    await fresh_schema()
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        await connection.close()


async def _schema_exists(connection: Any) -> bool:
    return bool(await connection.fetchval("SELECT 1 FROM pg_namespace WHERE nspname = 'app'"))


@pytest.mark.anyio
@requires_database
async def test_down_reverts_and_up_reapplies(admin: Any) -> None:
    migrations = discover(DEFAULT_DIR)

    assert await migrate_up(admin, migrations) == []  # já aplicadas: nada a fazer
    assert await migrate_down(admin, migrations, "0000") == ["0005", "0004", "0003", "0002", "0001"]
    assert not await _schema_exists(admin)
    assert await migrate_up(admin, migrations) == ["0001", "0002", "0003", "0004", "0005"]
    assert await _schema_exists(admin)


@requires_database
def test_cli_up_and_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    asyncio.run(fresh_schema())
    monkeypatch.setenv("IPC_DATABASE_ADMIN_URL", DATABASE_URL)

    assert migrate.main(["status"]) == 0
    assert (
        capsys.readouterr().out.strip()
        == "aplicadas: 0001, 0002, 0003, 0004, 0005; pendentes: nenhuma"
    )
    assert migrate.main(["up"]) == 0
    assert capsys.readouterr().out.strip() == "aplicadas: nenhuma"


async def _insert_account(connection: Any, name: str, role: str | None, status: str) -> Any:
    return await connection.fetchval(
        "INSERT INTO app.account (name, course, treatment, role, status, signup_method) "
        "VALUES ($1, 'Ciência da Computação', 'neutro', $2, $3, 'senha') RETURNING id",
        name,
        role,
        status,
    )


@pytest.mark.anyio
@requires_database
async def test_ja_foi_monitor_chefe_never_goes_back(admin: Any) -> None:
    account = await _insert_account(admin, "Chefe", "monitor_chefe", "ativo")
    read = "SELECT ja_foi_monitor_chefe FROM app.account WHERE id = $1"

    assert await admin.fetchval(read, account) is True
    await admin.execute("UPDATE app.account SET role = 'monitor' WHERE id = $1", account)
    await admin.execute(
        "UPDATE app.account SET ja_foi_monitor_chefe = false WHERE id = $1", account
    )
    assert await admin.fetchval(read, account) is True

    other = await _insert_account(admin, "Monitor", "monitor", "ativo")
    assert await admin.fetchval(read, other) is False


@pytest.mark.anyio
@requires_database
@pytest.mark.parametrize(
    "email",
    ["x@xcin.ufpe.br", "x@ee.ufpe.br", "X@cin.ufpe.br", "x@cin.ufpe.br.exemplo.com", "x@gmail.com"],
)
async def test_only_lowercase_emails_of_the_allowed_domains(admin: Any, email: str) -> None:
    account = await _insert_account(admin, "Alguém", "monitor", "ativo")

    with pytest.raises(asyncpg.CheckViolationError):
        await admin.execute(
            "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)", email, account
        )
    await admin.execute(
        "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)",
        "alguem@cin.ufpe.br",
        account,
    )


@pytest.mark.anyio
@requires_database
async def test_names_are_unique_ignoring_case_and_active_needs_a_role(admin: Any) -> None:
    await _insert_account(admin, "Ana Souza", "monitor", "ativo")

    with pytest.raises(asyncpg.UniqueViolationError):
        await _insert_account(admin, "ANA SOUZA", "monitor", "ativo")
    with pytest.raises(asyncpg.CheckViolationError):
        await _insert_account(admin, "Sem Cargo", None, "ativo")
    await _insert_account(admin, "Esperando", None, "aguardando_aprovacao")


@pytest.mark.anyio
@requires_database
async def test_api_role_cannot_delete_accounts_or_change_the_schema(admin: Any) -> None:
    password = secrets.token_urlsafe(16)
    await ensure_login_role(admin, "ipc_api_teste", password)
    await ensure_login_role(admin, "ipc_api_teste", password)  # de novo: atualiza, não falha
    account = await _insert_account(admin, "Alguém", "monitor", "ativo")

    parts = urlsplit(DATABASE_URL)
    netloc = f"ipc_api_teste:{password}@{parts.hostname}:{parts.port}"
    api: Any = await asyncpg.connect(urlunsplit(parts._replace(netloc=netloc)))
    try:
        assert await api.fetchval("SELECT count(*) FROM app.account") == 1
        await api.execute("UPDATE app.account SET course = 'Outro' WHERE id = $1", account)
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await api.execute("DELETE FROM app.account WHERE id = $1", account)
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await api.execute("CREATE TABLE app.intrusa (x int)")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await api.execute("DROP TABLE app.session")
    finally:
        await api.close()


@pytest.mark.anyio
@requires_database
@pytest.mark.parametrize("role", ["Maiúscula", "1numero", "com espaço", "x" * 64, "a;drop"])
async def test_login_role_name_is_validated(admin: Any, role: str) -> None:
    with pytest.raises(ValueError, match="inválido"):
        await ensure_login_role(admin, role, "senha")


@pytest.mark.anyio
@requires_database
async def test_login_role_needs_a_password(admin: Any) -> None:
    with pytest.raises(ValueError, match="IPC_DB_LOGIN_PASSWORD"):
        await ensure_login_role(admin, "ipc_api_teste", "")


@pytest.mark.anyio
@requires_database
async def test_a_legacy_tracking_table_moves_out_of_public(admin: Any) -> None:
    # Um banco de antes da Sprint 25: a tabela de controle ficava em public, exposta pela Data
    # API do Supabase. A primeira execução a move para ipc_meta, sem perder o que foi aplicado.
    before = await applied_versions(admin)
    await admin.execute("ALTER TABLE ipc_meta.schema_migrations SET SCHEMA public")
    await admin.execute("ALTER TABLE public.schema_migrations RENAME TO ipc_schema_migrations")

    assert await applied_versions(admin) == before
    assert await admin.fetchval("SELECT to_regclass('public.ipc_schema_migrations')") is None
    # Ninguém além do administrador usa o esquema de controle.
    assert not await admin.fetchval("SELECT has_schema_privilege('public', 'ipc_meta', 'USAGE')")

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
    assert await migrate_down(admin, migrations, "0000") == [
        "0008",
        "0007",
        "0006",
        "0005",
        "0004",
        "0003",
        "0002",
        "0001",
    ]
    assert not await _schema_exists(admin)
    assert await migrate_up(admin, migrations) == [
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
        "0007",
        "0008",
    ]
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
        == "aplicadas: 0001, 0002, 0003, 0004, 0005, 0006, 0007, 0008; pendentes: nenhuma"
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


# --- Checksum das migrações aplicadas (S28-04) -------------------------------------------------


def _copy_migrations(target: Path) -> Path:
    for path in DEFAULT_DIR.iterdir():
        (target / path.name).write_bytes(path.read_bytes())
    return target


@pytest.mark.anyio
@requires_database
async def test_each_applied_migration_keeps_its_checksum(admin: Any) -> None:
    migrations = discover(DEFAULT_DIR)
    stored = dict(await admin.fetch("SELECT version, checksum FROM ipc_meta.schema_migrations"))

    assert stored == {m.version: m.checksum for m in migrations}


def test_the_checksum_ignores_windows_line_endings(tmp_path: Path) -> None:
    (tmp_path / "0001_a.up.sql").write_bytes(b"SELECT 1;\nSELECT 2;\n")
    (tmp_path / "0001_a.down.sql").write_bytes(b"SELECT 1;\n")
    unix = discover(tmp_path)[0].checksum
    (tmp_path / "0001_a.up.sql").write_bytes(b"SELECT 1;\r\nSELECT 2;\r\n")

    assert discover(tmp_path)[0].checksum == unix


@pytest.mark.anyio
@requires_database
async def test_an_applied_migration_that_changed_is_refused(admin: Any, tmp_path: Path) -> None:
    folder = _copy_migrations(tmp_path)
    edited = folder / "0003_registro_gerenciamento.up.sql"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n-- editada\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"0003 .* mudou depois de aplicada"):
        await migrate_up(admin, discover(folder))
    with pytest.raises(ValueError, match="mudou depois de aplicada"):
        await migrate.run("status", url=DATABASE_URL, directory=folder, target="0", login_role=None)


@pytest.mark.anyio
@requires_database
async def test_migrations_applied_before_the_checksum_get_one(admin: Any) -> None:
    await admin.execute("UPDATE ipc_meta.schema_migrations SET checksum = NULL")
    migrations = discover(DEFAULT_DIR)

    assert await migrate.verify_checksums(admin, migrations) == [m.version for m in migrations]
    assert await migrate.verify_checksums(admin, migrations) == []


@pytest.mark.anyio
@requires_database
async def test_versions_newer_than_the_folder_are_ignored(admin: Any, tmp_path: Path) -> None:
    # Um deploy de volta para uma versão anterior (docs/runbook.md): o banco já tem a 0008, e a
    # pasta antiga não. As migrações só acrescentam, então a versão anterior sobe normalmente.
    folder = _copy_migrations(tmp_path)
    for path in folder.glob("0008_*"):
        path.unlink()

    assert await migrate_up(admin, discover(folder)) == []


@pytest.mark.anyio
@requires_database
async def test_the_catalog_only_grows_and_checks_its_identifiers(admin: Any) -> None:
    # 0008 (S50-05): a API acrescenta e reescreve o catálogo, mas não apaga questões nem rodadas;
    # o identificador da questão segue L1-Q1, e o treino é a única tarefa sem número.
    for table, delete in (
        ("app.catalog_question", False),
        ("app.catalog_list", False),
        ("app.import_run", False),
        ("app.import_token", False),
        ("app.catalog_question_version", True),
    ):
        assert await admin.fetchval("SELECT has_table_privilege('ipc_app', $1, 'INSERT')", table), (
            table
        )
        assert (
            await admin.fetchval("SELECT has_table_privilege('ipc_app', $1, 'DELETE')", table)
            is delete
        ), table
    await admin.execute("INSERT INTO app.catalog_period VALUES ('2026.2', now())")
    with pytest.raises(asyncpg.CheckViolationError):
        await admin.execute(
            "INSERT INTO app.catalog_list (id, period, kind, number, title, last_seen) "
            "VALUES (gen_random_uuid(), '2026.2', 'treino', 1, 'Treino', now())"
        )
    list_id = await admin.fetchval(
        "INSERT INTO app.catalog_list (id, period, kind, number, title, last_seen) "
        "VALUES (gen_random_uuid(), '2026.2', 'lista', 1, 'Lista 1', now()) RETURNING id"
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await admin.execute(
            "INSERT INTO app.catalog_question (id, period, question_id, list_id, "
            "dikastis_problem_id, title, description, input_description, output_description, "
            "samples, content_hash, version, first_seen, updated_at) VALUES (gen_random_uuid(), "
            "'2026.2', 'L1Q1', $1, 'P', 'T', '', '', '', '[]', repeat('a', 64), 1, now(), now())",
            list_id,
        )


@pytest.mark.anyio
@requires_database
async def test_import_tokens_and_runs_go_away_with_the_account(admin: Any) -> None:
    account = await _insert_account(admin, "Chefia", "monitor_chefe", "ativo")
    await admin.execute("INSERT INTO app.catalog_period VALUES ('2026.2', now())")
    await admin.execute(
        "INSERT INTO app.import_token (id, account_id, token_hash, label, created_at, expires_at) "
        "VALUES (gen_random_uuid(), $1, repeat('b', 64), 'Chrome', now(), now())",
        account,
    )
    await admin.execute(
        "INSERT INTO app.import_run (id, account_id, mode, period, started_at) "
        "VALUES (gen_random_uuid(), $1, 'manual', '2026.2', now())",
        account,
    )

    await admin.execute("DELETE FROM app.account WHERE id = $1", account)

    assert await admin.fetchval("SELECT count(*) FROM app.import_token") == 0
    assert await admin.fetchval("SELECT count(*) FROM app.import_run") == 0


# --- Conta de verificação do deploy (S28-02) ---------------------------------------------------


async def _check_flags(connection: Any) -> dict[str, bool]:
    rows = await connection.fetch("SELECT name, check_account FROM app.account")
    return {row["name"]: row["check_account"] for row in rows}


@pytest.mark.anyio
@requires_database
async def test_the_check_account_is_marked_by_email_or_name(admin: Any) -> None:
    check = await _insert_account(admin, "Verificação", "monitor", "ativo")
    await admin.execute(
        "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)",
        "verificacao@cin.ufpe.br",
        check,
    )
    await _insert_account(admin, "Monitora", "monitor", "ativo")

    assert await migrate.mark_check_account(admin, " Verificacao@CIN.ufpe.br ")
    assert await _check_flags(admin) == {"Verificação": True, "Monitora": False}
    # Só uma conta fica marcada: trocar a conta de verificação desmarca a anterior.
    assert await migrate.mark_check_account(admin, "monitora")
    assert await _check_flags(admin) == {"Verificação": False, "Monitora": True}
    # Um login que não existe não muda nada.
    assert not await migrate.mark_check_account(admin, "ninguem@cin.ufpe.br")
    assert await _check_flags(admin) == {"Verificação": False, "Monitora": True}


@requires_database
def test_cli_up_marks_the_check_account(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    asyncio.run(fresh_schema())
    monkeypatch.setenv("IPC_DATABASE_ADMIN_URL", DATABASE_URL)
    monkeypatch.setenv("IPC_CHECK_ACCOUNT_LOGIN", "ninguem@cin.ufpe.br")

    assert migrate.main(["up"]) == 0
    assert (
        capsys.readouterr().out.strip()
        == "aplicadas: nenhuma; conta de verificação: não encontrada"
    )

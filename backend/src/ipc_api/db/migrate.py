"""Migrações SQL do banco (S13-01): ``database/migrations/NNNN_nome.up.sql`` e ``.down.sql``.

Roda com a credencial de administrador, nunca com a da API::

    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate up
    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate down --to 0
    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate status

Cada migração roda numa transação, e um *advisory lock* impede duas execuções ao mesmo tempo.
Com ``--login-role NOME``, o comando também cria (ou atualiza) o usuário com que a API entra no
banco, com a senha de ``IPC_DB_LOGIN_PASSWORD``, e o torna membro de ``ipc_app``: é assim que o
Compose prepara o banco local. Nenhuma senha vai para a saída.

Cada migração aplicada guarda o SHA-256 do ``.up.sql`` (S28-04). Antes de aplicar qualquer coisa,
o comando confere que nenhum arquivo já aplicado mudou: uma migração se corrige com outra, nunca
editando a que já rodou. Versões aplicadas que não existem na pasta (um deploy de volta para uma
versão anterior, docs/runbook.md) são ignoradas, porque as migrações só acrescentam.

Com ``IPC_CHECK_ACCOUNT_LOGIN`` (e-mail ou nome), o ``up`` também marca a conta de verificação do
deploy (S28-02): as verificações dela não entram na telemetria nem no relatório de eficácia. Só uma
conta fica marcada; se o login não existir, nada muda.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncpg

#: Repositório: backend/src/ipc_api/db/migrate.py -> raiz. Nas imagens, IPC_MIGRATIONS_DIR.
DEFAULT_DIR = Path(__file__).resolve().parents[4] / "database" / "migrations"
_FILE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.(up|down)\.sql$")
_ROLE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
#: Chave do advisory lock das migrações ("IPCMIGR" em hexadecimal).
_LOCK_KEY = 0x4950434D494752

#: Controle das migrações num esquema próprio, sem acesso para ninguém além do administrador.
#: Até a Sprint 25 a tabela ficava em ``public``, que o Supabase expõe pela Data API às chaves
#: anônimas; um banco antigo tem a tabela movida para cá na primeira execução (S25-02).
_TRACKING = """
CREATE SCHEMA IF NOT EXISTS ipc_meta;
REVOKE ALL ON SCHEMA ipc_meta FROM PUBLIC;
DO $$
BEGIN
  IF to_regclass('public.ipc_schema_migrations') IS NOT NULL
     AND to_regclass('ipc_meta.schema_migrations') IS NULL THEN
    ALTER TABLE public.ipc_schema_migrations SET SCHEMA ipc_meta;
    ALTER TABLE ipc_meta.ipc_schema_migrations RENAME TO schema_migrations;
  END IF;
END
$$;
CREATE TABLE IF NOT EXISTS ipc_meta.schema_migrations (
  version text PRIMARY KEY,
  name text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE ipc_meta.schema_migrations ADD COLUMN IF NOT EXISTS checksum text;
"""


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    name: str
    up: Path
    down: Path

    @property
    def checksum(self) -> str:
        """SHA-256 do ``.up.sql``, com as quebras de linha normalizadas (checkout no Windows)."""
        text = self.up.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(text).hexdigest()


def discover(directory: Path) -> list[Migration]:
    """Lista as migrações em ordem; cada versão precisa ter ida e volta."""
    found: dict[str, dict[str, Path]] = {}
    names: dict[str, str] = {}
    for path in directory.iterdir():
        match = _FILE.match(path.name)
        if match is None:
            continue
        version, name, direction = match.groups()
        if names.setdefault(version, name) != name:
            raise ValueError(f"A versão {version} tem dois nomes: {names[version]} e {name}.")
        found.setdefault(version, {})[direction] = path
    migrations = []
    for version in sorted(found):
        files = found[version]
        if set(files) != {"up", "down"}:
            raise ValueError(f"A migração {version} precisa de .up.sql e .down.sql.")
        migrations.append(Migration(version, names[version], files["up"], files["down"]))
    return migrations


async def applied_versions(connection: Any) -> list[str]:
    await connection.execute(_TRACKING)
    rows = await connection.fetch("SELECT version FROM ipc_meta.schema_migrations ORDER BY 1")
    return [str(row["version"]) for row in rows]


async def verify_checksums(connection: Any, migrations: Sequence[Migration]) -> list[str]:
    """Confere os arquivos já aplicados; preenche o SHA-256 das aplicadas antes da S28-04.

    Devolve as versões preenchidas agora. Levanta ``ValueError`` se um arquivo aplicado mudou.
    """
    await applied_versions(connection)
    stored = {
        str(row["version"]): row["checksum"]
        for row in await connection.fetch(
            "SELECT version, checksum FROM ipc_meta.schema_migrations"
        )
    }
    filled = []
    for migration in migrations:
        if migration.version not in stored:
            continue
        checksum = stored[migration.version]
        if checksum is None:
            await connection.execute(
                "UPDATE ipc_meta.schema_migrations SET checksum = $2 WHERE version = $1",
                migration.version,
                migration.checksum,
            )
            filled.append(migration.version)
        elif checksum != migration.checksum:
            raise ValueError(
                f"A migração {migration.version} ({migration.up.name}) mudou depois de aplicada. "
                "Desfaça a edição e corrija com uma migração nova."
            )
    return filled


async def migrate_up(connection: Any, migrations: Sequence[Migration]) -> list[str]:
    await verify_checksums(connection, migrations)
    done = set(await applied_versions(connection))
    applied = []
    for migration in migrations:
        if migration.version in done:
            continue
        async with connection.transaction():
            await connection.execute(migration.up.read_text(encoding="utf-8"))
            await connection.execute(
                "INSERT INTO ipc_meta.schema_migrations (version, name, checksum) "
                "VALUES ($1, $2, $3)",
                migration.version,
                migration.name,
                migration.checksum,
            )
        applied.append(migration.version)
    return applied


async def migrate_down(connection: Any, migrations: Sequence[Migration], target: str) -> list[str]:
    """Reverte, da mais nova para a mais antiga, as versões acima de ``target``."""
    by_version = {migration.version: migration for migration in migrations}
    reverted = []
    for version in reversed(await applied_versions(connection)):
        if version <= target:
            break
        migration = by_version.get(version)
        if migration is None:
            raise ValueError(f"A versão {version} está aplicada, mas não existe na pasta.")
        async with connection.transaction():
            await connection.execute(migration.down.read_text(encoding="utf-8"))
            await connection.execute(
                "DELETE FROM ipc_meta.schema_migrations WHERE version = $1", version
            )
        reverted.append(version)
    return reverted


async def ensure_login_role(connection: Any, role: str, password: str) -> None:
    """Cria ou atualiza o usuário da API e o põe em ``ipc_app``; o Postgres faz as aspas."""
    if not _ROLE.match(role):
        raise ValueError(f"Nome de usuário inválido: {role!r}.")
    if not password:
        raise ValueError("Defina IPC_DB_LOGIN_PASSWORD para criar o usuário da API.")
    exists = await connection.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role)
    verb = "ALTER" if exists else "CREATE"
    statement = await connection.fetchval(
        f"SELECT format('{verb} ROLE %I LOGIN PASSWORD %L', $1::text, $2::text)", role, password
    )
    await connection.execute(statement)
    grant = await connection.fetchval("SELECT format('GRANT ipc_app TO %I', $1::text)", role)
    await connection.execute(grant)


async def mark_check_account(connection: Any, login: str) -> bool:
    """Marca a conta de verificação pelo e-mail ou pelo nome e desmarca as outras (S28-02).

    Devolve ``False``, sem mudar nada, se nenhuma conta tem esse login.
    """
    target = await connection.fetchval(
        "SELECT a.id FROM app.account a WHERE lower(a.name) = lower(btrim($1)) "
        "OR a.id = (SELECT account_id FROM app.account_email WHERE email = lower(btrim($1)))",
        login,
    )
    if target is None:
        return False
    await connection.execute(
        "UPDATE app.account SET check_account = (id = $1) WHERE check_account OR id = $1", target
    )
    return True


async def run(
    command: str, *, url: str, directory: Path, target: str, login_role: str | None
) -> str:
    migrations = discover(directory)
    connection = await asyncpg.connect(url)
    try:
        await connection.execute("SELECT pg_advisory_lock($1)", _LOCK_KEY)
        try:
            if command == "up":
                changed = await migrate_up(connection, migrations)
                if login_role is not None:
                    await ensure_login_role(
                        connection, login_role, os.environ.get("IPC_DB_LOGIN_PASSWORD", "")
                    )
                result = f"aplicadas: {', '.join(changed) or 'nenhuma'}"
                check_login = os.environ.get("IPC_CHECK_ACCOUNT_LOGIN", "").strip()
                if check_login:
                    found = await mark_check_account(connection, check_login)
                    result += "; conta de verificação: " + (
                        "marcada" if found else "não encontrada"
                    )
                return result
            if command == "down":
                changed = await migrate_down(connection, migrations, target)
                return f"revertidas: {', '.join(changed) or 'nenhuma'}"
            await verify_checksums(connection, migrations)
            versions = await applied_versions(connection)
            pending = [m.version for m in migrations if m.version not in set(versions)]
            return (
                f"aplicadas: {', '.join(versions) or 'nenhuma'}; "
                f"pendentes: {', '.join(pending) or 'nenhuma'}"
            )
        finally:
            await connection.execute("SELECT pg_advisory_unlock($1)", _LOCK_KEY)
    finally:
        await connection.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrações do banco do IP-Checker.")
    parser.add_argument("command", choices=["up", "down", "status"])
    parser.add_argument("--to", default="0000", help="down: versão que fica (padrão: nenhuma)")
    parser.add_argument("--login-role", help="up: cria ou atualiza o usuário da API em ipc_app")
    args = parser.parse_args(argv)
    url = os.environ.get("IPC_DATABASE_ADMIN_URL", "")
    if not url:
        print(
            "Defina IPC_DATABASE_ADMIN_URL (credencial de administrador do banco).", file=sys.stderr
        )
        return 2
    directory = Path(os.environ.get("IPC_MIGRATIONS_DIR", DEFAULT_DIR))
    print(
        asyncio.run(
            run(
                args.command,
                url=url,
                directory=directory,
                target=args.to,
                login_role=args.login_role,
            )
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

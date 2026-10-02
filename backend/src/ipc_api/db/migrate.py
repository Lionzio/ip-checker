"""Migrações SQL do banco (S13-01): ``database/migrations/NNNN_nome.up.sql`` e ``.down.sql``.

Roda com a credencial de administrador, nunca com a da API::

    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate up
    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate down --to 0
    IPC_DATABASE_ADMIN_URL=postgresql://... python -m ipc_api.db.migrate status

Cada migração roda numa transação, e um *advisory lock* impede duas execuções ao mesmo tempo.
Com ``--login-role NOME``, o comando também cria (ou atualiza) o usuário com que a API entra no
banco, com a senha de ``IPC_DB_LOGIN_PASSWORD``, e o torna membro de ``ipc_app``: é assim que o
Compose prepara o banco local. Nenhuma senha vai para a saída.
"""

from __future__ import annotations

import argparse
import asyncio
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

_TRACKING = """
CREATE TABLE IF NOT EXISTS public.ipc_schema_migrations (
  version text PRIMARY KEY,
  name text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    name: str
    up: Path
    down: Path


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
    rows = await connection.fetch("SELECT version FROM public.ipc_schema_migrations ORDER BY 1")
    return [str(row["version"]) for row in rows]


async def migrate_up(connection: Any, migrations: Sequence[Migration]) -> list[str]:
    done = set(await applied_versions(connection))
    applied = []
    for migration in migrations:
        if migration.version in done:
            continue
        async with connection.transaction():
            await connection.execute(migration.up.read_text(encoding="utf-8"))
            await connection.execute(
                "INSERT INTO public.ipc_schema_migrations (version, name) VALUES ($1, $2)",
                migration.version,
                migration.name,
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
                "DELETE FROM public.ipc_schema_migrations WHERE version = $1", version
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
                return f"aplicadas: {', '.join(changed) or 'nenhuma'}"
            if command == "down":
                changed = await migrate_down(connection, migrations, target)
                return f"revertidas: {', '.join(changed) or 'nenhuma'}"
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

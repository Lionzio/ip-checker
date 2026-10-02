"""PostgreSQL nos testes (S13-01): só roda com ``IPC_TEST_DATABASE_URL`` (credencial de admin).

Na CI, um serviço ``postgres`` do job do backend. Localmente, um contêiner descartável, sem
conflito com outros projetos::

    docker run -d --name ipc-test-db -e POSTGRES_PASSWORD=... -e POSTGRES_DB=ipc_test \\
        -p 127.0.0.1:55432:5432 postgres:17-alpine
    IPC_TEST_DATABASE_URL=postgresql://postgres:...@127.0.0.1:55432/ipc_test uv run pytest

Cada teste recomeça do zero: as migrações são revertidas e aplicadas de novo.
"""

from __future__ import annotations

import os
from typing import Any

import asyncpg
import pytest

from ipc_api.db.migrate import DEFAULT_DIR, discover, migrate_down, migrate_up

DATABASE_URL = os.environ.get("IPC_TEST_DATABASE_URL", "")

requires_database = pytest.mark.skipif(
    not DATABASE_URL, reason="defina IPC_TEST_DATABASE_URL para rodar contra o PostgreSQL"
)


async def fresh_schema() -> None:
    """Reverte e reaplica todas as migrações: o banco de teste volta ao estado inicial."""
    connection: Any = await asyncpg.connect(DATABASE_URL)
    try:
        migrations = discover(DEFAULT_DIR)
        await migrate_down(connection, migrations, "0000")
        await migrate_up(connection, migrations)
    finally:
        await connection.close()

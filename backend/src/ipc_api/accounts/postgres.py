"""``AccountStore`` no PostgreSQL (esquema ``app``, 5.2.5), pelo usuário da API em ``ipc_app``.

O ``asyncpg`` não publica tipos; o uso dele fica restrito a este módulo e ao ``db/migrate.py``.
Toda falha de conexão ou do servidor vira ``StoreUnavailable``, que a API transforma em 503.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    DeveloperSeed,
    Role,
    SessionRecord,
    SignupMethod,
    Status,
    StoreUnavailable,
    Treatment,
    normalize_email,
)

_SELECT_ACCOUNT = """
SELECT
    a.id, a.name, a.course, a.treatment::text AS treatment, a.role::text AS role,
    a.status::text AS status, a.ja_foi_monitor_chefe, a.password_hash, a.signup_method,
    a.created_at,
    array(
        SELECT e.email FROM app.account_email e
        WHERE e.account_id = a.id ORDER BY e.is_primary DESC, e.email
    ) AS emails
FROM app.account a
"""
# Só constantes deste módulo são concatenadas; os valores vão sempre como parâmetros ($1).
_BY_EMAIL = _SELECT_ACCOUNT + (  # noqa: S608
    "WHERE a.id = (SELECT account_id FROM app.account_email WHERE email = $1)"
)
_BY_NAME = _SELECT_ACCOUNT + "WHERE lower(a.name) = lower($1)"
_BY_ID = _SELECT_ACCOUNT + "WHERE a.id = $1"
_SESSION = """
SELECT s.account_id, s.created_at, s.last_seen_at, s.expires_at
FROM app.session s WHERE s.token_hash = $1
"""


def _account(row: Any) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        course=row["course"],
        treatment=Treatment(row["treatment"]),
        role=Role(row["role"]) if row["role"] is not None else None,
        status=Status(row["status"]),
        ja_foi_monitor_chefe=row["ja_foi_monitor_chefe"],
        password_hash=row["password_hash"],
        signup_method=SignupMethod(row["signup_method"]),
        emails=tuple(row["emails"]),
        created_at=row["created_at"],
    )


@asynccontextmanager
async def _guard() -> AsyncIterator[None]:
    try:
        yield
    except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        raise StoreUnavailable(type(exc).__name__) from exc


class PostgresAccountStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, dsn: str) -> PostgresAccountStore:
        # Poucas conexões: uma instância da API (ADR-03) e consultas curtas.
        async with _guard():
            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=5)
        return cls(pool)

    async def ping(self) -> None:
        async with _guard():
            await self._pool.fetchval("SELECT 1")

    async def find_by_login(self, login: str) -> Account | None:
        text = login.strip()
        async with _guard():
            if "@" in text:
                row = await self._pool.fetchrow(_BY_EMAIL, normalize_email(text))
            else:
                row = await self._pool.fetchrow(_BY_NAME, text)
        return _account(row) if row is not None else None

    async def get_account(self, account_id: UUID) -> Account | None:
        async with _guard():
            row = await self._pool.fetchrow(_BY_ID, account_id)
        return _account(row) if row is not None else None

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        async with _guard(), self._pool.acquire() as connection, connection.transaction():
            owners = await connection.fetch(
                "SELECT DISTINCT account_id FROM app.account_email WHERE email = ANY($1::text[])",
                list(seed.emails),
            )
            if len(owners) > 1:
                raise AccountConflict("os e-mails do desenvolvedor estão em contas diferentes")
            if owners:
                account_id = owners[0]["account_id"]
                await connection.execute(
                    "UPDATE app.account SET role = 'desenvolvedor', status = 'ativo' WHERE id = $1",
                    account_id,
                )
            else:
                try:
                    account_id = await connection.fetchval(
                        "INSERT INTO app.account (name, course, treatment, role, status, "
                        "password_hash, signup_method, created_at) VALUES ($1, $2, 'masculino', "
                        "'desenvolvedor', 'ativo', $3, 'seed', $4) RETURNING id",
                        seed.name,
                        seed.course,
                        seed.password_hash,
                        now,
                    )
                except asyncpg.UniqueViolationError:
                    raise AccountConflict(
                        "já existe uma conta com o nome do desenvolvedor"
                    ) from None
            for index, email in enumerate(seed.emails):
                await connection.execute(
                    "INSERT INTO app.account_email (email, account_id, is_primary, verified_at) "
                    "VALUES ($1, $2, $3, $4) ON CONFLICT (email) DO NOTHING",
                    email,
                    account_id,
                    index == 0 and not owners,
                    now,
                )
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def create_session(
        self, token_hash: bytes, account_id: UUID, now: datetime, expires_at: datetime
    ) -> None:
        async with _guard():
            await self._pool.execute(
                "INSERT INTO app.session (token_hash, account_id, created_at, last_seen_at, "
                "expires_at) VALUES ($1, $2, $3, $3, $4)",
                token_hash,
                account_id,
                now,
                expires_at,
            )

    async def get_session(self, token_hash: bytes) -> SessionRecord | None:
        async with _guard():
            session = await self._pool.fetchrow(_SESSION, token_hash)
            if session is None:
                return None
            row = await self._pool.fetchrow(_BY_ID, session["account_id"])
        if row is None:
            return None
        return SessionRecord(
            account=_account(row),
            created_at=session["created_at"],
            last_seen_at=session["last_seen_at"],
            expires_at=session["expires_at"],
        )

    async def touch_session(self, token_hash: bytes, now: datetime) -> None:
        async with _guard():
            await self._pool.execute(
                "UPDATE app.session SET last_seen_at = $2 WHERE token_hash = $1", token_hash, now
            )

    async def delete_session(self, token_hash: bytes) -> None:
        async with _guard():
            await self._pool.execute("DELETE FROM app.session WHERE token_hash = $1", token_hash)

    async def close(self) -> None:
        await self._pool.close()

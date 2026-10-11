"""``AccountStore`` no PostgreSQL (esquema ``app``, 5.2.5), pelo usuário da API em ``ipc_app``.

O ``asyncpg`` não publica tipos; o uso dele fica restrito a este módulo e ao ``db/migrate.py``.
Toda falha de conexão ou do servidor vira ``StoreUnavailable``, que a API transforma em 503; o pool
cheio por sobrecarga vira ``StoreBusy``, que a API responde como ``OVERLOADED`` (S35-08).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Collection
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any
from uuid import UUID

import asyncpg

from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    DeveloperSeed,
    HousekeepingCounts,
    ManagementRecord,
    NewAccount,
    NewGoogleAccount,
    QuotaExceeded,
    Role,
    SessionRecord,
    SignupMethod,
    Status,
    StoreBusy,
    StoreUnavailable,
    Treatment,
    normalize_email,
)

_SELECT_ACCOUNT = """
SELECT
    a.id, a.name, a.course, a.treatment::text AS treatment, a.role::text AS role,
    a.status::text AS status, a.ja_foi_monitor_chefe, a.password_hash, a.signup_method,
    a.created_at, a.google_sub, a.check_account,
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
_BY_GOOGLE_SUB = _SELECT_ACCOUNT + "WHERE a.google_sub = $1"
_BY_STATUS = _SELECT_ACCOUNT + (
    "WHERE a.status = ANY($1::app.status[]) ORDER BY a.created_at, lower(a.name)"
)
_TRANSITION = """
UPDATE app.account SET
    status = $2::app.status,
    role = $3::app.role,
    decided_by = CASE WHEN $4::uuid IS NULL THEN decided_by ELSE $4::uuid END,
    decided_at = CASE WHEN $4::uuid IS NULL THEN decided_at ELSE $5 END,
    last_activity_at = $5
WHERE id = $1 AND status = $6::app.status AND role IS NOT DISTINCT FROM $7::app.role
RETURNING id
"""
_LOG_INSERT = """
INSERT INTO app.management_log (
    at, action, actor_id, actor_name, actor_role, target_id, target_name,
    from_status, to_status, from_role, to_role
) VALUES ($1, $2, $3, $4, $5::app.role, $6, $7, $8::app.status, $9::app.status,
          $10::app.role, $11::app.role)
"""
_LOG_SELECT = """
SELECT at, action, actor_id, actor_name, actor_role::text AS actor_role, target_id, target_name,
       from_status::text AS from_status, to_status::text AS to_status,
       from_role::text AS from_role, to_role::text AS to_role
FROM app.management_log ORDER BY at DESC, id DESC LIMIT $1
"""
# A sessão e a conta numa consulta só (S25-04): cada requisição autenticada faz uma ida ao banco.
_SESSION = (
    _SELECT_ACCOUNT.replace(
        "FROM app.account a",
        "FROM app.session s JOIN app.account a ON a.id = s.account_id",
    ).replace(
        "SELECT\n",
        "SELECT\n    s.created_at AS session_created_at, s.last_seen_at, s.expires_at,\n",
    )
    + "WHERE s.token_hash = $1"
)


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
        google_sub=row["google_sub"],
        check_account=row["check_account"],
    )


def _role(value: str | None) -> Role | None:
    return Role(value) if value is not None else None


def _value(role: Role | None) -> str | None:
    return role.value if role is not None else None


def _record(row: Any) -> ManagementRecord:
    return ManagementRecord(
        at=row["at"],
        action=row["action"],
        actor_id=row["actor_id"],
        actor_name=row["actor_name"],
        actor_role=_role(row["actor_role"]),
        target_id=row["target_id"],
        target_name=row["target_name"],
        from_status=Status(row["from_status"]),
        to_status=Status(row["to_status"]),
        from_role=_role(row["from_role"]),
        to_role=_role(row["to_role"]),
    )


def _conflict_field(exc: asyncpg.UniqueViolationError) -> str:
    constraint = str(exc.constraint_name)
    if "account_email" in constraint:
        return "email"
    return "google" if "google_sub" in constraint else "nome"


#: Prazo de uma operação no banco, incluindo a espera por uma conexão livre do pool (S25-04):
#: com o banco lento ou o pool esgotado, a requisição recebe DATABASE_UNAVAILABLE em vez de esperar.
DB_DEADLINE_S = 5.0
#: Chave da trava da cota de feedbacks (``pg_advisory_xact_lock``), só desta aplicação.
_QUOTA_LOCK = 0x1C_25_05
#: A limpeza diária pode apagar muitas linhas de uma vez; roda fora das requisições.
HOUSEKEEPING_DEADLINE_S = 60.0


@asynccontextmanager
async def _guard(deadline_s: float = DB_DEADLINE_S) -> AsyncIterator[None]:
    try:
        async with asyncio.timeout(deadline_s):
            yield
    except TimeoutError:
        raise StoreUnavailable("TimeoutError") from None
    except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        raise StoreUnavailable(type(exc).__name__) from exc


#: Conexões do pool (``create_pool(max_size=...)``).
POOL_SIZE = 5
#: Operações no banco ao mesmo tempo, contando as que esperam uma conexão do pool (S35-08). Acima
#: disso, a API recusa na hora com ``OVERLOADED``, como a admissão do analisador, em vez de esperar
#: o prazo de 5 s e responder ``DATABASE_UNAVAILABLE`` (ADR-03, "Pico no plano gratuito").
MAX_PENDING = 20


class PostgresAccountStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self._pending = 0

    @asynccontextmanager
    async def _op(self, deadline_s: float = DB_DEADLINE_S) -> AsyncIterator[None]:
        """Uma operação no banco, com o prazo do ``_guard`` e a recusa rápida do pool cheio.

        O prazo estourado com mais operações que conexões é a espera pelo pool: sobrecarga
        (``StoreBusy``), não banco fora do ar.
        """
        if self._pending >= MAX_PENDING:
            raise StoreBusy("pool de conexões cheio")
        self._pending += 1
        crowded = self._pending > POOL_SIZE
        try:
            async with _guard(deadline_s):
                yield
        except StoreUnavailable as exc:
            if crowded and exc.args == ("TimeoutError",):
                raise StoreBusy("prazo estourado esperando uma conexão do pool") from exc
            raise
        finally:
            self._pending -= 1

    @classmethod
    async def connect(cls, dsn: str) -> PostgresAccountStore:
        # Poucas conexões: uma instância da API (ADR-03) e consultas curtas.
        async with _guard():
            pool = await asyncpg.create_pool(
                dsn, min_size=1, max_size=POOL_SIZE, command_timeout=5, timeout=5
            )
        return cls(pool)

    async def ping(self) -> None:
        async with self._op():
            await self._pool.fetchval("SELECT 1")

    async def find_by_login(self, login: str) -> Account | None:
        text = login.strip()
        async with self._op():
            if "@" in text:
                row = await self._pool.fetchrow(_BY_EMAIL, normalize_email(text))
            else:
                row = await self._pool.fetchrow(_BY_NAME, text)
        return _account(row) if row is not None else None

    async def get_account(self, account_id: UUID) -> Account | None:
        async with self._op():
            row = await self._pool.fetchrow(_BY_ID, account_id)
        return _account(row) if row is not None else None

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            owners = await connection.fetch(
                "SELECT DISTINCT account_id FROM app.account_email WHERE email = ANY($1::text[])",
                list(seed.emails),
            )
            if len(owners) > 1:
                raise AccountConflict(
                    "os e-mails do desenvolvedor estão em contas diferentes", "email"
                )
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
                        "password_hash, signup_method, created_at, last_activity_at) VALUES "
                        "($1, $2, 'masculino', 'desenvolvedor', 'ativo', $3, 'seed', $4, $4) "
                        "RETURNING id",
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

    async def register(self, new: NewAccount, now: datetime) -> Account:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            existing = await connection.fetchrow(
                "SELECT a.id, a.status::text AS status FROM app.account_email e "
                "JOIN app.account a ON a.id = e.account_id WHERE e.email = $1 FOR UPDATE OF a",
                new.email,
            )
            if existing is not None and existing["status"] != Status.AGUARDANDO_VERIFICACAO:
                raise AccountConflict("e-mail já cadastrado", "email")
            other = await connection.fetchval(
                "SELECT id FROM app.account WHERE lower(name) = lower($1)", new.name
            )
            if other is not None and (existing is None or other != existing["id"]):
                raise AccountConflict("nome já cadastrado", "nome")
            try:
                if existing is not None:
                    account_id = existing["id"]
                    await connection.execute(
                        "UPDATE app.account SET name = $2, course = $3, treatment = $4, "
                        "password_hash = $5, last_activity_at = $6 WHERE id = $1",
                        account_id,
                        new.name,
                        new.course,
                        new.treatment.value,
                        new.password_hash,
                        now,
                    )
                    await connection.execute(
                        "UPDATE app.email_token SET used_at = $2 "
                        "WHERE account_id = $1 AND used_at IS NULL",
                        account_id,
                        now,
                    )
                else:
                    account_id = await connection.fetchval(
                        "INSERT INTO app.account (name, course, treatment, status, password_hash, "
                        "signup_method, created_at, last_activity_at) VALUES ($1, $2, $3, "
                        "'aguardando_verificacao', $4, 'senha', $5, $5) RETURNING id",
                        new.name,
                        new.course,
                        new.treatment.value,
                        new.password_hash,
                        now,
                    )
                    await connection.execute(
                        "INSERT INTO app.account_email (email, account_id) VALUES ($1, $2)",
                        new.email,
                        account_id,
                    )
            except asyncpg.UniqueViolationError as exc:
                raise AccountConflict(
                    "nome ou e-mail já cadastrado", _conflict_field(exc)
                ) from None
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def find_by_google_sub(self, sub: str) -> Account | None:
        async with self._op():
            row = await self._pool.fetchrow(_BY_GOOGLE_SUB, sub)
        return _account(row) if row is not None else None

    async def link_google(self, account_id: UUID, sub: str) -> Account:
        try:
            async with self._op(), self._pool.acquire() as connection, connection.transaction():
                linked = await connection.fetchval(
                    "UPDATE app.account SET google_sub = $2 WHERE id = $1 "
                    "AND (google_sub IS NULL OR google_sub = $2) RETURNING id",
                    account_id,
                    sub,
                )
                if linked is None:
                    raise AccountConflict("outra conta Google já está ligada", "google")
                row = await connection.fetchrow(_BY_ID, account_id)
        except StoreUnavailable as exc:
            if isinstance(exc.__cause__, asyncpg.UniqueViolationError):
                raise AccountConflict("conta Google já ligada", "google") from None
            raise
        return _account(row)

    async def register_google(self, new: NewGoogleAccount, now: datetime) -> Account:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            existing = await connection.fetchrow(
                "SELECT a.id, a.status::text AS status FROM app.account_email e "
                "JOIN app.account a ON a.id = e.account_id WHERE e.email = $1 FOR UPDATE OF a",
                new.email,
            )
            if existing is not None and existing["status"] != Status.AGUARDANDO_VERIFICACAO:
                raise AccountConflict("e-mail já cadastrado", "email")
            other = await connection.fetchval(
                "SELECT id FROM app.account WHERE lower(name) = lower($1)", new.name
            )
            if other is not None and (existing is None or other != existing["id"]):
                raise AccountConflict("nome já cadastrado", "nome")
            try:
                if existing is not None:
                    # Pré-sequestro (FR-25): quem pediu o cadastro sem confirmar o e-mail perde a
                    # senha e os dados pendentes; o Google provou quem é o dono do e-mail.
                    account_id = existing["id"]
                    await connection.execute(
                        "UPDATE app.account SET name = $2, course = $3, treatment = $4, "
                        "password_hash = NULL, google_sub = $5, signup_method = 'google', "
                        "status = 'aguardando_aprovacao', last_activity_at = $6 WHERE id = $1",
                        account_id,
                        new.name,
                        new.course,
                        new.treatment.value,
                        new.google_sub,
                        now,
                    )
                    await connection.execute(
                        "UPDATE app.email_token SET used_at = $2 "
                        "WHERE account_id = $1 AND used_at IS NULL",
                        account_id,
                        now,
                    )
                    await connection.execute(
                        "UPDATE app.account_email SET verified_at = $2 WHERE email = $1",
                        new.email,
                        now,
                    )
                else:
                    account_id = await connection.fetchval(
                        "INSERT INTO app.account (name, course, treatment, status, google_sub, "
                        "signup_method, created_at, last_activity_at) VALUES ($1, $2, $3, "
                        "'aguardando_aprovacao', $4, 'google', $5, $5) RETURNING id",
                        new.name,
                        new.course,
                        new.treatment.value,
                        new.google_sub,
                        now,
                    )
                    await connection.execute(
                        "INSERT INTO app.account_email (email, account_id, verified_at) "
                        "VALUES ($1, $2, $3)",
                        new.email,
                        account_id,
                        now,
                    )
            except asyncpg.UniqueViolationError as exc:
                raise AccountConflict(
                    "nome, e-mail ou conta Google já cadastrados", _conflict_field(exc)
                ) from None
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def add_email_token(
        self, token_hash: bytes, account_id: UUID, purpose: str, now: datetime, expires_at: datetime
    ) -> None:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            await connection.execute(
                "UPDATE app.email_token SET used_at = $3 "
                "WHERE account_id = $1 AND purpose = $2 AND used_at IS NULL",
                account_id,
                purpose,
                now,
            )
            await connection.execute(
                "INSERT INTO app.email_token (token_hash, account_id, purpose, expires_at) "
                "VALUES ($1, $2, $3, $4)",
                token_hash,
                account_id,
                purpose,
                expires_at,
            )

    async def verify_email(self, token_hash: bytes, now: datetime) -> Account | None:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            # O token é gasto mesmo que a conta já não espere a verificação: uso único.
            account_id = await connection.fetchval(
                "WITH t AS (UPDATE app.email_token SET used_at = $2 WHERE token_hash = $1 "
                "AND purpose = 'verificacao' AND used_at IS NULL AND expires_at > $2 "
                "RETURNING account_id) "
                "UPDATE app.account a SET status = 'aguardando_aprovacao', "
                "last_activity_at = $2 FROM t "
                "WHERE a.id = t.account_id AND a.status = 'aguardando_verificacao' RETURNING a.id",
                token_hash,
                now,
            )
            if account_id is None:
                return None
            await connection.execute(
                "UPDATE app.account_email SET verified_at = $2 WHERE account_id = $1",
                account_id,
                now,
            )
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def reset_password(
        self, token_hash: bytes, password_hash: str, now: datetime
    ) -> Account | None:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            # Uso único: o token é gasto na mesma transação que troca a senha.
            account_id = await connection.fetchval(
                "WITH t AS (UPDATE app.email_token SET used_at = $2 WHERE token_hash = $1 "
                "AND purpose = 'redefinicao' AND used_at IS NULL AND expires_at > $2 "
                "RETURNING account_id) "
                "UPDATE app.account a SET password_hash = $3, last_activity_at = $2 FROM t "
                "WHERE a.id = t.account_id RETURNING a.id",
                token_hash,
                now,
                password_hash,
            )
            if account_id is None:
                return None
            await connection.execute("DELETE FROM app.session WHERE account_id = $1", account_id)
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def update_profile(
        self, account_id: UUID, name: str, course: str, treatment: Treatment
    ) -> Account:
        try:
            async with self._op():
                await self._pool.execute(
                    "UPDATE app.account SET name = $2, course = $3, treatment = $4 WHERE id = $1",
                    account_id,
                    name,
                    course,
                    treatment.value,
                )
                row = await self._pool.fetchrow(_BY_ID, account_id)
        except StoreUnavailable as exc:
            if isinstance(exc.__cause__, asyncpg.UniqueViolationError):
                raise AccountConflict("nome já cadastrado", "nome") from None
            raise
        return _account(row)

    async def set_password(self, account_id: UUID, password_hash: str) -> None:
        async with self._op():
            await self._pool.execute(
                "UPDATE app.account SET password_hash = $2 WHERE id = $1", account_id, password_hash
            )

    async def list_accounts(self, statuses: Collection[Status]) -> list[Account]:
        async with self._op():
            rows = await self._pool.fetch(_BY_STATUS, [s.value for s in statuses])
        return [_account(row) for row in rows]

    async def transition(
        self,
        account_id: UUID,
        *,
        expected: tuple[Status, Role | None],
        status: Status,
        role: Role | None,
        decided_by: UUID | None,
        now: datetime,
        end_sessions: bool,
        record: ManagementRecord | None = None,
    ) -> Account | None:
        old_status, old_role = expected
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            changed = await connection.fetchval(
                _TRANSITION,
                account_id,
                status.value,
                role.value if role is not None else None,
                decided_by,
                now,
                old_status.value,
                old_role.value if old_role is not None else None,
            )
            if changed is None:
                return None
            if end_sessions:
                await connection.execute(
                    "DELETE FROM app.session WHERE account_id = $1", account_id
                )
            if record is not None:
                await connection.fetchval("SELECT app.purge_management_log($1)", now)
                await connection.execute(
                    _LOG_INSERT,
                    record.at,
                    record.action,
                    record.actor_id,
                    record.actor_name,
                    _value(record.actor_role),
                    record.target_id,
                    record.target_name,
                    record.from_status.value,
                    record.to_status.value,
                    _value(record.from_role),
                    _value(record.to_role),
                )
            row = await connection.fetchrow(_BY_ID, account_id)
        return _account(row)

    async def housekeeping(self, now: datetime) -> HousekeepingCounts:
        async with self._op(HOUSEKEEPING_DEADLINE_S):
            row = await self._pool.fetchrow(
                "SELECT * FROM app.housekeeping($1)", now, timeout=HOUSEKEEPING_DEADLINE_S
            )
        return HousekeepingCounts(
            sessions=row["sessions"],
            tokens=row["tokens"],
            unverified=row["unverified"],
            inactive=row["inactive"],
            log=row["log"],
        )

    async def record_adoption(self, account_id: UUID, semester: str, list_number: int) -> None:
        async with self._op():
            await self._pool.execute(
                "INSERT INTO app.list_adoption (account_id, semester, list_number) "
                "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                account_id,
                semester,
                list_number,
            )

    async def take_feedback_quota(
        self, account_id: UUID, day: date, per_account: int, daily_cap: int
    ) -> QuotaExceeded | None:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            # Uma trava da transação: a soma do dia e o gasto não se cruzam entre pedidos.
            await connection.execute("SELECT pg_advisory_xact_lock($1)", _QUOTA_LOCK)
            used = await connection.fetchval(
                "SELECT used FROM app.feedback_quota WHERE day = $1 AND account_id = $2",
                day,
                account_id,
            )
            total = await connection.fetchval(
                "SELECT coalesce(sum(used), 0) FROM app.feedback_quota WHERE day = $1", day
            )
            if (used or 0) >= per_account:
                return "conta"
            if total >= daily_cap:
                return "servidor"
            await connection.execute(
                "INSERT INTO app.feedback_quota (day, account_id, used) VALUES ($1, $2, 1) "
                "ON CONFLICT (day, account_id) DO UPDATE SET used = app.feedback_quota.used + 1",
                day,
                account_id,
            )
        return None

    async def management_log(self, limit: int, now: datetime) -> list[ManagementRecord]:
        async with self._op(), self._pool.acquire() as connection, connection.transaction():
            await connection.fetchval("SELECT app.purge_management_log($1)", now)
            rows = await connection.fetch(_LOG_SELECT, limit)
        return [_record(row) for row in rows]

    async def delete_sessions(self, account_id: UUID, keep: bytes | None = None) -> None:
        async with self._op():
            await self._pool.execute(
                "DELETE FROM app.session WHERE account_id = $1 "
                "AND ($2::bytea IS NULL OR token_hash <> $2)",
                account_id,
                keep,
            )

    async def create_session(
        self, token_hash: bytes, account_id: UUID, now: datetime, expires_at: datetime
    ) -> None:
        async with self._op():
            await self._pool.execute(
                "WITH s AS (INSERT INTO app.session (token_hash, account_id, created_at, "
                "last_seen_at, expires_at) VALUES ($1, $2, $3, $3, $4)) "
                "UPDATE app.account SET last_activity_at = $3 WHERE id = $2",
                token_hash,
                account_id,
                now,
                expires_at,
            )

    async def get_session(self, token_hash: bytes) -> SessionRecord | None:
        async with self._op():
            row = await self._pool.fetchrow(_SESSION, token_hash)
        if row is None:
            return None
        return SessionRecord(
            account=_account(row),
            created_at=row["session_created_at"],
            last_seen_at=row["last_seen_at"],
            expires_at=row["expires_at"],
        )

    async def touch_session(self, token_hash: bytes, now: datetime) -> None:
        async with self._op():
            await self._pool.execute(
                "UPDATE app.session SET last_seen_at = $2 WHERE token_hash = $1", token_hash, now
            )

    async def delete_session(self, token_hash: bytes) -> None:
        async with self._op():
            await self._pool.execute("DELETE FROM app.session WHERE token_hash = $1", token_hash)

    async def close(self) -> None:
        await self._pool.close()

"""Os gabaritos no PostgreSQL (Sprint 51, S51-01; migração ``0009``).

Usa o pool e o prazo do repositório de contas (``PostgresAccountStore.operation``), como o
catálogo. As regras são as de ``answer_keys/store.py``: a mesma bateria de testes roda nas duas.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.answer_keys.models import (
    AuditEntry,
    GabaritoKind,
    GabaritoSource,
    RuleHit,
    StoredGabarito,
    code_sha256,
)
from ipc_api.answer_keys.store import Actor, sort_key

_SELECT = (
    "SELECT g.period, g.question_id, g.kind, g.source, g.code, g.violations, g.created_by, "
    "g.created_at, g.updated_by, g.updated_at, a.name AS updated_by_name "
    "FROM app.gabarito g LEFT JOIN app.account a ON a.id = g.updated_by"
)


def _violations(value: Any) -> tuple[RuleHit, ...]:
    data = json.loads(value) if isinstance(value, str) else value
    return tuple(RuleHit(str(item["rule_id"]), int(item["line"])) for item in data)


def _row(row: Any) -> StoredGabarito:
    return StoredGabarito(
        period=row["period"],
        question_id=row["question_id"],
        kind=row["kind"],
        source=row["source"],
        code=row["code"],
        violations=_violations(row["violations"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
        updated_by_name=row["updated_by_name"],
    )


class PostgresGabaritoStore:
    def __init__(self, accounts: PostgresAccountStore) -> None:
        self._accounts = accounts
        self._pool = accounts.pool

    async def get(self, period: str, question_id: str, kind: GabaritoKind) -> StoredGabarito | None:
        async with self._accounts.operation():
            row = await self._pool.fetchrow(
                f"{_SELECT} WHERE g.period = $1 AND g.question_id = $2 AND g.kind = $3",
                period,
                question_id,
                kind,
            )
        return None if row is None else _row(row)

    async def list_period(self, period: str) -> list[StoredGabarito]:
        async with self._accounts.operation():
            rows = await self._pool.fetch(f"{_SELECT} WHERE g.period = $1", period)
        return sorted((_row(row) for row in rows), key=sort_key)

    async def all(self) -> list[StoredGabarito]:
        async with self._accounts.operation():
            rows = await self._pool.fetch(_SELECT)
        return sorted((_row(row) for row in rows), key=lambda g: (g.period, *sort_key(g)))

    async def save(
        self,
        *,
        period: str,
        question_id: str,
        kind: GabaritoKind,
        source: GabaritoSource,
        code: str,
        violations: Sequence[RuleHit],
        actor: Actor,
        now: datetime,
    ) -> StoredGabarito:
        hits = json.dumps([{"rule_id": v.rule_id, "line": v.line} for v in violations])
        async with (
            self._accounts.operation(),
            self._pool.acquire() as connection,
            connection.transaction(),
        ):
            # O gabarito pertence a um período do catálogo (Sprint 50); o import cria o período.
            await connection.execute(
                "INSERT INTO app.catalog_period (period, first_seen) VALUES ($1, $2) "
                "ON CONFLICT (period) DO NOTHING",
                period,
                now,
            )
            existed = await connection.fetchval(
                "SELECT 1 FROM app.gabarito WHERE period = $1 AND question_id = $2 AND kind = $3",
                period,
                question_id,
                kind,
            )
            await connection.execute(
                "INSERT INTO app.gabarito (id, period, question_id, kind, source, code, "
                "violations, created_by, created_at, updated_by, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $8, $9) "
                "ON CONFLICT (period, question_id, kind) DO UPDATE SET source = EXCLUDED.source, "
                "code = EXCLUDED.code, violations = EXCLUDED.violations, "
                "updated_by = EXCLUDED.updated_by, updated_at = EXCLUDED.updated_at",
                uuid.uuid4(),
                period,
                question_id,
                kind,
                source,
                code,
                hits,
                actor.account_id,
                now,
            )
            await self._log(
                connection,
                period,
                question_id,
                kind,
                "alterar" if existed else "criar",
                actor,
                now,
                code,
            )
            row = await connection.fetchrow(
                f"{_SELECT} WHERE g.period = $1 AND g.question_id = $2 AND g.kind = $3",
                period,
                question_id,
                kind,
            )
        return _row(row)

    async def delete(
        self, period: str, question_id: str, kind: GabaritoKind, actor: Actor, now: datetime
    ) -> bool:
        async with (
            self._accounts.operation(),
            self._pool.acquire() as connection,
            connection.transaction(),
        ):
            code = await connection.fetchval(
                "DELETE FROM app.gabarito WHERE period = $1 AND question_id = $2 AND kind = $3 "
                "RETURNING code",
                period,
                question_id,
                kind,
            )
            if code is None:
                return False
            await self._log(connection, period, question_id, kind, "apagar", actor, now, code)
        return True

    async def audit(self, period: str, question_id: str) -> list[AuditEntry]:
        async with self._accounts.operation():
            rows = await self._pool.fetch(
                "SELECT period, question_id, kind, action, account_id, at, code_sha256 "
                "FROM app.gabarito_audit WHERE period = $1 AND question_id = $2 "
                "ORDER BY at DESC, id DESC",
                period,
                question_id,
            )
        return [
            AuditEntry(
                period=row["period"],
                question_id=row["question_id"],
                kind=row["kind"],
                action=row["action"],
                account_id=row["account_id"],
                at=row["at"],
                code_sha256=row["code_sha256"],
            )
            for row in rows
        ]

    @staticmethod
    async def _log(
        connection: Any,
        period: str,
        question_id: str,
        kind: GabaritoKind,
        action: str,
        actor: Actor,
        now: datetime,
        code: str,
    ) -> None:
        await connection.execute(
            "INSERT INTO app.gabarito_audit "
            "(period, question_id, kind, action, account_id, at, code_sha256) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            period,
            question_id,
            kind,
            action,
            actor.account_id,
            now,
            code_sha256(code),
        )

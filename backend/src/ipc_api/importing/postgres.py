"""O catálogo e os tokens de importação no PostgreSQL (S50-04, S50-05; migração ``0008``).

Usa o pool e o prazo do repositório de contas (``PostgresAccountStore.operation``): a mesma
conexão, o mesmo limite de operações ao mesmo tempo, a mesma recusa rápida com o pool cheio. As
regras são as de ``importing/store.py`` (a mesma bateria de testes roda nas duas).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.importing.hashing import Sample
from ipc_api.importing.models import (
    ClassIn,
    ImportMode,
    ImportToken,
    ListIn,
    ManifestResult,
    QuestionIn,
    QuestionsResult,
    StoredList,
    StoredQuestion,
)
from ipc_api.importing.store import (
    MAX_VERSIONS,
    UnknownListError,
    UnknownRunError,
    list_key,
    manifest_refs,
    merge_lists,
    question_order,
)

_TOKEN_COLUMNS = (
    "id, account_id, token_hash, label, created_at, expires_at, revoked_at, last_used_at"  # noqa: S105
)


def _token(row: Any) -> ImportToken:
    return ImportToken(
        id=row["id"],
        account_id=row["account_id"],
        token_hash=row["token_hash"],
        label=row["label"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        last_used_at=row["last_used_at"],
    )


def _samples_json(samples: Sequence[Sample]) -> str:
    return json.dumps([{"input": s.input, "output": s.output} for s in samples], ensure_ascii=False)


def _samples(value: Any) -> tuple[Sample, ...]:
    data = json.loads(value) if isinstance(value, str) else value
    return tuple(Sample(str(item["input"]), str(item["output"])) for item in data)


class PostgresCatalogStore:
    def __init__(self, accounts: PostgresAccountStore) -> None:
        self._accounts = accounts

    @property
    def _pool(self) -> Any:
        return self._accounts.pool

    # --- tokens -------------------------------------------------------------------------------
    async def add_import_token(self, token: ImportToken) -> None:
        async with self._accounts.operation():
            await self._pool.execute(
                f"INSERT INTO app.import_token ({_TOKEN_COLUMNS}) "  # noqa: S608 - colunas fixas
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                token.id,
                token.account_id,
                token.token_hash,
                token.label,
                token.created_at,
                token.expires_at,
                token.revoked_at,
                token.last_used_at,
            )

    async def list_import_tokens(self, account_id: UUID) -> list[ImportToken]:
        async with self._accounts.operation():
            rows = await self._pool.fetch(
                f"SELECT {_TOKEN_COLUMNS} FROM app.import_token "  # noqa: S608 - colunas fixas
                "WHERE account_id = $1 ORDER BY created_at DESC",
                account_id,
            )
        return [_token(row) for row in rows]

    async def find_import_token(self, token_hash: str) -> ImportToken | None:
        async with self._accounts.operation():
            row = await self._pool.fetchrow(
                f"SELECT {_TOKEN_COLUMNS} FROM app.import_token "  # noqa: S608 - colunas fixas
                "WHERE token_hash = $1",
                token_hash,
            )
        return _token(row) if row is not None else None

    async def revoke_import_token(self, account_id: UUID, token_id: UUID, now: datetime) -> bool:
        async with self._accounts.operation():
            status = await self._pool.execute(
                "UPDATE app.import_token SET revoked_at = $3 "
                "WHERE id = $1 AND account_id = $2 AND revoked_at IS NULL",
                token_id,
                account_id,
                now,
            )
        return bool(status.endswith(" 1"))

    async def touch_import_token(self, token_id: UUID, now: datetime) -> None:
        async with self._accounts.operation():
            await self._pool.execute(
                "UPDATE app.import_token SET last_used_at = $2 WHERE id = $1", token_id, now
            )

    # --- catálogo -----------------------------------------------------------------------------
    async def apply_manifest(
        self,
        *,
        account_id: UUID,
        mode: ImportMode,
        period: str,
        classes: Sequence[ClassIn],
        lists: Sequence[ListIn],
        now: datetime,
    ) -> ManifestResult:
        merged = merge_lists(lists)
        refs = manifest_refs(lists)
        async with (
            self._accounts.operation(),
            self._pool.acquire() as connection,
            connection.transaction(),
        ):
            await connection.execute(
                "INSERT INTO app.catalog_period (period, first_seen) VALUES ($1, $2) "
                "ON CONFLICT (period) DO NOTHING",
                period,
                now,
            )
            class_ids: dict[str, UUID] = {}
            for school_class in classes:
                class_ids[school_class.dikastis_org_id] = await connection.fetchval(
                    "INSERT INTO app.catalog_class "
                    "(id, dikastis_org_id, period, name, course, last_seen) "
                    "VALUES ($1, $2, $3, $4, $5, $6) "
                    "ON CONFLICT (dikastis_org_id) DO UPDATE SET name = EXCLUDED.name, "
                    "course = EXCLUDED.course, last_seen = EXCLUDED.last_seen RETURNING id",
                    uuid.uuid4(),
                    school_class.dikastis_org_id,
                    period,
                    school_class.name,
                    school_class.course,
                    now,
                )
            list_ids: dict[tuple[str, int], UUID] = {}
            for key, merged_list in merged.items():
                list_ids[key] = await connection.fetchval(
                    "INSERT INTO app.catalog_list "
                    "(id, period, kind, number, title, starts_at, ends_at, last_seen) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                    "ON CONFLICT (period, kind, coalesce(number, 0)) DO UPDATE SET "
                    "title = EXCLUDED.title, starts_at = EXCLUDED.starts_at, "
                    "ends_at = EXCLUDED.ends_at, last_seen = EXCLUDED.last_seen, "
                    "missing_since = NULL RETURNING id",
                    uuid.uuid4(),
                    period,
                    merged_list.kind,
                    merged_list.number,
                    merged_list.title,
                    merged_list.starts_at,
                    merged_list.ends_at,
                    now,
                )
            for item in lists:
                class_id = class_ids.get(item.class_org_id)
                if class_id is None:
                    continue
                await connection.execute(
                    "INSERT INTO app.catalog_list_task (dikastis_task_id, list_id, class_id) "
                    "VALUES ($1, $2, $3) ON CONFLICT (dikastis_task_id) DO UPDATE SET "
                    "list_id = EXCLUDED.list_id, class_id = EXCLUDED.class_id",
                    item.dikastis_task_id,
                    list_ids[list_key(item.kind, item.number)],
                    class_id,
                )
            await connection.execute(
                "UPDATE app.catalog_list SET missing_since = $2 WHERE period = $1 "
                "AND missing_since IS NULL AND NOT (id = ANY($3::uuid[]))",
                period,
                now,
                list(list_ids.values()),
            )
            stored = {
                row["question_id"]: row["content_hash"]
                for row in await connection.fetch(
                    "SELECT question_id, content_hash FROM app.catalog_question WHERE period = $1",
                    period,
                )
            }
            need = [
                problem_id
                for question_id, (problem_id, digest, _key) in refs.items()
                if stored.get(question_id) != digest
            ]
            unchanged = len(refs) - len(need)
            missing = sorted(set(stored) - set(refs))
            await connection.execute(
                "UPDATE app.catalog_question SET missing_since = NULL "
                "WHERE period = $1 AND question_id = ANY($2::text[]) AND missing_since IS NOT NULL",
                period,
                list(refs),
            )
            await connection.execute(
                "UPDATE app.catalog_question SET missing_since = $3 "
                "WHERE period = $1 AND question_id = ANY($2::text[]) AND missing_since IS NULL",
                period,
                missing,
                now,
            )
            run_id = uuid.uuid4()
            counts = {
                "unchanged": unchanged,
                "missing": len(missing),
                "lists": len(merged),
                "classes": len(classes),
                "created": 0,
                "updated": 0,
            }
            await connection.execute(
                "INSERT INTO app.import_run (id, account_id, mode, period, started_at, counts) "
                "VALUES ($1, $2, $3, $4, $5, $6::jsonb)",
                run_id,
                account_id,
                mode,
                period,
                now,
                json.dumps(counts),
            )
        return ManifestResult(run_id, tuple(need), unchanged, tuple(missing))

    async def apply_questions(
        self,
        *,
        account_id: UUID,
        run_id: UUID,
        period: str,
        questions: Sequence[QuestionIn],
        now: datetime,
    ) -> QuestionsResult:
        created = updated = unchanged = 0
        async with (
            self._accounts.operation(),
            self._pool.acquire() as connection,
            connection.transaction(),
        ):
            run = await connection.fetchrow(
                "SELECT account_id, period FROM app.import_run WHERE id = $1 FOR UPDATE", run_id
            )
            if run is None or run["account_id"] != account_id or run["period"] != period:
                raise UnknownRunError(str(run_id))
            for item in questions:
                list_id = await connection.fetchval(
                    "SELECT id FROM app.catalog_list WHERE period = $1 AND kind = $2 "
                    "AND coalesce(number, 0) = $3",
                    period,
                    item.list_kind,
                    item.list_number or 0,
                )
                if list_id is None:
                    raise UnknownListError(item.question_id)
                current = await connection.fetchrow(
                    "SELECT * FROM app.catalog_question WHERE period = $1 AND question_id = $2 "
                    "FOR UPDATE",
                    period,
                    item.question_id,
                )
                if current is not None and current["content_hash"] == item.content_hash:
                    unchanged += 1
                    continue
                samples = _samples_json(item.samples)
                if current is None:
                    created += 1
                    await connection.execute(
                        "INSERT INTO app.catalog_question (id, period, question_id, list_id, "
                        "dikastis_problem_id, title, description, input_description, "
                        "output_description, samples, time_limit_ms, content_hash, version, "
                        "first_seen, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, "
                        "$10::jsonb, $11, $12, 1, $13, $13)",
                        uuid.uuid4(),
                        period,
                        item.question_id,
                        list_id,
                        item.dikastis_problem_id,
                        item.title,
                        item.description,
                        item.input_description,
                        item.output_description,
                        samples,
                        item.time_limit_ms,
                        item.content_hash,
                        now,
                    )
                    continue
                updated += 1
                await connection.execute(
                    "INSERT INTO app.catalog_question_version (question_id, version, title, "
                    "description, input_description, output_description, samples, "
                    "content_hash, replaced_at) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)",
                    current["id"],
                    current["version"],
                    current["title"],
                    current["description"],
                    current["input_description"],
                    current["output_description"],
                    json.dumps(_samples_payload(current["samples"]), ensure_ascii=False),
                    current["content_hash"],
                    now,
                )
                await connection.execute(
                    "DELETE FROM app.catalog_question_version WHERE question_id = $1 AND version "
                    "NOT IN (SELECT version FROM app.catalog_question_version "
                    "WHERE question_id = $1 ORDER BY version DESC LIMIT $2)",
                    current["id"],
                    MAX_VERSIONS,
                )
                await connection.execute(
                    "UPDATE app.catalog_question SET list_id = $2, dikastis_problem_id = $3, "
                    "title = $4, description = $5, input_description = $6, "
                    "output_description = $7, samples = $8::jsonb, time_limit_ms = $9, "
                    "content_hash = $10, version = version + 1, updated_at = $11, "
                    "missing_since = NULL WHERE id = $1",
                    current["id"],
                    list_id,
                    item.dikastis_problem_id,
                    item.title,
                    item.description,
                    item.input_description,
                    item.output_description,
                    samples,
                    item.time_limit_ms,
                    item.content_hash,
                    now,
                )
            await connection.execute(
                "UPDATE app.import_run SET finished_at = $2, counts = counts || jsonb_build_object("
                "'created', coalesce((counts->>'created')::int, 0) + $3, "
                "'updated', coalesce((counts->>'updated')::int, 0) + $4, "
                "'unchanged', coalesce((counts->>'unchanged')::int, 0) + $5) WHERE id = $1",
                run_id,
                now,
                created,
                updated,
                unchanged,
            )
        return QuestionsResult(created, updated, unchanged)

    async def catalog(self, period: str) -> tuple[list[StoredList], list[StoredQuestion]]:
        async with self._accounts.operation():
            list_rows = await self._pool.fetch(
                "SELECT l.kind, l.number, l.title, l.starts_at, l.ends_at, l.missing_since, "
                "coalesce(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), '{}') "
                "AS classes FROM app.catalog_list l "
                "LEFT JOIN app.catalog_list_task t ON t.list_id = l.id "
                "LEFT JOIN app.catalog_class c ON c.id = t.class_id "
                "WHERE l.period = $1 GROUP BY l.id ORDER BY l.kind, coalesce(l.number, 0)",
                period,
            )
            question_rows = await self._pool.fetch(
                "SELECT q.*, l.kind AS list_kind, l.number AS list_number "
                "FROM app.catalog_question q JOIN app.catalog_list l ON l.id = q.list_id "
                "WHERE q.period = $1",
                period,
            )
        lists = [
            StoredList(
                kind=row["kind"],
                number=row["number"],
                title=row["title"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
                classes=tuple(sorted(row["classes"])),
                missing_since=row["missing_since"],
            )
            for row in list_rows
        ]
        questions = [
            StoredQuestion(
                question_id=row["question_id"],
                dikastis_problem_id=row["dikastis_problem_id"],
                list_kind=row["list_kind"],
                list_number=row["list_number"],
                title=row["title"],
                description=row["description"],
                input_description=row["input_description"],
                output_description=row["output_description"],
                samples=_samples(row["samples"]),
                time_limit_ms=row["time_limit_ms"],
                content_hash=row["content_hash"],
                version=row["version"],
                first_seen=row["first_seen"],
                updated_at=row["updated_at"],
                missing_since=row["missing_since"],
            )
            for row in question_rows
        ]
        return lists, sorted(questions, key=lambda q: question_order(q.question_id))

    async def periods(self) -> list[str]:
        async with self._accounts.operation():
            rows = await self._pool.fetch(
                "SELECT period FROM app.catalog_period ORDER BY period DESC"
            )
        return [row["period"] for row in rows]


def _samples_payload(value: Any) -> list[dict[str, str]]:
    return [{"input": s.input, "output": s.output} for s in _samples(value)]

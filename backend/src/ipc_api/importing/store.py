"""O repositório do catálogo e dos tokens de importação (S50-04, S50-05): o contrato e a memória.

A implementação no PostgreSQL fica em ``importing/postgres.py``; a de memória serve aos testes e
ao ambiente sem banco. As duas seguem as mesmas regras, conferidas pelos mesmos testes:

- **manifesto:** grava o período, as turmas e as listas (pequenos, vêm inteiros); diz quais
  questões faltam (nova ou com outro hash); marca ``missing_since`` nas questões e listas do
  período que não vieram e limpa a marca das que voltaram; nunca apaga nada;
- **questões:** a nova entra na versão 1; a que mudou guarda a anterior (as 5 mais recentes) e
  sobe de versão; a igual não é tocada.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ipc_api.importing.models import (
    ClassIn,
    ImportMode,
    ImportToken,
    ListIn,
    ListKind,
    ManifestResult,
    QuestionIn,
    QuestionsResult,
    RunCounts,
    StoredList,
    StoredQuestion,
)

#: Versões anteriores de um enunciado guardadas por questão.
MAX_VERSIONS = 5


class UnknownRunError(Exception):
    """A rodada não existe, é de outra conta ou de outro período."""


class UnknownListError(Exception):
    """A questão aponta para uma lista que o manifesto não trouxe."""


class CatalogStore(Protocol):
    async def add_import_token(self, token: ImportToken) -> None: ...

    async def list_import_tokens(self, account_id: UUID) -> list[ImportToken]: ...

    async def find_import_token(self, token_hash: str) -> ImportToken | None: ...

    async def revoke_import_token(
        self, account_id: UUID, token_id: UUID, now: datetime
    ) -> bool: ...

    async def touch_import_token(self, token_id: UUID, now: datetime) -> None: ...

    async def apply_manifest(
        self,
        *,
        account_id: UUID,
        mode: ImportMode,
        period: str,
        classes: Sequence[ClassIn],
        lists: Sequence[ListIn],
        now: datetime,
    ) -> ManifestResult: ...

    async def apply_questions(
        self,
        *,
        account_id: UUID,
        run_id: UUID,
        period: str,
        questions: Sequence[QuestionIn],
        now: datetime,
    ) -> QuestionsResult: ...

    async def catalog(self, period: str) -> tuple[list[StoredList], list[StoredQuestion]]: ...

    async def periods(self) -> list[str]: ...

    async def last_sync(self, period: str) -> datetime | None: ...


def list_key(kind: ListKind, number: int | None) -> tuple[str, int]:
    return kind, number or 0


def merge_lists(lists: Sequence[ListIn]) -> dict[tuple[str, int], ListIn]:
    """A mesma lista vista em várias turmas vira uma: a primeira ocorrência dá título e datas."""
    merged: dict[tuple[str, int], ListIn] = {}
    for item in lists:
        merged.setdefault(list_key(item.kind, item.number), item)
    return merged


def manifest_refs(lists: Sequence[ListIn]) -> dict[str, tuple[str, str, tuple[str, int]]]:
    """``question_id`` → (problema, hash, lista); a primeira ocorrência vale."""
    refs: dict[str, tuple[str, str, tuple[str, int]]] = {}
    for item in lists:
        for ref in item.questions:
            refs.setdefault(
                ref.question_id,
                (ref.dikastis_problem_id, ref.content_hash, list_key(item.kind, item.number)),
            )
    return refs


@dataclass(slots=True)
class _Run:
    account_id: UUID
    period: str
    mode: ImportMode
    started_at: datetime
    counts: RunCounts
    finished_at: datetime | None = None


@dataclass(slots=True)
class _MemoryList:
    kind: ListKind
    number: int | None
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    classes: set[str] = field(default_factory=set)
    missing_since: datetime | None = None


@dataclass(slots=True)
class MemoryCatalogStore:
    tokens: dict[UUID, ImportToken] = field(default_factory=dict)
    lists: dict[tuple[str, tuple[str, int]], _MemoryList] = field(default_factory=dict)
    questions: dict[tuple[str, str], StoredQuestion] = field(default_factory=dict)
    versions: dict[tuple[str, str], list[StoredQuestion]] = field(default_factory=dict)
    runs: dict[UUID, _Run] = field(default_factory=dict)
    known_periods: dict[str, datetime] = field(default_factory=dict)
    classes: dict[str, ClassIn] = field(default_factory=dict)

    # --- tokens -------------------------------------------------------------------------------
    async def add_import_token(self, token: ImportToken) -> None:
        self.tokens[token.id] = token

    async def list_import_tokens(self, account_id: UUID) -> list[ImportToken]:
        found = [t for t in self.tokens.values() if t.account_id == account_id]
        return sorted(found, key=lambda t: t.created_at, reverse=True)

    async def find_import_token(self, token_hash: str) -> ImportToken | None:
        return next((t for t in self.tokens.values() if t.token_hash == token_hash), None)

    async def revoke_import_token(self, account_id: UUID, token_id: UUID, now: datetime) -> bool:
        token = self.tokens.get(token_id)
        if token is None or token.account_id != account_id or token.revoked_at is not None:
            return False
        self.tokens[token_id] = replace(token, revoked_at=now)
        return True

    async def touch_import_token(self, token_id: UUID, now: datetime) -> None:
        token = self.tokens.get(token_id)
        if token is not None:
            self.tokens[token_id] = replace(token, last_used_at=now)

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
        self.known_periods.setdefault(period, now)
        for school_class in classes:
            self.classes[school_class.dikastis_org_id] = school_class
        merged = merge_lists(lists)
        for key, entry in merged.items():
            stored = self.lists.get((period, key))
            if stored is None:
                stored = _MemoryList(
                    entry.kind, entry.number, entry.title, entry.starts_at, entry.ends_at
                )
                self.lists[(period, key)] = stored
            stored.title = entry.title
            stored.starts_at, stored.ends_at = entry.starts_at, entry.ends_at
            stored.missing_since = None
        for item in lists:
            self.lists[(period, list_key(item.kind, item.number))].classes.add(item.class_org_id)
        for (list_period, key), stored in self.lists.items():
            if list_period == period and key not in merged and stored.missing_since is None:
                stored.missing_since = now

        refs = manifest_refs(lists)
        need: list[str] = []
        unchanged = 0
        for question_id, (problem_id, digest, _key) in refs.items():
            current = self.questions.get((period, question_id))
            if current is None or current.content_hash != digest:
                need.append(problem_id)
            else:
                unchanged += 1
                if current.missing_since is not None:
                    self.questions[(period, question_id)] = replace(current, missing_since=None)
        missing: list[str] = []
        for (question_period, question_id), current in list(self.questions.items()):
            if question_period != period or question_id in refs:
                continue
            missing.append(question_id)
            if current.missing_since is None:
                self.questions[(question_period, question_id)] = replace(current, missing_since=now)

        run_id = uuid.uuid4()
        counts = RunCounts(
            unchanged=unchanged, missing=len(missing), lists=len(merged), classes=len(classes)
        )
        self.runs[run_id] = _Run(account_id, period, mode, now, counts)
        return ManifestResult(run_id, tuple(need), unchanged, tuple(sorted(missing)))

    async def apply_questions(
        self,
        *,
        account_id: UUID,
        run_id: UUID,
        period: str,
        questions: Sequence[QuestionIn],
        now: datetime,
    ) -> QuestionsResult:
        run = self.runs.get(run_id)
        if run is None or run.account_id != account_id or run.period != period:
            raise UnknownRunError(str(run_id))
        created = updated = unchanged = 0
        for item in questions:
            if (period, list_key(item.list_kind, item.list_number)) not in self.lists:
                raise UnknownListError(item.question_id)
            key = (period, item.question_id)
            current = self.questions.get(key)
            if current is not None and current.content_hash == item.content_hash:
                unchanged += 1
                continue
            stored = StoredQuestion(
                question_id=item.question_id,
                dikastis_problem_id=item.dikastis_problem_id,
                list_kind=item.list_kind,
                list_number=item.list_number,
                title=item.title,
                description=item.description,
                input_description=item.input_description,
                output_description=item.output_description,
                samples=item.samples,
                time_limit_ms=item.time_limit_ms,
                content_hash=item.content_hash,
                version=1 if current is None else current.version + 1,
                first_seen=now if current is None else current.first_seen,
                updated_at=now,
            )
            if current is None:
                created += 1
            else:
                updated += 1
                history = self.versions.setdefault(key, [])
                history.append(current)
                del history[:-MAX_VERSIONS]
            self.questions[key] = stored
        run.counts.created += created
        run.counts.updated += updated
        run.counts.unchanged += unchanged
        run.finished_at = now
        return QuestionsResult(created, updated, unchanged)

    async def catalog(self, period: str) -> tuple[list[StoredList], list[StoredQuestion]]:
        lists = [
            StoredList(
                kind=item.kind,
                number=item.number,
                title=item.title,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                classes=tuple(
                    sorted(self.classes[c].name for c in item.classes if c in self.classes)
                ),
                missing_since=item.missing_since,
            )
            for (list_period, _key), item in sorted(self.lists.items(), key=lambda kv: kv[0][1])
            if list_period == period
        ]
        questions = [q for (p, _q), q in self.questions.items() if p == period]
        return lists, sorted(questions, key=lambda q: question_order(q.question_id))

    async def periods(self) -> list[str]:
        return sorted(self.known_periods, reverse=True)

    async def last_sync(self, period: str) -> datetime | None:
        """Quando foi a última rodada (o manifesto) do período."""
        return max((r.started_at for r in self.runs.values() if r.period == period), default=None)


def question_order(question_id: str) -> tuple[str, int, int]:
    """``L2-Q10`` depois de ``L2-Q9``; as provas depois das listas."""
    kind, rest = question_id[0], question_id[1:]
    number, question = rest.split("-Q")
    return ("1" if kind == "L" else "2"), int(number), int(question)

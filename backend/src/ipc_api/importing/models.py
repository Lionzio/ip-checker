"""Os dados do catálogo e do token de importação, sem dependência de banco (S50-04, S50-05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from ipc_api.importing.hashing import Sample

ListKind = Literal["treino", "lista", "prova"]
Course = Literal["SI", "EC", "CC/IA", "CC", "outro"]
ImportMode = Literal["manual", "semi"]


@dataclass(frozen=True, slots=True)
class ImportToken:
    id: UUID
    account_id: UUID
    token_hash: str
    label: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None

    def active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at


@dataclass(frozen=True, slots=True)
class ClassIn:
    dikastis_org_id: str
    name: str
    course: Course


@dataclass(frozen=True, slots=True)
class QuestionRef:
    """Uma questão no manifesto: o que a extensão viu, sem o enunciado."""

    dikastis_problem_id: str
    question_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class ListIn:
    """Uma lista vista numa turma. A mesma lista (período, tipo, número) vem de várias turmas."""

    dikastis_task_id: str
    class_org_id: str
    kind: ListKind
    number: int | None
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    questions: tuple[QuestionRef, ...]


@dataclass(frozen=True, slots=True)
class QuestionIn:
    question_id: str
    dikastis_problem_id: str
    list_kind: ListKind
    list_number: int | None
    title: str
    description: str
    input_description: str
    output_description: str
    samples: tuple[Sample, ...]
    time_limit_ms: int | None
    content_hash: str


@dataclass(frozen=True, slots=True)
class StoredQuestion:
    question_id: str
    dikastis_problem_id: str
    list_kind: ListKind
    list_number: int | None
    title: str
    description: str
    input_description: str
    output_description: str
    samples: tuple[Sample, ...]
    time_limit_ms: int | None
    content_hash: str
    version: int
    first_seen: datetime
    updated_at: datetime
    missing_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class StoredList:
    kind: ListKind
    number: int | None
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    classes: tuple[str, ...]
    missing_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class ManifestResult:
    run_id: UUID
    need: tuple[str, ...]
    unchanged: int
    missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuestionsResult:
    created: int
    updated: int
    unchanged: int


@dataclass(slots=True)
class RunCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    missing: int = 0
    lists: int = 0
    classes: int = 0
    extra: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "missing": self.missing,
            "lists": self.lists,
            "classes": self.classes,
            **self.extra,
        }

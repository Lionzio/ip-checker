"""O repositório dos gabaritos (Sprint 51, S51-01): o contrato e a versão em memória.

A versão do PostgreSQL fica em ``answer_keys/postgres.py``; as duas passam pelos mesmos testes
(``test_answer_key_store.py``). Regras: um gabarito por (período, questão, tipo); salvar de novo
reescreve; cada criação, alteração e remoção entra na auditoria, só com o SHA-256 do código.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ipc_api.answer_keys.models import (
    GABARITO_KINDS,
    AuditEntry,
    GabaritoKind,
    GabaritoSource,
    RuleHit,
    StoredGabarito,
    code_sha256,
)

Key = tuple[str, str, GabaritoKind]


@dataclass(frozen=True, slots=True)
class Actor:
    """Quem salvou: a conta, ou ``None`` num import feito pelo autor no terminal."""

    account_id: UUID | None
    name: str | None


class GabaritoStore(Protocol):
    async def get(
        self, period: str, question_id: str, kind: GabaritoKind
    ) -> StoredGabarito | None: ...

    async def list_period(self, period: str) -> list[StoredGabarito]: ...

    async def all(self) -> list[StoredGabarito]: ...

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
    ) -> StoredGabarito: ...

    async def delete(
        self, period: str, question_id: str, kind: GabaritoKind, actor: Actor, now: datetime
    ) -> bool: ...

    async def audit(self, period: str, question_id: str) -> list[AuditEntry]: ...


def sort_key(item: StoredGabarito) -> tuple[int, int, int]:
    """L2-Q10 depois de L2-Q9; o Notion antes do IP CC."""
    number, question = item.question_id[1:].split("-Q")
    return int(number), int(question), GABARITO_KINDS.index(item.kind)


@dataclass(slots=True)
class MemoryGabaritoStore:
    items: dict[Key, StoredGabarito] = field(default_factory=dict)
    entries: list[AuditEntry] = field(default_factory=list)

    async def get(self, period: str, question_id: str, kind: GabaritoKind) -> StoredGabarito | None:
        return self.items.get((period, question_id, kind))

    async def list_period(self, period: str) -> list[StoredGabarito]:
        return sorted((g for g in self.items.values() if g.period == period), key=sort_key)

    async def all(self) -> list[StoredGabarito]:
        return sorted(self.items.values(), key=lambda g: (g.period, *sort_key(g)))

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
        key = (period, question_id, kind)
        current = self.items.get(key)
        stored = StoredGabarito(
            period=period,
            question_id=question_id,
            kind=kind,
            source=source,
            code=code,
            violations=tuple(violations),
            created_at=now if current is None else current.created_at,
            created_by=actor.account_id if current is None else current.created_by,
            updated_at=now,
            updated_by=actor.account_id,
            updated_by_name=actor.name,
        )
        self.items[key] = stored
        self._log(stored, "criar" if current is None else "alterar", actor, now)
        return stored

    async def delete(
        self, period: str, question_id: str, kind: GabaritoKind, actor: Actor, now: datetime
    ) -> bool:
        current = self.items.pop((period, question_id, kind), None)
        if current is None:
            return False
        self._log(current, "apagar", actor, now)
        return True

    async def audit(self, period: str, question_id: str) -> list[AuditEntry]:
        found = [e for e in self.entries if e.period == period and e.question_id == question_id]
        return sorted(found, key=lambda e: e.at, reverse=True)

    def forget_account(self, account_id: UUID) -> None:
        """Como o ``ON DELETE SET NULL`` do banco: a conta some, o gabarito fica."""
        for key, item in self.items.items():
            self.items[key] = replace(
                item,
                created_by=None if item.created_by == account_id else item.created_by,
                updated_by=None if item.updated_by == account_id else item.updated_by,
                updated_by_name=None if item.updated_by == account_id else item.updated_by_name,
            )

    def _log(self, item: StoredGabarito, action: str, actor: Actor, now: datetime) -> None:
        self.entries.append(
            AuditEntry(
                period=item.period,
                question_id=item.question_id,
                kind=item.kind,
                action=action,  # type: ignore[arg-type]
                account_id=actor.account_id,
                at=now,
                code_sha256=code_sha256(item.code),
            )
        )

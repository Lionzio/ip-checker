"""Os dados dos gabaritos (Sprint 51, S51-01), sem dependência de banco nem de HTTP."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

#: Os dois tipos de gabarito (ADR-17): a página do Notion da monitoria e a solução da conta IP CC
#: UFPE no Dikastis. A ordem é a de preferência quando só um pode valer (o export para o harness).
GabaritoKind = Literal["notion", "ip_cc"]
GABARITO_KINDS: tuple[GabaritoKind, ...] = ("notion", "ip_cc")
KIND_LABELS: dict[GabaritoKind, str] = {"notion": "Notion", "ip_cc": "IP CC"}

#: De onde veio: colado no painel, trazido do Dikastis pela extensão ou importado do repositório
#: antigo de gabaritos (S51-05).
GabaritoSource = Literal["painel", "dikastis", "importado"]

#: Só as questões das listas têm gabarito: ``L<lista>-Q<número>``, Listas 1 a 6.
QUESTION_ID = re.compile(r"^L(?P<list>[1-6])-Q[1-9]\d?$")


def list_number(question_id: str) -> int:
    match = QUESTION_ID.fullmatch(question_id)
    if match is None:
        raise ValueError(f"questão fora do padrão L<lista>-Q<número>: {question_id!r}")
    return int(match.group("list"))


def code_sha256(code: str) -> str:
    """O que a auditoria guarda no lugar do código."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RuleHit:
    """Uma regra acionada pelo gabarito ao salvar: a regra e a linha, nunca um trecho."""

    rule_id: str
    line: int


@dataclass(frozen=True, slots=True)
class StoredGabarito:
    period: str
    question_id: str
    kind: GabaritoKind
    source: GabaritoSource
    #: Fora do ``repr``: um ``print`` ou um log de depuração nunca mostra o gabarito.
    code: str = field(repr=False)
    violations: tuple[RuleHit, ...]
    created_at: datetime
    updated_at: datetime
    updated_by_name: str | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AuditEntry:
    period: str
    question_id: str
    kind: GabaritoKind
    action: Literal["criar", "alterar", "apagar"]
    account_id: UUID | None
    at: datetime
    code_sha256: str

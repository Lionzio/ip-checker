"""O contrato da importação do Dikastis (S50-04, S50-05): o token e o catálogo.

Os limites protegem a API de uma extensão adulterada: textos de até 20 KB, até 10 casos de
exemplo de até 4 KB cada, até 60 questões por pedido (o corpo inteiro fica abaixo dos 128 KB de
sempre). O enunciado é texto; nada dele é interpretado como HTML.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, Strict, StringConstraints

from .common import PeriodId, _Strict

DikastisId = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[\w-]+$")]
CatalogQuestionId = Annotated[str, StringConstraints(pattern=r"^[LP][1-9]\d?-Q[1-9]\d?$")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Title = Annotated[str, StringConstraints(min_length=1, max_length=300)]
LongText = Annotated[str, StringConstraints(max_length=20_000)]
SampleText = Annotated[str, StringConstraints(max_length=4_000)]
ListKind = Literal["treino", "lista", "prova"]
Course = Literal["SI", "EC", "CC/IA", "CC", "outro"]
#: O JSON traz data e UUID como texto; só estes campos aceitam a conversão (o resto é estrito).
JsonDatetime = Annotated[datetime, Strict(False)]
JsonUUID = Annotated[UUID, Strict(False)]


class ImportTokenCreate(_Strict):
    label: Annotated[str, StringConstraints(min_length=1, max_length=60, strip_whitespace=True)] = (
        Field(description='Um nome para lembrar onde o token está, como "Chrome do notebook".')
    )


class ImportTokenInfo(_Strict):
    id: UUID
    label: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    active: bool


class ImportTokenCreated(ImportTokenInfo):
    token: str = Field(description="O token, mostrado só nesta resposta; guarde-o na extensão.")


class ImportTokens(_Strict):
    tokens: list[ImportTokenInfo]


class CatalogClass(_Strict):
    dikastis_org_id: DikastisId
    name: Title
    course: Course


class QuestionReference(_Strict):
    dikastis_problem_id: DikastisId
    question_id: CatalogQuestionId
    content_hash: Hash


class CatalogListIn(_Strict):
    dikastis_task_id: DikastisId
    class_org_id: DikastisId
    kind: ListKind
    number: Annotated[int, Field(ge=1, le=20)] | None
    title: Title
    starts_at: JsonDatetime | None = None
    ends_at: JsonDatetime | None = None
    questions: list[QuestionReference] = Field(max_length=40)


class CatalogManifest(_Strict):
    period: PeriodId
    mode: Literal["manual", "semi"] = "manual"
    classes: list[CatalogClass] = Field(min_length=1, max_length=20)
    lists: list[CatalogListIn] = Field(max_length=200)


class CatalogManifestResult(_Strict):
    run_id: UUID
    need: list[str] = Field(description="Os problemas do Dikastis cujo enunciado falta ou mudou.")
    unchanged: int
    missing: list[str] = Field(description="As questões do período que não vieram desta vez.")


class SampleIn(_Strict):
    input: SampleText
    output: SampleText


class CatalogQuestionIn(_Strict):
    question_id: CatalogQuestionId
    dikastis_problem_id: DikastisId
    list_kind: ListKind
    list_number: Annotated[int, Field(ge=1, le=20)] | None
    title: Title
    description: LongText
    input_description: LongText
    output_description: LongText
    samples: list[SampleIn] = Field(max_length=10)
    time_limit_ms: Annotated[int, Field(ge=0, le=600_000)] | None = None
    content_hash: Hash


class CatalogQuestionsIn(_Strict):
    run_id: JsonUUID
    period: PeriodId
    questions: list[CatalogQuestionIn] = Field(min_length=1, max_length=60)


class CatalogQuestionsResult(_Strict):
    created: int
    updated: int
    unchanged: int

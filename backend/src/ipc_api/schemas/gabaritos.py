"""O contrato dos gabaritos pelo painel (Sprint 51, S51-02; ADR-17).

``GabaritoInfo`` é o que a equipe vê: a existência, a origem, quem salvou, quando e as regras que o
gabarito aciona (regra e linha). O código só vai em ``GabaritoText``, à chefia e ao desenvolvedor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from .common import _Strict

GabaritoKindField = Literal["notion", "ip_cc"]
GabaritoSourceField = Literal["painel", "dikastis", "importado"]
#: Como na verificação: o teto do corpo da requisição (128 KB) protege a API, e ``check_code`` dá o
#: 413 com o tamanho e o limite de 50 KB de uma submissão, ao salvar.
GabaritoCode = Annotated[str, StringConstraints(max_length=120_000)]


class RuleHitInfo(_Strict):
    rule_id: Annotated[str, StringConstraints(pattern=r"^R-\d{2}$")]
    line: Annotated[int, Field(ge=1)]


class GabaritoInfo(_Strict):
    question_id: str
    kind: GabaritoKindField
    source: GabaritoSourceField
    violations: list[RuleHitInfo] = Field(
        description="As regras que o gabarito aciona, conferidas ao salvar; vazio é 'sem violação'."
    )
    updated_at: datetime
    updated_by_name: str | None = Field(
        description="Quem salvou por último; nulo num gabarito importado ou de uma conta apagada."
    )


class GabaritosOfPeriod(_Strict):
    period: str
    items: list[GabaritoInfo]


class GabaritoText(GabaritoInfo):
    code: str = Field(description="O código do gabarito: só para a chefia e o desenvolvedor.")


class GabaritoSave(_Strict):
    code: GabaritoCode

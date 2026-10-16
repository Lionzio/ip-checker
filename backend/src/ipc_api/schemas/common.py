"""Os tipos que os outros módulos do contrato dividem: textos, posições, faixas e o modelo estrito.

Parte do contrato da API (5.2.2), dividido em módulos na S39-02; importe de ``ipc_api.schemas``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Category = Literal["ANULACAO", "PROIBIDO_NA_QUESTAO", "FORA_DA_LISTA", "NAO_CONSTA", "EXIGENCIA"]
Status = Literal["valid", "invalid", "syntax_error"]
Notice = Literal["QUESTION_RULES_NOT_APPLIED", "QUESTION_RULES_NOT_REGISTERED"]
QuestionId = Annotated[str, StringConstraints(pattern=r"^L[1-6]-Q[1-9]\d?$")]
ListNumber = Annotated[int, Field(ge=1, le=6)]
Position = Annotated[int, Field(ge=1, le=1_000_000)]
Message = Annotated[str, StringConstraints(min_length=1, max_length=1_000)]
RulesetVersion = Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]\.\d+$")]

#: Mesmo teto do analyzer: ele nunca devolve mais violações que isso.
MAX_VIOLATIONS = 200


class _Strict(BaseModel):
    # strict: "1" ou true não viram o número 1; o contrato pede inteiros de verdade.
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


BandId = Literal[
    "plagio", "altas_chances", "requer_atencao", "ligeiramente_suspeito", "sem_suspeitas"
]


class SimilarityBand(_Strict):
    id: BandId
    label: str = Field(description="O nome da faixa, sempre escrito junto da cor (NFR-19).")
    minimum: float = Field(description="A faixa começa neste valor, inclusive (FR-29).")


Percent = Annotated[float, Field(ge=0, le=100)]
Line = Annotated[int, Field(ge=1)]


GabaritoStatus = Literal["compared", "no_gabarito", "unavailable", "not_compared"]


class SyntaxErrorInfo(_Strict):
    line: Position
    col: Position
    message: Message

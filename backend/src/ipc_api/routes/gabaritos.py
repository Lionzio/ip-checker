"""As rotas dos gabaritos pelo painel (Sprint 51, S51-02; ADR-17).

- ``GET /api/v1/gabaritos/{p}`` (equipe): por questão e tipo, a origem, quem salvou, quando e as
  regras acionadas; nunca o código.
- ``GET``, ``PUT`` e ``DELETE /api/v1/gabaritos/{p}/{q}/{tipo}`` (chefia e desenvolvedor): o código,
  salvar (conferido pelo analisador) e apagar.

Toda resposta leva ``Cache-Control: no-store``: nem a lista nem o código ficam em cache.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from ipc_api.accounts.models import Account, StoreUnavailable
from ipc_api.answer_keys.deps import get_gabarito_service
from ipc_api.answer_keys.models import StoredGabarito
from ipc_api.answer_keys.service import GabaritoService
from ipc_api.auth.deps import require_active_account
from ipc_api.errors import database_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas.gabaritos import (
    GabaritoInfo,
    GabaritoKindField,
    GabaritoSave,
    GabaritosOfPeriod,
    GabaritoText,
    RuleHitInfo,
)

router = APIRouter(
    prefix="/api/v1/gabaritos",
    tags=["gabaritos"],
    dependencies=[Depends(require_active_account)],
)

Period = Annotated[str, Path(pattern=r"^\d{4}\.[12]$", examples=["2026.2"])]
Question = Annotated[str, Path(pattern=r"^L[1-6]-Q[1-9]\d?$", examples=["L2-Q4"])]
Kind = Annotated[GabaritoKindField, Path(description="notion ou ip_cc")]

UNAUTHENTICATED = "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe."
FORBIDDEN = "FORBIDDEN: só a chefia e o desenvolvedor veem e cadastram o código dos gabaritos."
UNAVAILABLE = "DATABASE_UNAVAILABLE ou ANALYZER_UNAVAILABLE: tente de novo em instantes."
NOT_FOUND = "GABARITO_NOT_FOUND: a questão não tem esse gabarito."


def _info(item: StoredGabarito) -> GabaritoInfo:
    return GabaritoInfo(
        question_id=item.question_id,
        kind=item.kind,
        source=item.source,
        violations=[RuleHitInfo(rule_id=v.rule_id, line=v.line) for v in item.violations],
        updated_at=item.updated_at,
        updated_by_name=item.updated_by_name,
    )


@router.get(
    "/{period}",
    summary="Os gabaritos do período, sem o código: quem salvou, quando e as regras acionadas",
    responses=error_docs(
        {401: UNAUTHENTICATED, 422: "INVALID_INPUT: período fora do formato.", 503: UNAVAILABLE}
    ),
)
async def list_gabaritos(
    period: Period,
    response: Response,
    service: Annotated[GabaritoService, Depends(get_gabarito_service)],
) -> GabaritosOfPeriod:
    response.headers["Cache-Control"] = "no-store"
    try:
        items = await service.list_period(period)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return GabaritosOfPeriod(period=period, items=[_info(item) for item in items])


@router.get(
    "/{period}/{question_id}/{kind}",
    summary="O código de um gabarito (chefia e desenvolvedor)",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            404: NOT_FOUND,
            422: "INVALID_INPUT: período, questão ou tipo fora do formato.",
            503: UNAVAILABLE,
        }
    ),
)
async def read_gabarito(
    period: Period,
    question_id: Question,
    kind: Kind,
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[GabaritoService, Depends(get_gabarito_service)],
) -> GabaritoText:
    response.headers["Cache-Control"] = "no-store"
    try:
        item = await service.read(account, period, question_id, kind)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return GabaritoText(**_info(item).model_dump(), code=item.code)


@router.put(
    "/{period}/{question_id}/{kind}",
    summary="Salva um gabarito: o analisador o confere e as regras acionadas ficam registradas",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: f"{FORBIDDEN} Ou ORIGIN_MISMATCH.",
            413: "PAYLOAD_TOO_LARGE: o gabarito passa dos 50 KB de uma submissão.",
            422: (
                "INVALID_INPUT (vazio, erro de sintaxe, lista fora do período), UNKNOWN_PERIOD "
                "(período não carregado) ou ANALYSIS_LIMIT."
            ),
            503: f"{UNAVAILABLE} Sem o analisador, nada é gravado.",
        }
    ),
)
async def save_gabarito(
    period: Period,
    question_id: Question,
    kind: Kind,
    body: GabaritoSave,
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[GabaritoService, Depends(get_gabarito_service)],
) -> GabaritoInfo:
    response.headers["Cache-Control"] = "no-store"
    try:
        item = await service.save(account, period, question_id, kind, body.code)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return _info(item)


@router.delete(
    "/{period}/{question_id}/{kind}",
    status_code=204,
    summary="Apaga um gabarito (chefia e desenvolvedor); a auditoria registra quem apagou",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: f"{FORBIDDEN} Ou ORIGIN_MISMATCH.",
            404: NOT_FOUND,
            422: "INVALID_INPUT: período, questão ou tipo fora do formato.",
            503: UNAVAILABLE,
        }
    ),
)
async def delete_gabarito(
    period: Period,
    question_id: Question,
    kind: Kind,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[GabaritoService, Depends(get_gabarito_service)],
) -> Response:
    try:
        await service.delete(account, period, question_id, kind)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=204, headers={"Cache-Control": "no-store"})

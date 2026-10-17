"""O catálogo do período na página (S50-06; ADR-19): as listas, as questões e o ``.zip``.

- ``GET /api/v1/periods/{period}/catalog`` (equipe): listas e questões com o estado da etapa 1
  (enunciado, regras e gabarito); nenhum texto de enunciado nem de gabarito.
- ``GET /api/v1/periods/{period}/catalog/statements.zip`` (chefia e desenvolvedor): os enunciados
  das listas, um ``L1-Q1.md`` por questão, para o gerador de referências (Sprint 42).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from ipc_api.accounts.models import Account, StoreUnavailable
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.deps import get_analyzer, get_gabaritos
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, database_unavailable
from ipc_api.gabaritos import Gabaritos
from ipc_api.importing.deps import get_importing
from ipc_api.importing.service import ImportService, can_import
from ipc_api.importing.statements import statements_zip
from ipc_api.periods import loaded_periods
from ipc_api.routes import error_docs
from ipc_api.schemas.importing import CatalogListInfo, CatalogQuestionInfo, CatalogResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/periods/{period}/catalog",
    tags=["importação do Dikastis"],
    dependencies=[Depends(require_active_account)],
)

Period = Annotated[str, Path(pattern=r"^\d{4}\.[12]$", examples=["2026.2"])]
UNAUTHENTICATED = "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe."
INVALID_PERIOD = "INVALID_INPUT: o período não segue o formato AAAA.S."
#: As listas primeiro, depois as provas, e o treino no fim.
_KIND_ORDER = {"lista": 0, "prova": 1, "treino": 2}


@router.get(
    "",
    summary="As listas e questões do período, com o estado da etapa 1 (S50-06)",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            422: INVALID_PERIOD,
            503: "ANALYZER_UNAVAILABLE ou DATABASE_UNAVAILABLE: tente de novo em instantes.",
        }
    ),
)
async def catalog(
    period: Period,
    service: Annotated[ImportService, Depends(get_importing)],
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    gabaritos: Annotated[Gabaritos, Depends(get_gabaritos)],
) -> CatalogResponse:
    try:
        lists, questions = await service.store.catalog(period)
        last_sync = await service.store.last_sync(period)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    try:
        manifest = await analyzer.manifest()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    with_rules = {
        question.id
        for view in loaded_periods(manifest)
        if view.period == period
        for item in view.lists
        for question in item.questions
    }
    by_list: dict[tuple[str, int], list[CatalogQuestionInfo]] = {}
    for question in questions:
        by_list.setdefault((question.list_kind, question.list_number or 0), []).append(
            CatalogQuestionInfo(
                question_id=question.question_id,
                title=question.title,
                version=question.version,
                updated_at=question.updated_at,
                missing_since=question.missing_since,
                has_rules=question.question_id in with_rules,
                has_gabarito=gabaritos.get(period, question.question_id) is not None,
            )
        )
    ordered = sorted(lists, key=lambda item: (_KIND_ORDER[item.kind], item.number or 0))
    return CatalogResponse(
        period=period,
        last_sync=last_sync,
        lists=[
            CatalogListInfo(
                kind=item.kind,
                number=item.number,
                title=item.title,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                classes=list(item.classes),
                missing_since=item.missing_since,
                questions=by_list.get((item.kind, item.number or 0), []),
            )
            for item in ordered
        ],
    )


@router.get(
    "/statements.zip",
    summary="Os enunciados das listas do período em .zip, para o gerador de referências",
    response_class=Response,
    responses={
        200: {
            "description": "Um L1-Q1.md por questão de lista (as provas e o treino ficam de fora).",
            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
        },
        **error_docs(
            {
                401: UNAUTHENTICATED,
                403: "FORBIDDEN: só a chefia e o desenvolvedor baixam os enunciados.",
                422: f"{INVALID_PERIOD} Ou o período ainda não tem enunciados de listas.",
                503: "DATABASE_UNAVAILABLE: o banco não respondeu; tente de novo.",
            }
        ),
    },
)
async def statements(
    period: Period,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> Response:
    if not can_import(account):
        raise ApiError(
            403,
            ErrorCode.FORBIDDEN,
            "Só a chefia (monitor-chefe, professor) e o desenvolvedor baixam os enunciados.",
        )
    try:
        _lists, questions = await service.store.catalog(period)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    content, count = statements_zip(questions)
    if count == 0:
        raise ApiError(
            422,
            ErrorCode.INVALID_INPUT,
            f"O período {period} ainda não tem enunciados de listas: sincronize pela extensão.",
        )
    return Response(
        content,
        media_type="application/zip",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="enunciados-{period}.zip"',
        },
    )

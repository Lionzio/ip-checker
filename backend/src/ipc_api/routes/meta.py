"""Listas habilitadas (com sessão), ``/health`` (processo vivo) e ``/ready`` (pronto para validar).

``/health`` e ``/ready`` ficam abertos para o monitoramento (UptimeRobot) e não revelam dados.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ipc_api.accounts.models import StoreUnavailable
from ipc_api.auth.deps import get_authenticator, require_active_account
from ipc_api.auth.sessions import Authenticator
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.deps import get_analyzer, get_settings
from ipc_api.errors import analyzer_unavailable, database_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas import HealthResponse, ListInfo, ReadyResponse
from ipc_api.settings import ApiSettings

logger = logging.getLogger(__name__)

router = APIRouter()
#: Rotas da equipe: exigem uma sessão de conta ativa (FR-22).
protected = APIRouter(dependencies=[Depends(require_active_account)])

UNAVAILABLE = error_docs({503: "ANALYZER_UNAVAILABLE: o analisador não respondeu."})


@protected.get(
    "/api/v1/lists",
    tags=["listas"],
    summary="Listas habilitadas, com o título de cada uma",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            503: (
                "ANALYZER_UNAVAILABLE (o analisador não respondeu) ou DATABASE_UNAVAILABLE "
                "(o banco de contas não respondeu)."
            ),
        }
    ),
)
async def lists(
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> list[ListInfo]:
    try:
        manifest = await analyzer.manifest()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    return [item for item in manifest.lists if item.number in settings.enabled_lists]


@router.get("/health", tags=["operação"], summary="O processo da API está no ar")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    tags=["operação"],
    summary=(
        "A API consegue atender: o analisador e o banco de contas respondem (monitorado pelo "
        "UptimeRobot)"
    ),
    responses=error_docs(
        {
            503: (
                "ANALYZER_UNAVAILABLE (o analisador não respondeu) ou DATABASE_UNAVAILABLE "
                "(o banco de contas não respondeu)."
            )
        }
    ),
)
async def ready(
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> ReadyResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        status = await analyzer.health()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    try:
        await authenticator.store.ping()
    except StoreUnavailable:
        logger.warning("banco de contas indisponível")
        raise database_unavailable() from None
    return ReadyResponse(
        status="ready", ruleset_version=status.ruleset_version, release=settings.release
    )

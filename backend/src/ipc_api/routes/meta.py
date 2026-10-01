"""Listas habilitadas, ``/health`` (processo vivo) e ``/ready`` (pronto para validar)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.deps import get_analyzer, get_settings
from ipc_api.errors import analyzer_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas import HealthResponse, ListInfo, ReadyResponse
from ipc_api.settings import ApiSettings

logger = logging.getLogger(__name__)

router = APIRouter()

UNAVAILABLE = error_docs({503: "ANALYZER_UNAVAILABLE: o analisador não respondeu."})


@router.get(
    "/api/v1/lists",
    tags=["listas"],
    summary="Listas habilitadas, com o título de cada uma",
    responses=UNAVAILABLE,
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
    summary="A API consegue validar código: o analisador responde (monitorado pelo UptimeRobot)",
    responses=UNAVAILABLE,
)
async def ready(
    response: Response, analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)]
) -> ReadyResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        status = await analyzer.health()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    return ReadyResponse(status="ready", ruleset_version=status.ruleset_version)

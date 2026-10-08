"""Listas habilitadas (com sessão), ``/health`` (processo vivo), ``/ready`` (pronto para validar)
e ``/health/slo`` (latência e erros recentes, S21-02).

As três rotas de operação ficam abertas para o monitoramento (UptimeRobot) e não revelam dados.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from ipc_api.accounts.models import StoreUnavailable
from ipc_api.auth.deps import get_authenticator, require_active_account
from ipc_api.auth.sessions import Authenticator
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.deps import get_analyzer, get_housekeeping, get_settings, get_slo, get_telemetry
from ipc_api.errors import analyzer_unavailable, database_unavailable
from ipc_api.housekeeping import Housekeeping
from ipc_api.ratelimit import client_ip
from ipc_api.routes import error_docs
from ipc_api.schemas import (
    HealthResponse,
    ListInfo,
    ReadyResponse,
    SloHousekeeping,
    SloResponse,
    SloTelemetry,
)
from ipc_api.settings import ApiSettings
from ipc_api.slo import SloMonitor
from ipc_api.telemetry import Telemetry

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


# HEAD nas rotas de operação (S30-04): o plano gratuito do UptimeRobot só consulta com HEAD (o
# método é opção paga); sem estas rotas, a API responderia 405 e o monitor ficaria vermelho. Fora
# do OpenAPI: é o mesmo contrato do GET, sem corpo.
@router.head("/health", include_in_schema=False)
@router.get("/health", tags=["operação"], summary="O processo da API está no ar")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.head("/ready", include_in_schema=False)
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


@router.head("/health/service", include_in_schema=False)
@router.get(
    "/health/service",
    tags=["operação"],
    summary=(
        "A API e o analisador respondem, sem consultar o banco (health check do Render): uma "
        "oscilação do banco não derruba a instância nem trava o deploy"
    ),
    responses=error_docs({503: "ANALYZER_UNAVAILABLE: o analisador não respondeu."}),
)
async def service_health(
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> ReadyResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        status = await analyzer.health()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    return ReadyResponse(
        status="ready", ruleset_version=status.ruleset_version, release=settings.release
    )


@router.head("/health/slo", include_in_schema=False)
@router.get(
    "/health/slo",
    tags=["operação"],
    summary=(
        "Latência e erros dos últimos 5 minutos: 503 quando o P95 da verificação passa de 200 ms "
        "ou mais de 1% das respostas são 5xx (alerta do UptimeRobot)"
    ),
    responses={503: {"model": SloResponse, "description": "Fora da meta do NFR-15."}},
)
async def slo(
    response: Response,
    monitor: Annotated[SloMonitor, Depends(get_slo)],
    telemetry: Annotated[Telemetry, Depends(get_telemetry)],
    housekeeping: Annotated[Housekeeping, Depends(get_housekeeping)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> SloResponse:
    response.headers["Cache-Control"] = "no-store"
    report = monitor.report()
    if not report.healthy:
        response.status_code = 503
    stats = telemetry.stats
    return SloResponse(
        status="ok" if report.healthy else "degraded",
        window_s=int(settings.slo.window_s),
        requests=report.requests,
        validations=report.validations,
        p95_ms=report.p95_ms,
        error_rate_pct=report.error_rate_pct,
        reasons=list(report.reasons),
        telemetry=SloTelemetry(
            written=stats.written,
            dropped=stats.dropped,
            failed_batches=stats.failed_batches,
            queued=telemetry.queued,
        ),
        housekeeping=SloHousekeeping(
            runs=housekeeping.stats.runs,
            failures=housekeeping.stats.failures,
            sessions=housekeeping.stats.removed.sessions,
            tokens=housekeeping.stats.removed.tokens,
            unverified=housekeeping.stats.removed.unverified,
            inactive=housekeeping.stats.removed.inactive,
            log=housekeeping.stats.removed.log,
        ),
    )


#: Cabeçalhos de proxy que o diagnóstico devolve (S30-03); nenhum outro sai na resposta.
PROXY_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "x-vercel-forwarded-for",
    "cf-connecting-ip",
    "true-client-ip",
    "forwarded",
    "via",
)


# GET e POST: a Vercel pode tratar os cabeçalhos de um jeito em cada método.
@router.api_route("/api/v1/proxy-check", methods=["GET", "POST"], include_in_schema=False)
async def proxy_check(
    request: Request, settings: Annotated[ApiSettings, Depends(get_settings)]
) -> JSONResponse:
    """Diagnóstico do IP do cliente atrás da Vercel e do Render (S30-03, P-15 b).

    Devolve a quem chama só os cabeçalhos de proxy da própria requisição e o IP que o limite por IP
    usaria. É o mesmo que o cliente já sabe (o próprio IP) mais os endereços dos proxies; nada vai
    para o log, a telemetria ou o banco. O teste do piloto o usa para conferir que um
    ``X-Forwarded-For`` forjado não escolhe a chave do limite.
    """
    found = {name: request.headers.getlist(name) for name in PROXY_HEADERS}
    config = settings.rate_limit
    address = client_ip(
        request.scope, config.trusted_proxy_hops, trust_forwarded=config.trust_forwarded_header
    )
    return JSONResponse(
        {
            "headers": {name: values for name, values in found.items() if values},
            "client_ip": str(address) if address else None,
            "trusted_proxy_hops": config.trusted_proxy_hops,
            "trust_forwarded_header": config.trust_forwarded_header,
        },
        headers={"Cache-Control": "no-store"},
    )

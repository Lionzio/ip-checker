"""O período de cada pedido (S43-02; ADR-12): o ativo por padrão, ou um anterior carregado.

A API nunca lê regras: os períodos, as listas e as questões vêm do manifesto do analisador, que
carrega o ativo e os até 5 anteriores (S43-01). Um período fora disso é recusado com 422
``UNKNOWN_PERIOD``, com os disponíveis na mensagem.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable
from ipc_api.schemas import AnalyzerManifest, ListInfo
from ipc_api.settings import ApiSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PeriodView:
    """Um período carregado no analisador, como a API o enxerga."""

    period: str
    active: bool
    ruleset_version: str
    lists: tuple[ListInfo, ...]


def loaded_periods(manifest: AnalyzerManifest) -> list[PeriodView]:
    """Os períodos carregados, do mais novo ao mais antigo. Um analisador anterior à S43-01 (sem
    ``periods`` no manifesto) tem só o ativo."""
    if not manifest.periods:
        return [PeriodView(manifest.period, True, manifest.ruleset_version, tuple(manifest.lists))]
    return [
        PeriodView(item.period, item.active, item.ruleset_version, tuple(item.lists))
        for item in manifest.periods
    ]


def pick_period(manifest: AnalyzerManifest, period: str | None) -> PeriodView:
    """O período pedido; ``None`` é o ativo. Fora da janela, 422 ``UNKNOWN_PERIOD``."""
    views = loaded_periods(manifest)
    if period is None:
        return next((view for view in views if view.active), views[0])
    for view in views:
        if view.period == period:
            return view
    available = ", ".join(view.period for view in views)
    raise ApiError(
        422,
        ErrorCode.UNKNOWN_PERIOD,
        f"O período {period} não está disponível no IP-Checker. Períodos disponíveis: {available}.",
    )


async def resolve_period(analyzer: AnalyzerClient, period: str | None) -> PeriodView:
    try:
        manifest = await analyzer.manifest()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    return pick_period(manifest, period)


def require_list(view: PeriodView, list_number: int, settings: ApiSettings) -> None:
    """No período ativo, só as listas habilitadas (``IPC_ENABLED_LISTS``); num anterior, todas as
    listas dele, que já foram corrigidas (a lista atrasada, US-39)."""
    allowed = (
        list_number in settings.enabled_lists
        if view.active
        else any(item.number == list_number for item in view.lists)
    )
    if not allowed:
        raise ApiError(
            422,
            ErrorCode.LIST_NOT_ENABLED,
            f"A Lista {list_number} ainda não está habilitada no IP-Checker.",
        )

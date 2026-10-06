"""Regras por questão do lado da API (R-01, FR-11): a questão pedida existe e é da lista?

A API nunca lê regras: confere a questão no manifesto do analisador, que lista as questões
cadastradas no período do ruleset ativo (P-07). O analisador confere de novo antes de analisar.
"""

from __future__ import annotations

import logging

from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerUnavailable
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable

logger = logging.getLogger(__name__)


async def check_question(
    analyzer: AnalyzerClient, list_number: int, question_id: str | None
) -> None:
    """Recusa com 422 ``UNKNOWN_QUESTION`` uma questão inexistente ou de outra lista."""
    if question_id is None:
        return
    try:
        manifest = await analyzer.manifest()
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None
    owner = next(
        (item.number for item in manifest.lists for q in item.questions if q.id == question_id),
        None,
    )
    if owner is None:
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {question_id} não está cadastrada no IP-Checker.",
        )
    if owner != list_number:
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {question_id} é da Lista {owner}, não da Lista {list_number}.",
        )

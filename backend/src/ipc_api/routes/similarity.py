"""``POST /api/v1/similarity``: o painel de plágio (S17-02; FR-29, ADR-05).

Os dois códigos são comparados no analisador isolado, como na verificação: nada é executado nem
guardado. A API confere os limites de cada código, ocupa uma vaga de análise e classifica o
resultado pelas faixas do FR-29.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.admission import Admission, Overloaded
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_admission, get_analyzer, get_request_id
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, overloaded
from ipc_api.routes import error_docs
from ipc_api.schemas import (
    SimilarityBand,
    SimilarityRequest,
    SimilarityResponse,
    SimilaritySyntaxError,
)
from ipc_api.similarity import NOTICE, SHORT_CODE_TOKENS, classify, displayed
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", tags=["plágio"], dependencies=[Depends(require_active_account)]
)


def _check(code: str, label: str) -> None:
    try:
        check_code(code)
    except ApiError as exc:
        raise ApiError(exc.status, exc.code, f"Código {label}: {exc.message}") from None


@router.post(
    "/similarity",
    summary="Compara duas soluções e classifica a similaridade (indício de plágio)",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: um código acima de 51.200 bytes, ou corpo acima de 128 KB.",
            422: "INVALID_INPUT (entrada inválida) ou ANALYSIS_LIMIT (código complexo demais).",
            429: (
                "RATE_LIMITED: muitas verificações da mesma conta ou da mesma rede em 1 minuto. "
                "Veja retry_after_s."
            ),
            503: ("OVERLOADED, ANALYZER_UNAVAILABLE ou DATABASE_UNAVAILABLE. Veja retry_after_s."),
        }
    ),
)
async def similarity(
    body: SimilarityRequest,
    request: Request,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> SimilarityResponse:
    # O resultado diz respeito ao código de alunos: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    _check(body.code_a, "A")
    _check(body.code_b, "B")
    try:
        async with admission.slot():
            result = await analyzer.similarity(body.code_a, body.code_b, request_id=request_id)
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    request.state.outcome = result.status
    if result.status == "syntax_error":
        problem, side = result.syntax_error, result.syntax_error_side
        assert problem is not None  # noqa: S101 - conferido pelo esquema da resposta
        return SimilarityResponse(
            request_id=request_id,
            status="syntax_error",
            similarity=None,
            band=None,
            short_code=False,
            syntax_error=SimilaritySyntaxError(
                code="a" if side == 1 else "b",
                line=problem.line,
                col=problem.col,
                message=problem.message,
            ),
            notice=NOTICE,
        )
    assert result.percent is not None  # noqa: S101 - conferido pelo esquema da resposta
    assert result.token_counts is not None  # noqa: S101
    band = classify(result.percent)
    return SimilarityResponse(
        request_id=request_id,
        status="compared",
        similarity=displayed(result.percent),
        band=SimilarityBand(id=band.id, label=band.label, minimum=band.minimum),
        short_code=min(result.token_counts) < SHORT_CODE_TOKENS,
        syntax_error=None,
        notice=NOTICE,
    )

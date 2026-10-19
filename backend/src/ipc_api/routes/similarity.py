"""``POST /api/v1/similarity`` e ``/similarity/batch``: o painel de plágio (S17-02, S27; FR-29,
ADR-05, ADR-07).

Os dois códigos são comparados no analisador isolado, como na verificação: nada é executado nem
guardado. A API confere os limites de cada código, ocupa uma vaga de análise e classifica o
resultado pelas faixas do FR-29.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api import gabarito_result
from ipc_api.admission import Admission, Overloaded
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_admission, get_analyzer, get_gabaritos, get_request_id, get_settings
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, overloaded
from ipc_api.gabaritos import Gabaritos
from ipc_api.periods import resolve_period
from ipc_api.questions import check_question
from ipc_api.routes import error_docs
from ipc_api.schemas import (
    AnalyzerClassItem,
    AnalyzerSimilarity,
    MatrixPair,
    MatrixSolution,
    SimilarityBand,
    SimilarityClassItem,
    SimilarityClassRequest,
    SimilarityClassResponse,
    SimilarityGabarito,
    SimilarityMatrixRequest,
    SimilarityMatrixResponse,
    SimilarityRequest,
    SimilarityResponse,
    SimilaritySyntaxError,
)
from ipc_api.settings import ApiSettings
from ipc_api.similarity import BANDS, NOTICE, SHORT_CODE_TOKENS, classify, displayed
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", tags=["plágio"], dependencies=[Depends(require_active_account)]
)


def _check(code: str, label: str) -> None:
    try:
        check_code(code)
    except ApiError as exc:
        prefix = "Solução comparada" if label == "comparado" else f"Código {label}"
        raise ApiError(exc.status, exc.code, f"{prefix}: {exc.message}") from None


@router.post(
    "/similarity",
    summary="Compara duas soluções e classifica a similaridade (indício de plágio)",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: um código acima de 51.200 bytes, ou corpo acima de 128 KB.",
            422: (
                "INVALID_INPUT (entrada inválida), UNKNOWN_QUESTION, UNKNOWN_PERIOD (período não "
                "carregado) ou ANALYSIS_LIMIT (código complexo demais)."
            ),
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
    gabaritos: Annotated[Gabaritos, Depends(get_gabaritos)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> SimilarityResponse:
    # O resultado diz respeito ao código de alunos: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    _check(body.code_a, "A")
    _check(body.code_b, "B")
    pair: tuple[tuple[str, str], ...] = ()
    # Sem questão nem período, a comparação não precisa do manifesto.
    view = (
        await resolve_period(analyzer, body.period)
        if body.question_id is not None or body.period is not None
        else None
    )
    if view is not None and body.question_id is not None:
        # A numeração oficial diz a lista (L3-Q2 é da Lista 3, P-07).
        check = check_question(view, int(body.question_id[1]), body.question_id, gabaritos)
        if check is not None:
            pair = gabaritos.pair(check.period, body.question_id)
    try:
        async with admission.slot():
            result = await analyzer.similarity(
                body.code_a,
                body.code_b,
                request_id=request_id,
                gabaritos=[code for _kind, code in pair],
                period=None if view is None or view.active else view.period,
            )
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
            gabarito=_gabarito(body.question_id, result, gabaritos, pair, settings),
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
        metrics=result.metrics,
        matches=result.matches,
        gabarito=_gabarito(body.question_id, result, gabaritos, pair, settings),
    )


def _gabarito(
    question_id: str | None,
    result: AnalyzerSimilarity,
    gabaritos: Gabaritos,
    pair: tuple[tuple[str, str], ...],
    settings: ApiSettings,
) -> SimilarityGabarito | None:
    if question_id is None:
        return None
    return gabarito_result.for_similarity(
        question_id,
        result,
        gabaritos,
        bool(pair),
        settings.gabaritos,
        kinds=[kind for kind, _code in pair],
    )


def _class_item(label: str, item: AnalyzerClassItem) -> SimilarityClassItem:
    if item.status != "compared" or item.percent is None:
        return SimilarityClassItem(
            label=label,
            status=item.status,
            similarity=None,
            band=None,
            short_code=False,
            metrics=None,
            syntax_error=item.syntax_error,
            message=item.message,
        )
    band = classify(item.percent)
    return SimilarityClassItem(
        label=label,
        status="compared",
        similarity=displayed(item.percent),
        band=SimilarityBand(id=band.id, label=band.label, minimum=band.minimum),
        short_code=(item.token_count or 0) < SHORT_CODE_TOKENS,
        metrics=item.metrics,
        syntax_error=None,
        message=None,
    )


@router.post(
    "/similarity/batch",
    summary=(
        "Compara uma solução com até 100 da turma (S27-02): o que toda a turma escreve quase não "
        "conta"
    ),
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: (
                "PAYLOAD_TOO_LARGE: a solução comparada acima de 51.200 bytes, ou corpo acima de "
                "128 KB."
            ),
            422: (
                "INVALID_INPUT (entrada inválida) ou ANALYSIS_LIMIT (solução comparada complexa "
                "demais)."
            ),
            429: (
                "RATE_LIMITED: muitas requisições da mesma conta ou da mesma rede. Veja "
                "retry_after_s."
            ),
            503: "OVERLOADED, ANALYZER_UNAVAILABLE ou DATABASE_UNAVAILABLE. Veja retry_after_s.",
        }
    ),
)
async def similarity_batch(
    body: SimilarityClassRequest,
    request: Request,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> SimilarityClassResponse:
    response.headers["Cache-Control"] = "no-store"
    _check(body.code, "comparado")
    labels = [
        solution.label.strip() or str(index + 1) for index, solution in enumerate(body.solutions)
    ]
    try:
        async with admission.slot():
            result = await analyzer.similarity_class(
                body.code, [solution.code for solution in body.solutions], request_id=request_id
            )
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    request.state.outcome = result.status
    if result.status == "syntax_error":
        return SimilarityClassResponse(
            request_id=request_id,
            status="syntax_error",
            syntax_error=result.syntax_error,
            results=[],
            notice=NOTICE,
        )
    # O aviso de código curto usa o tamanho de cada solução da turma.
    items = [_class_item(label, item) for label, item in zip(labels, result.results, strict=True)]
    items.sort(key=lambda item: (item.similarity is None, -(item.similarity or 0.0)))
    return SimilarityClassResponse(
        request_id=request_id, status="compared", syntax_error=None, results=items, notice=NOTICE
    )


#: Os grupos ligam as soluções a partir da faixa "Requer atenção" (S40-02).
GROUP_MIN = next(band.minimum for band in BANDS if band.id == "requer_atencao")
#: Quantos pares a página recebe: os mais parecidos, que são os que pedem leitura.
MAX_PAIRS = 200


@router.post(
    "/similarity/class-matrix",
    summary="Compara todas as soluções da turma entre si e agrupa as parecidas (S40-02)",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: corpo acima de 128 KB.",
            422: "INVALID_INPUT: entrada inválida (menos de 2 ou mais de 60 soluções).",
            429: (
                "RATE_LIMITED: muitas requisições da mesma conta ou da mesma rede. Veja "
                "retry_after_s."
            ),
            503: "OVERLOADED, ANALYZER_UNAVAILABLE ou DATABASE_UNAVAILABLE. Veja retry_after_s.",
        }
    ),
)
async def similarity_matrix(
    body: SimilarityMatrixRequest,
    request: Request,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> SimilarityMatrixResponse:
    response.headers["Cache-Control"] = "no-store"
    labels = [
        solution.label.strip() or str(index + 1) for index, solution in enumerate(body.solutions)
    ]
    try:
        async with admission.slot():
            result = await analyzer.similarity_matrix(
                [solution.code for solution in body.solutions], GROUP_MIN, request_id=request_id
            )
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    request.state.outcome = "compared"
    pairs = []
    for pair in result.pairs[:MAX_PAIRS]:
        band = classify(pair.percent)
        pairs.append(
            MatrixPair(
                a=labels[pair.first],
                b=labels[pair.second],
                similarity=displayed(pair.percent),
                band=SimilarityBand(id=band.id, label=band.label, minimum=band.minimum),
            )
        )
    return SimilarityMatrixResponse(
        request_id=request_id,
        solutions=[
            MatrixSolution(
                label=label,
                status=item.status,
                syntax_error=item.syntax_error,
                message=item.message,
            )
            for label, item in zip(labels, result.solutions, strict=True)
        ],
        pairs=pairs,
        groups=[[labels[index] for index in group] for group in result.groups],
        notice=NOTICE,
    )

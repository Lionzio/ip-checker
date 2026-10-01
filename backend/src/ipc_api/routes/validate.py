"""``POST /api/v1/validate`` (FR-04, FR-12; 5.2.2)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_analyzer, get_request_id, get_settings
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas import ValidateRequest, ValidateResponse
from ipc_api.settings import ApiSettings
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["validação"])


@router.post(
    "/validate",
    summary="Confere se o código respeita as permissões da lista, sem executá-lo",
    responses=error_docs(
        {
            413: "PAYLOAD_TOO_LARGE: código acima de 51.200 bytes ou corpo acima de 128 KB.",
            422: (
                "INVALID_INPUT (entrada inválida), LIST_NOT_ENABLED (lista não liberada), "
                "UNKNOWN_QUESTION (questão não cadastrada) ou ANALYSIS_LIMIT (código complexo "
                "demais)."
            ),
            503: "ANALYZER_UNAVAILABLE: o analisador não respondeu. Veja retry_after_s.",
        }
    ),
)
async def validate(
    body: ValidateRequest,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> ValidateResponse:
    # O resultado diz respeito ao código de um aluno: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    check_code(body.code)
    if body.list_number not in settings.enabled_lists:
        raise ApiError(
            422,
            ErrorCode.LIST_NOT_ENABLED,
            f"A Lista {body.list_number} ainda não está habilitada no IP-Checker.",
        )
    if body.question_id is not None:
        # As regras por questão (R-01) entram na Sprint 17; até lá, nenhuma está cadastrada.
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {body.question_id} não está cadastrada no IP-Checker.",
        )

    try:
        result = await analyzer.analyze(body.code, body.list_number)
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    return ValidateResponse(
        request_id=request_id,
        ruleset_version=result.ruleset_version,
        status=result.status,
        list_number=result.list_number,
        question_id=None,
        notices=["QUESTION_RULES_NOT_APPLIED"],
        syntax_error=result.syntax_error,
        violations=result.violations,
        truncated=result.truncated,
    )

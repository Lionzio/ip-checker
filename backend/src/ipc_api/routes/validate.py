"""``POST /api/v1/validate`` (FR-04, FR-12; 5.2.2)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.admission import Admission, Overloaded
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_admission, get_analyzer, get_request_id, get_settings
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, overloaded
from ipc_api.routes import error_docs
from ipc_api.schemas import ValidateRequest, ValidateResponse
from ipc_api.settings import ApiSettings
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", tags=["validação"], dependencies=[Depends(require_active_account)]
)


@router.post(
    "/validate",
    summary="Confere se o código respeita as permissões da lista, sem executá-lo",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: código acima de 51.200 bytes ou corpo acima de 128 KB.",
            422: (
                "INVALID_INPUT (entrada inválida), LIST_NOT_ENABLED (lista não liberada), "
                "UNKNOWN_QUESTION (questão não cadastrada) ou ANALYSIS_LIMIT (código complexo "
                "demais)."
            ),
            429: (
                "RATE_LIMITED: muitas verificações da mesma conta ou da mesma rede em 1 minuto. "
                "Veja retry_after_s."
            ),
            503: (
                "OVERLOADED (sem vaga para a análise), ANALYZER_UNAVAILABLE (o analisador não "
                "respondeu) ou DATABASE_UNAVAILABLE (o banco de contas não respondeu). Veja "
                "retry_after_s."
            ),
        }
    ),
)
async def validate(
    body: ValidateRequest,
    request: Request,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> ValidateResponse:
    # O resultado diz respeito ao código de um aluno: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    request.state.list_number = body.list_number
    check_code(body.code)
    if body.list_number not in settings.enabled_lists:
        raise ApiError(
            422,
            ErrorCode.LIST_NOT_ENABLED,
            f"A Lista {body.list_number} ainda não está habilitada no IP-Checker.",
        )
    if body.question_id is not None:
        # As regras por questão (R-01) entram na Sprint 24; até lá, nenhuma está cadastrada.
        raise ApiError(
            422,
            ErrorCode.UNKNOWN_QUESTION,
            f"A questão {body.question_id} não está cadastrada no IP-Checker.",
        )

    try:
        # A vaga só é ocupada durante a análise, com a entrada já lida e validada.
        async with admission.slot():
            result = await analyzer.analyze(body.code, body.list_number, request_id=request_id)
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    request.state.ruleset_version = result.ruleset_version
    request.state.outcome = result.status
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

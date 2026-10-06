"""``POST /api/v1/feedback``: o feedback por LLM para o aluno (S18-02; FR-30, ADR-06).

O código é analisado de novo aqui, no analisador isolado: a frase obrigatória sai do resultado do
motor, nunca do que a página mandou. O texto vem da IA principal, da de reserva ou, sem nenhuma
delas, de modelos de texto: o botão funciona mesmo sem IA configurada, e aí nada sai do servidor.
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.accounts.models import Account
from ipc_api.admission import Admission, Overloaded
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_admission, get_analyzer, get_request_id, get_settings
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, overloaded
from ipc_api.feedback.compose import Evaluator, Item
from ipc_api.feedback.service import FeedbackService
from ipc_api.questions import check_question
from ipc_api.routes import error_docs
from ipc_api.schemas import FeedbackRequest, FeedbackResponse
from ipc_api.settings import ApiSettings
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", tags=["feedback"], dependencies=[Depends(require_active_account)]
)


def get_feedback(request: Request) -> FeedbackService:
    service: FeedbackService = request.app.state.feedback
    return service


def _clean(text: str, field: str, *, lines: bool) -> str:
    allowed = {"\n", "\t"} if lines else set()
    if any(unicodedata.category(char).startswith("C") and char not in allowed for char in text):
        raise ApiError(422, ErrorCode.INVALID_INPUT, f"{field} tem caracteres de controle.")
    return text.strip()


@router.post(
    "/feedback",
    summary="Redige o feedback para o aluno a partir do resultado do motor (FR-30)",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: código acima de 51.200 bytes ou corpo acima de 128 KB.",
            422: (
                "INVALID_INPUT (entrada inválida ou código com erro de sintaxe), "
                "LIST_NOT_ENABLED ou ANALYSIS_LIMIT."
            ),
            429: (
                "RATE_LIMITED: muitas requisições em 1 minuto ou a cota de feedbacks do dia. "
                "Veja retry_after_s."
            ),
            503: "OVERLOADED, ANALYZER_UNAVAILABLE ou DATABASE_UNAVAILABLE. Veja retry_after_s.",
        }
    ),
)
async def feedback(
    body: FeedbackRequest,
    request: Request,
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[FeedbackService, Depends(get_feedback)],
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> FeedbackResponse:
    # O texto fala de um aluno: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    request.state.list_number = body.list_number
    student = _clean(body.student_name, "O nome do aluno", lines=False)
    if len(student) < 2:
        raise ApiError(422, ErrorCode.INVALID_INPUT, "Informe o nome do aluno.")
    annotation = _clean(body.annotation, "A anotação", lines=True) if body.annotation else None
    check_code(body.code)
    if body.list_number not in settings.enabled_lists:
        raise ApiError(
            422,
            ErrorCode.LIST_NOT_ENABLED,
            f"A Lista {body.list_number} ainda não está habilitada no IP-Checker.",
        )
    await check_question(analyzer, body.list_number, body.question_id)
    service.take_quota(account.id.bytes)
    try:
        async with admission.slot():
            data = await analyzer.feedback_input(
                body.code, body.list_number, request_id=request_id, question_id=body.question_id
            )
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    if data.status == "syntax_error" or data.syntax_error is not None:
        problem = data.syntax_error
        where = f" (linha {problem.line}, coluna {problem.col})" if problem is not None else ""
        # Q-18 c: com erro de sintaxe, as permissões não foram verificadas, então não há feedback.
        raise ApiError(
            422,
            ErrorCode.INVALID_INPUT,
            f"O código tem um erro de sintaxe{where}: as permissões não foram verificadas, "
            "então não há feedback. Corrija o código e verifique de novo.",
        )
    role = account.role
    assert role is not None  # noqa: S101 - conta ativa sempre tem cargo (CHECK no banco)
    evaluator = Evaluator(name=account.name, role=role.value, treatment=account.treatment.value)
    result = await service.write(
        student=student,
        annotation=annotation,
        evaluator=evaluator,
        items=[Item(kind=item.kind, label=item.label) for item in data.items],
        code=data.code,
    )
    request.state.outcome = result.source
    return FeedbackResponse(
        request_id=request_id,
        status=data.status,
        text=result.text,
        source=result.source,
        provider=result.provider,
    )

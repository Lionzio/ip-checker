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

from ipc_api.accounts.models import Account, StoreUnavailable
from ipc_api.admission import Admission, Overloaded
from ipc_api.auth.deps import require_active_account
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import get_admission, get_analyzer, get_gabaritos, get_request_id, get_settings
from ipc_api.errors import (
    ApiError,
    ErrorCode,
    analyzer_unavailable,
    database_unavailable,
    overloaded,
)
from ipc_api.feedback.cache import CachedItem, CachedResult, result_key
from ipc_api.feedback.compose import Evaluator, Item
from ipc_api.feedback.service import FeedbackService
from ipc_api.gabaritos import Gabaritos
from ipc_api.periods import requested, resolve_request
from ipc_api.questions import check_question
from ipc_api.routes import error_docs
from ipc_api.schemas import FeedbackRequest, FeedbackResponse
from ipc_api.settings import ApiSettings
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

NO_AI = "O Aprimorar com IA não está configurado neste servidor: fica o texto sem IA."
NO_ANSWER = (
    "Nenhuma IA respondeu agora (fora do ar, sem cota ou com um texto que não passou na "
    "conferência): fica o texto sem IA. Tente de novo em alguns minutos."
)

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
                "LIST_NOT_ENABLED, UNKNOWN_QUESTION, UNKNOWN_PERIOD ou ANALYSIS_LIMIT."
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
    gabaritos: Annotated[Gabaritos, Depends(get_gabaritos)],
) -> FeedbackResponse:
    # O texto fala de um aluno: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    request.state.list_number = body.list_number
    student = _clean(body.student_name, "O nome do aluno", lines=False)
    if len(student) < 2:
        raise ApiError(422, ErrorCode.INVALID_INPUT, "Informe o nome do aluno.")
    annotation = _clean(body.annotation, "A anotação", lines=True) if body.annotation else None
    check_code(body.code)
    view = await resolve_request(
        analyzer, settings, body.list_number, body.period, body.question_id
    )
    # Uma questão só com gabarito (ADR-11, item 6) usa as regras da lista, como na verificação.
    check = check_question(view, body.list_number, body.question_id, gabaritos)
    question_id = body.question_id if check is not None and check.registered else None
    # S38-04: "Gerar" de novo (outro nome, outra anotação) reaproveita a análise anterior, que
    # fica em memória sem o código. O "Aprimorar com IA" precisa do código sem comentários, que só
    # o analisador isolado prepara, então ele sempre analisa (e renova o resultado guardado).
    key = result_key(body.code, body.list_number, question_id, requested(view) or "")
    cached = None if body.enhance else service.results.get(key)
    code_for_ai = ""
    if cached is None:
        try:
            async with admission.slot():
                data = await analyzer.feedback_input(
                    body.code,
                    body.list_number,
                    request_id=request_id,
                    question_id=question_id,
                    period=requested(view),
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
            # Q-18 c: com erro de sintaxe, as permissões não foram verificadas; não há feedback.
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"O código tem um erro de sintaxe{where}: as permissões não foram verificadas, "
                "então não há feedback. Corrija o código e verifique de novo.",
            )
        cached = CachedResult(
            status=data.status,
            items=tuple(CachedItem(i.kind, i.label, i.alternative) for i in data.items),
        )
        service.results.put(key, cached)
        code_for_ai = data.code
    role = account.role
    assert role is not None  # noqa: S101 - conta ativa sempre tem cargo (CHECK no banco)
    evaluator = Evaluator(name=account.name, role=role.value, treatment=account.treatment.value)
    items = [
        Item(kind=item.kind, label=item.label, alternative=item.alternative)
        for item in cached.items
    ]
    # Q-16 (opção A): o texto sem IA é o padrão e não gasta cota.
    result = service.write(student=student, annotation=annotation, evaluator=evaluator, items=items)
    notice: str | None = None
    if body.enhance:
        if not service.ai_enabled:
            notice = NO_AI
        else:
            # S25-05: a cota só é cobrada depois da análise; um erro antes dela não gasta nada.
            try:
                await service.take_quota(account.id)
            except StoreUnavailable as exc:
                raise database_unavailable(exc) from None
            enhanced = await service.enhance(
                student=student,
                annotation=annotation,
                evaluator=evaluator,
                items=items,
                code=code_for_ai,
            )
            if enhanced is None:
                notice = NO_ANSWER
            else:
                result = enhanced
    request.state.outcome = result.source
    return FeedbackResponse(
        request_id=request_id,
        status=cached.status,
        text=result.text,
        source=result.source,
        provider=result.provider,
        can_enhance=service.ai_enabled,
        notice=notice,
    )

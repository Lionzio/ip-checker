"""``POST /api/v1/validate`` (FR-04, FR-12; 5.2.2)."""

from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api import gabarito_result
from ipc_api.accounts.models import Account
from ipc_api.admission import Admission, Overloaded
from ipc_api.adoption import Adoption
from ipc_api.auth.deps import require_active_account
from ipc_api.auth.policy import sees_indicators
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.deps import (
    get_admission,
    get_adoption,
    get_analyzer,
    get_gabaritos,
    get_request_id,
    get_settings,
    get_telemetry,
)
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable, overloaded
from ipc_api.gabaritos import Gabaritos
from ipc_api.periods import requested, resolve_request
from ipc_api.questions import check_question
from ipc_api.routes import error_docs
from ipc_api.schemas import (
    AnalyzerResult,
    BatchResult,
    Category,
    GabaritoComparison,
    Indicators,
    ValidateBatchRequest,
    ValidateBatchResponse,
    ValidateRequest,
    ValidateResponse,
)
from ipc_api.settings import ApiSettings
from ipc_api.similarity import displayed
from ipc_api.telemetry import Outcome, Telemetry, TelemetryEvent, semester_of
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)

INDICATORS_NOTICE = (
    "Indícios não são prova de uso de IA. Eles servem para decidir com quem conversar; a "
    "confirmação é sempre uma conversa em que o aluno explica ou modifica o próprio código."
)

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
                "UNKNOWN_QUESTION (questão não cadastrada), UNKNOWN_PERIOD (período não "
                "carregado) ou ANALYSIS_LIMIT (código complexo demais)."
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
    telemetry: Annotated[Telemetry, Depends(get_telemetry)],
    adoption: Annotated[Adoption, Depends(get_adoption)],
    account: Annotated[Account, Depends(require_active_account)],
    gabaritos: Annotated[Gabaritos, Depends(get_gabaritos)],
) -> ValidateResponse:
    # O resultado diz respeito ao código de um aluno: nenhum proxy ou navegador deve guardá-lo.
    response.headers["Cache-Control"] = "no-store"
    # As verificações da conta de verificação do deploy não contam no uso (S28-02).
    counted = not account.check_account
    # Os indícios só para os cargos ligados (S42-05): os outros nem pedem o cálculo.
    with_indicators = sees_indicators(account, settings.ai_indicators)
    request.state.list_number = body.list_number
    try:
        check_code(body.code)
    except ApiError:
        if body.list_number in settings.enabled_lists and counted:
            _record_refusal(telemetry, body.list_number, "rejected")
        raise
    # O período das regras (S43-02): o ativo, ou um anterior para a lista atrasada (US-39).
    view = await resolve_request(
        analyzer, settings, body.list_number, body.period, body.question_id
    )
    check = check_question(view, body.list_number, body.question_id, gabaritos)
    # Uma questão só com gabarito (ADR-11, item 6) usa as regras da lista.
    registered = check is not None and check.registered
    # Os gabaritos da questão (Sprint 51): até dois, Notion e IP CC; vale o mais parecido.
    pair = (
        gabaritos.pair(check.period, body.question_id)
        if check is not None and body.question_id is not None
        else ()
    )

    try:
        # A vaga só é ocupada durante a análise, com a entrada já lida e validada.
        async with admission.slot():
            started = time.perf_counter()
            result = await analyzer.analyze(
                body.code,
                body.list_number,
                request_id=request_id,
                question_id=body.question_id if registered else None,
                indicators=with_indicators,
                # As referências de IA valem também para a questão só com gabarito (S42-04).
                reference_question=(
                    body.question_id if with_indicators and check is not None else None
                ),
                gabaritos=[code for _kind, code in pair],
                period=requested(view),
            )
            analysis_ms = round((time.perf_counter() - started) * 1000)
    except Overloaded:
        raise overloaded() from None
    except AnalyzerRejected as exc:
        limit = exc.code == ErrorCode.ANALYSIS_LIMIT
        if counted:
            outcome: Outcome = "analysis_limit" if limit else "rejected"
            _record_refusal(
                telemetry, body.list_number, outcome, view.ruleset_version if view else None
            )
        raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
    except AnalyzerUnavailable as exc:
        logger.warning("analyzer indisponível: %s", exc)
        raise analyzer_unavailable() from None

    request.state.ruleset_version = result.ruleset_version
    request.state.outcome = result.status
    if counted:
        # Fora do caminho da resposta: só entra na fila, sem código, conta ou IP (FR-16).
        telemetry.record(
            TelemetryEvent.from_result(
                ruleset_version=result.ruleset_version,
                list_number=result.list_number,
                question_id=body.question_id,
                outcome=result.status,
                rule_ids=[violation.rule_id for violation in result.violations],
                analysis_ms=analysis_ms,
            )
        )
        # A adoção é ligada à conta, mas só diz que ela usou a lista no período (P-09, critério 2).
        adoption.record(account.id, semester_of(result.ruleset_version), result.list_number)
    return ValidateResponse(
        request_id=request_id,
        ruleset_version=result.ruleset_version,
        status=result.status,
        list_number=result.list_number,
        question_id=body.question_id,
        # Sem questão, ou com uma só com gabarito, valem só as regras da lista, e a resposta
        # avisa (FR-11; ADR-11, item 6).
        notices=(
            ["QUESTION_RULES_NOT_APPLIED"]
            if body.question_id is None
            else []
            if registered
            else ["QUESTION_RULES_NOT_REGISTERED"]
        ),
        syntax_error=result.syntax_error,
        violations=result.violations,
        truncated=result.truncated,
        # Só para a equipe (ADR-08): nunca entram no feedback, na telemetria nem no log.
        indicators=(
            Indicators(**result.indicators.model_dump(), notice=INDICATORS_NOTICE)
            if with_indicators and result.indicators is not None
            else None
        ),
        gabarito=_gabarito(body.question_id, pair, gabaritos, result),
    )


def _gabarito(
    question_id: str | None,
    pair: tuple[tuple[str, str], ...],
    gabaritos: Gabaritos,
    result: AnalyzerResult,
) -> GabaritoComparison | None:
    if question_id is None:
        return None
    if not pair:
        return gabarito_result.missing(question_id, gabaritos)
    return gabarito_result.for_validation(
        question_id,
        result.gabarito,
        syntax_error=result.status == "syntax_error",
        kinds=[kind for kind, _code in pair],
    )


def _record_refusal(
    telemetry: Telemetry, list_number: int, outcome: Outcome, version: str | None = None
) -> None:
    """Código recusado antes ou durante a análise, na versão do período pedido (S43-02) ou, antes
    de saber o período, na do ativo; sem versão conhecida, não conta."""
    version = version or telemetry.ruleset_version
    if version is None:
        return
    telemetry.record(
        TelemetryEvent.from_result(
            ruleset_version=version, list_number=list_number, outcome=outcome
        )
    )


@router.post(
    "/validate/batch",
    summary="Confere até 20 arquivos de uma vez, para corrigir a turma inteira (S40-01)",
    responses=error_docs(
        {
            401: "UNAUTHENTICATED: sem sessão de uma conta ativa da equipe.",
            403: "ORIGIN_MISMATCH: a requisição veio de outro site.",
            413: "PAYLOAD_TOO_LARGE: corpo acima de 128 KB.",
            422: (
                "INVALID_INPUT (mais de 20 arquivos ou entrada inválida), LIST_NOT_ENABLED, "
                "UNKNOWN_QUESTION ou UNKNOWN_PERIOD. Um arquivo recusado não recusa os outros: "
                "ele volta com o status rejected."
            ),
            429: "RATE_LIMITED: muitas requisições da mesma conta ou da mesma rede.",
            503: "OVERLOADED ou ANALYZER_UNAVAILABLE: a parte pode ser enviada de novo.",
        }
    ),
)
async def validate_batch(
    body: ValidateBatchRequest,
    request: Request,
    response: Response,
    analyzer: Annotated[AnalyzerClient, Depends(get_analyzer)],
    admission: Annotated[Admission, Depends(get_admission)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    request_id: Annotated[str, Depends(get_request_id)],
    telemetry: Annotated[Telemetry, Depends(get_telemetry)],
    adoption: Annotated[Adoption, Depends(get_adoption)],
    account: Annotated[Account, Depends(require_active_account)],
    gabaritos: Annotated[Gabaritos, Depends(get_gabaritos)],
) -> ValidateBatchResponse:
    """A turma inteira em partes (S40-01): cada arquivo passa pelos mesmos limites da verificação
    e pela admissão, um de cada vez, e entra na telemetria anônima; nada é guardado."""
    response.headers["Cache-Control"] = "no-store"
    counted = not account.check_account
    request.state.list_number = body.list_number
    view = await resolve_request(
        analyzer, settings, body.list_number, body.period, body.question_id
    )
    check = check_question(view, body.list_number, body.question_id, gabaritos)
    registered = check is not None and check.registered
    # Os gabaritos da questão (Sprint 51): até dois, Notion e IP CC; vale o mais parecido.
    pair = (
        gabaritos.pair(check.period, body.question_id)
        if check is not None and body.question_id is not None
        else ()
    )
    results: list[BatchResult] = []
    version = view.ruleset_version if view else telemetry.ruleset_version or ""
    for file in body.files:
        try:
            check_code(file.code)
        except ApiError as exc:
            results.append(_refused(file.name, exc.message))
            continue
        try:
            async with admission.slot():
                started = time.perf_counter()
                result = await analyzer.analyze(
                    file.code,
                    body.list_number,
                    request_id=request_id,
                    question_id=body.question_id if registered else None,
                    indicators=False,
                    gabaritos=[code for _kind, code in pair],
                    period=requested(view),
                )
                analysis_ms = round((time.perf_counter() - started) * 1000)
        except Overloaded:
            raise overloaded() from None
        except AnalyzerRejected as exc:
            results.append(_refused(file.name, exc.message))
            continue
        except AnalyzerUnavailable as exc:
            logger.warning("analyzer indisponível: %s", exc)
            raise analyzer_unavailable() from None
        version = result.ruleset_version
        if counted:
            telemetry.record(
                TelemetryEvent.from_result(
                    ruleset_version=result.ruleset_version,
                    list_number=result.list_number,
                    question_id=body.question_id,
                    outcome=result.status,
                    rule_ids=[violation.rule_id for violation in result.violations],
                    analysis_ms=analysis_ms,
                )
            )
        counts: dict[Category, int] = {}
        for violation in result.violations:
            counts[violation.category] = counts.get(violation.category, 0) + 1
        results.append(
            BatchResult(
                name=file.name,
                status=result.status,
                counts=counts,
                rule_ids=list(dict.fromkeys(v.rule_id for v in result.violations)),
                syntax_error=result.syntax_error,
                gabarito_similarity=(
                    displayed(result.gabarito.percent) if result.gabarito is not None else None
                ),
            )
        )
    request.state.outcome = "batch"
    if counted and version:
        adoption.record(account.id, semester_of(version), body.list_number)
    return ValidateBatchResponse(request_id=request_id, ruleset_version=version, results=results)


def _refused(name: str, message: str) -> BatchResult:
    return BatchResult(name=name, status="rejected", counts={}, rule_ids=[], message=message)

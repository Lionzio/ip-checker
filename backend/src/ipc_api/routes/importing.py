"""Rotas da importação do Dikastis (S50-04, S50-05; ADR-15 e ADR-19).

- ``/api/v1/profile/import-tokens``: o token de importação, com a sessão de sempre (Perfil).
- ``/api/v1/import/catalog/*``: o manifesto e as questões, com o token de importação (a extensão).
  A origem da extensão (``chrome-extension://<id>``) é aceita só aqui (``OriginCheckMiddleware``).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from ipc_api.accounts.models import Account, StoreUnavailable
from ipc_api.auth.deps import require_active_account
from ipc_api.errors import ApiError, ErrorCode, database_unavailable
from ipc_api.importing.deps import get_importing, require_import_token
from ipc_api.importing.hashing import Sample
from ipc_api.importing.models import ClassIn, ImportToken, ListIn, QuestionIn, QuestionRef
from ipc_api.importing.service import ImportService
from ipc_api.routes import error_docs
from ipc_api.schemas.importing import (
    CatalogManifest,
    CatalogManifestResult,
    CatalogQuestionsIn,
    CatalogQuestionsResult,
    ImportTokenCreate,
    ImportTokenCreated,
    ImportTokenInfo,
    ImportTokens,
)

UNAUTHENTICATED = "UNAUTHENTICATED: sem sessão (Perfil) ou sem token de importação válido."
UNAVAILABLE = "DATABASE_UNAVAILABLE ou OVERLOADED: o banco não respondeu; tente de novo."
FORBIDDEN_ORIGIN = "ORIGIN_MISMATCH: a requisição veio de outro site ou de outra extensão."

tokens = APIRouter(
    prefix="/api/v1/profile/import-tokens",
    tags=["importação do Dikastis"],
    dependencies=[Depends(require_active_account)],
)
catalog = APIRouter(prefix="/api/v1/import/catalog", tags=["importação do Dikastis"])


def _info(token: ImportToken, now_active: bool) -> ImportTokenInfo:
    return ImportTokenInfo(
        id=token.id,
        label=token.label,
        created_at=token.created_at,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        last_used_at=token.last_used_at,
        active=now_active,
    )


@tokens.get(
    "",
    summary="Os tokens de importação da própria conta, sem o valor",
    responses=error_docs({401: UNAUTHENTICATED, 503: UNAVAILABLE}),
)
async def list_tokens(
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> ImportTokens:
    response.headers["Cache-Control"] = "no-store"
    try:
        found = await service.list_tokens(account)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    now = service.now()
    return ImportTokens(tokens=[_info(token, token.active(now)) for token in found])


@tokens.post(
    "",
    status_code=201,
    summary="Cria um token de importação (chefia e desenvolvedor); o valor aparece só aqui",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: "FORBIDDEN: só a chefia e o desenvolvedor criam tokens; ou ORIGIN_MISMATCH.",
            422: "INVALID_INPUT: rótulo inválido ou já há 3 tokens ativos.",
            503: UNAVAILABLE,
        }
    ),
)
async def create_token(
    body: ImportTokenCreate,
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> ImportTokenCreated:
    response.headers["Cache-Control"] = "no-store"
    try:
        raw, token = await service.create_token(account, body.label)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    info = _info(token, True)
    return ImportTokenCreated(**info.model_dump(), token=raw)


@tokens.delete(
    "/{token_id}",
    status_code=204,
    summary="Revoga um token de importação da própria conta",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: FORBIDDEN_ORIGIN,
            404: "ACCOUNT_NOT_FOUND: o token não existe, é de outra conta ou já foi revogado.",
            422: "INVALID_INPUT: o identificador do token não é um UUID.",
            503: UNAVAILABLE,
        }
    ),
)
async def revoke_token(
    token_id: UUID,
    account: Annotated[Account, Depends(require_active_account)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> Response:
    try:
        revoked = await service.revoke_token(account, token_id)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    if not revoked:
        raise ApiError(
            404, ErrorCode.ACCOUNT_NOT_FOUND, "Esse token não existe ou já foi revogado."
        )
    return Response(status_code=204)


@catalog.post(
    "/manifest",
    summary="Recebe o que a extensão viu no Dikastis e devolve o que falta (S50-05)",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: FORBIDDEN_ORIGIN,
            422: "INVALID_INPUT: o manifesto está fora do formato ou dos limites.",
            429: "RATE_LIMITED: muitas sincronizações seguidas com o mesmo token.",
            503: UNAVAILABLE,
        }
    ),
)
async def manifest(
    body: CatalogManifest,
    response: Response,
    account: Annotated[Account, Depends(require_import_token)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> CatalogManifestResult:
    response.headers["Cache-Control"] = "no-store"
    classes = [ClassIn(c.dikastis_org_id, c.name, c.course) for c in body.classes]
    lists = [
        ListIn(
            dikastis_task_id=item.dikastis_task_id,
            class_org_id=item.class_org_id,
            kind=item.kind,
            number=item.number,
            title=item.title,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            questions=tuple(
                QuestionRef(q.dikastis_problem_id, q.question_id, q.content_hash)
                for q in item.questions
            ),
        )
        for item in body.lists
    ]
    _check_numbers(lists)
    try:
        result = await service.manifest(
            account, mode=body.mode, period=body.period, classes=classes, lists=lists
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return CatalogManifestResult(
        run_id=result.run_id,
        need=list(result.need),
        unchanged=result.unchanged,
        missing=list(result.missing),
    )


@catalog.put(
    "/questions",
    summary="Grava as questões novas ou alteradas de uma rodada (S50-05)",
    responses=error_docs(
        {
            401: UNAUTHENTICATED,
            403: FORBIDDEN_ORIGIN,
            413: "PAYLOAD_TOO_LARGE: envie em partes menores.",
            422: "INVALID_INPUT: fora do formato, hash que não confere ou rodada desconhecida.",
            429: "RATE_LIMITED: muitas sincronizações seguidas com o mesmo token.",
            503: UNAVAILABLE,
        }
    ),
)
async def questions(
    body: CatalogQuestionsIn,
    response: Response,
    account: Annotated[Account, Depends(require_import_token)],
    service: Annotated[ImportService, Depends(get_importing)],
) -> CatalogQuestionsResult:
    response.headers["Cache-Control"] = "no-store"
    items = [
        QuestionIn(
            question_id=q.question_id,
            dikastis_problem_id=q.dikastis_problem_id,
            list_kind=q.list_kind,
            list_number=q.list_number,
            title=q.title,
            description=q.description,
            input_description=q.input_description,
            output_description=q.output_description,
            samples=tuple(Sample(s.input, s.output) for s in q.samples),
            time_limit_ms=q.time_limit_ms,
            content_hash=q.content_hash,
        )
        for q in body.questions
    ]
    try:
        result = await service.questions(
            account, run_id=body.run_id, period=body.period, questions=items
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return CatalogQuestionsResult(
        created=result.created, updated=result.updated, unchanged=result.unchanged
    )


def _check_numbers(lists: list[ListIn]) -> None:
    """Treino sem número; lista e prova com número (a mesma regra do banco)."""
    for item in lists:
        if (item.kind == "treino") != (item.number is None):
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"A tarefa {item.title!r}: a de treino não tem número; lista e prova têm.",
            )

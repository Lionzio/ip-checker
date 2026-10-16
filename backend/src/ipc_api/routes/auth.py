"""Entrar, sair, a conta logada (S13-02) e o registro com verificação de e-mail (S14)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ipc_api.accounts.models import ROLE_LABELS, Account, StoreUnavailable, Treatment
from ipc_api.auth.accounts import AccountService
from ipc_api.auth.deps import get_accounts, get_authenticator, require_active_account
from ipc_api.auth.middleware import session_token
from ipc_api.auth.policy import can_manage, can_view_log, sees_indicators
from ipc_api.auth.sessions import Authenticator, SessionConfig
from ipc_api.deps import get_settings
from ipc_api.errors import database_unavailable
from ipc_api.routes import error_docs
from ipc_api.schemas import (
    AccountResponse,
    AuthOptions,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendRequest,
    ResetPasswordRequest,
    VerifyRequest,
    VerifyResponse,
)
from ipc_api.settings import ApiSettings

router = APIRouter(prefix="/api/v1/auth", tags=["autenticação"])

FORBIDDEN_ORIGIN = "ORIGIN_MISMATCH: a requisição veio de outro site."
UNAVAILABLE = "DATABASE_UNAVAILABLE: o banco de contas não respondeu. Veja retry_after_s."


def account_response(account: Account, ai_indicators: str = "0") -> AccountResponse:
    # Uma conta ativa sempre tem cargo (CHECK no banco).
    role = account.role
    assert role is not None  # noqa: S101 - invariante garantida pelo esquema
    return AccountResponse(
        name=account.name,
        email=account.primary_email,
        course=account.course,
        treatment=account.treatment.value,
        role=role.value,
        role_label=ROLE_LABELS[role],
        has_password=account.password_hash is not None,
        can_manage=can_manage(account),
        can_view_log=can_view_log(account),
        ai_indicators=sees_indicators(account, ai_indicators),
    )


def set_session_cookie(response: Response, config: SessionConfig, token: str) -> None:
    """O cookie da sessão (NFR-22): HttpOnly, Secure, SameSite=Lax e ``__Host-``."""
    response.set_cookie(
        config.cookie_name,
        token,
        max_age=config.absolute_timeout_s,
        path="/",
        secure=config.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/login",
    summary="Entra com nome ou e-mail institucional e senha; abre a sessão no cookie",
    responses=error_docs(
        {
            401: "INVALID_CREDENTIALS: nome, e-mail ou senha incorretos (mensagem única).",
            403: (
                "ACCOUNT_PENDING_VERIFICATION, ACCOUNT_PENDING_APPROVAL, ACCOUNT_REJECTED ou "
                "ACCOUNT_REMOVED (só com a senha correta), ou " + FORBIDDEN_ORIGIN
            ),
            422: "DOMAIN_NOT_ALLOWED (e-mail fora de @cin.ufpe.br e @ufpe.br) ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas tentativas. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> AccountResponse:
    _no_store(response)
    try:
        account, token = await authenticator.login(body.login, body.password, request.scope)
        # Um identificador apresentado antes do login nunca é reaproveitado (fixação de sessão).
        await authenticator.logout(session_token(request.scope, authenticator.config.cookie_name))
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    set_session_cookie(response, authenticator.config, token)
    return account_response(account, request.app.state.settings.ai_indicators)


@router.get("/options", summary="Formas de entrar disponíveis neste servidor")
async def options(request: Request, response: Response) -> AuthOptions:
    _no_store(response)
    return AuthOptions(
        google=request.app.state.google.oidc.config.enabled,
        feedback_ai=request.app.state.feedback.ai_enabled,
        ai_indicators=request.app.state.settings.ai_indicators != "0",
    )


@router.post(
    "/logout",
    status_code=204,
    summary="Sai: encerra a sessão no servidor e apaga o cookie",
    responses=error_docs({403: FORBIDDEN_ORIGIN, 503: UNAVAILABLE}),
)
async def logout(
    request: Request, authenticator: Annotated[Authenticator, Depends(get_authenticator)]
) -> Response:
    config = authenticator.config
    try:
        await authenticator.logout(session_token(request.scope, config.cookie_name))
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    response = Response(status_code=204)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        config.cookie_name, path="/", secure=config.cookie_secure, httponly=True, samesite="lax"
    )
    return response


@router.get(
    "/me",
    summary="A conta logada (o tratamento só aparece aqui, para o próprio titular)",
    responses=error_docs(
        {401: "UNAUTHENTICATED: sem sessão de uma conta ativa.", 503: UNAVAILABLE}
    ),
)
async def me(
    response: Response,
    account: Annotated[Account, Depends(require_active_account)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AccountResponse:
    _no_store(response)
    return account_response(account, settings.ai_indicators)


@router.post(
    "/register",
    status_code=201,
    summary="Pede o cadastro com e-mail institucional e senha; envia o link de verificação",
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            409: "NAME_TAKEN ou EMAIL_TAKEN: o nome ou o e-mail já pertencem a outra conta.",
            422: "DOMAIN_NOT_ALLOWED, WEAK_PASSWORD ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s.",
            503: (
                "EMAIL_UNAVAILABLE (cadastro recebido, e-mail não enviado: peça um novo link) "
                "ou DATABASE_UNAVAILABLE."
            ),
        }
    ),
)
async def register(
    body: RegisterRequest,
    response: Response,
    accounts: Annotated[AccountService, Depends(get_accounts)],
) -> RegisterResponse:
    _no_store(response)
    try:
        account = await accounts.register(
            name=body.name,
            email=body.email,
            password=body.password,
            course=body.course,
            treatment=Treatment(body.treatment),
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return RegisterResponse(status="aguardando_verificacao", email=account.primary_email)


@router.post(
    "/verify",
    summary="Confirma o e-mail pelo token do link; o cadastro vai para a fila de aprovação",
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            422: "INVALID_TOKEN (inválido, já usado ou vencido) ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def verify(
    body: VerifyRequest,
    response: Response,
    accounts: Annotated[AccountService, Depends(get_accounts)],
) -> VerifyResponse:
    _no_store(response)
    try:
        await accounts.verify(body.token)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return VerifyResponse(status="aguardando_aprovacao")


@router.post(
    "/verify/resend",
    status_code=202,
    response_class=Response,
    summary="Reenvia o link de verificação; a resposta é a mesma, exista a conta ou não",
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            422: "DOMAIN_NOT_ALLOWED ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def resend(
    body: ResendRequest, accounts: Annotated[AccountService, Depends(get_accounts)]
) -> Response:
    try:
        await accounts.resend(body.email)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=202, headers={"Cache-Control": "no-store"})


@router.post(
    "/password/forgot",
    status_code=202,
    response_class=Response,
    summary='Envia o link de "esqueci minha senha"; a resposta é a mesma, exista a conta ou não',
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            422: "DOMAIN_NOT_ALLOWED ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def forgot_password(
    body: ForgotPasswordRequest, accounts: Annotated[AccountService, Depends(get_accounts)]
) -> Response:
    try:
        await accounts.forgot_password(body.email)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=202, headers={"Cache-Control": "no-store"})


@router.post(
    "/password/reset",
    status_code=204,
    response_class=Response,
    summary="Define a senha nova pelo token do link; encerra todas as sessões da conta",
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            422: "INVALID_TOKEN (inválido, já usado ou vencido), WEAK_PASSWORD ou INVALID_INPUT.",
            429: "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s.",
            503: UNAVAILABLE,
        }
    ),
)
async def reset_password(
    body: ResetPasswordRequest, accounts: Annotated[AccountService, Depends(get_accounts)]
) -> Response:
    try:
        await accounts.reset_password(body.token, body.new_password)
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    return Response(status_code=204, headers={"Cache-Control": "no-store"})

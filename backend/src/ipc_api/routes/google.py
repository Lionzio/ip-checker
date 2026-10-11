"""Entrada e registro pelo Google (S16-01; FR-24, FR-25). O fluxo está em ``auth/google.py``.

``start`` e ``callback`` são navegações do navegador, não chamadas da página: respondem com
redirecionamentos para o Google ou de volta para a SPA, e os motivos de recusa vão na URL só como
códigos (``/entrar?google=dominio``), nunca com dados pessoais.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from ipc_api.accounts.models import StoreUnavailable, Treatment
from ipc_api.auth.deps import get_authenticator
from ipc_api.auth.google import Expiring, Flow, GoogleIdentity, GoogleOidc, GoogleRefusal
from ipc_api.auth.google_accounts import GoogleAccounts, NeedsSignup, Refused, SignedIn
from ipc_api.auth.middleware import session_token
from ipc_api.auth.sessions import Authenticator
from ipc_api.errors import ApiError, ErrorCode, database_unavailable
from ipc_api.routes import error_docs
from ipc_api.routes.auth import FORBIDDEN_ORIGIN, UNAVAILABLE, set_session_cookie
from ipc_api.schemas import GooglePending, GoogleSignup, GoogleSignupResponse


@dataclass(slots=True)
class GoogleLogin:
    """O que o fluxo do Google guarda entre as requisições."""

    oidc: GoogleOidc
    accounts: GoogleAccounts
    flows: Expiring[Flow]
    signups: Expiring[GoogleIdentity]
    redirect_uri: str


def get_google(request: Request) -> GoogleLogin:
    google: GoogleLogin = request.app.state.google
    return google


router = APIRouter(prefix="/api/v1/auth/google", tags=["autenticação"])

Google = Annotated[GoogleLogin, Depends(get_google)]
Auth = Annotated[Authenticator, Depends(get_authenticator)]

LIMITED = "RATE_LIMITED: muitas requisições da mesma rede. Veja retry_after_s."
EXPIRED = (
    "INVALID_TOKEN: não há cadastro pelo Google em andamento neste navegador, ou ele venceu "
    "(10 minutos)."
)


def _cookie(base: str, authenticator: Authenticator) -> str:
    # Mesma regra do cookie da sessão: ``__Host-`` exige Secure, Path=/ e nenhum Domain.
    return f"__Host-{base}" if authenticator.config.cookie_secure else base


def _redirect(location: str) -> RedirectResponse:
    response = RedirectResponse(location, status_code=303)
    response.headers["Cache-Control"] = "no-store"
    return response


def _set(response: Response, name: str, value: str, max_age: int, secure: bool) -> None:
    response.set_cookie(
        name, value, max_age=max_age, path="/", secure=secure, httponly=True, samesite="lax"
    )


def _drop(response: Response, name: str, secure: bool) -> None:
    response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="lax")


def _signup_identity(request: Request, google: GoogleLogin, auth: Authenticator) -> GoogleIdentity:
    identity = google.signups.peek(request.cookies.get(_cookie("ipc_google", auth)))
    if identity is None:
        raise ApiError(
            422,
            ErrorCode.INVALID_TOKEN,
            "O cadastro pelo Google expirou. Entre com o Google de novo para continuar.",
        )
    return identity


@router.get(
    "/start",
    status_code=303,
    response_class=RedirectResponse,
    summary="Começa a entrada pelo Google: redireciona para a escolha da conta",
    responses={
        303: {"description": "Para o Google, ou para /entrar se ele não estiver configurado."},
        **error_docs({429: LIMITED}),
    },
)
async def start(google: Google, auth: Auth) -> RedirectResponse:
    if not google.oidc.config.enabled:
        return _redirect("/entrar?google=indisponivel")
    flow = google.oidc.new_flow()
    state = google.flows.put(flow)
    response = _redirect(
        google.oidc.authorization_url(state=state, flow=flow, redirect_uri=google.redirect_uri)
    )
    secure = auth.config.cookie_secure
    _set(response, _cookie("ipc_oauth", auth), state, google.oidc.config.flow_ttl_s, secure)
    return response


@router.get(
    "/callback",
    status_code=303,
    response_class=RedirectResponse,
    summary="Retorno do Google: entra, liga a conta de mesmo e-mail ou leva ao formulário",
    responses={
        303: {
            "description": (
                "Para / (sessão aberta), /google/concluir (formulário complementar) ou "
                "/entrar?google=<motivo> (recusa)."
            )
        },
        **error_docs({422: "INVALID_INPUT: parâmetros longos demais.", 429: LIMITED}),
    },
)
async def callback(
    request: Request,
    google: Google,
    auth: Auth,
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=256)] = None,
    error: Annotated[str | None, Query(max_length=256)] = None,
) -> RedirectResponse:
    secure = auth.config.cookie_secure
    oauth_cookie = _cookie("ipc_oauth", auth)
    expected = request.cookies.get(oauth_cookie)

    def refuse(reason: str) -> RedirectResponse:
        response = _redirect(f"/entrar?google={reason}")
        _drop(response, oauth_cookie, secure)
        return response

    if error is not None:
        return refuse("cancelado")
    if not google.oidc.config.enabled:
        return refuse("indisponivel")
    # O state precisa ser o deste navegador: um retorno forjado com o código de outra pessoa
    # (CSRF de login) não tem o cookie.
    if code is None or state is None or expected is None:
        return refuse("estado")
    if not hmac.compare_digest(state.encode(), expected.encode()):
        return refuse("estado")
    flow = google.flows.pop(state)
    if flow is None:
        return refuse("estado")
    try:
        identity = await google.oidc.identity(
            code=code, flow=flow, redirect_uri=google.redirect_uri
        )
        result = await google.accounts.resolve(identity)
        if isinstance(result, SignedIn):
            # Um identificador apresentado antes nunca é reaproveitado (fixação de sessão).
            await auth.logout(session_token(request.scope, auth.config.cookie_name))
    except GoogleRefusal as refusal:
        return refuse(refusal.reason)
    except StoreUnavailable:
        return refuse("indisponivel")

    if isinstance(result, Refused):
        return refuse(result.reason)
    if isinstance(result, NeedsSignup):
        response = _redirect("/google/concluir")
        key = google.signups.put(result.identity)
        _set(response, _cookie("ipc_google", auth), key, google.oidc.config.flow_ttl_s, secure)
    else:
        response = _redirect("/")
        set_session_cookie(response, auth.config, result.token)
    _drop(response, oauth_cookie, secure)
    return response


@router.get(
    "/pending",
    summary="O e-mail e o nome sugerido do cadastro pelo Google em andamento",
    responses=error_docs({422: EXPIRED}),
)
async def pending(
    request: Request, response: Response, google: Google, auth: Auth
) -> GooglePending:
    response.headers["Cache-Control"] = "no-store"
    identity = _signup_identity(request, google, auth)
    return GooglePending(email=identity.email, name=identity.name)


@router.post(
    "/complete",
    status_code=201,
    summary="Formulário complementar do Google: nome, curso e tratamento; vai para a aprovação",
    responses=error_docs(
        {
            403: FORBIDDEN_ORIGIN,
            409: "NAME_TAKEN ou EMAIL_TAKEN: o nome, o e-mail ou a conta Google já têm conta.",
            422: EXPIRED.removesuffix(".") + ", ou INVALID_INPUT.",
            429: LIMITED,
            503: UNAVAILABLE,
        }
    ),
)
async def complete(
    body: GoogleSignup, request: Request, response: Response, google: Google, auth: Auth
) -> GoogleSignupResponse:
    identity = _signup_identity(request, google, auth)
    try:
        account = await google.accounts.complete(
            identity, name=body.name, course=body.course, treatment=Treatment(body.treatment)
        )
    except StoreUnavailable as exc:
        raise database_unavailable(exc) from None
    cookie = _cookie("ipc_google", auth)
    google.signups.pop(request.cookies.get(cookie))
    response.headers["Cache-Control"] = "no-store"
    _drop(response, cookie, auth.config.cookie_secure)
    return GoogleSignupResponse(status="aguardando_aprovacao", email=account.primary_email)

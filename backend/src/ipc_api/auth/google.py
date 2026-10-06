"""Entrada pelo Google (S16-01; FR-24, ADR-04): OpenID Connect com ``state``, ``nonce`` e PKCE.

O fluxo é o *authorization code* com PKCE (S256). A ``api`` guarda, por até 10 minutos, o ``nonce``
e o ``code_verifier`` de cada fluxo, ligados ao navegador por um cookie ``__Host-`` com o ``state``:
um retorno que não traga o mesmo ``state`` do cookie é recusado (CSRF de login).

O ID token é validado pela joserfc, a implementação JOSE do Authlib: assinatura RS256 com as chaves
publicadas pelo Google (JWKS, em cache por até 1 hora e recarregadas quando aparece um ``kid``
desconhecido; o token vem direto do endpoint de token do Google, por TLS),
emissor, audiência, validade e ``nonce``. A decisão usa só o ``email`` e o ``email_verified`` do
token, com o domínio exato (``cin.ufpe.br`` ou ``ufpe.br``); o ``hd`` vai na URL do Google só como
dica para a tela de escolha da conta e nunca é tomado como prova.

Os fluxos ficam na memória do processo, como o limite de taxa: há uma única instância da API
(ADR-03). Uma reinicialização no meio do fluxo só pede para entrar de novo.
"""

from __future__ import annotations

import secrets
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx2
from authlib.common.security import generate_token  # type: ignore[import-untyped]
from authlib.oauth2.rfc7636 import create_s256_code_challenge  # type: ignore[import-untyped]
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jws import extract_compact

from ipc_api.accounts.models import email_domain_allowed, normalize_email

GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
#: Idade máxima das chaves do JWKS em cache; o Google publica as chaves novas antes de usá-las.
KEYS_MAX_AGE_S = 3600.0
#: Folga de relógio aceita na validade do token.
LEEWAY_S = 60


@dataclass(frozen=True, slots=True)
class GoogleConfig:
    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    issuer: str = GOOGLE_ISSUERS[0]
    authorization_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint: str = "https://oauth2.googleapis.com/token"  # noqa: S105 - URL, não segredo
    jwks_uri: str = "https://www.googleapis.com/oauth2/v3/certs"
    #: Só uma dica para a tela do Google: ``*`` sugere contas de organizações, não as pessoais.
    hosted_domain_hint: str = "*"
    timeout_s: float = 10.0
    #: Quanto tempo a pessoa tem para escolher a conta no Google e para o formulário complementar.
    flow_ttl_s: int = 600

    @property
    def enabled(self) -> bool:
        return self.client_id is not None and self.client_secret is not None

    @property
    def issuers(self) -> tuple[str, ...]:
        # O Google usa os dois valores de ``iss`` nos ID tokens.
        return GOOGLE_ISSUERS if self.issuer == GOOGLE_ISSUERS[0] else (self.issuer,)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GoogleConfig:
        client_id = env.get("IPC_GOOGLE_CLIENT_ID") or None
        secret = env.get("IPC_GOOGLE_CLIENT_SECRET") or None
        if (client_id is None) != (secret is None):
            raise ValueError(
                "Defina IPC_GOOGLE_CLIENT_ID e IPC_GOOGLE_CLIENT_SECRET juntos, ou nenhum dos dois."
            )
        return cls(client_id=client_id, client_secret=secret)


class GoogleRefusal(Exception):  # noqa: N818 - é um resultado, não um erro de programação
    """O Google não confirmou uma identidade aceita. ``reason`` vai para a página, sem dados."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    sub: str
    #: Já em minúsculas, verificado pelo Google e de um domínio aceito.
    email: str
    #: O nome da conta Google; só sugere o nome no formulário complementar.
    name: str


@dataclass(frozen=True, slots=True)
class Flow:
    nonce: str
    verifier: str


class Expiring[T]:
    """Valores de vida curta por chave aleatória, de uso único, com teto de memória."""

    def __init__(
        self,
        ttl_s: float,
        *,
        max_items: int = 10_000,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_s = ttl_s
        self._max_items = max_items
        self._monotonic = monotonic
        self._items: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def put(self, value: T) -> str:
        now = self._monotonic()
        while self._items:
            key, (expires, _) = next(iter(self._items.items()))
            if expires > now and len(self._items) < self._max_items:
                break
            del self._items[key]
        key = secrets.token_urlsafe(32)
        self._items[key] = (now + self._ttl_s, value)
        return key

    def peek(self, key: str | None) -> T | None:
        if key is None or key not in self._items:
            return None
        expires, value = self._items[key]
        if expires <= self._monotonic():
            del self._items[key]
            return None
        return value

    def pop(self, key: str | None) -> T | None:
        value = self.peek(key)
        if value is not None and key is not None:
            del self._items[key]
        return value


class GoogleOidc:
    def __init__(
        self,
        config: GoogleConfig,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._transport = transport
        self._clock = clock
        self._monotonic = monotonic
        self._keys: KeySet | None = None
        self._keys_at = float("-inf")

    @staticmethod
    def new_flow() -> Flow:
        # 64 caracteres de [A-Za-z0-9]: dentro dos 43 a 128 do PKCE (RFC 7636).
        return Flow(nonce=secrets.token_urlsafe(32), verifier=generate_token(64))

    def authorization_url(self, *, state: str, flow: Flow, redirect_uri: str) -> str:
        assert self.config.client_id is not None  # noqa: S101 - só com o Google configurado
        query = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "nonce": flow.nonce,
            "code_challenge": create_s256_code_challenge(flow.verifier),
            "code_challenge_method": "S256",
            "hd": self.config.hosted_domain_hint,
            "prompt": "select_account",
        }
        return f"{self.config.authorization_endpoint}?{urlencode(query)}"

    async def identity(self, *, code: str, flow: Flow, redirect_uri: str) -> GoogleIdentity:
        """Troca o código pelo ID token, valida o token e confere e-mail e domínio."""
        id_token = await self._exchange(code, flow, redirect_uri)
        claims = await self._validate(id_token, flow.nonce)
        if claims.get("email_verified") is not True:
            raise GoogleRefusal("email_nao_verificado")
        email = normalize_email(str(claims["email"]))
        if not email_domain_allowed(email):
            raise GoogleRefusal("dominio")
        name = claims.get("name")
        return GoogleIdentity(
            sub=str(claims["sub"]), email=email, name=name if isinstance(name, str) else ""
        )

    async def _client(self) -> httpx2.AsyncClient:
        # Proxies do ambiente nunca valem para a troca do código (S25-04).
        return httpx2.AsyncClient(
            transport=self._transport, timeout=self.config.timeout_s, trust_env=False
        )

    async def _exchange(self, code: str, flow: Flow, redirect_uri: str) -> str:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.config.client_id or "",
            "client_secret": self.config.client_secret or "",
            "code_verifier": flow.verifier,
        }
        try:
            async with await self._client() as client:
                response = await client.post(
                    self.config.token_endpoint, data=data, headers={"Accept": "application/json"}
                )
        except httpx2.HTTPError:
            raise GoogleRefusal("indisponivel") from None
        if response.status_code >= 500:
            raise GoogleRefusal("indisponivel")
        if response.status_code != 200:
            # Código inválido, já usado ou de outro cliente: a pessoa recomeça.
            raise GoogleRefusal("token")
        try:
            body = response.json()
        except ValueError:
            raise GoogleRefusal("token") from None
        id_token = body.get("id_token") if isinstance(body, dict) else None
        if not isinstance(id_token, str):
            raise GoogleRefusal("token")
        return id_token

    async def _key_set(self, kid: str | None) -> KeySet:
        now = self._monotonic()
        cached = self._keys
        if cached is not None and now - self._keys_at < KEYS_MAX_AGE_S and _has_kid(cached, kid):
            return cached
        try:
            async with await self._client() as client:
                response = await client.get(self.config.jwks_uri)
            response.raise_for_status()
            keys = KeySet.import_key_set(response.json())
        except (httpx2.HTTPError, ValueError, JoseError):
            if cached is not None:
                return cached
            raise GoogleRefusal("indisponivel") from None
        self._keys, self._keys_at = keys, now
        return keys

    async def _validate(self, id_token: str, nonce: str) -> dict[str, Any]:
        try:
            kid = extract_compact(id_token.encode()).headers().get("kid")
            keys = await self._key_set(kid if isinstance(kid, str) else None)
            token = jwt.decode(id_token, keys, algorithms=["RS256"])
        except (JoseError, ValueError):
            raise GoogleRefusal("token") from None
        registry = jwt.JWTClaimsRegistry(
            now=int(self._clock()),
            leeway=LEEWAY_S,
            iss={"essential": True, "values": list(self.config.issuers)},
            aud={"essential": True, "value": self.config.client_id or ""},
            sub={"essential": True},
            exp={"essential": True},
            iat={"essential": True},
            email={"essential": True},
            nonce={"essential": True, "value": nonce},
        )
        try:
            registry.validate(token.claims)
        except JoseError:
            raise GoogleRefusal("token") from None
        azp = token.claims.get("azp")
        if azp is not None and azp != self.config.client_id:
            raise GoogleRefusal("token")
        return dict(token.claims)


def _has_kid(keys: KeySet, kid: str | None) -> bool:
    try:
        keys.get_by_kid(kid)
    except JoseError:
        return False
    return True

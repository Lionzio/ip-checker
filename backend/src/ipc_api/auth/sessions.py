"""Login por senha e sessões no servidor (FR-22, FR-25, NFR-22; ADR-04).

- O identificador da sessão tem 256 bits e só vai no cookie; o banco guarda o SHA-256 dele.
- A sessão expira após 12 h sem uso e em no máximo 7 dias; um novo identificador a cada login.
- "Credenciais inválidas" é uma mensagem única: não revela se a conta existe. O status da conta
  (aguardando, recusada, removida) só aparece depois de a senha ser confirmada.
- Uma conta que deixou de estar ativa perde as sessões na próxima requisição.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from starlette.types import Scope

from ipc_api.accounts.models import (
    REMOVED,
    Account,
    Status,
    email_domain_allowed,
    normalize_email,
)
from ipc_api.accounts.passwords import Passwords
from ipc_api.accounts.store import AccountStore
from ipc_api.auth.throttle import LoginThrottle, LoginThrottleConfig
from ipc_api.errors import ApiError, ErrorCode
from ipc_api.ratelimit import RateLimitConfig, client_ip

#: Nome do cookie. O prefixo __Host- obriga Secure, Path=/ e nenhum Domain.
SECURE_COOKIE = "__Host-ipc_session"
#: Só para quando o navegador não aceitar Secure em HTTP local (P-15 c).
PLAIN_COOKIE = "ipc_session"
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")


@dataclass(frozen=True, slots=True)
class SessionConfig:
    cookie_secure: bool = True
    idle_timeout_s: int = 12 * 3600
    absolute_timeout_s: int = 7 * 24 * 3600
    #: De quanto em quanto tempo o "último uso" é gravado, para não escrever a cada requisição.
    touch_interval_s: int = 300

    @property
    def cookie_name(self) -> str:
        return SECURE_COOKIE if self.cookie_secure else PLAIN_COOKIE


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


def valid_token(value: str | None) -> bool:
    return value is not None and _TOKEN.match(value) is not None


_STATUS_ERRORS: dict[Status, tuple[ErrorCode, str]] = {
    Status.AGUARDANDO_VERIFICACAO: (
        ErrorCode.ACCOUNT_PENDING_VERIFICATION,
        "Confirme o seu e-mail pelo link que enviamos antes de entrar.",
    ),
    Status.AGUARDANDO_APROVACAO: (
        ErrorCode.ACCOUNT_PENDING_APPROVAL,
        "O seu cadastro está aguardando a aprovação de um monitor-chefe, de um professor ou do "
        "desenvolvedor.",
    ),
    Status.RECUSADO: (ErrorCode.ACCOUNT_REJECTED, "O seu cadastro foi recusado."),
    **dict.fromkeys(
        REMOVED,
        (ErrorCode.ACCOUNT_REMOVED, "Esta conta foi removida da equipe e não tem mais acesso."),
    ),
}


def status_refusal(account: Account) -> ApiError | None:
    """O 403 de uma conta que não está ativa (FR-25), só depois de a identidade ser confirmada."""
    if account.status is Status.ATIVO:
        return None
    code, message = _STATUS_ERRORS[account.status]
    return ApiError(403, code, message)


INVALID_CREDENTIALS = (
    "Nome, e-mail ou senha incorretos. Se você criou a conta pelo Google, entre pelo Google ou "
    "defina uma senha no perfil."
)


class Authenticator:
    def __init__(
        self,
        store: AccountStore,
        passwords: Passwords,
        config: SessionConfig,
        *,
        rate_limit: RateLimitConfig,
        throttle_config: LoginThrottleConfig,
        throttle: LoginThrottle | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.passwords = passwords
        self.config = config
        self._rate_limit = rate_limit
        self._throttle_config = throttle_config
        self._throttle = throttle or LoginThrottle(max_keys=throttle_config.max_keys)
        self._clock = clock

    def _ip_limit(self, scope: Scope) -> tuple[bytes, int]:
        address = client_ip(scope, self._rate_limit.trusted_proxy_hops)
        if address is None:
            return self._throttle.key("i", b"desconhecido"), self._throttle_config.ip_failures
        campus = any(
            address.version == network.version and address in network
            for network in self._rate_limit.campus_networks
        )
        if isinstance(address, ipaddress.IPv6Address):
            value = ipaddress.ip_network((address, 64), strict=False).network_address.packed
        else:
            value = address.packed
        limit = (
            self._throttle_config.campus_ip_failures
            if campus
            else self._throttle_config.ip_failures
        )
        return self._throttle.key("i", value), limit

    async def login(self, login: str, password: str, scope: Scope) -> tuple[Account, str]:
        """Confere as credenciais e abre uma sessão; devolve a conta e o identificador do cookie."""
        text = login.strip()
        if "@" in text and not email_domain_allowed(normalize_email(text)):
            raise ApiError(
                422,
                ErrorCode.DOMAIN_NOT_ALLOWED,
                "Só e-mails @cin.ufpe.br e @ufpe.br têm acesso ao IP-Checker.",
            )
        account = await self.store.find_by_login(text)
        subject = self._throttle.key("a", account.id.bytes if account else text.lower())
        ip_key, ip_limit = self._ip_limit(scope)
        wait = self._throttle.retry_after(
            [(subject, self._throttle_config.account_failures), (ip_key, ip_limit)]
        )
        if wait is not None:
            raise ApiError(
                429,
                ErrorCode.RATE_LIMITED,
                "Muitas tentativas de entrada. Espere um pouco antes de tentar de novo.",
                retry_after_s=wait,
            )
        hashed = account.password_hash if account is not None else None
        if not await self.passwords.verify(hashed, password) or account is None:
            self._throttle.fail([subject, ip_key])
            raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, INVALID_CREDENTIALS)
        self._throttle.clear(subject)
        refusal = status_refusal(account)
        if refusal is not None:
            raise refusal
        return account, await self.open_session(account)

    async def open_session(self, account: Account) -> str:
        """Abre uma sessão para uma conta cuja identidade já foi confirmada (senha ou Google)."""
        token = new_token()
        now = self._clock()
        await self.store.create_session(
            token_hash(token),
            account.id,
            now,
            now + timedelta(seconds=self.config.absolute_timeout_s),
        )
        return token

    async def resolve(self, token: str | None) -> Account | None:
        """A conta ativa dona da sessão, ou ``None`` se a sessão não existe ou já venceu."""
        if token is None or not valid_token(token):
            return None
        hashed = token_hash(token)
        record = await self.store.get_session(hashed)
        if record is None:
            return None
        now = self._clock()
        idle = now - record.last_seen_at
        if (
            now >= record.expires_at
            or idle >= timedelta(seconds=self.config.idle_timeout_s)
            or record.account.status is not Status.ATIVO
        ):
            await self.store.delete_session(hashed)
            return None
        if idle >= timedelta(seconds=self.config.touch_interval_s):
            await self.store.touch_session(hashed, now)
        return record.account

    async def logout(self, token: str | None) -> None:
        if token is not None and valid_token(token):
            await self.store.delete_session(token_hash(token))

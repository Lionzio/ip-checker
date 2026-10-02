"""Registro, verificação de e-mail e perfil (Sprint 14; FR-23, FR-25 e FR-26).

- Registro: domínio exato, senha na política, nome e e-mail únicos, e-mails do desenvolvedor
  reservados. A conta nasce ``aguardando_verificacao`` e recebe o link por e-mail.
- Verificação: token de 256 bits, guardado só como hash, de uso único e válido por 24 h. O link
  abre uma página que confirma por POST; abrir o link (GET) não gasta o token.
- Reenvio: sempre a mesma resposta, exista a conta ou não, e no máximo 1 por minuto e 5 por dia
  por conta [PREMISSA].
- Perfil: nome, curso e tratamento; o cargo nunca. Trocar a senha pede a atual (salvo numa conta
  só do Google) e encerra as outras sessões.
"""

from __future__ import annotations

import logging
import secrets
import time
import unicodedata
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    NewAccount,
    Status,
    Treatment,
    email_domain_allowed,
    normalize_email,
)
from ipc_api.accounts.passwords import Passwords, password_problems
from ipc_api.accounts.store import VERIFICATION, AccountStore
from ipc_api.auth.sessions import token_hash
from ipc_api.auth.throttle import LoginThrottle
from ipc_api.errors import ApiError, ErrorCode
from ipc_api.mail import EmailConfig, EmailSender, EmailUnavailable, verification_message

logger = logging.getLogger(__name__)

DOMAIN_MESSAGE = "Só e-mails @cin.ufpe.br e @ufpe.br têm acesso ao IP-Checker."


@dataclass(frozen=True, slots=True)
class AccountsConfig:
    #: Endereço da página, de onde sai o link do e-mail (nunca o Host da requisição).
    public_base_url: str = "http://127.0.0.1:8180"
    token_ttl_s: int = 24 * 3600
    resend_interval_s: int = 60
    resend_per_day: int = 5
    #: Falhas da senha atual ao trocá-la, em 15 min, antes de esperar.
    password_change_failures: int = 5


def clean_text(value: str) -> str:
    """Espaços repetidos viram um; caracteres de controle não passam."""
    text = " ".join(value.split())
    if any(unicodedata.category(char).startswith("C") for char in text):
        raise ApiError(422, ErrorCode.INVALID_INPUT, "O texto tem caracteres de controle.")
    return text


def clean_name(value: str) -> str:
    name = clean_text(value)
    if not 2 <= len(name) <= 120:
        raise ApiError(422, ErrorCode.INVALID_INPUT, "O nome precisa ter entre 2 e 120 caracteres.")
    if "@" in name:
        # O login aceita nome ou e-mail e distingue os dois pelo @.
        raise ApiError(422, ErrorCode.INVALID_INPUT, "O nome não pode ter @.")
    return name


def clean_course(value: str) -> str:
    course = clean_text(value)
    if not 2 <= len(course) <= 120:
        raise ApiError(
            422, ErrorCode.INVALID_INPUT, "O curso precisa ter entre 2 e 120 caracteres."
        )
    return course


def check_password(password: str) -> None:
    problems = password_problems(password)
    if problems:
        raise ApiError(422, ErrorCode.WEAK_PASSWORD, "A senha precisa " + ", ".join(problems) + ".")


def conflict(error: AccountConflict) -> ApiError:
    if error.field == "email":
        return ApiError(409, ErrorCode.EMAIL_TAKEN, "Este e-mail já tem uma conta no IP-Checker.")
    if error.field == "google":
        return ApiError(
            409,
            ErrorCode.EMAIL_TAKEN,
            "Esta conta Google já está ligada a outra conta do IP-Checker.",
        )
    return ApiError(
        409, ErrorCode.NAME_TAKEN, "Este nome já é usado por outra conta; ele serve para entrar."
    )


class AccountService:
    def __init__(
        self,
        store: AccountStore,
        passwords: Passwords,
        sender: EmailSender,
        email: EmailConfig,
        config: AccountsConfig,
        *,
        reserved_emails: tuple[str, ...],
        throttle: LoginThrottle,
        clock: Callable[[], datetime],
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store = store
        self.passwords = passwords
        self.sender = sender
        self.email = email
        self.config = config
        self._reserved = frozenset(reserved_emails)
        self._throttle = throttle
        self._clock = clock
        self._monotonic = monotonic
        self._resends: dict[bytes, deque[float]] = {}

    # --- Registro e verificação --------------------------------------------------------------

    async def register(
        self, *, name: str, email: str, password: str, course: str, treatment: Treatment
    ) -> Account:
        address = normalize_email(email)
        if not email_domain_allowed(address):
            raise ApiError(422, ErrorCode.DOMAIN_NOT_ALLOWED, DOMAIN_MESSAGE)
        new_name, new_course = clean_name(name), clean_course(course)
        if address in self._reserved:
            raise conflict(AccountConflict("e-mail reservado", "email"))
        check_password(password)
        new = NewAccount(
            new_name, address, new_course, treatment, await self.passwords.hash(password)
        )
        try:
            account = await self.store.register(new, self._clock())
        except AccountConflict as error:
            raise conflict(error) from None
        await self._send_verification(account)
        return account

    async def _send_verification(self, account: Account) -> None:
        token = secrets.token_urlsafe(32)
        now = self._clock()
        await self.store.add_email_token(
            token_hash(token),
            account.id,
            VERIFICATION,
            now,
            now + timedelta(seconds=self.config.token_ttl_s),
        )
        base = self.config.public_base_url.rstrip("/")
        link = f"{base}/verificar?{urlencode({'token': token})}"
        message = verification_message(self.email.sender, account.primary_email, account.name, link)
        try:
            await self.sender.send(message)
        except EmailUnavailable as exc:
            logger.warning("e-mail de verificação não enviado: %s", exc)
            raise ApiError(
                503,
                ErrorCode.EMAIL_UNAVAILABLE,
                "O cadastro foi recebido, mas o e-mail de verificação não pôde ser enviado agora. "
                "Peça um novo link em alguns minutos.",
                retry_after_s=60,
            ) from None

    def _may_resend(self, account: Account) -> bool:
        key = account.id.bytes
        now = self._monotonic()
        sent = self._resends.setdefault(key, deque())
        while sent and sent[0] <= now - 24 * 3600:
            sent.popleft()
        if len(sent) >= self.config.resend_per_day or (
            sent and now - sent[-1] < self.config.resend_interval_s
        ):
            return False
        sent.append(now)
        return True

    async def resend(self, email: str) -> None:
        """Reenvia o link; a resposta é sempre a mesma, para não revelar quem tem conta."""
        address = normalize_email(email)
        if not email_domain_allowed(address):
            raise ApiError(422, ErrorCode.DOMAIN_NOT_ALLOWED, DOMAIN_MESSAGE)
        account = await self.store.find_by_login(address)
        if account is None or account.status is not Status.AGUARDANDO_VERIFICACAO:
            return
        if not self._may_resend(account):
            return
        try:
            await self._send_verification(account)
        except ApiError:
            return  # já registrado no log; a resposta continua a mesma

    async def verify(self, token: str) -> Account:
        account = await self.store.verify_email(token_hash(token), self._clock())
        if account is None:
            raise ApiError(
                422,
                ErrorCode.INVALID_TOKEN,
                "O link de verificação é inválido, já foi usado ou venceu. Peça um novo.",
            )
        return account

    # --- Perfil ------------------------------------------------------------------------------

    async def update_profile(
        self,
        account: Account,
        *,
        name: str | None,
        course: str | None,
        treatment: Treatment | None,
    ) -> Account:
        try:
            return await self.store.update_profile(
                account.id,
                clean_name(name) if name is not None else account.name,
                clean_course(course) if course is not None else account.course,
                treatment if treatment is not None else account.treatment,
            )
        except AccountConflict as error:
            raise conflict(error) from None

    async def change_password(
        self, account: Account, *, current: str | None, new: str, keep_session: bytes | None
    ) -> None:
        if account.password_hash is not None:
            key = self._throttle.key("p", account.id.bytes)
            limits = [(key, self.config.password_change_failures)]
            wait = self._throttle.retry_after(limits)
            if wait is not None:
                raise ApiError(
                    429,
                    ErrorCode.RATE_LIMITED,
                    "Muitas tentativas com a senha atual errada. Espere um pouco.",
                    retry_after_s=wait,
                )
            if current is None or not await self.passwords.verify(account.password_hash, current):
                self._throttle.fail([key])
                raise ApiError(403, ErrorCode.INVALID_CREDENTIALS, "A senha atual está incorreta.")
            self._throttle.clear(key)
        check_password(new)
        await self.store.set_password(account.id, await self.passwords.hash(new))
        # As outras sessões caem (NFR-22); a desta página continua.
        await self.store.delete_sessions(account.id, keep=keep_session)

"""Envio de e-mail (S14-02; FR-23, Q-17): o link de verificação do cadastro.

Dois transportes atrás do mesmo ``EmailSender``, escolhidos por ``IPC_EMAIL_TRANSPORT``:

- ``smtp`` (padrão): serve a qualquer provedor (servidor institucional ou serviço transacional) e,
  no desenvolvimento, ao Mailpit do compose, que captura as mensagens sem enviá-las. Tudo vem de
  ``IPC_SMTP_*``; sem ``IPC_SMTP_HOST``, o envio fica desligado e o registro responde 503
  ``EMAIL_UNAVAILABLE``. O ``smtplib`` roda numa thread, com tempo-limite.
- ``brevo``: a API HTTPS do Brevo, com a chave em ``IPC_EMAIL_API_KEY``. O plano gratuito do
  Render bloqueia as portas SMTP de saída (25, 465 e 587) desde 09/2025; por HTTPS, o piloto não
  depende do plano. A resposta do provedor nunca vai para o log nem para o erro.

O link nunca é montado a partir do ``Host`` da requisição, só de ``IPC_PUBLIC_BASE_URL``
(ameaça 21).
"""

from __future__ import annotations

import smtplib
import ssl
from collections.abc import Mapping
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr
from html import escape
from typing import Literal, Protocol

import httpx2
from starlette.concurrency import run_in_threadpool

Security = Literal["starttls", "ssl", "none"]
Transport = Literal["smtp", "brevo"]

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class EmailUnavailable(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """O e-mail não pôde ser enviado (sem configuração ou servidor fora do ar)."""


@dataclass(frozen=True, slots=True)
class EmailConfig:
    transport: Transport = "smtp"
    #: Chave da API HTTPS (transporte ``brevo``).
    api_key: str | None = field(default=None, repr=False)
    host: str | None = None
    port: int = 587
    security: Security = "starttls"
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    sender: str = "IP-Checker <nao-responda@ip-checker.local>"
    timeout_s: float = 10.0

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> EmailConfig:
        defaults = cls()
        transport = env.get("IPC_EMAIL_TRANSPORT", defaults.transport)
        if transport not in ("smtp", "brevo"):
            raise ValueError(f"IPC_EMAIL_TRANSPORT inválida: {transport!r}. Use smtp ou brevo.")
        api_key = env.get("IPC_EMAIL_API_KEY") or None
        if transport == "brevo" and api_key is None:
            raise ValueError("IPC_EMAIL_TRANSPORT=brevo exige IPC_EMAIL_API_KEY.")
        security = env.get("IPC_SMTP_SECURITY", defaults.security)
        if security not in ("starttls", "ssl", "none"):
            raise ValueError(
                f"IPC_SMTP_SECURITY inválida: {security!r}. Use starttls, ssl ou none."
            )
        return cls(
            transport=transport,  # type: ignore[arg-type]  # conferido acima
            api_key=api_key,
            host=env.get("IPC_SMTP_HOST") or None,
            port=int(env.get("IPC_SMTP_PORT", defaults.port)),
            security=security,  # type: ignore[arg-type]  # conferido acima
            username=env.get("IPC_SMTP_USERNAME") or None,
            password=env.get("IPC_SMTP_PASSWORD") or None,
            sender=env.get("IPC_EMAIL_FROM", defaults.sender),
        )


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """Envia a mensagem ou levanta ``EmailUnavailable``."""


class SmtpSender:
    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    async def send(self, message: EmailMessage) -> None:
        if self.config.host is None:
            raise EmailUnavailable("IPC_SMTP_HOST não definida")
        try:
            await run_in_threadpool(self._send, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailUnavailable(type(exc).__name__) from exc

    def _send(self, message: EmailMessage) -> None:
        config = self.config
        assert config.host is not None  # noqa: S101 - conferido em send()
        if config.security == "ssl":
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                config.host,
                config.port,
                timeout=config.timeout_s,
                context=ssl.create_default_context(),
            )
        else:
            client = smtplib.SMTP(config.host, config.port, timeout=config.timeout_s)
        with client:
            if config.security == "starttls":
                client.starttls(context=ssl.create_default_context())
            if config.username is not None and config.password is not None:
                client.login(config.username, config.password)
            client.send_message(message)


class BrevoSender:
    """API transacional do Brevo por HTTPS (``POST /v3/smtp/email``)."""

    def __init__(self, config: EmailConfig, transport: httpx2.AsyncBaseTransport | None = None):
        self.config = config
        self._transport = transport

    async def send(self, message: EmailMessage) -> None:
        if self.config.api_key is None:
            raise EmailUnavailable("IPC_EMAIL_API_KEY não definida")
        try:
            async with httpx2.AsyncClient(
                transport=self._transport, timeout=self.config.timeout_s, trust_env=False
            ) as client:
                response = await client.post(
                    BREVO_URL,
                    json=brevo_payload(message),
                    headers={"api-key": self.config.api_key, "accept": "application/json"},
                )
        except httpx2.HTTPError as exc:
            raise EmailUnavailable(type(exc).__name__) from exc
        if not response.is_success:
            raise EmailUnavailable(f"HTTP {response.status_code}")


def brevo_payload(message: EmailMessage) -> dict[str, object]:
    """O corpo da API do Brevo a partir da mesma mensagem que o SMTP envia."""
    sender_name, sender_email = parseaddr(str(message["From"]))
    sender: dict[str, str] = {"email": sender_email}
    if sender_name:
        sender["name"] = sender_name
    text = message.get_body(("plain",))
    html = message.get_body(("html",))
    payload: dict[str, object] = {
        "sender": sender,
        "to": [{"email": address} for _, address in getaddresses([str(message["To"])])],
        "subject": str(message["Subject"]),
    }
    if text is not None:
        payload["textContent"] = text.get_content()
    if html is not None:
        payload["htmlContent"] = html.get_content()
    return payload


def email_sender_for(config: EmailConfig) -> EmailSender:
    return BrevoSender(config) if config.transport == "brevo" else SmtpSender(config)


class MemorySender:
    """Guarda as mensagens em vez de enviá-las (testes)."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []
        self.available = True

    async def send(self, message: EmailMessage) -> None:
        if not self.available:
            raise EmailUnavailable("envio simulado fora do ar")
        self.messages.append(message)


def verification_message(sender: str, to: str, name: str, link: str) -> EmailMessage:
    """O e-mail do FR-23, com o texto "Clique aqui para verificar seu acesso."."""
    message = EmailMessage()
    message["Subject"] = "Confirme o seu cadastro no IP-Checker"
    message["From"] = sender
    message["To"] = to
    message.set_content(
        f"Olá, {name}.\n\n"
        "Recebemos um pedido de cadastro no IP-Checker com este e-mail. Para confirmar, abra o "
        f"link abaixo (vale por 24 horas e só uma vez):\n\n{link}\n\n"
        "Depois da confirmação, o pedido vai para a aprovação de um monitor-chefe, de um "
        "professor ou do desenvolvedor.\n\n"
        "Se você não pediu este cadastro, ignore esta mensagem.\n"
    )
    message.add_alternative(
        f"<p>Olá, {escape(name)}.</p>"
        "<p>Recebemos um pedido de cadastro no IP-Checker com este e-mail.</p>"
        f'<p><a href="{escape(link, quote=True)}">Clique aqui para verificar seu acesso.</a></p>'
        "<p>O link vale por 24 horas e só uma vez. Depois da confirmação, o pedido vai para a "
        "aprovação de um monitor-chefe, de um professor ou do desenvolvedor.</p>"
        "<p>Se você não pediu este cadastro, ignore esta mensagem.</p>",
        subtype="html",
    )
    return message


def reset_message(sender: str, to: str, name: str, link: str) -> EmailMessage:
    """O e-mail do "esqueci minha senha" (S24-04): link de uso único, válido por 1 hora."""
    message = EmailMessage()
    message["Subject"] = "Redefina a sua senha do IP-Checker"
    message["From"] = sender
    message["To"] = to
    message.set_content(
        f"Olá, {name}.\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta no IP-Checker. Para escolher uma "
        f"senha nova, abra o link abaixo (vale por 1 hora e só uma vez):\n\n{link}\n\n"
        "Ao definir a senha nova, as sessões abertas da sua conta são encerradas.\n\n"
        "Se você não pediu isso, ignore esta mensagem: a sua senha continua a mesma.\n"
    )
    message.add_alternative(
        f"<p>Olá, {escape(name)}.</p>"
        "<p>Recebemos um pedido para redefinir a senha da sua conta no IP-Checker.</p>"
        f'<p><a href="{escape(link, quote=True)}">Clique aqui para escolher uma senha nova.</a></p>'
        "<p>O link vale por 1 hora e só uma vez. Ao definir a senha nova, as sessões abertas "
        "da sua conta são encerradas.</p>"
        "<p>Se você não pediu isso, ignore esta mensagem: a sua senha continua a mesma.</p>",
        subtype="html",
    )
    return message

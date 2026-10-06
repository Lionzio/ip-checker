"""Configuração da API, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from ipc_api.accounts.models import email_domain_allowed, normalize_email
from ipc_api.admission import AdmissionConfig
from ipc_api.auth.accounts import AccountsConfig
from ipc_api.auth.google import GoogleConfig
from ipc_api.auth.sessions import SessionConfig
from ipc_api.auth.throttle import LoginThrottleConfig
from ipc_api.edge import parse_origins
from ipc_api.feedback.providers import LlmSettings
from ipc_api.feedback.service import FeedbackLimits
from ipc_api.mail import EmailConfig
from ipc_api.ratelimit import RateLimitConfig, parse_networks
from ipc_api.slo import SloConfig
from ipc_api.telemetry import TelemetryConfig

KIB = 1024


def parse_lists(value: str) -> frozenset[int]:
    """Converte ``"1,2"`` em ``{1, 2}``; recusa listas fora de 1 a 6 (falha ao subir, FR-15)."""
    try:
        lists = frozenset(int(item) for item in value.split(",") if item.strip())
    except ValueError:
        lists = frozenset()
    if not lists or not lists <= set(range(1, 7)):
        raise ValueError(f"IPC_ENABLED_LISTS inválida: {value!r}. Use números de 1 a 6, como 1,2.")
    return lists


#: E-mails da conta do desenvolvedor (P-14): o primeiro é o principal.
DEVELOPER_EMAILS = ("vlacg@cin.ufpe.br", "vinicius.leoncio@ufpe.br")


def parse_emails(value: str) -> tuple[str, ...]:
    emails = tuple(normalize_email(item) for item in value.split(",") if item.strip())
    if not emails or not all(email_domain_allowed(email) for email in emails):
        raise ValueError(
            f"IPC_DEV_EMAILS inválida: {value!r}. Use e-mails @cin.ufpe.br ou @ufpe.br."
        )
    return emails


@dataclass(frozen=True, slots=True)
class DeveloperSettings:
    """A conta criada por *seed* na subida da API (P-14, S13-01)."""

    #: Nome completo e curso do autor (02/10/2026). Editáveis no perfil; o seed não altera uma
    #: conta que já existe.
    name: str = "Vinícius Leôncio de Andrade Corrêa Gondim"
    course: str = "Ciência da Computação"
    emails: tuple[str, ...] = DEVELOPER_EMAILS
    #: Senha inicial, usada só na criação da conta. Sem ela, a conta nasce sem senha.
    initial_password: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class ApiSettings:
    analyzer_url: str = "http://127.0.0.1:8001"
    #: Listas habilitadas na ferramenta (ENABLED_LISTS): a 1 desde o MVP, a 2 desde a Sprint 20, a
    #: 3 e a 4 desde a 22 e a 5 e a 6 desde a 23. Uma lista só é habilitada depois que as regras
    #: dela estão no ruleset e testadas.
    enabled_lists: frozenset[int] = field(default_factory=lambda: frozenset(range(1, 7)))
    #: Tempo máximo de uma chamada ao analyzer: 2 s de análise mais a ida e a volta.
    analyzer_timeout_s: float = 3.0
    #: Corpo máximo aceito antes de ler a requisição. Nas Fases 0 e 2 o Caddy também aplica esse
    #: limite; na Fase 1 (Render) não há Caddy, e a API é a primeira barreira (DoD, item 1).
    max_body_bytes: int = 128 * KIB
    #: Logs JSON no stdout (S9-01). Ligado por padrão; desligar só para depurar localmente.
    json_logs: bool = True
    #: Limite de taxa por cliente anônimo e por IP (S10-01, FR-19).
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    #: Controle de admissão das chamadas ao analyzer (S10-01, NFR-05).
    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    #: Origens da página que podem chamar a API pelo navegador (CORS). Vazio nas Fases 0 e 2,
    #: em que página e API têm a mesma origem; no piloto, o endereço da página na Vercel.
    cors_origins: tuple[str, ...] = ()
    #: Cabeçalho HSTS nas respostas (piloto: a API é servida em HTTPS pelo Render).
    hsts: bool = False
    #: Versão implantada (commit), mostrada em /ready para o pipeline saber que o deploy entrou.
    release: str | None = None
    #: Banco de contas e sessões (S13-01), com o usuário da API, membro de ipc_app.
    database_url: str | None = field(default=None, repr=False)
    #: Cookie e tempos da sessão (S13-02, NFR-22).
    session: SessionConfig = field(default_factory=SessionConfig)
    #: Bloqueio de login por falhas (S13-02, FR-25).
    login_throttle: LoginThrottleConfig = field(default_factory=LoginThrottleConfig)
    #: Origens aceitas, além da própria, em requisições que mudam estado (CSRF, ADR-04).
    allowed_origins: tuple[str, ...] = ()
    developer: DeveloperSettings = field(default_factory=DeveloperSettings)
    #: Envio de e-mail (S14-02, Q-17): SMTP do provedor ou, no compose, o Mailpit.
    email: EmailConfig = field(default_factory=EmailConfig)
    #: Entrada pelo Google (S16-01); desligada sem IPC_GOOGLE_CLIENT_ID e IPC_GOOGLE_CLIENT_SECRET.
    google: GoogleConfig = field(default_factory=GoogleConfig)
    #: Feedback por LLM (S18): IA principal e de reserva; sem nenhuma, só modelos de texto.
    llm: LlmSettings = field(default_factory=LlmSettings)
    feedback_limits: FeedbackLimits = field(default_factory=FeedbackLimits)
    #: Registro, verificação e perfil (S14); o endereço público monta o link do e-mail.
    accounts: AccountsConfig = field(default_factory=AccountsConfig)
    #: Telemetria anônima (S21-01): grava no mesmo banco, com o usuário da API (ipc_writer).
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    #: Limites dos alertas de latência e de erro em /health/slo (S21-02, NFR-15).
    slo: SloConfig = field(default_factory=SloConfig)

    @property
    def page_origin(self) -> str:
        """A origem da página (``IPC_PUBLIC_BASE_URL``).

        No piloto, a Vercel repassa ``/api/*`` ao Render (S16-02): a API vê o ``Host`` do Render, e
        o navegador manda o ``Origin`` da página.
        """
        parts = urlsplit(self.accounts.public_base_url)
        return f"{parts.scheme}://{parts.netloc}".lower()

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApiSettings:
        env = os.environ if environ is None else environ
        defaults = cls()
        lists = env.get("IPC_ENABLED_LISTS")
        return cls(
            analyzer_url=env.get("IPC_ANALYZER_URL", defaults.analyzer_url),
            enabled_lists=parse_lists(lists) if lists is not None else defaults.enabled_lists,
            analyzer_timeout_s=float(
                env.get("IPC_ANALYZER_TIMEOUT_S", defaults.analyzer_timeout_s)
            ),
            max_body_bytes=int(env.get("IPC_MAX_BODY_BYTES", defaults.max_body_bytes)),
            json_logs=env.get("IPC_JSON_LOGS", "1") != "0",
            rate_limit=_rate_limit_from_env(env),
            admission=_admission_from_env(env),
            cors_origins=parse_origins(env.get("IPC_CORS_ORIGINS", "")),
            hsts=env.get("IPC_HSTS", "0") == "1",
            # O Render informa o commit implantado em RENDER_GIT_COMMIT.
            release=env.get("IPC_RELEASE") or env.get("RENDER_GIT_COMMIT") or None,
            database_url=env.get("IPC_DATABASE_URL") or None,
            session=_session_from_env(env),
            login_throttle=_login_throttle_from_env(env),
            allowed_origins=parse_origins(env.get("IPC_ALLOWED_ORIGINS", "")),
            developer=_developer_from_env(env),
            email=EmailConfig.from_env(env),
            google=GoogleConfig.from_env(env),
            llm=LlmSettings.from_env(env),
            feedback_limits=FeedbackLimits.from_env(env),
            accounts=AccountsConfig(
                public_base_url=env.get("IPC_PUBLIC_BASE_URL", AccountsConfig().public_base_url)
            ),
            telemetry=TelemetryConfig.from_env(env),
            slo=SloConfig.from_env(env),
        )


def _session_from_env(env: Mapping[str, str]) -> SessionConfig:
    defaults = SessionConfig()
    return SessionConfig(
        cookie_secure=env.get("IPC_SESSION_COOKIE_SECURE", "1") != "0",
        idle_timeout_s=int(env.get("IPC_SESSION_IDLE_TIMEOUT_S", defaults.idle_timeout_s)),
        absolute_timeout_s=int(
            env.get("IPC_SESSION_ABSOLUTE_TIMEOUT_S", defaults.absolute_timeout_s)
        ),
    )


def _login_throttle_from_env(env: Mapping[str, str]) -> LoginThrottleConfig:
    defaults = LoginThrottleConfig()
    return LoginThrottleConfig(
        account_failures=int(env.get("IPC_LOGIN_ACCOUNT_FAILURES", defaults.account_failures)),
        ip_failures=int(env.get("IPC_LOGIN_IP_FAILURES", defaults.ip_failures)),
        campus_ip_failures=int(
            env.get("IPC_LOGIN_CAMPUS_IP_FAILURES", defaults.campus_ip_failures)
        ),
    )


def _developer_from_env(env: Mapping[str, str]) -> DeveloperSettings:
    defaults = DeveloperSettings()
    emails = env.get("IPC_DEV_EMAILS")
    return DeveloperSettings(
        name=env.get("IPC_DEV_NAME", defaults.name).strip(),
        course=env.get("IPC_DEV_COURSE", defaults.course).strip(),
        emails=parse_emails(emails) if emails is not None else defaults.emails,
        initial_password=env.get("IPC_DEV_INITIAL_PASSWORD") or None,
    )


def _rate_limit_from_env(env: Mapping[str, str]) -> RateLimitConfig:
    defaults = RateLimitConfig()
    cidrs = env.get("IPC_RATE_LIMIT_CAMPUS_CIDRS")
    return RateLimitConfig(
        client_per_min=int(env.get("IPC_RATE_LIMIT_CLIENT_PER_MIN", defaults.client_per_min)),
        ip_per_min=int(env.get("IPC_RATE_LIMIT_IP_PER_MIN", defaults.ip_per_min)),
        campus_per_min=int(env.get("IPC_RATE_LIMIT_CAMPUS_PER_MIN", defaults.campus_per_min)),
        campus_networks=parse_networks(cidrs) if cidrs is not None else defaults.campus_networks,
        trusted_proxy_hops=int(env.get("IPC_TRUSTED_PROXY_HOPS", defaults.trusted_proxy_hops)),
        max_keys=int(env.get("IPC_RATE_LIMIT_MAX_KEYS", defaults.max_keys)),
    )


def _admission_from_env(env: Mapping[str, str]) -> AdmissionConfig:
    defaults = AdmissionConfig()
    return AdmissionConfig(
        capacity=int(env.get("IPC_ADMISSION_CAPACITY", defaults.capacity)),
        max_waiting=int(env.get("IPC_ADMISSION_MAX_WAITING", defaults.max_waiting)),
        max_wait_s=float(env.get("IPC_ADMISSION_MAX_WAIT_S", defaults.max_wait_s)),
    )

"""Configuração da API, lida de variáveis de ambiente ``IPC_*``."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from ipc_api.accounts.models import email_domain_allowed, normalize_email
from ipc_api.admission import AdmissionConfig
from ipc_api.auth.accounts import AccountsConfig
from ipc_api.auth.google import GoogleConfig
from ipc_api.auth.sessions import SessionConfig
from ipc_api.auth.throttle import LoginThrottleConfig
from ipc_api.edge import parse_origins
from ipc_api.edge_gate import validate_edge_secret
from ipc_api.feedback.providers import LlmSettings
from ipc_api.feedback.service import FeedbackLimits
from ipc_api.gabaritos import GabaritosConfig
from ipc_api.housekeeping import HousekeepingConfig
from ipc_api.mail import EmailConfig
from ipc_api.ratelimit import RateLimitConfig, parse_networks
from ipc_api.slo import SloConfig
from ipc_api.telemetry import TelemetryConfig

KIB = 1024
#: Tempo máximo de uma análise no pool do analyzer (``IPC_TIMEOUT_S``, o mesmo nome dos dois
#: lados). Um teste garante que ele acompanha o padrão do pool.
ANALYSIS_TIMEOUT_S = 2.0
#: A ida e a volta até o analyzer, somadas ao tempo da análise (S25-04).
ANALYZER_MARGIN_S = 1.0


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


AiIndicators = Literal["0", "chefia", "1"]


def _ai_indicators_from_env(env: Mapping[str, str]) -> AiIndicators:
    """Um valor fora de ``0``, ``chefia`` e ``1`` derruba a API na subida (S42-05): um erro de
    digitação no Render não pode ligar o painel para toda a equipe."""
    value = env.get("IPC_AI_INDICATORS", "0").strip()
    if value == "0":
        return "0"
    if value == "chefia":
        return "chefia"
    if value == "1":
        return "1"
    raise ValueError(f"IPC_AI_INDICATORS inválida: {value!r}. Use 0, chefia ou 1.")


#: O ID da extensão do Dikastis do repositório (``extensao/manifest.json``, chave pública fixa).
DEFAULT_EXTENSION_ID = "hbndgmplpohgfbmdemopbbibfocbkdhh"
_EXTENSION_ID = re.compile(r"[a-p]{32}")


def _extension_ids(value: str | None) -> tuple[str, ...]:
    """``IPC_IMPORT_EXTENSION_IDS``: IDs separados por vírgula; vazia ou ausente, o padrão."""
    if value is None or not value.strip():
        return (DEFAULT_EXTENSION_ID,)
    ids = tuple(item.strip() for item in value.split(",") if item.strip())
    for item in ids:
        if not _EXTENSION_ID.fullmatch(item):
            raise ValueError(
                f"IPC_IMPORT_EXTENSION_IDS inválida: {item!r} não é um ID de extensão."
            )
    return ids


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
    #: Prazo de uma chamada ao analyzer: o tempo da análise mais a ida e a volta. Derivado do
    #: prazo do pool (``IPC_TIMEOUT_S``) quando ``IPC_ANALYZER_TIMEOUT_S`` não é definida.
    analyzer_timeout_s: float = ANALYSIS_TIMEOUT_S + ANALYZER_MARGIN_S
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
    #: Indícios de uso de IA na verificação (ADR-08, S29; S42-05): ``0`` desliga, ``chefia`` liga
    #: só para o desenvolvedor, os professores e os monitores-chefes, e ``1`` para toda a equipe.
    #: Desligados por padrão; a política pede a chefia primeiro (docs/indicios-de-ia.md).
    ai_indicators: AiIndicators = "0"
    #: Versão implantada (commit), mostrada em /ready para o pipeline saber que o deploy entrou.
    release: str | None = None
    #: Segredo que o middleware da página manda em ``/api/*`` (S30-03, ``ipc_api.edge_gate``).
    #: Vazio: a API atende qualquer origem de rede, como no compose.
    edge_secret: str | None = field(default=None, repr=False)
    #: Banco de contas e sessões (S13-01), com o usuário da API, membro de ipc_app.
    database_url: str | None = field(default=None, repr=False)
    #: Cookie e tempos da sessão (S13-02, NFR-22).
    session: SessionConfig = field(default_factory=SessionConfig)
    #: Bloqueio de login por falhas (S13-02, FR-25).
    login_throttle: LoginThrottleConfig = field(default_factory=LoginThrottleConfig)
    #: Origens aceitas, além da própria, em requisições que mudam estado (CSRF, ADR-04).
    allowed_origins: tuple[str, ...] = ()
    #: A extensão do Dikastis (S50-04, ADR-15): as origens chrome-extension://<id> aceitas só nas
    #: rotas /api/v1/import/*. O padrão é o ID fixo da extensão do repositório (extensao/).
    import_extension_ids: tuple[str, ...] = (DEFAULT_EXTENSION_ID,)
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
    #: Limpeza diária do banco e expurgo de contas sem atividade (S25-03).
    housekeeping: HousekeepingConfig = field(default_factory=HousekeepingConfig)
    #: Limites dos alertas de latência e de erro em /health/slo (S21-02, NFR-15).
    slo: SloConfig = field(default_factory=SloConfig)
    #: Gabaritos na memória da API e o alerta de possível vazamento (ADR-11, S32-02).
    gabaritos: GabaritosConfig = field(default_factory=GabaritosConfig)

    def check(self) -> None:
        """Recusa configurações perigosas na subida (S25-04).

        Com o cookie de sessão ``Secure``, o endereço público tem de ser ``https://``: um link de
        e-mail em ``http://`` levaria a uma página sem a sessão (e ao token em texto claro). Só o
        endereço local (``localhost``, ``127.0.0.1``, ``::1``) fica de fora, porque o navegador o
        trata como seguro.
        """
        parts = urlsplit(self.accounts.public_base_url)
        local = (parts.hostname or "") in {"localhost", "127.0.0.1", "::1"}
        if self.session.cookie_secure and parts.scheme != "https" and not local:
            raise ValueError(
                "IPC_PUBLIC_BASE_URL precisa começar com https:// quando o cookie de sessão é "
                f"seguro (IPC_SESSION_COOKIE_SECURE=1); recebido: {parts.scheme}://{parts.netloc}"
            )

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
                env.get(
                    "IPC_ANALYZER_TIMEOUT_S",
                    float(env.get("IPC_TIMEOUT_S", ANALYSIS_TIMEOUT_S)) + ANALYZER_MARGIN_S,
                )
            ),
            max_body_bytes=int(env.get("IPC_MAX_BODY_BYTES", defaults.max_body_bytes)),
            json_logs=env.get("IPC_JSON_LOGS", "1") != "0",
            rate_limit=_rate_limit_from_env(env),
            admission=_admission_from_env(env),
            cors_origins=parse_origins(env.get("IPC_CORS_ORIGINS", "")),
            hsts=env.get("IPC_HSTS", "0") == "1",
            ai_indicators=_ai_indicators_from_env(env),
            # O Render informa o commit implantado em RENDER_GIT_COMMIT.
            release=env.get("IPC_RELEASE") or env.get("RENDER_GIT_COMMIT") or None,
            database_url=env.get("IPC_DATABASE_URL") or None,
            edge_secret=validate_edge_secret(env.get("IPC_EDGE_SECRET")),
            session=_session_from_env(env),
            login_throttle=_login_throttle_from_env(env),
            allowed_origins=parse_origins(env.get("IPC_ALLOWED_ORIGINS", "")),
            import_extension_ids=_extension_ids(env.get("IPC_IMPORT_EXTENSION_IDS")),
            developer=_developer_from_env(env),
            email=EmailConfig.from_env(env),
            google=GoogleConfig.from_env(env),
            llm=LlmSettings.from_env(env),
            gabaritos=GabaritosConfig.from_env(env),
            feedback_limits=FeedbackLimits.from_env(env),
            accounts=AccountsConfig(
                public_base_url=env.get("IPC_PUBLIC_BASE_URL", AccountsConfig().public_base_url)
            ),
            telemetry=TelemetryConfig.from_env(env),
            housekeeping=HousekeepingConfig.from_env(env),
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
        trust_forwarded_header=env.get("IPC_TRUST_FORWARDED_HEADER", "0") == "1",
        max_keys=int(env.get("IPC_RATE_LIMIT_MAX_KEYS", defaults.max_keys)),
        api_ip_per_min=int(env.get("IPC_RATE_LIMIT_API_IP_PER_MIN", defaults.api_ip_per_min)),
        api_campus_per_min=int(
            env.get("IPC_RATE_LIMIT_API_CAMPUS_PER_MIN", defaults.api_campus_per_min)
        ),
        edge_ip_header=env.get("IPC_RATE_LIMIT_EDGE_HEADER", defaults.edge_ip_header).lower(),
        edge_anonymous_per_min=int(
            env.get("IPC_RATE_LIMIT_EDGE_ANONYMOUS_PER_MIN", defaults.edge_anonymous_per_min)
        ),
    )


def _admission_from_env(env: Mapping[str, str]) -> AdmissionConfig:
    defaults = AdmissionConfig()
    return AdmissionConfig(
        capacity=int(env.get("IPC_ADMISSION_CAPACITY", defaults.capacity)),
        max_waiting=int(env.get("IPC_ADMISSION_MAX_WAITING", defaults.max_waiting)),
        max_wait_s=float(env.get("IPC_ADMISSION_MAX_WAIT_S", defaults.max_wait_s)),
    )

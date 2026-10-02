"""Modelo das contas (blueprint 5.2.5): cargos, status, tratamento e e-mails aceitos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

#: Domínios aceitos, comparados exatamente depois do @ e sem diferenciar maiúsculas (P-13).
ALLOWED_DOMAINS = frozenset({"cin.ufpe.br", "ufpe.br"})
MAX_EMAIL = 254


class Role(StrEnum):
    """Cargos, do maior para o menor (P-14)."""

    DESENVOLVEDOR = "desenvolvedor"
    PROFESSOR = "professor"
    MONITOR_CHEFE = "monitor_chefe"
    MONITOR = "monitor"


#: Como cada cargo aparece na interface. O desenvolvedor aparece como "Monitor e desenvolvedor"
#: (pedido do autor em 02/10/2026); no feedback, ele usa a linha "Monitor" da tabela do FR-30.
ROLE_LABELS = {
    Role.DESENVOLVEDOR: "Monitor e desenvolvedor",
    Role.PROFESSOR: "Professor",
    Role.MONITOR_CHEFE: "Monitor-chefe",
    Role.MONITOR: "Monitor",
}


class Status(StrEnum):
    AGUARDANDO_VERIFICACAO = "aguardando_verificacao"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    ATIVO = "ativo"
    RECUSADO = "recusado"
    EX_MONITOR = "ex_monitor"
    CONSELHEIRO = "conselheiro"
    INATIVO = "inativo"


#: Status de quem foi removido da equipe (FR-27): a conta continua, sem acesso.
REMOVED = frozenset({Status.EX_MONITOR, Status.CONSELHEIRO, Status.INATIVO})

#: Como cada status aparece na tela de gerenciamento (FR-28).
STATUS_LABELS = {
    Status.AGUARDANDO_VERIFICACAO: "E-mail não confirmado",
    Status.AGUARDANDO_APROVACAO: "Pendente",
    Status.ATIVO: "Ativo",
    Status.RECUSADO: "Recusado",
    Status.EX_MONITOR: "Ex-monitor",
    Status.CONSELHEIRO: "Conselheiro",
    Status.INATIVO: "Inativo",
}


class Treatment(StrEnum):
    """Como a pessoa quer ser tratada no feedback (FR-26). Só o titular vê."""

    MASCULINO = "masculino"
    FEMININO = "feminino"
    NEUTRO = "neutro"


class SignupMethod(StrEnum):
    SENHA = "senha"
    GOOGLE = "google"
    SEED = "seed"


def normalize_email(value: str) -> str:
    return value.strip().lower()


def email_domain_allowed(email: str) -> bool:
    """Domínio exato depois do único @: ``x@xcin.ufpe.br`` e ``x@ee.ufpe.br`` não passam."""
    local, at, domain = email.rpartition("@")
    return bool(at) and bool(local) and "@" not in local and domain in ALLOWED_DOMAINS


@dataclass(frozen=True, slots=True)
class Account:
    id: UUID
    name: str
    course: str
    treatment: Treatment
    role: Role | None
    status: Status
    ja_foi_monitor_chefe: bool
    password_hash: str | None
    signup_method: SignupMethod
    #: O primeiro é o principal.
    emails: tuple[str, ...]
    created_at: datetime
    #: Identificador da conta Google ligada (``sub`` do ID token), se houver (FR-24).
    google_sub: str | None = None

    @property
    def primary_email(self) -> str:
        return self.emails[0]


@dataclass(frozen=True, slots=True)
class SessionRecord:
    account: Account
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class DeveloperSeed:
    """A conta do desenvolvedor, criada sem aprovação (P-14)."""

    name: str
    course: str
    emails: tuple[str, ...]
    #: Hash da senha inicial; só é usado se a conta ainda não existir.
    password_hash: str | None


@dataclass(frozen=True, slots=True)
class NewGoogleAccount:
    """Um registro pelo Google (FR-24): e-mail já verificado pelo Google, sem senha."""

    name: str
    email: str
    course: str
    treatment: Treatment
    google_sub: str


@dataclass(frozen=True, slots=True)
class NewAccount:
    """Um pedido de registro por e-mail e senha (FR-23), já validado."""

    name: str
    email: str
    course: str
    treatment: Treatment
    password_hash: str


class AccountConflict(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """Nome, e-mail ou conta Google já pertence a outra conta. ``field``: nome, email ou google."""

    def __init__(self, message: str, field: str = "nome") -> None:
        super().__init__(message)
        self.field = field


class StoreUnavailable(Exception):  # noqa: N818 - é um estado, não um erro de programação
    """O banco não respondeu; a API responde 503 ``DATABASE_UNAVAILABLE``."""

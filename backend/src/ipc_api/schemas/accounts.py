"""Contas e sessão da equipe (Sprint 13 em diante): entrar, registrar, perfil e gerenciamento.

Parte do contrato da API (5.2.2), dividido em módulos na S39-02; importe de ``ipc_api.schemas``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from .common import _Strict

# ---------------------------------------------------------------------------------------------
# Acesso restrito à equipe (Sprint 13)
# ---------------------------------------------------------------------------------------------

RoleName = Literal["desenvolvedor", "professor", "monitor_chefe", "monitor"]
TreatmentName = Literal["masculino", "feminino", "neutro"]
StatusName = Literal[
    "aguardando_verificacao",
    "aguardando_aprovacao",
    "ativo",
    "recusado",
    "ex_monitor",
    "conselheiro",
    "inativo",
]
ActionName = Literal["aprovar", "recusar", "alterar_cargo", "remover", "reativar"]


class LoginRequest(_Strict):
    login: Annotated[str, StringConstraints(min_length=1, max_length=254)] = Field(
        description="Nome ou e-mail institucional (@cin.ufpe.br ou @ufpe.br)."
    )
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)] = Field(
        description="Senha da conta. Nunca é registrada."
    )


Text120 = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Password = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Email = Annotated[str, StringConstraints(min_length=3, max_length=254)]
SessionToken = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{43}$")]


class RegisterRequest(_Strict):
    name: Text120 = Field(description="Nome; único sem diferenciar maiúsculas e usado para entrar.")
    email: Email = Field(description="E-mail institucional (@cin.ufpe.br ou @ufpe.br).")
    password: Password = Field(
        description="Pelo menos 9 caracteres, 1 letra maiúscula e 1 caractere especial."
    )
    course: Text120
    treatment: TreatmentName = Field(description="Como a pessoa quer ser tratada no feedback.")


class RegisterResponse(_Strict):
    status: Literal["aguardando_verificacao"]
    email: str = Field(description="Para onde o link de verificação foi enviado.")


class VerifyRequest(_Strict):
    token: SessionToken = Field(description="O token do link enviado por e-mail.")


class VerifyResponse(_Strict):
    status: Literal["aguardando_aprovacao"]


class AuthOptions(_Strict):
    google: bool = Field(description="A entrada pelo Google está configurada (FR-24).")
    feedback_ai: bool = Field(
        description="Há IA configurada para o feedback; sem ela, o texto é montado por modelos."
    )
    ai_indicators: bool = Field(
        description="Os indícios de uso de IA estão ligados neste servidor (ADR-08, S29)."
    )


class GooglePending(_Strict):
    email: str = Field(description="O e-mail confirmado pelo Google.")
    name: str = Field(description="O nome da conta Google, só como sugestão (pode vir vazio).")


class GoogleSignup(_Strict):
    name: Text120
    course: Text120
    treatment: TreatmentName = Field(description="Como a pessoa quer ser tratada no feedback.")


class GoogleSignupResponse(_Strict):
    status: Literal["aguardando_aprovacao"]
    email: str


class ResendRequest(_Strict):
    email: Email


class ForgotPasswordRequest(_Strict):
    email: Email


class ResetPasswordRequest(_Strict):
    token: SessionToken = Field(description="O token do link de redefinição enviado por e-mail.")
    new_password: Password


class ProfileUpdate(_Strict):
    name: Text120 | None = None
    course: Text120 | None = None
    treatment: TreatmentName | None = None


class PasswordChange(_Strict):
    current_password: Password | None = Field(
        default=None, description="Obrigatória, a não ser numa conta criada só pelo Google."
    )
    new_password: Password


class AccountResponse(_Strict):
    """A conta de quem está logado. O tratamento só aparece para o próprio titular (FR-26)."""

    name: str
    email: str = Field(description="E-mail principal.")
    course: str
    treatment: TreatmentName
    role: RoleName
    role_label: str = Field(
        description=(
            'Como o cargo aparece na interface; o desenvolvedor aparece como "Monitor e '
            'desenvolvedor".'
        )
    )
    has_password: bool = Field(
        description="Falso numa conta criada pelo Google que ainda não definiu uma senha."
    )
    can_manage: bool = Field(
        description="Verdadeiro para quem acessa o gerenciamento da equipe (FR-28)."
    )
    can_view_log: bool = Field(
        description=(
            "Verdadeiro para quem vê o registro das ações de gerenciamento: desenvolvedor e "
            "professores (REC-06)."
        )
    )


class ManagedAccount(_Strict):
    """Uma conta vista no gerenciamento (FR-28). Nunca traz o tratamento (FR-26)."""

    id: UUID
    name: str
    email: str = Field(description="E-mail principal.")
    course: str
    signup_method: Literal["senha", "google", "seed"]
    requested_at: datetime = Field(description="Data do pedido de cadastro.")
    role: RoleName | None = Field(description="Vazio num pedido; numa conta removida, o último.")
    role_label: str | None
    status: StatusName
    status_label: str
    actions: list[ActionName] = Field(description="O que quem consulta pode fazer com a conta.")
    roles: list[RoleName] = Field(
        description="Os cargos que quem consulta pode escolher ao aprovar, alterar ou reativar."
    )
    removal_status: StatusName | None = Field(
        description="O status que a conta recebe se for removida (ex_monitor, conselheiro ou "
        "inativo); vazio se quem consulta não pode removê-la."
    )


class RequestsResponse(_Strict):
    items: list[ManagedAccount]


class MembersResponse(_Strict):
    active: list[ManagedAccount]
    removed: list[ManagedAccount] = Field(description="Ex-monitores, conselheiros e inativos.")


class ManagementLogEntry(_Strict):
    """Uma ação de gerenciamento (REC-06). Nomes e cargos são os do momento da ação."""

    at: datetime = Field(description="Quando a ação foi aplicada.")
    action: ActionName
    action_label: str = Field(description='Como a ação aparece na tela, por exemplo "Aprovou".')
    actor_name: str = Field(description="Quem fez a ação.")
    actor_role_label: str | None = Field(description="O cargo de quem fez, na hora da ação.")
    target_name: str = Field(description="A conta sobre a qual a ação foi feita.")
    from_status: StatusName
    from_status_label: str
    to_status: StatusName
    to_status_label: str
    from_role: RoleName | None
    from_role_label: str | None
    to_role: RoleName | None
    to_role_label: str | None


class ManagementLogResponse(_Strict):
    items: list[ManagementLogEntry] = Field(
        description="As ações dos últimos 12 meses, da mais recente para a mais antiga (até 500)."
    )


class RoleChoice(_Strict):
    role: RoleName

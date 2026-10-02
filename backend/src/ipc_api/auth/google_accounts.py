"""Contas pelo Google (S16-01; FR-24, FR-25): entrar, ligar ao mesmo e-mail e registrar.

Depois de o Google confirmar a identidade:

1. a conta ligada a esse ``sub`` entra;
2. sem ela, a conta de mesmo e-mail **verificado** é ligada ao Google e entra (senha e Google levam
   à mesma conta, inclusive as do desenvolvedor);
3. sem conta, ou com uma conta cujo e-mail nunca foi verificado, a pessoa vai ao formulário
   complementar. Ao enviá-lo, a senha e os dados pendentes da conta não verificada são descartados:
   quem a criou não provou ser dono do e-mail (pré-sequestro de conta, ameaça 16).

Como a identidade já foi confirmada, o status da conta (aguardando, recusada, removida) pode ser
mostrado na hora.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    NewGoogleAccount,
    Status,
    Treatment,
)
from ipc_api.accounts.store import AccountStore
from ipc_api.auth.accounts import clean_course, clean_name, conflict
from ipc_api.auth.google import GoogleIdentity
from ipc_api.auth.sessions import Authenticator, status_refusal


@dataclass(frozen=True, slots=True)
class SignedIn:
    account: Account
    token: str


@dataclass(frozen=True, slots=True)
class NeedsSignup:
    identity: GoogleIdentity


@dataclass(frozen=True, slots=True)
class Refused:
    #: Código mostrado na página de entrada (``/entrar?google=...``); nunca um dado pessoal.
    reason: str


class GoogleAccounts:
    def __init__(
        self,
        store: AccountStore,
        authenticator: Authenticator,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.authenticator = authenticator
        self.clock = clock

    async def resolve(self, identity: GoogleIdentity) -> SignedIn | NeedsSignup | Refused:
        account = await self.store.find_by_google_sub(identity.sub)
        if account is None:
            by_email = await self.store.find_by_login(identity.email)
            if by_email is None or by_email.status is Status.AGUARDANDO_VERIFICACAO:
                return NeedsSignup(identity)
            try:
                account = await self.store.link_google(by_email.id, identity.sub)
            except AccountConflict:
                return Refused("outra_conta")
        refusal = status_refusal(account)
        if refusal is not None:
            return Refused(refusal.code.value)
        return SignedIn(account, await self.authenticator.open_session(account))

    async def complete(
        self, identity: GoogleIdentity, *, name: str, course: str, treatment: Treatment
    ) -> Account:
        """O formulário complementar: nome, curso e tratamento, sem senha (FR-24)."""
        new = NewGoogleAccount(
            name=clean_name(name),
            email=identity.email,
            course=clean_course(course),
            treatment=treatment,
            google_sub=identity.sub,
        )
        try:
            return await self.store.register_google(new, self.clock())
        except AccountConflict as error:
            raise conflict(error) from None

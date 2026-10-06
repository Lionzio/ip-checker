"""Repositório de contas e sessões: o contrato, a versão em memória e a do PostgreSQL.

A API só conhece o protocolo ``AccountStore``. Em produção ele é o ``PostgresAccountStore``; nos
testes, o ``MemoryAccountStore``. Os dois passam pelo mesmo conjunto de testes de contrato
(``tests/test_account_store.py``), para a versão em memória nunca divergir do banco.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Collection
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ipc_api.accounts.models import (
    LOG_RETENTION_MONTHS,
    Account,
    AccountConflict,
    DeveloperSeed,
    ManagementRecord,
    NewAccount,
    NewGoogleAccount,
    Role,
    SessionRecord,
    SignupMethod,
    Status,
    StoreUnavailable,
    Treatment,
    months_before,
    normalize_email,
)

#: Finalidades dos tokens de e-mail (5.2.5): a verificação do cadastro (S14-02) e a redefinição
#: de senha pelo "esqueci minha senha" (S24-04, Q-19 b).
VERIFICATION = "verificacao"
RESET = "redefinicao"


class AccountStore(Protocol):
    """Falha de conexão vira ``StoreUnavailable``; nome ou e-mail repetido, ``AccountConflict``."""

    async def ping(self) -> None:
        """Levanta uma exceção se o banco não responder."""

    async def find_by_login(self, login: str) -> Account | None:
        """Conta pelo e-mail (exato, em minúsculas) ou pelo nome (sem diferenciar maiúsculas)."""

    async def get_account(self, account_id: UUID) -> Account | None: ...

    async def find_by_google_sub(self, sub: str) -> Account | None:
        """A conta ligada a esta conta Google (FR-24)."""

    async def link_google(self, account_id: UUID, sub: str) -> Account:
        """Liga a conta Google a uma conta de e-mail verificado; o mesmo e-mail dá a mesma conta.

        Se a conta já estiver ligada a outra conta Google, ou o ``sub`` a outra conta:
        ``AccountConflict`` com o campo ``google``.
        """

    async def register_google(self, new: NewGoogleAccount, now: datetime) -> Account:
        """Cria a conta pelo Google, já ``aguardando_aprovacao`` e com o e-mail verificado.

        Se o e-mail pertence a uma conta nunca verificada, a senha e os dados pendentes dela são
        descartados e os links antigos deixam de valer (FR-25, pré-sequestro de conta). E-mail de
        uma conta verificada, nome de outra conta ou ``sub`` já ligado: ``AccountConflict``.
        """

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        """Cria a conta do desenvolvedor ou garante cargo, status e e-mails; nunca toca na senha."""

    async def register(self, new: NewAccount, now: datetime) -> Account:
        """Cria uma conta ``aguardando_verificacao`` (FR-23).

        Um e-mail cuja conta ainda não foi verificada pode ser registrado de novo: os dados
        pendentes são substituídos e os links antigos deixam de valer, porque uma conta não
        verificada não prova nada (FR-25). Nome ou e-mail de outra conta: ``AccountConflict``.
        """

    async def add_email_token(
        self, token_hash: bytes, account_id: UUID, purpose: str, now: datetime, expires_at: datetime
    ) -> None:
        """Guarda o hash de um token novo e invalida os anteriores da mesma finalidade."""

    async def verify_email(self, token_hash: bytes, now: datetime) -> Account | None:
        """Consome um token de verificação válido e leva a conta a ``aguardando_aprovacao``."""

    async def update_profile(
        self, account_id: UUID, name: str, course: str, treatment: Treatment
    ) -> Account: ...

    async def set_password(self, account_id: UUID, password_hash: str) -> None: ...

    async def reset_password(
        self, token_hash: bytes, password_hash: str, now: datetime
    ) -> Account | None:
        """Consome um token de redefinição válido, troca a senha e encerra todas as sessões.

        Devolve ``None`` se o token não existe, já foi usado, venceu ou é de outra finalidade.
        """

    async def list_accounts(self, statuses: Collection[Status]) -> list[Account]:
        """Contas nesses status, da mais antiga para a mais nova (gerenciamento, S15-02)."""

    async def transition(
        self,
        account_id: UUID,
        *,
        expected: tuple[Status, Role | None],
        status: Status,
        role: Role | None,
        decided_by: UUID | None,
        now: datetime,
        end_sessions: bool,
        record: ManagementRecord | None = None,
    ) -> Account | None:
        """Muda status e cargo só se a conta ainda estiver como ``expected`` (status, cargo).

        Devolve ``None`` se outra pessoa agiu antes. ``decided_by`` registra quem decidiu o
        pedido; ``end_sessions`` encerra as sessões da conta e ``record`` entra no registro de
        gerenciamento (REC-06), os dois na mesma transação. Receber o cargo de monitor-chefe liga
        ``ja_foi_monitor_chefe`` para sempre (FR-27).
        """

    async def management_log(self, limit: int, now: datetime) -> list[ManagementRecord]:
        """As ações de gerenciamento, da mais recente para a mais antiga (REC-06).

        Antes de ler, apaga as de mais de 12 meses; o usuário da API não apaga nem altera o
        registro de outro jeito.
        """

    async def delete_sessions(self, account_id: UUID, keep: bytes | None = None) -> None:
        """Encerra as sessões da conta, menos a de hash ``keep``."""

    async def create_session(
        self, token_hash: bytes, account_id: UUID, now: datetime, expires_at: datetime
    ) -> None: ...

    async def get_session(self, token_hash: bytes) -> SessionRecord | None: ...

    async def touch_session(self, token_hash: bytes, now: datetime) -> None: ...

    async def delete_session(self, token_hash: bytes) -> None: ...

    async def close(self) -> None: ...


# ---------------------------------------------------------------------------------------------
# Em memória (testes)
# ---------------------------------------------------------------------------------------------


@dataclass(slots=True)
class _Session:
    account_id: UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


@dataclass(slots=True)
class _EmailToken:
    account_id: UUID
    purpose: str
    expires_at: datetime
    used_at: datetime | None = None


class MemoryAccountStore:
    """Mesmas regras do esquema ``app``: nome e e-mail únicos, e-mails em minúsculas."""

    def __init__(self) -> None:
        self.accounts: dict[UUID, Account] = {}
        self.sessions: dict[bytes, _Session] = {}
        self.email_tokens: dict[bytes, _EmailToken] = {}
        #: Quem decidiu cada pedido e quando (``decided_by`` e ``decided_at`` no banco).
        self.decisions: dict[UUID, tuple[UUID, datetime]] = {}
        #: Registro das ações de gerenciamento (``app.management_log``), na ordem em que entraram.
        self.log: list[ManagementRecord] = []
        self.available = True
        self._lock = asyncio.Lock()

    def _check(self) -> None:
        if not self.available:
            raise StoreUnavailable("banco simulado fora do ar")

    async def ping(self) -> None:
        self._check()

    def _by_email(self, email: str) -> Account | None:
        return next((a for a in self.accounts.values() if email in a.emails), None)

    def _by_name(self, name: str) -> Account | None:
        folded = name.strip().lower()
        return next((a for a in self.accounts.values() if a.name.lower() == folded), None)

    async def find_by_login(self, login: str) -> Account | None:
        self._check()
        text = login.strip()
        if "@" in text:
            return self._by_email(normalize_email(text))
        return self._by_name(text)

    async def get_account(self, account_id: UUID) -> Account | None:
        self._check()
        return self.accounts.get(account_id)

    async def find_by_google_sub(self, sub: str) -> Account | None:
        self._check()
        return next((a for a in self.accounts.values() if a.google_sub == sub), None)

    async def link_google(self, account_id: UUID, sub: str) -> Account:
        self._check()
        async with self._lock:
            current = self.accounts[account_id]
            owner = next((a for a in self.accounts.values() if a.google_sub == sub), None)
            if (owner is not None and owner.id != account_id) or current.google_sub not in (
                None,
                sub,
            ):
                raise AccountConflict("outra conta Google já está ligada", "google")
            linked = replace(current, google_sub=sub)
            self.accounts[account_id] = linked
            return linked

    async def register_google(self, new: NewGoogleAccount, now: datetime) -> Account:
        self._check()
        async with self._lock:
            existing = self._by_email(new.email)
            if existing is not None and existing.status is not Status.AGUARDANDO_VERIFICACAO:
                raise AccountConflict("e-mail já cadastrado", "email")
            other = self._by_name(new.name)
            if other is not None and (existing is None or other.id != existing.id):
                raise AccountConflict("nome já cadastrado", "nome")
            if any(a.google_sub == new.google_sub for a in self.accounts.values()):
                raise AccountConflict("conta Google já ligada", "google")
            if existing is not None:
                for token in self.email_tokens.values():
                    if token.account_id == existing.id and token.used_at is None:
                        token.used_at = now
            account = Account(
                id=existing.id if existing is not None else uuid.uuid4(),
                name=new.name,
                course=new.course,
                treatment=new.treatment,
                role=None,
                status=Status.AGUARDANDO_APROVACAO,
                ja_foi_monitor_chefe=False,
                password_hash=None,
                signup_method=SignupMethod.GOOGLE,
                emails=(new.email,),
                created_at=now if existing is None else existing.created_at,
                google_sub=new.google_sub,
            )
            self.accounts[account.id] = account
            return account

    def add(self, account: Account) -> Account:
        """Insere uma conta pronta (só para os testes montarem cenários)."""
        names = {a.name.lower() for a in self.accounts.values()}
        emails = {e for a in self.accounts.values() for e in a.emails}
        if account.name.lower() in names:
            raise AccountConflict("nome já cadastrado", "nome")
        if emails & set(account.emails):
            raise AccountConflict("e-mail já cadastrado", "email")
        self.accounts[account.id] = account
        return account

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        self._check()
        async with self._lock:
            owners = {e: self._by_email(e) for e in seed.emails}
            ids = {owner.id for owner in owners.values() if owner is not None}
            if len(ids) > 1:
                raise AccountConflict(
                    "os e-mails do desenvolvedor estão em contas diferentes", "email"
                )
            if not ids:
                return self.add(
                    Account(
                        id=uuid.uuid4(),
                        name=seed.name,
                        course=seed.course,
                        treatment=Treatment.MASCULINO,
                        role=Role.DESENVOLVEDOR,
                        status=Status.ATIVO,
                        ja_foi_monitor_chefe=False,
                        password_hash=seed.password_hash,
                        signup_method=SignupMethod.SEED,
                        emails=seed.emails,
                        created_at=now,
                    )
                )
            current = self.accounts[ids.pop()]
            extra = tuple(e for e in seed.emails if e not in current.emails)
            updated = replace(
                current, role=Role.DESENVOLVEDOR, status=Status.ATIVO, emails=current.emails + extra
            )
            self.accounts[updated.id] = updated
            return updated

    async def register(self, new: NewAccount, now: datetime) -> Account:
        self._check()
        async with self._lock:
            existing = self._by_email(new.email)
            if existing is not None and existing.status is not Status.AGUARDANDO_VERIFICACAO:
                raise AccountConflict("e-mail já cadastrado", "email")
            other = self._by_name(new.name)
            if other is not None and (existing is None or other.id != existing.id):
                raise AccountConflict("nome já cadastrado", "nome")
            if existing is not None:
                for token in self.email_tokens.values():
                    if token.account_id == existing.id and token.used_at is None:
                        token.used_at = now
            account = Account(
                id=existing.id if existing is not None else uuid.uuid4(),
                name=new.name,
                course=new.course,
                treatment=new.treatment,
                role=None,
                status=Status.AGUARDANDO_VERIFICACAO,
                ja_foi_monitor_chefe=False,
                password_hash=new.password_hash,
                signup_method=SignupMethod.SENHA,
                emails=(new.email,),
                created_at=now if existing is None else existing.created_at,
            )
            self.accounts[account.id] = account
            return account

    async def add_email_token(
        self, token_hash: bytes, account_id: UUID, purpose: str, now: datetime, expires_at: datetime
    ) -> None:
        self._check()
        for token in self.email_tokens.values():
            if (
                token.account_id == account_id
                and token.purpose == purpose
                and token.used_at is None
            ):
                token.used_at = now
        self.email_tokens[token_hash] = _EmailToken(account_id, purpose, expires_at)

    async def verify_email(self, token_hash: bytes, now: datetime) -> Account | None:
        self._check()
        async with self._lock:
            token = self.email_tokens.get(token_hash)
            if (
                token is None
                or token.purpose != VERIFICATION
                or token.used_at is not None
                or token.expires_at <= now
            ):
                return None
            token.used_at = now
            account = self.accounts[token.account_id]
            if account.status is not Status.AGUARDANDO_VERIFICACAO:
                return None
            verified = replace(account, status=Status.AGUARDANDO_APROVACAO)
            self.accounts[verified.id] = verified
            return verified

    async def update_profile(
        self, account_id: UUID, name: str, course: str, treatment: Treatment
    ) -> Account:
        self._check()
        async with self._lock:
            other = self._by_name(name)
            if other is not None and other.id != account_id:
                raise AccountConflict("nome já cadastrado", "nome")
            updated = replace(
                self.accounts[account_id], name=name, course=course, treatment=treatment
            )
            self.accounts[account_id] = updated
            return updated

    async def set_password(self, account_id: UUID, password_hash: str) -> None:
        self._check()
        self.accounts[account_id] = replace(self.accounts[account_id], password_hash=password_hash)

    async def reset_password(
        self, token_hash: bytes, password_hash: str, now: datetime
    ) -> Account | None:
        self._check()
        async with self._lock:
            token = self.email_tokens.get(token_hash)
            if (
                token is None
                or token.purpose != RESET
                or token.used_at is not None
                or token.expires_at <= now
            ):
                return None
            token.used_at = now
            account = replace(self.accounts[token.account_id], password_hash=password_hash)
            self.accounts[account.id] = account
            await self.delete_sessions(account.id)
            return account

    async def list_accounts(self, statuses: Collection[Status]) -> list[Account]:
        self._check()
        wanted = set(statuses)
        found = [a for a in self.accounts.values() if a.status in wanted]
        return sorted(found, key=lambda a: (a.created_at, a.name.lower()))

    async def transition(
        self,
        account_id: UUID,
        *,
        expected: tuple[Status, Role | None],
        status: Status,
        role: Role | None,
        decided_by: UUID | None,
        now: datetime,
        end_sessions: bool,
        record: ManagementRecord | None = None,
    ) -> Account | None:
        self._check()
        async with self._lock:
            current = self.accounts.get(account_id)
            if current is None or (current.status, current.role) != expected:
                return None
            updated = replace(
                current,
                status=status,
                role=role,
                ja_foi_monitor_chefe=current.ja_foi_monitor_chefe or role is Role.MONITOR_CHEFE,
            )
            self.accounts[account_id] = updated
            if decided_by is not None:
                self.decisions[account_id] = (decided_by, now)
            if end_sessions:
                await self.delete_sessions(account_id)
            if record is not None:
                self._purge_log(now)
                self.log.append(record)
            return updated

    async def management_log(self, limit: int, now: datetime) -> list[ManagementRecord]:
        self._check()
        async with self._lock:
            self._purge_log(now)
            return list(reversed(self.log))[:limit]

    def _purge_log(self, now: datetime) -> None:
        oldest = months_before(now, LOG_RETENTION_MONTHS)
        self.log = [record for record in self.log if record.at >= oldest]

    async def delete_sessions(self, account_id: UUID, keep: bytes | None = None) -> None:
        self._check()
        for token_hash in [
            h for h, s in self.sessions.items() if s.account_id == account_id and h != keep
        ]:
            del self.sessions[token_hash]

    def add_session(
        self, token_hash: bytes, account_id: UUID, now: datetime, expires_at: datetime
    ) -> None:
        """Abre uma sessão sem passar pelo login (só para os testes)."""
        self.sessions[token_hash] = _Session(account_id, now, now, expires_at)

    async def create_session(
        self, token_hash: bytes, account_id: UUID, now: datetime, expires_at: datetime
    ) -> None:
        self._check()
        self.add_session(token_hash, account_id, now, expires_at)

    async def get_session(self, token_hash: bytes) -> SessionRecord | None:
        self._check()
        session = self.sessions.get(token_hash)
        if session is None:
            return None
        return SessionRecord(
            account=self.accounts[session.account_id],
            created_at=session.created_at,
            last_seen_at=session.last_seen_at,
            expires_at=session.expires_at,
        )

    async def touch_session(self, token_hash: bytes, now: datetime) -> None:
        self._check()
        session = self.sessions.get(token_hash)
        if session is not None:
            session.last_seen_at = now

    async def delete_session(self, token_hash: bytes) -> None:
        self._check()
        self.sessions.pop(token_hash, None)

    async def close(self) -> None:
        return None

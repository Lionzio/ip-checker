"""Repositório de contas e sessões: o contrato, a versão em memória e a do PostgreSQL.

A API só conhece o protocolo ``AccountStore``. Em produção ele é o ``PostgresAccountStore``; nos
testes, o ``MemoryAccountStore``. Os dois passam pelo mesmo conjunto de testes de contrato
(``tests/test_account_store.py``), para a versão em memória nunca divergir do banco.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ipc_api.accounts.models import (
    Account,
    AccountConflict,
    DeveloperSeed,
    Role,
    SessionRecord,
    SignupMethod,
    Status,
    StoreUnavailable,
    Treatment,
    normalize_email,
)


class AccountStore(Protocol):
    """Falha de conexão vira ``StoreUnavailable``; nome ou e-mail repetido, ``AccountConflict``."""

    async def ping(self) -> None:
        """Levanta uma exceção se o banco não responder."""

    async def find_by_login(self, login: str) -> Account | None:
        """Conta pelo e-mail (exato, em minúsculas) ou pelo nome (sem diferenciar maiúsculas)."""

    async def get_account(self, account_id: UUID) -> Account | None: ...

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        """Cria a conta do desenvolvedor ou garante cargo, status e e-mails; nunca toca na senha."""

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


class MemoryAccountStore:
    """Mesmas regras do esquema ``app``: nome e e-mail únicos, e-mails em minúsculas."""

    def __init__(self) -> None:
        self.accounts: dict[UUID, Account] = {}
        self.sessions: dict[bytes, _Session] = {}
        self.available = True
        self._lock = asyncio.Lock()

    def _check(self) -> None:
        if not self.available:
            raise StoreUnavailable("banco simulado fora do ar")

    async def ping(self) -> None:
        self._check()

    def _by_email(self, email: str) -> Account | None:
        return next((a for a in self.accounts.values() if email in a.emails), None)

    async def find_by_login(self, login: str) -> Account | None:
        self._check()
        text = login.strip()
        if "@" in text:
            return self._by_email(normalize_email(text))
        folded = text.lower()
        return next((a for a in self.accounts.values() if a.name.lower() == folded), None)

    async def get_account(self, account_id: UUID) -> Account | None:
        self._check()
        return self.accounts.get(account_id)

    def add(self, account: Account) -> Account:
        """Insere uma conta pronta (só para os testes montarem cenários)."""
        names = {a.name.lower() for a in self.accounts.values()}
        emails = {e for a in self.accounts.values() for e in a.emails}
        if account.name.lower() in names or emails & set(account.emails):
            raise AccountConflict("nome ou e-mail já cadastrado")
        self.accounts[account.id] = account
        return account

    async def ensure_developer(self, seed: DeveloperSeed, now: datetime) -> Account:
        self._check()
        async with self._lock:
            owners = {e: self._by_email(e) for e in seed.emails}
            ids = {owner.id for owner in owners.values() if owner is not None}
            if len(ids) > 1:
                raise AccountConflict("os e-mails do desenvolvedor estão em contas diferentes")
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

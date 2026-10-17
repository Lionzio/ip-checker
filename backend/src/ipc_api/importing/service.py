"""O serviço de importação (S50-04, S50-05): o token pessoal e as duas etapas do catálogo.

O token é um segredo aleatório (``ipc_imp_`` + 32 bytes em base64url), mostrado uma vez e guardado
só como SHA-256, com 90 dias de validade e no máximo 3 ativos por conta. Só a chefia e o
desenvolvedor criam (``IMPORT_ROLES``). Cada token tem um limite próprio de pedidos por minuto,
além do limite por IP de todo ``/api/*``.
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from collections import deque
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ipc_api.accounts.models import Account, Status
from ipc_api.auth.policy import IMPORT_ROLES
from ipc_api.errors import ApiError, ErrorCode
from ipc_api.importing.hashing import content_hash
from ipc_api.importing.models import (
    ClassIn,
    ImportMode,
    ImportToken,
    ListIn,
    ManifestResult,
    QuestionIn,
    QuestionsResult,
)
from ipc_api.importing.store import CatalogStore, UnknownListError, UnknownRunError

TOKEN_PREFIX = "ipc_imp_"  # noqa: S105 - o prefixo, não um segredo
TOKEN_TTL = timedelta(days=90)
MAX_ACTIVE_TOKENS = 3
#: Pedidos por minuto de um token (uma sincronização de uma lista grande cabe com folga).
TOKEN_REQUESTS_PER_MIN = 30
#: O último uso é gravado no máximo uma vez por minuto, para não escrever a cada pedido.
TOUCH_EVERY = timedelta(minutes=1)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def can_import(account: Account) -> bool:
    return account.status is Status.ATIVO and account.role in IMPORT_ROLES


class ImportService:
    def __init__(
        self,
        store: CatalogStore,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        per_minute: int = TOKEN_REQUESTS_PER_MIN,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store = store
        self._clock = clock
        self._per_minute = per_minute
        self._monotonic = monotonic
        self._recent: dict[UUID, deque[float]] = {}

    def now(self) -> datetime:
        return self._clock()

    # --- tokens -------------------------------------------------------------------------------
    async def create_token(self, account: Account, label: str) -> tuple[str, ImportToken]:
        if not can_import(account):
            raise ApiError(
                403,
                ErrorCode.FORBIDDEN,
                "Só a chefia (monitor-chefe, professor) e o desenvolvedor criam tokens de "
                "importação.",
            )
        now = self._clock()
        active = [t for t in await self.store.list_import_tokens(account.id) if t.active(now)]
        if len(active) >= MAX_ACTIVE_TOKENS:
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"Você já tem {MAX_ACTIVE_TOKENS} tokens ativos: revogue um antes de criar outro.",
            )
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
        token = ImportToken(
            id=uuid.uuid4(),
            account_id=account.id,
            token_hash=hash_token(raw),
            label=label,
            created_at=now,
            expires_at=now + TOKEN_TTL,
        )
        await self.store.add_import_token(token)
        return raw, token

    async def list_tokens(self, account: Account) -> list[ImportToken]:
        return await self.store.list_import_tokens(account.id)

    async def revoke_token(self, account: Account, token_id: UUID) -> bool:
        return await self.store.revoke_import_token(account.id, token_id, self._clock())

    async def authenticate(self, raw: str) -> ImportToken | None:
        """O token ativo com este valor, ou ``None`` (o motivo nunca vai para a resposta)."""
        if not raw.startswith(TOKEN_PREFIX) or len(raw) > 200:
            return None
        token = await self.store.find_import_token(hash_token(raw))
        now = self._clock()
        if token is None or not token.active(now):
            return None
        if token.last_used_at is None or now - token.last_used_at >= TOUCH_EVERY:
            await self.store.touch_import_token(token.id, now)
        return token

    def allow(self, token_id: UUID) -> int | None:
        """``None`` se o pedido cabe no minuto do token; senão, os segundos até caber."""
        now = self._monotonic()
        window = self._recent.setdefault(token_id, deque())
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= self._per_minute:
            return max(1, int(60 - (now - window[0])) + 1)
        window.append(now)
        return None

    # --- catálogo -----------------------------------------------------------------------------
    async def manifest(
        self,
        account: Account,
        *,
        mode: ImportMode,
        period: str,
        classes: Sequence[ClassIn],
        lists: Sequence[ListIn],
    ) -> ManifestResult:
        known = {item.dikastis_org_id for item in classes}
        for item in lists:
            if item.class_org_id not in known:
                raise ApiError(
                    422,
                    ErrorCode.INVALID_INPUT,
                    f"A lista {item.title!r} aponta para uma turma que o manifesto não trouxe.",
                )
        return await self.store.apply_manifest(
            account_id=account.id,
            mode=mode,
            period=period,
            classes=classes,
            lists=lists,
            now=self._clock(),
        )

    async def questions(
        self, account: Account, *, run_id: UUID, period: str, questions: Sequence[QuestionIn]
    ) -> QuestionsResult:
        for item in questions:
            expected = content_hash(
                title=item.title,
                description=item.description,
                input_description=item.input_description,
                output_description=item.output_description,
                samples=item.samples,
            )
            if expected != item.content_hash:
                raise ApiError(
                    422,
                    ErrorCode.INVALID_INPUT,
                    f"O hash da questão {item.question_id} não confere com o enunciado enviado: "
                    "atualize a extensão.",
                )
        try:
            return await self.store.apply_questions(
                account_id=account.id,
                run_id=run_id,
                period=period,
                questions=questions,
                now=self._clock(),
            )
        except UnknownRunError:
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                "A rodada de sincronização não existe ou é de outra conta: verifique de novo.",
            ) from None
        except UnknownListError as exc:
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"A questão {exc.args[0]} é de uma lista que o manifesto não trouxe.",
            ) from None

"""As regras dos gabaritos pelo painel (Sprint 51, S51-02; ADR-17).

- Só a chefia (monitor-chefe, professor) e o desenvolvedor leem o código, salvam e apagam; a equipe
  vê só a existência, a data, quem salvou e as regras acionadas.
- Ao salvar, o código passa pelos mesmos limites de uma submissão e pelo analisador, com as regras
  do período e da questão. As violações ficam registradas: a chefia decide se "o enunciado libera".
  Sem o analisador, nada é gravado (um gabarito nunca entra sem ser conferido).
- Toda escrita atualiza a cópia em memória (``ipc_api.gabaritos.Gabaritos``) que a verificação e o
  plágio usam.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from ipc_api.accounts.models import Account, Status
from ipc_api.answer_keys.models import (
    GabaritoKind,
    GabaritoSource,
    RuleHit,
    StoredGabarito,
    list_number,
)
from ipc_api.answer_keys.store import Actor, GabaritoStore
from ipc_api.auth.policy import GABARITO_ROLES
from ipc_api.clients.analyzer import AnalyzerClient, AnalyzerRejected, AnalyzerUnavailable
from ipc_api.errors import ApiError, ErrorCode, analyzer_unavailable
from ipc_api.gabaritos import Gabaritos
from ipc_api.periods import requested, resolve_period
from ipc_api.validation import check_code

logger = logging.getLogger(__name__)


def can_manage_gabaritos(account: Account) -> bool:
    return account.status is Status.ATIVO and account.role in GABARITO_ROLES


def forbidden_for_team() -> ApiError:
    return ApiError(
        403,
        ErrorCode.FORBIDDEN,
        "Só a chefia (monitor-chefe, professor) e o desenvolvedor veem e cadastram o código dos "
        "gabaritos.",
    )


def not_found(question_id: str, kind: GabaritoKind) -> ApiError:
    return ApiError(
        404, ErrorCode.GABARITO_NOT_FOUND, f"A questão {question_id} não tem o gabarito {kind}."
    )


class GabaritoService:
    def __init__(
        self,
        store: GabaritoStore,
        analyzer: AnalyzerClient,
        cache: Gabaritos,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self._analyzer = analyzer
        self._cache = cache
        self._clock = clock

    async def load_cache(self) -> int:
        """Põe na memória os gabaritos do banco (ao subir, depois do carregamento antigo)."""
        items = await self.store.all()
        for item in items:
            self._cache.put(item.period, item.question_id, item.kind, item.code)
        return len(items)

    async def list_period(self, period: str) -> list[StoredGabarito]:
        return await self.store.list_period(period)

    async def read(
        self, account: Account, period: str, question_id: str, kind: GabaritoKind
    ) -> StoredGabarito:
        if not can_manage_gabaritos(account):
            raise forbidden_for_team()
        found = await self.store.get(period, question_id, kind)
        if found is None:
            raise not_found(question_id, kind)
        return found

    async def save(
        self,
        account: Account | None,
        period: str,
        question_id: str,
        kind: GabaritoKind,
        code: str,
        *,
        source: GabaritoSource = "painel",
    ) -> StoredGabarito:
        """Confere e grava. ``account`` é ``None`` só no import feito pelo autor (S51-05)."""
        if account is not None and not can_manage_gabaritos(account):
            raise forbidden_for_team()
        violations = await self.check(period, question_id, code)
        actor = Actor(account.id, account.name) if account is not None else Actor(None, None)
        stored = await self.store.save(
            period=period,
            question_id=question_id,
            kind=kind,
            source=source,
            code=code,
            violations=violations,
            actor=actor,
            now=self._clock(),
        )
        self._cache.put(period, question_id, kind, code)
        # Só o que aconteceu, nunca o código (NFR-27).
        logger.info(
            "gabarito %s %s %s salvo: %d regra(s)", period, question_id, kind, len(violations)
        )
        return stored

    async def delete(
        self, account: Account, period: str, question_id: str, kind: GabaritoKind
    ) -> None:
        if not can_manage_gabaritos(account):
            raise forbidden_for_team()
        removed = await self.store.delete(
            period, question_id, kind, Actor(account.id, account.name), self._clock()
        )
        if not removed:
            raise not_found(question_id, kind)
        self._cache.remove(period, question_id, kind)
        logger.info("gabarito %s %s %s apagado", period, question_id, kind)

    async def check(self, period: str, question_id: str, code: str) -> tuple[RuleHit, ...]:
        """As regras que o gabarito aciona, com as regras do período e da questão."""
        check_code(code)
        number = list_number(question_id)
        view = await resolve_period(self._analyzer, period)
        if number not in {item.number for item in view.lists}:
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"O período {period} não tem a Lista {number} no IP-Checker.",
            )
        registered = any(q.id == question_id for item in view.lists for q in item.questions)
        try:
            result = await self._analyzer.analyze(
                code,
                number,
                question_id=question_id if registered else None,
                period=requested(view),
            )
        except AnalyzerRejected as exc:
            raise ApiError(exc.status, ErrorCode(exc.code), exc.message) from None
        except AnalyzerUnavailable as exc:
            logger.warning("analyzer indisponível ao conferir um gabarito: %s", exc)
            raise analyzer_unavailable() from None
        if result.syntax_error is not None:
            error = result.syntax_error
            raise ApiError(
                422,
                ErrorCode.INVALID_INPUT,
                f"O gabarito tem um erro de sintaxe na linha {error.line}: {error.message}.",
            )
        hits = {(v.rule_id, v.line) for v in result.violations}
        return tuple(RuleHit(rule, line) for rule, line in sorted(hits, key=lambda h: (h[1], h[0])))

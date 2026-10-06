"""O feedback de ponta a ponta (S18-02; FR-30, ADR-06, NFR-26).

Cada pedido gasta uma unidade da cota diária da conta e do teto diário do servidor, que limitam
o custo das IAs. Desde a S25-05 a cota fica no banco (não zera num deploy) e só é cobrada depois
de a análise dar certo: um código com erro de sintaxe ou um analisador fora do ar não gastam
nada. A ordem é:

1. a IA principal;
2. a IA de reserva, se houver; sem ela, uma nova tentativa da principal;
3. sem resposta válida dentro do prazo total, o feedback montado por modelos de texto, sem IA.

Uma resposta que não chega, que dá erro ou que não passa na validação conta como uma tentativa.
As partes fixas (abertura e frase obrigatória) são as mesmas nos três casos.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from ipc_api.accounts.store import AccountStore, MemoryAccountStore
from ipc_api.errors import ApiError, ErrorCode
from ipc_api.feedback.compose import (
    Evaluator,
    Item,
    build_prompt,
    fixed_text,
    free_text_problem,
    template_text,
    unmask,
)
from ipc_api.feedback.providers import LlmConfig, LlmSettings, Provider, ProviderError, Slot

#: Uma tentativa com menos tempo que isto não vale a pena.
MIN_ATTEMPT_S = 2.0


@dataclass(frozen=True, slots=True)
class FeedbackLimits:
    #: Feedbacks por conta por dia (UTC). Uma lista de 40 alunos cabe com folga.
    per_account_day: int = 60
    #: Feedbacks por dia no servidor inteiro: o teto de custo das IAs.
    daily_cap: int = 1_000

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> FeedbackLimits:
        defaults = cls()
        return cls(
            per_account_day=int(env.get("IPC_FEEDBACK_PER_ACCOUNT_DAY", defaults.per_account_day)),
            daily_cap=int(env.get("IPC_FEEDBACK_DAILY_CAP", defaults.daily_cap)),
        )


@dataclass(frozen=True, slots=True)
class FeedbackText:
    text: str
    #: "llm": com o trecho escrito por uma IA e validado; "template": montado sem IA.
    source: Literal["llm", "template"]
    #: Qual IA escreveu o trecho livre, quando foi uma.
    provider: Slot | None = None


@dataclass(frozen=True, slots=True)
class Ai:
    slot: Slot
    provider: Provider
    config: LlmConfig


class FeedbackService:
    def __init__(
        self,
        ais: Sequence[Ai],
        settings: LlmSettings,
        limits: FeedbackLimits,
        *,
        store: AccountStore | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ais = tuple(ais)
        self.settings = settings
        self.limits = limits
        #: Onde fica a cota do dia (``app.feedback_quota``).
        self.store: AccountStore = store if store is not None else MemoryAccountStore()
        self._now = now
        self._monotonic = monotonic

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ais)

    async def take_quota(self, account_id: UUID) -> None:
        """Gasta uma unidade da cota do dia ou recusa com 429 até o dia seguinte (UTC).

        Levanta ``StoreUnavailable`` quando o banco não responde.
        """
        now = self._now().astimezone(UTC)
        exceeded = await self.store.take_feedback_quota(
            account_id, now.date(), self.limits.per_account_day, self.limits.daily_cap
        )
        if exceeded is None:
            return
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), UTC)
        wait = max(1, int((tomorrow - now).total_seconds()))
        message = (
            "Você chegou ao limite de feedbacks de hoje."
            if exceeded == "conta"
            else "O IP-Checker chegou ao limite de feedbacks de hoje."
        )
        raise ApiError(429, ErrorCode.RATE_LIMITED, message, retry_after_s=wait)

    def _plan(self) -> tuple[Ai, ...]:
        # Com uma IA só, ela tem uma nova tentativa (NFR-26); com a reserva, cada uma tem uma.
        return self.ais * 2 if len(self.ais) == 1 else self.ais

    async def write(
        self,
        *,
        student: str,
        annotation: str | None,
        evaluator: Evaluator,
        items: list[Item],
        code: str,
    ) -> FeedbackText:
        fixed = fixed_text(student, evaluator, items)
        if self.ais:
            prompt = build_prompt(
                items=items,
                code=code,
                annotation=annotation,
                student=student,
                treatment=evaluator.treatment,
            )
            deadline = self._monotonic() + self.settings.deadline_s
            for ai in self._plan():
                remaining = deadline - self._monotonic()
                if remaining < MIN_ATTEMPT_S:
                    break
                timeout = min(ai.config.timeout_s, remaining)
                try:
                    raw = await asyncio.wait_for(
                        ai.provider.generate(prompt, timeout_s=timeout), timeout=timeout
                    )
                except (ProviderError, TimeoutError):
                    continue
                free = raw.strip()
                if free_text_problem(free, valid=not items, treatment=evaluator.treatment) is None:
                    return FeedbackText(f"{fixed} {unmask(free, student)}", "llm", ai.slot)
        free = template_text(student=student, items=items, annotation=annotation)
        return FeedbackText(f"{fixed} {free}", "template")

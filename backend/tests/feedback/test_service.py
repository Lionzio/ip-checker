"""O feedback de ponta a ponta no serviço (S18-02, NFR-26): IA principal, IA de reserva, prazo,
feedback montado sem IA e as cotas diárias."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.errors import ApiError
from ipc_api.feedback.compose import VALID_SENTENCE, Evaluator, Item
from ipc_api.feedback.providers import (
    FakeProvider,
    LlmConfig,
    LlmSettings,
    Prompt,
    ProviderError,
    Slot,
)
from ipc_api.feedback.service import Ai, FeedbackLimits, FeedbackService

pytestmark = pytest.mark.anyio

STUDENT = "Isabella Schultz"
MONITOR = Evaluator("Vinícius Leôncio", "desenvolvedor", "masculino")
OPENING = "Olá, Isabella Schultz, sou o monitor Vinícius Leôncio e seu código estava muito bom."
FAKE = LlmConfig(provider="fake")
SLOTS: tuple[Slot, Slot] = ("primary", "fallback")


class Scripted(FakeProvider):
    """Responde, em ordem, cada item da lista: um texto ou uma exceção."""

    def __init__(self, *answers: str | Exception) -> None:
        super().__init__()
        self.answers = list(answers)

    async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def service(
    *providers: FakeProvider, timeout_s: float = 12.0, deadline_s: float = 28.0
) -> FeedbackService:
    config = LlmConfig(provider="fake", timeout_s=timeout_s)
    ais = [Ai(SLOTS[index], provider, config) for index, provider in enumerate(providers)]
    return FeedbackService(ais, LlmSettings(deadline_s=deadline_s), FeedbackLimits())


async def write(
    svc: FeedbackService, items: list[Item] | None = None, annotation: str | None = None
) -> tuple[str, str, str | None]:
    result = await svc.write(
        student=STUDENT, annotation=annotation, evaluator=MONITOR, items=items or [], code="x = 1\n"
    )
    return result.text, result.source, result.provider


# --- IA principal e de reserva -------------------------------------------------------------------


async def test_a_good_answer_from_the_primary_ai_follows_the_fixed_parts() -> None:
    primary = Scripted("Gostei de como você organizou o código, [ALUNO].")

    text, source, provider = await write(service(primary))

    assert (source, provider) == ("llm", "primary")
    assert text == (
        f"{OPENING} {VALID_SENTENCE} Gostei de como você organizou o código, Isabella Schultz."
    )


async def test_with_one_ai_a_refused_answer_gets_one_more_try() -> None:
    primary = Scripted("Sua questão foi anulada.", "Gostei bastante do código.")

    text, source, provider = await write(service(primary))

    assert (source, provider, len(primary.prompts)) == ("llm", "primary", 2)
    assert text.endswith("Gostei bastante do código.")


@pytest.mark.parametrize(
    "failure",
    [ProviderError("HTTP 500"), ProviderError("tempo esgotado"), "Veja https://x.y"],
    ids=["erro", "tempo", "resposta-recusada"],
)
async def test_when_the_primary_fails_the_fallback_writes(failure: str | Exception) -> None:
    primary, fallback = Scripted(failure), Scripted("Gostei bastante da organização.")

    text, source, provider = await write(service(primary, fallback))

    assert (source, provider) == ("llm", "fallback")
    assert (len(primary.prompts), len(fallback.prompts)) == (1, 1)
    # A reserva recebe o mesmo prompt, também sem o nome do aluno.
    assert fallback.prompts == primary.prompts
    assert text.endswith("Gostei bastante da organização.")


async def test_with_both_ais_failing_the_feedback_is_assembled_without_ai() -> None:
    primary = Scripted(ProviderError("HTTP 429"))
    fallback = Scripted("Seu código está perfeito.")  # contradiz o motor

    text, source, provider = await write(service(primary, fallback), [Item("uso", "for")])

    assert (source, provider) == ("template", None)
    assert text.startswith(
        "Olá, Isabella Schultz, sou o monitor Vinícius Leôncio e seu código precisa de ajustes. "
        "Sua questão apresenta problemas, como o uso de for, portanto ela foi anulada. "
    )
    assert "for" in text.split("anulada. ", 1)[1]  # a dica fala do que o motor encontrou
    assert "perfeito" not in text


async def test_without_any_ai_the_feedback_is_assembled_without_ai() -> None:
    svc = service()

    text, source, provider = await write(svc, annotation="faltou testar o zero")

    assert not svc.ai_enabled
    assert (source, provider) == ("template", None)
    assert text.startswith(f"{OPENING} {VALID_SENTENCE} Deixo também uma observação: ")
    assert "faltou testar o zero." in text


async def test_a_slow_ai_is_cut_by_the_timeout() -> None:
    class Slow(FakeProvider):
        async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
            self.prompts.append(prompt)
            await asyncio.sleep(10)
            return "Gostei."

    primary, fallback = Slow(), Slow()

    _, source, _ = await write(service(primary, fallback, timeout_s=0.05, deadline_s=5))

    assert source == "template"
    assert (len(primary.prompts), len(fallback.prompts)) == (1, 1)


async def test_the_deadline_bounds_the_attempts() -> None:
    clock = [0.0]

    class Expensive(FakeProvider):
        async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
            self.prompts.append(prompt)
            clock[0] += 27.0  # a principal consome quase todo o prazo
            raise ProviderError("tempo esgotado")

    primary, fallback = Expensive(), Scripted("Gostei.")
    svc = FeedbackService(
        [Ai("primary", primary, FAKE), Ai("fallback", fallback, FAKE)],
        LlmSettings(deadline_s=28),
        FeedbackLimits(),
        monotonic=lambda: clock[0],
    )

    _, source, _ = await write(svc)

    assert source == "template"
    assert fallback.prompts == []  # não sobrou tempo para a reserva


# --- Cotas -------------------------------------------------------------------------------------


async def test_each_account_has_a_daily_quota_and_the_server_a_daily_cap() -> None:
    now = [datetime(2026, 10, 2, 23, 59, 0, tzinfo=UTC)]
    store = MemoryAccountStore()
    svc = FeedbackService(
        [],
        LlmSettings(),
        FeedbackLimits(per_account_day=2, daily_cap=3),
        store=store,
        now=lambda: now[0],
    )
    ana, bia, caio = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    await svc.take_quota(ana)
    await svc.take_quota(ana)
    with pytest.raises(ApiError) as own:
        await svc.take_quota(ana)
    await svc.take_quota(bia)
    with pytest.raises(ApiError) as server:
        await svc.take_quota(caio)

    assert (own.value.status, own.value.retry_after_s) == (429, 60)
    assert "Você chegou ao limite" in str(own.value)
    assert "O IP-Checker chegou ao limite" in str(server.value)
    now[0] += timedelta(minutes=1)  # dia seguinte (UTC)
    await svc.take_quota(ana)


async def test_the_quota_survives_a_restart() -> None:
    """S25-05: a cota fica no repositório, não no serviço; um deploy não a zera."""
    store = MemoryAccountStore()
    limits = FeedbackLimits(per_account_day=1, daily_cap=10)
    ana = uuid.uuid4()
    await FeedbackService([], LlmSettings(), limits, store=store).take_quota(ana)

    with pytest.raises(ApiError):
        await FeedbackService([], LlmSettings(), limits, store=store).take_quota(ana)

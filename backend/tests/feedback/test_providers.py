"""Camada de provedores de LLM (S18-01, ADR-06): configuração e adaptadores contra respostas
gravadas, sem rede. A chave nunca aparece em erro, em ``repr`` nem em resposta."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
import pytest

from ipc_api.feedback.providers import (
    FAKE_TEXT,
    FakeProvider,
    GeminiProvider,
    LlmConfig,
    LlmSettings,
    OpenAICompatProvider,
    Prompt,
    ProviderError,
    build_provider,
)
from ipc_api.settings import ApiSettings

RECORDED = Path(__file__).with_name("recorded")
KEY = "chave-llm-de-teste"
PROMPT = Prompt(system="regras", user="dados")
pytestmark = pytest.mark.anyio


def recorded(name: str) -> Any:
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


def transport(
    answer: httpx2.Response | Callable[[httpx2.Request], httpx2.Response],
    seen: list[httpx2.Request],
) -> httpx2.MockTransport:
    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return answer(request) if callable(answer) else answer

    return httpx2.MockTransport(handler)


# --- Configuração --------------------------------------------------------------------------------


def test_feedback_is_off_without_a_provider() -> None:
    config = LlmConfig.from_env({})

    assert not config.enabled
    assert build_provider(config) is None
    assert ApiSettings.from_env({}).llm.configured == ()


@pytest.mark.parametrize(
    ("env", "base_url"),
    [
        (
            {"IPC_LLM_PROVIDER": "openai_compat", "IPC_LLM_MODEL": "gpt-4o-mini"},
            "https://api.openai.com/v1",
        ),
        (
            {
                "IPC_LLM_PROVIDER": "openai_compat",
                "IPC_LLM_MODEL": "llama-3.3-70b-versatile",
                "IPC_LLM_BASE_URL": "https://api.groq.com/openai/v1/",
            },
            "https://api.groq.com/openai/v1",
        ),
        (
            {"IPC_LLM_PROVIDER": "gemini", "IPC_LLM_MODEL": "gemini-2.5-flash"},
            "https://generativelanguage.googleapis.com/v1beta",
        ),
    ],
)
def test_provider_settings_from_environment(env: dict[str, str], base_url: str) -> None:
    config = LlmConfig.from_env({**env, "IPC_LLM_API_KEY": KEY})

    assert config.enabled
    assert config.base_url == base_url
    assert config.timeout_s == 12.0
    assert KEY not in repr(ApiSettings(llm=LlmSettings(primary=config)))


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"IPC_LLM_PROVIDER": "chatbot"}, "IPC_LLM_PROVIDER"),
        ({"IPC_LLM_PROVIDER": "gemini", "IPC_LLM_API_KEY": KEY}, "IPC_LLM_MODEL"),
        ({"IPC_LLM_PROVIDER": "openai_compat", "IPC_LLM_MODEL": "m"}, "IPC_LLM_API_KEY"),
        (
            {
                "IPC_LLM_PROVIDER": "openai_compat",
                "IPC_LLM_MODEL": "m",
                "IPC_LLM_API_KEY": KEY,
                "IPC_LLM_BASE_URL": "http://api.example",
            },
            "HTTPS",
        ),
    ],
)
def test_invalid_provider_settings_prevent_startup(env: dict[str, str], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        LlmConfig.from_env(env)


def test_a_primary_and_a_fallback_ai_each_with_its_own_key() -> None:
    settings = LlmSettings.from_env(
        {
            "IPC_LLM_PROVIDER": "openai_compat",
            "IPC_LLM_BASE_URL": "https://api.groq.com/openai/v1",
            "IPC_LLM_MODEL": "modelo-principal",
            "IPC_LLM_API_KEY": KEY,
            "IPC_LLM_FALLBACK_PROVIDER": "gemini",
            "IPC_LLM_FALLBACK_MODEL": "modelo-reserva",
            "IPC_LLM_FALLBACK_API_KEY": "chave-da-reserva",
            "IPC_LLM_FALLBACK_TIMEOUT_S": "10",
            "IPC_LLM_DEADLINE_S": "25",
        }
    )

    assert [slot for slot, _ in settings.configured] == ["primary", "fallback"]
    assert (settings.primary.model, settings.fallback.model) == (
        "modelo-principal",
        "modelo-reserva",
    )
    assert settings.fallback.base_url == "https://generativelanguage.googleapis.com/v1beta"
    assert (settings.fallback.api_key, settings.fallback.timeout_s) == ("chave-da-reserva", 10.0)
    assert settings.deadline_s == 25.0
    shown = repr(ApiSettings(llm=settings))
    assert KEY not in shown
    assert "chave-da-reserva" not in shown


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"IPC_LLM_FALLBACK_PROVIDER": "fake"}, "defina antes a principal"),
        (
            {"IPC_LLM_PROVIDER": "fake", "IPC_LLM_FALLBACK_PROVIDER": "gemini"},
            "IPC_LLM_FALLBACK_MODEL",
        ),
    ],
)
def test_invalid_fallback_settings_prevent_startup(env: dict[str, str], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        LlmSettings.from_env(env)


def test_the_fake_provider_needs_no_key() -> None:
    config = LlmConfig.from_env({"IPC_LLM_PROVIDER": "fake"})

    assert isinstance(build_provider(config), FakeProvider)


# --- openai_compat (OpenAI, Groq, DeepSeek) ------------------------------------------------------

OPENAI = LlmConfig(
    provider="openai_compat", model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1", api_key=KEY,
)  # fmt: skip


async def test_openai_compat_sends_system_and_user_messages() -> None:
    seen: list[httpx2.Request] = []
    provider = OpenAICompatProvider(
        OPENAI, transport(httpx2.Response(200, json=recorded("openai_chat.json")), seen)
    )

    text = await provider.generate(PROMPT, timeout_s=20)

    assert text.startswith("Gostei bastante de como você organizou")
    [request] = seen
    assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(request.content)
    assert body["model"] == "llama-3.3-70b-versatile"
    assert body["messages"] == [
        {"role": "system", "content": "regras"},
        {"role": "user", "content": "dados"},
    ]
    assert body["max_tokens"] <= 400


# --- gemini --------------------------------------------------------------------------------------

GEMINI = LlmConfig(
    provider="gemini", model="gemini-2.5-flash",
    base_url="https://generativelanguage.googleapis.com/v1beta", api_key=KEY,
)  # fmt: skip


async def test_gemini_sends_the_system_instruction_and_joins_the_parts() -> None:
    seen: list[httpx2.Request] = []
    provider = GeminiProvider(
        GEMINI, transport(httpx2.Response(200, json=recorded("gemini_generate.json")), seen)
    )

    text = await provider.generate(PROMPT, timeout_s=20)

    assert text == (
        "Notei que você usou bem o elif. "
        "Vale revisar os nomes das variáveis para deixar o código mais claro."
    )
    [request] = seen
    assert request.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert request.headers["x-goog-api-key"] == KEY
    assert KEY not in str(request.url)  # a chave vai no cabeçalho, nunca na URL
    body = json.loads(request.content)
    assert body["systemInstruction"] == {"parts": [{"text": "regras"}]}
    assert body["contents"] == [{"role": "user", "parts": [{"text": "dados"}]}]


# --- Falhas dos dois adaptadores -----------------------------------------------------------------


def _raise(error: type[httpx2.RequestError]) -> Callable[[httpx2.Request], httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error("falha simulada", request=request)

    return handler


FAILURES: dict[str, httpx2.Response | Callable[[httpx2.Request], httpx2.Response]] = {
    "401": httpx2.Response(401, json={"error": {"message": f"chave {KEY} inválida"}}),
    "429": httpx2.Response(429, json={"error": "rate limit"}),
    "500": httpx2.Response(500, text="erro interno"),
    "nao-json": httpx2.Response(200, text="<html>"),
    "sem-escolhas": httpx2.Response(200, json={"choices": [], "candidates": []}),
    "bloqueado": httpx2.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
    "grande-demais": httpx2.Response(200, content=b"{" + b" " * 70_000 + b"}"),
    "tempo": _raise(httpx2.ReadTimeout),
    "rede": _raise(httpx2.ConnectError),
}


@pytest.mark.parametrize("failure", FAILURES, ids=list(FAILURES))
@pytest.mark.parametrize("adapter", ["openai_compat", "gemini"])
async def test_failures_become_provider_errors_without_the_key_or_the_body(
    adapter: str, failure: str
) -> None:
    seen: list[httpx2.Request] = []
    config, cls = (OPENAI, OpenAICompatProvider) if adapter == "openai_compat" else (
        GEMINI, GeminiProvider
    )  # fmt: skip
    provider = cls(config, transport(FAILURES[failure], seen))

    with pytest.raises(ProviderError) as caught:
        await provider.generate(PROMPT, timeout_s=1)

    assert KEY not in str(caught.value)
    assert "inválida" not in str(caught.value)


async def test_the_fake_provider_keeps_the_prompts() -> None:
    fake = FakeProvider()

    assert await fake.generate(PROMPT, timeout_s=1) == FAKE_TEXT
    assert fake.prompts == [PROMPT]

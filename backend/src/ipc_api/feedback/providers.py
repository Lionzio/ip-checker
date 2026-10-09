"""Camada de provedores de LLM (S18-01, ADR-06; S32-12): uma interface e um adaptador por API.

- ``openai_compat``: a API de *chat completions* da OpenAI, que a Groq, a DeepSeek e outros
  também oferecem; muda só a URL base.
- ``gemini``: a API ``generateContent`` do Google.
- ``fake``: respostas fixas, sem rede, para os testes e o e2e.

Desde a Sprint 32 (Q-16), o feedback é montado sem IA por padrão, e as IAs só entram no
"Aprimorar com IA", numa cadeia em ordem, com fallback: ``IPC_LLM_CHAIN=gemini,groq`` lista os
nomes, e cada um tem provedor, modelo, URL e chave próprios (``IPC_LLM_GEMINI_PROVIDER``,
``IPC_LLM_GEMINI_MODEL``...), lidos de variáveis de ambiente que só a ``api`` recebe. Sem a cadeia,
valem as duas vagas antigas: a principal (``IPC_LLM_*``) e a de reserva (``IPC_LLM_FALLBACK_*``).
A chave nunca vai para o log, para uma resposta nem para uma mensagem de erro, e o corpo das
respostas do provedor também não.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx2

ProviderName = Literal["openai_compat", "gemini", "fake"]

DEFAULT_BASE_URLS: dict[str, str] = {
    "openai_compat": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}
#: Respostas acima disso não são texto de feedback.
MAX_RESPONSE_BYTES = 64 * 1024
#: O trecho livre tem de 1 a 3 frases; isto sobra.
MAX_OUTPUT_TOKENS = 400


#: O nome de uma IA da cadeia (``gemini``, ``groq``...) ou, nas vagas antigas, primary e fallback.
Slot = str
_NAME = re.compile(r"[a-z][a-z0-9_]{0,19}")

#: Prefixo das variáveis de cada vaga.
PREFIXES: dict[Slot, str] = {"primary": "IPC_LLM_", "fallback": "IPC_LLM_FALLBACK_"}


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """Uma IA: provedor, modelo, URL e chave."""

    provider: ProviderName | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = field(default=None, repr=False)
    #: Tempo de cada tentativa: com a reserva, as duas cabem no prazo total.
    timeout_s: float = 12.0
    temperature: float = 0.4

    @property
    def enabled(self) -> bool:
        return self.provider is not None

    @classmethod
    def from_env(cls, env: Mapping[str, str], prefix: str = "IPC_LLM_") -> LlmConfig:
        name = env.get(f"{prefix}PROVIDER") or None
        if name is None:
            return cls()
        if name not in ("openai_compat", "gemini", "fake"):
            raise ValueError(
                f"{prefix}PROVIDER inválido: {name!r}. Use openai_compat, gemini ou fake."
            )
        model = env.get(f"{prefix}MODEL") or None
        api_key = env.get(f"{prefix}API_KEY") or None
        if name != "fake" and (model is None or api_key is None):
            raise ValueError(f"{prefix}PROVIDER={name} exige {prefix}MODEL e {prefix}API_KEY.")
        base_url = env.get(f"{prefix}BASE_URL") or DEFAULT_BASE_URLS.get(name)
        if base_url is not None and not base_url.startswith("https://"):
            raise ValueError(f"{prefix}BASE_URL precisa ser HTTPS.")
        return cls(
            provider=name,  # type: ignore[arg-type]  # conferido acima
            model=model,
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=api_key,
            timeout_s=float(env.get(f"{prefix}TIMEOUT_S", cls().timeout_s)),
        )


@dataclass(frozen=True, slots=True)
class LlmSettings:
    """As IAs do "Aprimorar com IA", em ordem, e o prazo total de um aprimoramento."""

    primary: LlmConfig = field(default_factory=LlmConfig)
    fallback: LlmConfig = field(default_factory=LlmConfig)
    #: A cadeia (S32-12): nomes e configurações, na ordem; vazia, valem as duas vagas antigas.
    chain: tuple[tuple[Slot, LlmConfig], ...] = ()
    #: Tempo total, com todas as tentativas: cabe no tempo-limite do rewrite da Vercel (P-15 a).
    deadline_s: float = 28.0
    #: Depois de um 429 (cota do plano gratuito), a IA fica fora da cadeia por este tempo.
    cooldown_s: float = 60.0

    @property
    def configured(self) -> tuple[tuple[Slot, LlmConfig], ...]:
        """As IAs configuradas, na ordem em que são tentadas."""
        if self.chain:
            return tuple((name, config) for name, config in self.chain if config.enabled)
        slots: tuple[tuple[Slot, LlmConfig], ...] = (
            ("primary", self.primary),
            ("fallback", self.fallback),
        )
        return tuple((slot, config) for slot, config in slots if config.enabled)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> LlmSettings:
        primary = LlmConfig.from_env(env, PREFIXES["primary"])
        fallback = LlmConfig.from_env(env, PREFIXES["fallback"])
        if fallback.enabled and not primary.enabled:
            raise ValueError(
                "IPC_LLM_FALLBACK_PROVIDER é a IA de reserva: defina antes a principal, "
                "IPC_LLM_PROVIDER."
            )
        names = [name.strip().lower() for name in env.get("IPC_LLM_CHAIN", "").split(",")]
        names = [name for name in names if name]
        if len(names) != len(set(names)) or not all(_NAME.fullmatch(name) for name in names):
            raise ValueError(
                "IPC_LLM_CHAIN inválida: use nomes curtos e distintos, como gemini,groq."
            )
        chain: list[tuple[Slot, LlmConfig]] = []
        for name in names:
            prefix = f"IPC_LLM_{name.upper()}_"
            config = LlmConfig.from_env(env, prefix)
            if not config.enabled:
                raise ValueError(f"IPC_LLM_CHAIN cita {name}, mas {prefix}PROVIDER está vazia.")
            chain.append((name, config))
        return cls(
            primary=primary,
            fallback=fallback,
            chain=tuple(chain),
            deadline_s=float(env.get("IPC_LLM_DEADLINE_S", cls().deadline_s)),
            cooldown_s=float(env.get("IPC_LLM_COOLDOWN_S", cls().cooldown_s)),
        )


@dataclass(frozen=True, slots=True)
class Prompt:
    #: As regras do texto; nunca traz dados do aluno.
    system: str
    #: O resultado do motor e os dados (código e anotação), em blocos delimitados.
    user: str
    #: Teto da resposta: o aprimoramento (S32-12) escreve mais que o trecho curto do S18.
    max_output_tokens: int = MAX_OUTPUT_TOKENS


class ProviderError(Exception):
    """O provedor não respondeu, respondeu com erro ou com algo que não é texto."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        #: O status HTTP do provedor, quando houve um (429 = cota do plano esgotada).
        self.status = status


class Provider(Protocol):
    name: str

    async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
        """O texto gerado, ou ``ProviderError``."""


class _HttpProvider:
    name = "http"

    def __init__(
        self, config: LlmConfig, transport: httpx2.AsyncBaseTransport | None = None
    ) -> None:
        self.config = config
        self._transport = transport

    async def _post(
        self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: float
    ) -> Any:
        try:
            async with httpx2.AsyncClient(
                transport=self._transport, timeout=timeout_s, trust_env=False
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx2.TimeoutException:
            raise ProviderError("tempo esgotado") from None
        except httpx2.HTTPError as exc:
            raise ProviderError(type(exc).__name__) from None
        if response.status_code != 200:
            raise ProviderError(f"HTTP {response.status_code}", status=response.status_code)
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ProviderError("resposta grande demais")
        try:
            return response.json()
        except ValueError:
            raise ProviderError("resposta não é JSON") from None


class OpenAICompatProvider(_HttpProvider):
    name = "openai_compat"

    async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
        body = await self._post(
            f"{self.config.base_url}/chat/completions",
            {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                "temperature": self.config.temperature,
                "max_tokens": prompt.max_output_tokens,
            },
            {"Authorization": f"Bearer {self.config.api_key}"},
            timeout_s,
        )
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("resposta fora do formato") from None
        if not isinstance(text, str):
            raise ProviderError("resposta fora do formato")
        return text


class GeminiProvider(_HttpProvider):
    name = "gemini"

    async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
        body = await self._post(
            f"{self.config.base_url}/models/{self.config.model}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": prompt.system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
                "generationConfig": {
                    "temperature": self.config.temperature,
                    "maxOutputTokens": prompt.max_output_tokens,
                },
            },
            {"x-goog-api-key": self.config.api_key or ""},
            timeout_s,
        )
        try:
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(part["text"] for part in parts if isinstance(part.get("text"), str))
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("resposta fora do formato") from None
        if not text:
            raise ProviderError("resposta sem texto")
        return text


#: O que o provedor falso responde por padrão: neutro, sem violações e sem nomes.
FAKE_TEXT = (
    "Gostei bastante de como você organizou a leitura dos dados. "
    "Como dica, vale testar o programa com outros valores de entrada."
)


class FakeProvider:
    """Sem rede: devolve o texto de ``respond`` e guarda cada prompt recebido."""

    name = "fake"

    def __init__(self, respond: Callable[[Prompt], str] | None = None) -> None:
        self.respond = respond or (lambda _prompt: FAKE_TEXT)
        self.prompts: list[Prompt] = []

    async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
        self.prompts.append(prompt)
        return self.respond(prompt)


def build_provider(
    config: LlmConfig, transport: httpx2.AsyncBaseTransport | None = None
) -> Provider | None:
    match config.provider:
        case "openai_compat":
            return OpenAICompatProvider(config, transport)
        case "gemini":
            return GeminiProvider(config, transport)
        case "fake":
            return FakeProvider()
        case _:
            return None

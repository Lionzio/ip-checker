"""``POST /api/v1/feedback`` com o analyzer de verdade e um provedor falso (S18-02; US-32).

Confere cada critério da US-32 por chamada à API: as frases obrigatórias, a apresentação e as
autorreferências pelo tratamento, a recusa de texto que contradiz o motor e, no fim, que nenhuma
requisição ao provedor leva o nome real do aluno.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import BASE_URL, cookie_header, make_app, member, open_session
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.accounts.models import Account, Role, Treatment
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.feedback.compose import INVALID_SENTENCE, VALID_SENTENCE
from ipc_api.feedback.providers import FakeProvider, LlmConfig, LlmSettings, Prompt, ProviderError
from ipc_api.feedback.service import FeedbackLimits
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

STUDENT = "Isabella Schultz"
VALID = "# Isabella Schultz, 20261234\nn = int(input())\nif n > 0:\n    print('positivo')\n"
INVALID = "x = int(input())\nfor i in range(x):\n    print(i)\n"
SETTINGS = ApiSettings(
    rate_limit=RateLimitConfig(client_per_min=1_000_000, ip_per_min=1_000_000),
    llm=LlmSettings(primary=LlmConfig(provider="fake")),
    feedback_limits=FeedbackLimits(per_account_day=1_000, daily_cap=1_000),
)


class Recorder(FakeProvider):
    """Provedor falso que responde o que o teste mandar e guarda cada prompt."""

    def __init__(self) -> None:
        super().__init__(lambda _prompt: "Gostei bastante de como você organizou o código.")


@pytest.fixture(scope="module")
def analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as client:
        yield client


def _bridge(analyzer: TestClient) -> httpx2.MockTransport:
    def bridge(request: httpx2.Request) -> httpx2.Response:
        answer = analyzer.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={"Content-Type": "application/json"},
        )
        return httpx2.Response(
            answer.status_code,
            content=answer.content,
            headers={"Content-Type": answer.headers["content-type"]},
        )

    return httpx2.MockTransport(bridge)


@pytest.fixture
def provider() -> Recorder:
    return Recorder()


@pytest.fixture
def stack(
    analyzer: TestClient, provider: Recorder
) -> Iterator[tuple[TestClient, MemoryAccountStore]]:
    store = MemoryAccountStore()
    app, _ = make_app(
        SETTINGS, store=store, analyzer_transport=_bridge(analyzer), llm_providers=[provider]
    )
    with TestClient(app, base_url=BASE_URL) as client:
        yield client, store


def ask(
    stack: tuple[TestClient, MemoryAccountStore],
    account: Account,
    code: str = VALID,
    **extra: Any,
) -> httpx2.Response:
    api, store = stack
    body = {"code": code, "list_number": 1, "student_name": STUDENT, **extra}
    return api.post(
        "/api/v1/feedback", json=body, headers=cookie_header(open_session(store, account))
    )


def test_without_violations_the_text_has_the_valid_sentence(
    stack: tuple[TestClient, MemoryAccountStore],
) -> None:
    ana = member(stack[1], name="Ana Lima", treatment=Treatment.FEMININO)

    response = ask(stack, ana)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json()
    assert (body["status"], body["source"], body["provider"]) == ("valid", "llm", "primary")
    assert body["text"] == (
        "Olá, Isabella Schultz, sou a monitora Ana Lima e seu código estava muito bom. "
        f"{VALID_SENTENCE} Gostei bastante de como você organizou o código."
    )


def test_with_violations_the_sentence_lists_what_the_engine_found(
    stack: tuple[TestClient, MemoryAccountStore],
) -> None:
    professor = member(
        stack[1], name="Rui Costa", role=Role.PROFESSOR, treatment=Treatment.MASCULINO
    )

    body = ask(stack, professor, INVALID).json()

    assert body["status"] == "invalid"
    expected = INVALID_SENTENCE.format(
        itens="o uso de for e range() e a falta de if ou operador ternário"
    )
    assert body["text"].startswith(
        "Olá, Isabella Schultz, sou o professor Rui Costa e seu código precisa de ajustes. "
        + expected
    )


@pytest.mark.parametrize(
    ("role", "treatment", "presentation"),
    [
        (Role.MONITOR_CHEFE, Treatment.NEUTRO, "aqui é Bia Rocha, da chefia da monitoria, e"),
        (Role.MONITOR_CHEFE, Treatment.FEMININO, "sou a monitora-chefe Bia Rocha e"),
        (Role.DESENVOLVEDOR, Treatment.MASCULINO, "sou o monitor Bia Rocha e"),
    ],
)
def test_the_presentation_comes_from_the_role_and_treatment(
    stack: tuple[TestClient, MemoryAccountStore],
    role: Role,
    treatment: Treatment,
    presentation: str,
) -> None:
    evaluator = member(stack[1], name="Bia Rocha", role=role, treatment=treatment)

    text = ask(stack, evaluator).json()["text"]

    assert text.startswith(f"Olá, Isabella Schultz, {presentation} seu código estava muito bom.")


def test_a_gendered_answer_in_the_neutral_treatment_gives_way_to_the_template(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    provider.respond = lambda _prompt: "Fiquei satisfeito com o código."
    evaluator = member(stack[1], name="Bia Rocha", treatment=Treatment.NEUTRO)

    body = ask(stack, evaluator).json()

    assert body["source"] == "template"
    assert f"{VALID_SENTENCE} " in body["text"]
    assert "satisfeito" not in body["text"]
    assert len(provider.prompts) == 2


def test_an_answer_that_contradicts_the_engine_is_never_shown(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    provider.respond = lambda _prompt: "Seu código está perfeito, sem erros."

    body = ask(stack, member(stack[1]), INVALID).json()

    assert body["source"] == "template"
    assert "perfeito" not in body["text"]


def test_the_provider_never_receives_the_real_name(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    evaluator = member(stack[1], name="Ana Lima")
    provider.respond = lambda _prompt: "Notei que você tratou bem o caso zero, [ALUNO]."

    body = ask(
        stack, evaluator, annotation="A Isabella esqueceu o caso negativo; Schultz, revise."
    ).json()

    [prompt] = provider.prompts
    sent = prompt.system + prompt.user
    for secret in ("Isabella", "Schultz", "20261234", "Ana Lima"):
        assert secret not in sent
    assert "[ALUNO]" in prompt.user
    # A resposta volta com o nome no lugar do marcador.
    assert body["text"].endswith("Notei que você tratou bem o caso zero, Isabella Schultz.")


def test_a_syntax_error_has_no_feedback(stack: tuple[TestClient, MemoryAccountStore]) -> None:
    response = ask(stack, member(stack[1]), "if x\n    y = 1\n")

    assert (response.status_code, response.json()["error"]["code"]) == (422, "INVALID_INPUT")
    assert "linha 1, coluna 5" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ({"student_name": " "}, "Informe o nome do aluno."),
        ({"student_name": "Ana\x00"}, "caracteres de controle"),
        ({"annotation": "linha\x07"}, "caracteres de controle"),
        ({"list_number": 5}, "Lista 5"),
    ],
)
def test_invalid_input_is_refused_before_the_provider(
    stack: tuple[TestClient, MemoryAccountStore],
    provider: Recorder,
    extra: dict[str, Any],
    message: str,
) -> None:
    response = ask(stack, member(stack[1]), **extra)

    assert response.status_code == 422
    assert message in response.json()["error"]["message"]
    assert provider.prompts == []


def test_annotations_keep_line_breaks(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    response = ask(stack, member(stack[1]), annotation="Primeiro ponto.\nSegundo ponto.")

    assert response.status_code == 200
    assert "Primeiro ponto.\nSegundo ponto." in provider.prompts[0].user


def test_the_daily_quota_is_per_account(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    api, store = stack
    api.app.state.feedback.limits = FeedbackLimits(per_account_day=1, daily_cap=100)  # type: ignore[attr-defined]
    ana, bia = member(store), member(store)

    first, second, other = ask(stack, ana), ask(stack, ana), ask(stack, bia)

    assert (first.status_code, other.status_code) == (200, 200)
    assert (second.status_code, second.json()["error"]["code"]) == (429, "RATE_LIMITED")
    assert second.headers["Retry-After"] == str(second.json()["error"]["retry_after_s"])


def test_without_any_ai_the_feedback_is_assembled_without_ai(analyzer: TestClient) -> None:
    store = MemoryAccountStore()
    app, _ = make_app(
        replace(SETTINGS, llm=LlmSettings()), store=store, analyzer_transport=_bridge(analyzer)
    )
    with TestClient(app, base_url=BASE_URL) as api:
        options = api.get("/api/v1/auth/options").json()
        response = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT},
            headers=cookie_header(open_session(store, member(store, name="Ana Lima"))),
        )

    assert options["feedback_ai"] is False
    body = response.json()
    assert (response.status_code, body["source"], body["provider"]) == (200, "template", None)
    assert body["text"].startswith(
        "Olá, Isabella Schultz, sou a monitora Ana Lima e seu código estava muito bom. "
        f"{VALID_SENTENCE} "
    )


def test_when_the_primary_ai_fails_the_fallback_writes(analyzer: TestClient) -> None:
    class Down(FakeProvider):
        async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
            self.prompts.append(prompt)
            raise ProviderError("HTTP 503")

    store = MemoryAccountStore()
    down, fallback = Down(), Recorder()
    app, _ = make_app(
        SETTINGS, store=store, analyzer_transport=_bridge(analyzer), llm_providers=[down, fallback]
    )
    with TestClient(app, base_url=BASE_URL) as api:
        body = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT},
            headers=cookie_header(open_session(store, member(store))),
        ).json()

    assert (body["source"], body["provider"]) == ("llm", "fallback")
    assert len(down.prompts) == len(fallback.prompts) == 1


def test_with_an_ai_the_page_knows(stack: tuple[TestClient, MemoryAccountStore]) -> None:
    assert stack[0].get("/api/v1/auth/options").json()["feedback_ai"] is True


def test_feedback_needs_a_session(stack: tuple[TestClient, MemoryAccountStore]) -> None:
    response = stack[0].post(
        "/api/v1/feedback", json={"code": VALID, "list_number": 1, "student_name": STUDENT}
    )

    assert (response.status_code, response.json()["error"]["code"]) == (401, "UNAUTHENTICATED")


def test_prompt_type_is_the_provider_contract(provider: Recorder) -> None:
    # O provedor recebe só regras (system) e dados delimitados (user).
    assert Prompt.__dataclass_fields__.keys() == {"system", "user"}


def test_an_analysis_limit_comes_back_as_is(stack: tuple[TestClient, MemoryAccountStore]) -> None:
    response = ask(stack, member(stack[1]), "(" * 1_000 + ")" * 1_000)

    assert (response.status_code, response.json()["error"]["code"]) == (422, "ANALYSIS_LIMIT")


def test_an_unavailable_analyzer_is_503() -> None:
    store = MemoryAccountStore()
    app, _ = make_app(
        SETTINGS,
        store=store,
        analyzer_transport=httpx2.MockTransport(lambda _: httpx2.Response(500)),
    )
    with TestClient(app, base_url=BASE_URL) as api:
        response = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT},
            headers=cookie_header(open_session(store, member(store))),
        )

    assert (response.status_code, response.json()["error"]["code"]) == (503, "ANALYZER_UNAVAILABLE")

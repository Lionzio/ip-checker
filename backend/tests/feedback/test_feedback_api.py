"""``POST /api/v1/feedback`` com o analyzer de verdade e um provedor falso (S18-02; US-32; S32-12).

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
    # Todas as listas vêm habilitadas desde a Sprint 23; a 6 fica de fora para o LIST_NOT_ENABLED.
    enabled_lists=frozenset({1, 2, 3, 4, 5}),
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
    # Estes testes conferem o texto da IA: pedem o "Aprimorar com IA" (S32-12), salvo se o
    # teste disser outra coisa.
    body = {"code": code, "list_number": 1, "student_name": STUDENT, "enhance": True, **extra}
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
        ({"list_number": 6}, "Lista 6"),
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


def test_a_refused_code_does_not_spend_the_quota(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    """S25-05: a cota só é cobrada depois da análise."""
    api, store = stack
    api.app.state.feedback.limits = FeedbackLimits(per_account_day=1, daily_cap=100)  # type: ignore[attr-defined]
    ana = member(store)

    broken = ask(stack, ana, code="if True print(1)\n")
    fine = ask(stack, ana)

    assert broken.status_code == 422
    assert fine.status_code == 200
    assert sum(store.feedback_quota.values()) == 1


def test_personal_data_never_reaches_the_ai(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    code = (
        "def soma(a, b):\n"
        '    """Isabella Schultz, matrícula 20231234567, isa@cin.ufpe.br"""\n'
        '    cpf = "123.456.789-09"\n'
        "    return a + b\n"
        "x = int(input())\n"
        "if x > 0:\n"
        "    print(soma(x, 1))\n"
    )
    response = ask(
        stack,
        member(stack[1]),
        code=code,
        annotation="Falei com ela pelo isa@cin.ufpe.br, matrícula 20231234567.",
    )

    assert response.status_code == 200
    sent = provider.prompts[0].user
    for secret in ("20231234567", "isa@cin.ufpe.br", "123.456.789-09", "Schultz"):
        assert secret not in sent
    assert "[EMAIL]" in sent
    assert "[MATRICULA]" in sent
    assert '"[CPF]"' in sent
    assert "def soma(a, b):\n    ...\n" in sent


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
            json={"code": VALID, "list_number": 1, "student_name": STUDENT, "enhance": True},
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
    # O provedor recebe só regras (system), dados delimitados (user) e o teto da resposta.
    assert Prompt.__dataclass_fields__.keys() == {"system", "user", "max_output_tokens"}


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


# --- Sem IA por padrão e o "Aprimorar com IA" (Q-16, S32-12) ------------------------------------


def test_generating_is_without_ai_and_spends_no_quota(
    stack: tuple[TestClient, MemoryAccountStore], provider: Recorder
) -> None:
    api, store = stack
    api.app.state.feedback.limits = FeedbackLimits(per_account_day=1, daily_cap=100)  # type: ignore[attr-defined]
    ana = member(store)

    plain = [ask(stack, ana, enhance=False).json() for _ in range(3)]
    enhanced = ask(stack, ana)

    assert {(body["source"], body["provider"], body["notice"]) for body in plain} == {
        ("template", None, None)
    }
    # Os três textos sem IA não chamaram a IA; o aprimoramento chamou uma vez.
    assert len(provider.prompts) == 1
    # Só o aprimoramento gasta a cota (1 por dia aqui): os três textos sem IA não contaram.
    assert enhanced.status_code == 200
    assert enhanced.json()["source"] == "llm"
    assert ask(stack, ana).status_code == 429


def test_enhancing_without_ai_keeps_the_text_and_says_why(analyzer: TestClient) -> None:
    store = MemoryAccountStore()
    settings = replace(SETTINGS, llm=LlmSettings())
    app, _ = make_app(settings, store=store, analyzer_transport=_bridge(analyzer))
    with TestClient(app, base_url=BASE_URL) as api:
        body = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT, "enhance": True},
            headers=cookie_header(open_session(store, member(store))),
        ).json()

    assert (body["source"], body["provider"]) == ("template", None)
    assert "não está configurado" in body["notice"]


def test_when_no_ai_answers_the_text_stays_without_ai(analyzer: TestClient) -> None:
    class Busy(FakeProvider):
        async def generate(self, prompt: Prompt, *, timeout_s: float) -> str:
            self.prompts.append(prompt)
            raise ProviderError("HTTP 429", status=429)

    store = MemoryAccountStore()
    first, second = Busy(), Busy()
    app, _ = make_app(
        SETTINGS, store=store, analyzer_transport=_bridge(analyzer), llm_providers=[first, second]
    )
    with TestClient(app, base_url=BASE_URL) as api:
        body = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT, "enhance": True},
            headers=cookie_header(open_session(store, member(store))),
        ).json()

    assert (body["source"], body["provider"]) == ("template", None)
    assert "Nenhuma IA respondeu" in body["notice"]
    assert body["text"].startswith("Olá, Isabella Schultz")
    assert (len(first.prompts), len(second.prompts)) == (1, 1)


def test_the_answer_says_whether_the_page_can_enhance(
    stack: tuple[TestClient, MemoryAccountStore], analyzer: TestClient
) -> None:
    assert ask(stack, member(stack[1]), enhance=False).json()["can_enhance"] is True
    store = MemoryAccountStore()
    app, _ = make_app(
        replace(SETTINGS, llm=LlmSettings()), store=store, analyzer_transport=_bridge(analyzer)
    )
    with TestClient(app, base_url=BASE_URL) as api:
        body = api.post(
            "/api/v1/feedback",
            json={"code": VALID, "list_number": 1, "student_name": STUDENT},
            headers=cookie_header(open_session(store, member(store))),
        ).json()
    assert body["can_enhance"] is False


def test_generating_again_reuses_the_analysis_without_keeping_the_code(
    analyzer: TestClient,
) -> None:
    """S38-04: o segundo "Gerar" do mesmo código não chama o analisador, e o cache não guarda
    o código, o nome do aluno nem o texto; o "Aprimorar" sempre analisa (o código limpo)."""
    calls: list[str] = []
    inner = _bridge(analyzer)

    def counting(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return inner.handle_request(request)

    store = MemoryAccountStore()
    app, _ = make_app(SETTINGS, store=store, analyzer_transport=httpx2.MockTransport(counting))
    with TestClient(app, base_url=BASE_URL) as api:
        headers = cookie_header(open_session(store, member(store)))

        def generate(annotation: str | None = None, *, enhance: bool = False) -> dict[str, Any]:
            response = api.post(
                "/api/v1/feedback",
                json={
                    "code": INVALID,
                    "list_number": 1,
                    "student_name": STUDENT,
                    "annotation": annotation,
                    "enhance": enhance,
                },
                headers=headers,
            )
            assert response.status_code == 200, response.text
            return response.json()  # type: ignore[no-any-return]

        first = generate()
        analyses = [path for path in calls if "feedback" in path]
        second = generate("Releia o enunciado")

        assert [path for path in calls if "feedback" in path] == analyses
        assert second["status"] == first["status"] == "invalid"
        assert "Releia o enunciado" in second["text"]
        cache = api.app.state.feedback.results  # type: ignore[attr-defined]
        stored = repr(cache._entries)
        assert "range(x)" not in stored
        assert STUDENT not in stored
        assert "Olá" not in stored

        generate(enhance=True)
        assert len([path for path in calls if "feedback" in path]) == len(analyses) + 1


def test_the_cache_expires_and_drops_the_oldest() -> None:
    from ipc_api.feedback.cache import CachedResult, FeedbackResultCache, result_key

    now = [0.0]
    cache = FeedbackResultCache(ttl_s=600, max_entries=2, monotonic=lambda: now[0])
    keys = [result_key(f"x = {n}\n", 1, None) for n in range(3)]
    result = CachedResult("valid", ())
    for key in keys:
        cache.put(key, result)

    assert cache.get(keys[0]) is None
    assert cache.get(keys[2]) == result
    now[0] = 601
    assert cache.get(keys[2]) is None
    assert (
        result_key("x = 1\n", 1, None)
        != result_key("x = 1\n", 2, None)
        != result_key("x = 1\n", 1, "L1-Q1")
    )

"""Plágio pela API (S17-02; FR-29, US-31): faixas, contrato da rota e comparação de verdade.

As faixas são conferidas nos valores exatos de 99, 95, 90 e 80% e logo abaixo deles. A rota é
testada com o analyzer simulado (cada resposta e cada falha) e com o analyzer de verdade, em
memória, numa cópia com as variáveis renomeadas.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings
from ipc_api.similarity import BANDS, NOTICE, SHORT_CODE_TOKENS, classify

UNLIMITED = ApiSettings(rate_limit=RateLimitConfig(client_per_min=1_000_000, ip_per_min=1_000_000))
Handler = Callable[[httpx2.Request], httpx2.Response]


@pytest.mark.parametrize(
    ("percent", "band"),
    [
        (100.0, "plagio"),
        (99.0, "plagio"),
        (98.96, "plagio"),  # exibido como 99,0%
        (98.9, "altas_chances"),
        (95.0, "altas_chances"),
        (94.9, "requer_atencao"),
        (90.0, "requer_atencao"),
        (89.9, "ligeiramente_suspeito"),
        (80.0, "ligeiramente_suspeito"),
        (79.9, "sem_suspeitas"),
        (0.0, "sem_suspeitas"),
    ],
)
def test_each_value_falls_in_the_band_that_starts_at_it(percent: float, band: str) -> None:
    assert classify(percent).id == band


def test_the_bands_are_the_ones_of_fr29() -> None:
    assert [(band.label, band.minimum) for band in BANDS] == [
        ("Plágio", 99.0),
        ("Altas chances de plágio", 95.0),
        ("Requer atenção", 90.0),
        ("Ligeiramente suspeito", 80.0),
        ("Sem suspeitas", 0.0),
    ]


# --- Rota com o analyzer simulado ----------------------------------------------------------------


def _api(handler: Handler) -> TestClient:
    return authed_client(*make_app(UNLIMITED, analyzer_transport=httpx2.MockTransport(handler)))


def _compared(percent: float, tokens: tuple[int, int] = (120, 130)) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/internal/similarity"
        assert json.loads(request.content) == {"first": "a = 1\n", "second": "b = 1\n"}
        return httpx2.Response(
            200,
            json={
                "status": "compared",
                "percent": percent,
                "token_counts": list(tokens),
                "syntax_error_side": None,
                "syntax_error": None,
            },
        )

    return handler


def _post(api: TestClient, **body: Any) -> httpx2.Response:
    return api.post("/api/v1/similarity", json={"code_a": "a = 1\n", "code_b": "b = 1\n", **body})


def test_a_comparison_comes_with_the_band_and_the_notice() -> None:
    with _api(_compared(99.0)) as api:
        response = _post(api)

    body = response.json()
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert body["status"] == "compared"
    assert body["similarity"] == 99.0
    assert body["band"] == {"id": "plagio", "label": "Plágio", "minimum": 99.0}
    assert body["short_code"] is False
    assert body["syntax_error"] is None
    assert body["notice"] == NOTICE
    assert body["request_id"] == response.headers["X-Request-Id"]


def test_short_codes_get_an_extra_warning() -> None:
    with _api(_compared(85.0, (SHORT_CODE_TOKENS - 1, 400))) as api:
        body = _post(api).json()

    assert (body["short_code"], body["band"]["id"]) == (True, "ligeiramente_suspeito")


@pytest.mark.parametrize(("side", "code"), [(1, "a"), (2, "b")])
def test_a_syntax_error_says_which_code(side: int, code: str) -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "status": "syntax_error",
                "percent": None,
                "token_counts": None,
                "syntax_error_side": side,
                "syntax_error": {"line": 2, "col": 5, "message": "Faltou ':' no fim da linha."},
            },
        )

    with _api(handler) as api:
        body = _post(api).json()

    assert body["status"] == "syntax_error"
    assert (body["similarity"], body["band"]) == (None, None)
    assert body["syntax_error"] == {
        "code": code,
        "line": 2,
        "col": 5,
        "message": "Faltou ':' no fim da linha.",
    }


@pytest.mark.parametrize(("field", "label"), [("code_a", "Código A"), ("code_b", "Código B")])
def test_each_code_is_checked_before_the_analyzer(field: str, label: str) -> None:
    calls: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(500)

    with _api(handler) as api:
        too_big = _post(api, **{field: "#" + "a" * 51_200})
        too_long = _post(api, **{field: "x = 1\n" * 1_001})

    assert (too_big.status_code, too_big.json()["error"]["code"]) == (413, "PAYLOAD_TOO_LARGE")
    assert too_big.json()["error"]["message"].startswith(f"{label}: ")
    assert (too_long.status_code, too_long.json()["error"]["code"]) == (422, "INVALID_INPUT")
    assert calls == []


@pytest.mark.parametrize(
    ("answer", "status", "code"),
    [
        (
            httpx2.Response(
                422,
                json={
                    "error": {
                        "code": "ANALYSIS_LIMIT",
                        "message": "Código B: x",
                    }
                },
            ),
            422,
            "ANALYSIS_LIMIT",
        ),
        (httpx2.Response(500), 503, "ANALYZER_UNAVAILABLE"),
        (
            httpx2.Response(200, json={"status": "compared", "percent": 150}),
            503,
            "ANALYZER_UNAVAILABLE",
        ),
        (
            httpx2.Response(
                200,
                json={
                    "status": "compared",
                    "percent": 50.0,
                    "token_counts": None,
                    "syntax_error_side": 1,
                    "syntax_error": None,
                },
            ),
            503,
            "ANALYZER_UNAVAILABLE",
        ),
    ],
    ids=["recusa", "erro", "fora-do-esquema", "incoerente"],
)
def test_analyzer_answers_are_mapped_or_distrusted(
    answer: httpx2.Response, status: int, code: str
) -> None:
    with _api(lambda _: answer) as api:
        response = _post(api)

    assert (response.status_code, response.json()["error"]["code"]) == (status, code)


def test_comparing_needs_a_session() -> None:
    app, _ = make_app(UNLIMITED)
    with TestClient(app, base_url="https://testserver") as api:
        response = _post(api)

    assert (response.status_code, response.json()["error"]["code"]) == (401, "UNAUTHENTICATED")


def test_invalid_bodies_are_explained() -> None:
    with _api(_compared(10.0)) as api:
        response = api.post("/api/v1/similarity", json={"code_a": "x = 1\n"})

    assert response.status_code == 422
    assert "code_a e code_b" in response.json()["error"]["message"]


# --- Com o analyzer de verdade -------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_api() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as analyzer:

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

        with _api(bridge) as api:
            yield api


ORIGINAL = """\
nota = float(input())
frequencia = float(input())
if frequencia < 75:
    situacao = "reprovado por falta"
elif nota >= 7:
    situacao = "aprovado"
elif nota >= 3:
    situacao = "final"
else:
    situacao = "reprovado"
print(situacao)
"""


def test_a_renamed_copy_is_plagiarism(real_api: TestClient) -> None:
    copy = (
        ORIGINAL.replace("nota", "media").replace("frequencia", "presenca")
        .replace("situacao", "resultado")
    )  # fmt: skip

    body = real_api.post("/api/v1/similarity", json={"code_a": ORIGINAL, "code_b": copy}).json()

    assert body["status"] == "compared"
    assert body["similarity"] >= 99.0
    assert body["band"]["label"] == "Plágio"


def test_a_real_syntax_error_points_to_code_b(real_api: TestClient) -> None:
    body = real_api.post(
        "/api/v1/similarity", json={"code_a": ORIGINAL, "code_b": "if x\n    y = 1\n"}
    ).json()

    assert body["status"] == "syntax_error"
    assert (body["syntax_error"]["code"], body["syntax_error"]["line"]) == ("b", 1)


def test_a_real_limit_says_which_code(real_api: TestClient) -> None:
    response = real_api.post(
        "/api/v1/similarity", json={"code_a": "(" * 1_000 + ")" * 1_000, "code_b": ORIGINAL}
    )

    assert (response.status_code, response.json()["error"]["code"]) == (422, "ANALYSIS_LIMIT")
    assert response.json()["error"]["message"].startswith("Código A: ")


def test_a_real_comparison_brings_the_metrics_and_the_matches(real_api: TestClient) -> None:
    # A cópia com as condições reescritas e as linhas trocadas (ADR-07).
    reordered = (
        ORIGINAL.replace("frequencia = float(input())\n", "")
        .replace("nota = float(input())\n", "nota = float(input())\nfrequencia = float(input())\n")
        .replace("frequencia < 75", "75 > frequencia")
    )

    body = real_api.post(
        "/api/v1/similarity", json={"code_a": ORIGINAL, "code_b": reordered}
    ).json()

    assert body["similarity"] == 100.0
    assert body["metrics"]["tree_dice"] == 100.0
    assert body["metrics"]["sequence"] < 100.0
    assert {"a_first": 3, "a_last": 10, "b_first": 3, "b_last": 10} in body["matches"]


# --- Contra a turma (S27-02) ---------------------------------------------------------------------


def _class_answer(results: list[dict[str, Any]], status: str = "compared") -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/internal/similarity/class"
        return httpx2.Response(
            200, json={"status": status, "syntax_error": None, "results": results}
        )

    return handler


def _item(percent: float, tokens: int = 100) -> dict[str, Any]:
    return {
        "status": "compared",
        "percent": percent,
        "token_count": tokens,
        "metrics": {"sequence": None, "tree_dice": percent, "tree_containment": percent},
    }


def test_the_class_comes_sorted_with_bands_and_the_refused_last() -> None:
    results = [
        _item(40.0),
        {"status": "rejected", "message": "O código está vazio."},
        _item(99.5, tokens=30),
        {"status": "syntax_error", "syntax_error": {"line": 2, "col": 1, "message": "faltou ':'"}},
    ]
    solutions = [{"label": f"Aluno {n}", "code": "x = 1\n"} for n in range(4)]

    with _api(_class_answer(results)) as api:
        response = api.post(
            "/api/v1/similarity/batch", json={"code": "y = 1\n", "solutions": solutions}
        )

    body = response.json()
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert [item["label"] for item in body["results"]] == [
        "Aluno 2",
        "Aluno 0",
        "Aluno 1",
        "Aluno 3",
    ]
    first = body["results"][0]
    assert (first["similarity"], first["band"]["label"], first["short_code"]) == (
        99.5,
        "Plágio",
        True,
    )
    assert body["results"][2]["message"] == "O código está vazio."
    assert body["results"][3]["syntax_error"]["message"] == "faltou ':'"
    assert body["notice"] == NOTICE


def test_the_compared_solution_with_a_syntax_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "status": "syntax_error",
                "syntax_error": {"line": 1, "col": 5, "message": "faltou ':'"},
                "results": [],
            },
        )

    with _api(handler) as api:
        body = api.post(
            "/api/v1/similarity/batch",
            json={"code": "if x\n", "solutions": [{"label": "A", "code": "x = 1\n"}]},
        ).json()

    assert (body["status"], body["results"]) == ("syntax_error", [])
    assert body["syntax_error"]["line"] == 1


def test_the_class_answer_must_match_the_class() -> None:
    with _api(_class_answer([_item(10.0)])) as api:
        response = api.post(
            "/api/v1/similarity/batch",
            json={
                "code": "y = 1\n",
                "solutions": [{"label": "A", "code": "x\n"}, {"label": "B", "code": "z\n"}],
            },
        )

    assert (response.status_code, response.json()["error"]["code"]) == (503, "ANALYZER_UNAVAILABLE")


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"code": "x = 1\n", "solutions": []}, 422),
        ({"code": "x = 1\n", "solutions": [{"label": "", "code": "x\n"}]}, 422),
        ({"code": "x = 1\n", "solutions": [{"label": "A", "code": "x\n"}] * 101}, 422),
        ({"code": "", "solutions": [{"label": "A", "code": "x\n"}]}, 422),
    ],
    ids=["vazia", "sem-rotulo", "mais-de-100", "codigo-vazio"],
)
def test_invalid_class_requests_are_refused_before_the_analyzer(
    body: dict[str, Any], status: int
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("o analyzer não deveria ser chamado")

    with _api(handler) as api:
        response = api.post("/api/v1/similarity/batch", json=body)

    assert response.status_code == status


def test_the_class_needs_a_session() -> None:
    app, _ = make_app(UNLIMITED)
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/similarity/batch",
            json={"code": "x\n", "solutions": [{"label": "A", "code": "x\n"}]},
        )

    assert (response.status_code, response.json()["error"]["code"]) == (401, "UNAUTHENTICATED")


def test_a_real_class_ignores_what_everybody_writes(real_api: TestClient) -> None:
    common = "valor = int(input())\nprint(valor * 2 + 1)\n"
    target = common + "if valor > 10:\n    print('grande')\n"
    solutions = [
        {"label": f"Aluno {k}", "code": common + f"for i in range({k}):\n    print(i * {k})\n"}
        for k in range(2, 12)
    ]
    copy = target.replace("grande", "enorme").replace("valor", "numero")
    solutions.append({"label": "Cópia", "code": copy})

    body = real_api.post(
        "/api/v1/similarity/batch", json={"code": target, "solutions": solutions}
    ).json()

    assert body["results"][0]["label"] == "Cópia"
    assert body["results"][0]["band"]["label"] == "Plágio"
    assert all(item["similarity"] < 80.0 for item in body["results"][1:])


def test_a_lone_carriage_return_in_the_class_is_not_a_server_error(real_api: TestClient) -> None:
    # O caso do schemathesis: o tokenize falhava com "\r" depois de "Ý" e a rota dava 500.
    response = real_api.post(
        "/api/v1/similarity/batch",
        json={"code": "Ý\rØ", "solutions": [{"code": "Ý\rØ\r", "label": "Aluno"}]},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["similarity"] == 100.0


def test_all_against_all_groups_the_copies_and_labels_every_pair(real_api: TestClient) -> None:
    """S40-02: pela API e o analisador de verdade, a cópia renomeada forma um grupo."""
    copy = (
        ORIGINAL.replace("nota", "media").replace("frequencia", "presenca")
        .replace("situacao", "resultado")
    )  # fmt: skip
    other = "n = int(input())\nif n % 2 == 0:\n    print('par')\nelse:\n    print('ímpar')\n"
    solutions = [
        {"label": "Ana", "code": ORIGINAL},
        {"label": "Bruno", "code": other},
        {"label": "Carla", "code": copy},
        {"label": "Davi", "code": "if x\n"},
    ]

    response = real_api.post("/api/v1/similarity/class-matrix", json={"solutions": solutions})

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["status"] for item in body["solutions"]] == [
        "compared",
        "compared",
        "compared",
        "syntax_error",
    ]
    assert body["groups"] == [["Ana", "Carla"]]
    first = body["pairs"][0]
    assert {first["a"], first["b"]} == {"Ana", "Carla"}
    assert first["band"]["label"] == "Plágio"
    assert len(body["pairs"]) == 3
    assert body["notice"] == NOTICE


def test_all_against_all_needs_two_to_sixty_solutions(real_api: TestClient) -> None:
    one = [{"label": "A", "code": "x = 1\n"}]
    many = [{"label": str(n), "code": f"x = {n}\n"} for n in range(61)]

    for solutions in (one, many):
        response = real_api.post("/api/v1/similarity/class-matrix", json={"solutions": solutions})
        assert response.status_code == 422

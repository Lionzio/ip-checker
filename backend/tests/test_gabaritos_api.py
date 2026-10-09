"""A comparação com o gabarito na verificação e no plágio (ADR-11, FR-32; S32-04, S32-05, S32-09).

A API conversa com o analisador de verdade (em memória, com o pool real), e os gabaritos são
sintéticos, numa pasta temporária (``IPC_GABARITOS_DIR``). O canário só existe no gabarito: ele
nunca pode aparecer numa resposta nem num log.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.gabaritos import GabaritosConfig
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

CANARY = "canario_gabarito_s32"
#: Gabarito sintético da L1-Q1 (sem regra cadastrada) do período ativo.
GABARITO = f"""\
{CANARY} = int(input())
total = 0
contador = 0
while contador < {CANARY}:
    valor = int(input())
    if valor % 2 == 0:
        total = total + valor
    contador = contador + 1
if total > 100:
    print("MARCADOR-DO-GABARITO", total)
else:
    print("pouco", total)
"""
STUDENT = (
    GABARITO.replace(CANARY, "quantidade")
    .replace("MARCADOR-DO-GABARITO", "muito")
    .replace("total", "soma")
)
INDEPENDENT = "n = int(input())\nif n > 0:\n    print('positivo')\nelse:\n    print('outro')\n"
SETTINGS = ApiSettings(
    rate_limit=RateLimitConfig(
        client_per_min=1_000_000, ip_per_min=1_000_000, api_ip_per_min=1_000_000
    ),
)


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


@pytest.fixture(scope="module")
def folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("gabaritos")
    (root / "2026.2" / "lista-1").mkdir(parents=True)
    (root / "2026.2" / "lista-1" / "L1-Q1.py").write_text(GABARITO, encoding="utf-8")
    (root / "2026.2" / "lista-1" / "L1-Q2.py").write_text("print(1)\n", encoding="utf-8")
    # De outro período: não aparece no seletor do período ativo.
    (root / "2025.2" / "lista-1").mkdir(parents=True)
    (root / "2025.2" / "lista-1" / "L1-Q3.py").write_text("print(2)\n", encoding="utf-8")
    return root


@pytest.fixture
def api(analyzer: TestClient, folder: Path) -> Iterator[TestClient]:
    settings = replace(SETTINGS, gabaritos=GabaritosConfig(local_dir=folder))
    app, store = make_app(settings, analyzer_transport=_bridge(analyzer))
    with authed_client(app, store) as client:
        yield client


@pytest.fixture
def api_without_gabaritos(analyzer: TestClient) -> Iterator[TestClient]:
    app, store = make_app(SETTINGS, analyzer_transport=_bridge(analyzer))
    with authed_client(app, store) as client:
        yield client


def _validate(client: TestClient, code: str, question: str | None, lst: int = 1) -> httpx2.Response:
    body = {"code": code, "list_number": lst, "question_id": question}
    return client.post("/api/v1/validate", json=body)


def test_the_lists_show_which_questions_have_a_gabarito(api: TestClient) -> None:
    lists = {item["number"]: item for item in api.get("/api/v1/lists").json()}

    assert lists[1]["gabaritos"] == ["L1-Q1", "L1-Q2"]
    assert lists[2]["gabaritos"] == []
    # A questão do ensaio (L3-Q9) tem regra, mas não gabarito.
    assert lists[3]["gabaritos"] == []


def test_the_validation_compares_with_the_gabarito(
    api: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    response = _validate(api, STUDENT, "L1-Q1")

    assert response.status_code == 200
    body = response.json()
    # L1-Q1 não tem regra cadastrada: valem as da lista, e a resposta avisa (ADR-11, item 6).
    assert body["notices"] == ["QUESTION_RULES_NOT_REGISTERED"]
    assert body["question_id"] == "L1-Q1"
    gabarito = body["gabarito"]
    assert gabarito["status"] == "compared"
    assert gabarito["similarity"] >= 99.0
    assert gabarito["band"]["id"] in {"plagio", "altas_chances"}
    assert "while" in gabarito["common"]
    assert gabarito["student_lines"]
    # S32-09: nada do texto do gabarito na resposta nem no log.
    assert CANARY not in response.text
    assert "MARCADOR-DO-GABARITO" not in response.text
    assert CANARY not in caplog.text
    assert "MARCADOR-DO-GABARITO" not in caplog.text


def test_an_independent_solution_is_far_from_the_gabarito(api: TestClient) -> None:
    gabarito = _validate(api, INDEPENDENT, "L1-Q1").json()["gabarito"]

    assert gabarito["status"] == "compared"
    assert gabarito["similarity"] < 80.0
    assert "while" in gabarito["only_gabarito"]


def test_a_question_without_gabarito_says_so(api: TestClient) -> None:
    code = "v = [1, 2]\nfor x in v:\n    print(x)\n"

    body = _validate(api, code, "L3-Q9", lst=3).json()

    assert body["notices"] == []
    assert body["gabarito"]["status"] == "no_gabarito"
    assert body["gabarito"]["similarity"] is None


def test_without_question_there_is_no_comparison(api: TestClient) -> None:
    assert _validate(api, INDEPENDENT, None).json()["gabarito"] is None


def test_a_syntax_error_is_not_compared(api: TestClient) -> None:
    gabarito = _validate(api, "if x\n", "L1-Q1").json()["gabarito"]

    assert gabarito["status"] == "not_compared"
    assert "sintaxe" in gabarito["message"]


def test_a_question_with_neither_rule_nor_gabarito_is_unknown(api: TestClient) -> None:
    response = _validate(api, INDEPENDENT, "L1-Q7")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_QUESTION"


def test_a_gabarito_of_another_list_is_refused(api: TestClient) -> None:
    response = _validate(api, "v = [1]\nprint(v)\n", "L1-Q1", lst=3)

    assert response.status_code == 422


def test_without_gabaritos_the_validation_works_and_warns(
    api_without_gabaritos: TestClient,
) -> None:
    code = "v = [1, 2]\nfor x in v:\n    print(x)\n"

    body = _validate(api_without_gabaritos, code, "L3-Q9", lst=3).json()

    assert body["status"] == "valid"
    assert body["gabarito"]["status"] == "unavailable"
    # Sem gabaritos carregados, uma questão sem regra não é conhecida.
    response = _validate(api_without_gabaritos, INDEPENDENT, "L1-Q1")
    assert response.status_code == 422
    assert api_without_gabaritos.get("/ready").status_code == 200


def test_similarity_with_the_question_raises_the_leak_alert(api: TestClient) -> None:
    copy = STUDENT.replace("soma", "acumulado")

    response = api.post(
        "/api/v1/similarity", json={"code_a": STUDENT, "code_b": copy, "question_id": "L1-Q1"}
    )

    assert response.status_code == 200
    gabarito = response.json()["gabarito"]
    assert gabarito["status"] == "compared"
    assert gabarito["a"]["similarity"] >= 95.0
    assert gabarito["b"]["similarity"] >= 95.0
    assert gabarito["leak_alert"] is True
    assert "não quem o vazou" in gabarito["message"]
    assert CANARY not in response.text


def test_no_alert_when_only_one_student_matches_the_gabarito(api: TestClient) -> None:
    response = api.post(
        "/api/v1/similarity",
        json={"code_a": STUDENT, "code_b": INDEPENDENT, "question_id": "L1-Q1"},
    )

    gabarito = response.json()["gabarito"]
    assert gabarito["leak_alert"] is False
    assert gabarito["b"]["similarity"] < 80.0


def test_no_alert_with_short_codes(api: TestClient) -> None:
    response = api.post(
        "/api/v1/similarity",
        json={"code_a": "print(1)\n", "code_b": "print(1)\n", "question_id": "L1-Q2"},
    )

    gabarito = response.json()["gabarito"]
    assert gabarito["status"] == "compared"
    assert gabarito["a"]["similarity"] == 100.0
    # Três códigos idênticos, mas curtos demais para dizer algo (ADR-11, item 5).
    assert gabarito["leak_alert"] is False


def test_similarity_without_question_is_unchanged(api: TestClient) -> None:
    response = api.post("/api/v1/similarity", json={"code_a": STUDENT, "code_b": INDEPENDENT})

    assert response.json()["gabarito"] is None

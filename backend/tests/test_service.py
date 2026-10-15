"""Serviço interno do analisador (S5-01): contrato, erros e fail-fast na inicialização."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import BASE_RULESET, RULESETS
from ipc_analyzer.engine.ruleset import RulesetError, resolve_ruleset_path
from ipc_analyzer.runtime.limits import MIB
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings

SETTINGS = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app(SETTINGS)) as test_client:
        yield test_client


def test_health_reports_the_loaded_ruleset(client: TestClient) -> None:
    response = client.get("/internal/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ruleset_version"] == "2026.2.7"
    assert body["target_python"] == "3.13"
    assert body["workers"] == 1
    assert len(body["ruleset_sha256"]) == 64


def test_manifest_describes_the_active_ruleset(client: TestClient) -> None:
    response = client.get("/internal/ruleset/manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["ruleset_version"] == "2026.2.7"
    assert body["period"] == "2026.2"
    assert len(body["ruleset_sha256"]) == 64
    assert [item["number"] for item in body["lists"]] == [1, 2, 3, 4, 5, 6]
    assert body["lists"][0] == {"number": 1, "title": "Comandos condicionais", "questions": []}


def test_valid_code(client: TestClient) -> None:
    code = "x = int(input())\nif x > 0:\n    print(x)\n"

    response = client.post("/internal/analyze", json={"code": code, "list_number": 1})

    assert response.status_code == 200
    assert response.json() == {
        "ruleset_version": "2026.2.7",
        "status": "valid",
        "list_number": 1,
        "syntax_error": None,
        "violations": [],
        "truncated": False,
        "indicators": None,
        "gabarito": None,
    }


def test_violations_follow_the_contract(client: TestClient) -> None:
    code = "x = 3\nif x > 0:\n    print(x)\nwhile x > 0:\n    x -= 1\n"

    response = client.post("/internal/analyze", json={"code": code, "list_number": 1})

    assert response.status_code == 200
    violations = response.json()["violations"]
    # S38-01: a explicação e a alternativa vêm do ruleset; o texto é conferido pelo golden.
    assert violations[0].pop("explanation").startswith("O documento de permissões libera os laços")
    assert violations[0].pop("alternative").startswith("Na Lista 1, resolva com comandos")
    assert violations == [
        {
            "rule_id": "R-34",
            "category": "FORA_DA_LISTA",
            "line": 4,
            "col": 1,
            "end_line": 5,
            "end_col": 11,
            "construct": "node:While",
            "allowed_from_list": 2,
            "message": "Laços de repetição (for, while) só são permitidos a partir da Lista 2.",
        }
    ]


def test_syntax_error(client: TestClient) -> None:
    response = client.post("/internal/analyze", json={"code": "x = (1\n", "list_number": 1})

    body = response.json()
    assert body["status"] == "syntax_error"
    assert body["syntax_error"] == {
        "line": 1,
        "col": 5,
        "message": "o '(' foi aberto e nunca fechado",
    }
    assert body["violations"] == []


@pytest.mark.parametrize(
    ("payload", "status", "code"),
    [
        ({"code": "  ", "list_number": 1}, 422, "INVALID_INPUT"),
        ({"code": "x = '\x00'", "list_number": 1}, 422, "INVALID_INPUT"),
        ({"code": "#" + "a" * 60_000, "list_number": 1}, 413, "PAYLOAD_TOO_LARGE"),
        ({"code": "#" + "é" * 25_600, "list_number": 1}, 413, "PAYLOAD_TOO_LARGE"),
        ({"code": "(" * 1_000 + ")" * 1_000, "list_number": 1}, 422, "ANALYSIS_LIMIT"),
        ({"code": "x = 1", "list_number": 7}, 422, "INVALID_INPUT"),
        ({"code": "x = 1", "list_number": 1, "extra": True}, 422, "INVALID_INPUT"),
        ({"list_number": 1}, 422, "INVALID_INPUT"),
    ],
    ids=[
        "vazio",
        "nulo",
        "60k",
        "utf8-51201",
        "1000-parenteses",
        "lista-7",
        "campo-extra",
        "sem-code",
    ],
)
def test_rejected_inputs_use_the_error_contract(
    client: TestClient, payload: dict[str, object], status: int, code: str
) -> None:
    response = client.post("/internal/analyze", json=payload)

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]


@pytest.mark.parametrize(
    "body",
    [b'{"code": "x = \xff\xfe", "list_number": 1}', b'{"code": "x = 1"', b""],
    ids=["utf8-invalido", "json-quebrado", "corpo-vazio"],
)
def test_malformed_bodies_are_invalid_input(client: TestClient, body: bytes) -> None:
    response = client.post(
        "/internal/analyze", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_internal_service_has_no_public_documentation(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_invalid_ruleset_prevents_startup(tmp_path: Path) -> None:
    broken = tmp_path / "base.yaml"
    broken.write_text("rules: []\n", encoding="utf-8")
    app = create_app(AnalyzerSettings(ruleset_path=broken, pool=PoolConfig(workers=1)))

    with pytest.raises(RulesetError), TestClient(app):
        pass


def test_settings_from_environment() -> None:
    settings = AnalyzerSettings.from_env(
        {
            "IPC_RULESET_PATH": "/app/rulesets/2026.2/base.yaml",
            "IPC_WORKERS": "3",
            "IPC_MAX_TASKS": "100",
            "IPC_TIMEOUT_S": "1.5",
            "IPC_MEMORY_MB": "300",
        }
    )

    assert settings.ruleset_path == Path("/app/rulesets/2026.2/base.yaml")
    assert settings.pool.workers == 3
    assert settings.pool.max_tasks == 100
    assert settings.pool.timeout_s == 1.5
    assert settings.pool.limits.memory_bytes == 300 * MIB


def test_settings_defaults_point_to_the_repository_ruleset() -> None:
    settings = AnalyzerSettings.from_env({})

    # A raiz rulesets/: o analisador carrega o período da linha de rulesets/ATIVO (S31-09).
    assert settings.ruleset_path == RULESETS
    assert resolve_ruleset_path(settings.ruleset_path) == BASE_RULESET
    assert settings.pool == PoolConfig()


# --- Plágio (S17-02) -----------------------------------------------------------------------------


def test_similarity_compares_in_a_worker(client: TestClient) -> None:
    code = "nota = float(input())\nif nota >= 7:\n    print('aprovado')\n"
    copy = code.replace("nota", "media")

    response = client.post("/internal/similarity", json={"first": code, "second": copy})

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["percent"]) == ("compared", 100.0)
    assert body["token_counts"][0] == body["token_counts"][1] > 0
    assert (body["syntax_error_side"], body["syntax_error"]) == (None, None)
    # S27: as métricas por trás da porcentagem e os trechos em comum.
    assert body["metrics"]["tree_dice"] == body["metrics"]["tree_containment"] == 100.0
    assert body["matches"] == [
        {"a_first": 1, "a_last": 1, "b_first": 1, "b_last": 1},
        {"a_first": 2, "a_last": 3, "b_first": 2, "b_last": 3},
    ]


def test_similarity_points_to_the_code_with_a_syntax_error(client: TestClient) -> None:
    response = client.post(
        "/internal/similarity", json={"first": "x = 1\n", "second": "if x\n    y = 2\n"}
    )

    body = response.json()
    assert (body["status"], body["percent"], body["syntax_error_side"]) == ("syntax_error", None, 2)
    assert (body["syntax_error"]["line"], body["syntax_error"]["col"]) == (1, 5)


@pytest.mark.parametrize(
    ("first", "second", "status", "code", "prefix"),
    [
        ("#" + "a" * 51_200, "x = 1\n", 413, "PAYLOAD_TOO_LARGE", "Código A: "),
        ("x = 1\n", "#" + "a" * 51_200, 413, "PAYLOAD_TOO_LARGE", "Código B: "),
        ("x = 1\n", "(" * 1_000 + ")" * 1_000, 422, "ANALYSIS_LIMIT", "Código B: "),
        ("x = '\x00'\n", "x = 1\n", 422, "INVALID_INPUT", "Código A: "),
    ],
    ids=["50kb-em-a", "50kb-em-b", "aninhamento-em-b", "byte-nulo-em-a"],
)
def test_similarity_refuses_inputs_like_the_analysis(
    client: TestClient, first: str, second: str, status: int, code: str, prefix: str
) -> None:
    response = client.post("/internal/similarity", json={"first": first, "second": second})

    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert response.json()["error"]["message"].startswith(prefix)


def test_similarity_body_is_strict(client: TestClient) -> None:
    response = client.post("/internal/similarity", json={"first": "x = 1\n"})

    assert (response.status_code, response.json()["error"]["code"]) == (422, "INVALID_INPUT")


# --- Feedback (S18-02) ---------------------------------------------------------------------------


def test_feedback_input_names_what_the_engine_found_and_strips_comments(client: TestClient) -> None:
    code = (
        "# Isabella Schultz, 20261234\nx = int(input())  # lê\nfor i in range(x):\n    print(i)\n"
    )

    response = client.post("/internal/feedback-input", json={"code": code, "list_number": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "invalid"
    # S38-02: cada item traz a alternativa do ruleset, que o feedback sem IA usa.
    assert all(item.pop("alternative") for item in body["items"])
    assert body["items"] == [
        {"kind": "falta", "label": "if ou operador ternário"},
        {"kind": "uso", "label": "for"},
        {"kind": "uso", "label": "range()"},
    ]
    assert body["code"] == "x = int(input())\nfor i in range(x):\n    print(i)\n"
    assert "Isabella" not in body["code"]
    assert body["syntax_error"] is None


def test_feedback_input_of_valid_code_and_of_a_syntax_error(client: TestClient) -> None:
    valid = client.post(
        "/internal/feedback-input", json={"code": "x = 1\nif x:\n    print(x)\n", "list_number": 1}
    ).json()
    broken = client.post(
        "/internal/feedback-input", json={"code": "if x\n    y = 2\n", "list_number": 1}
    ).json()

    assert (valid["status"], valid["items"]) == ("valid", [])
    assert (broken["status"], broken["code"], broken["syntax_error"]["line"]) == (
        "syntax_error",
        "",
        1,
    )


def test_feedback_input_refuses_inputs_like_the_analysis(client: TestClient) -> None:
    big = client.post(
        "/internal/feedback-input", json={"code": "#" + "a" * 51_200, "list_number": 1}
    )
    nested = client.post(
        "/internal/feedback-input", json={"code": "(" * 1_000 + ")" * 1_000, "list_number": 1}
    )

    assert (big.status_code, big.json()["error"]["code"]) == (413, "PAYLOAD_TOO_LARGE")
    assert (nested.status_code, nested.json()["error"]["code"]) == (422, "ANALYSIS_LIMIT")


# --- Plágio contra a turma (S27-02) ---------------------------------------------------------------


def test_similarity_against_the_class(client: TestClient) -> None:
    code = "valor = int(input())\nif valor > 10:\n    print('grande')\n"
    others = [
        code.replace("valor", "numero"),
        "if True\n    pass\n",
        "",
        "n = int(input())\nfor i in range(n):\n    print(i)\n",
    ]

    response = client.post("/internal/similarity/class", json={"code": code, "others": others})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "compared"
    copy, broken, empty, other = body["results"]
    assert (copy["status"], copy["percent"]) == ("compared", 100.0)
    assert copy["metrics"]["sequence"] is None
    assert broken["status"] == "syntax_error"
    assert broken["syntax_error"]["line"] == 1
    assert (empty["status"], empty["message"]) == ("rejected", "O código está vazio.")
    assert other["status"] == "compared"
    assert other["percent"] < copy["percent"]


def test_similarity_against_the_class_with_a_broken_target(client: TestClient) -> None:
    response = client.post(
        "/internal/similarity/class", json={"code": "if x\n", "others": ["x = 1\n"]}
    )

    body = response.json()
    assert (body["status"], body["results"]) == ("syntax_error", [])
    assert body["syntax_error"]["line"] == 1


def test_similarity_against_the_class_refuses_a_too_big_target_and_too_many(
    client: TestClient,
) -> None:
    big = client.post(
        "/internal/similarity/class", json={"code": "#" + "a" * 51_200, "others": ["x = 1\n"]}
    )
    many = client.post(
        "/internal/similarity/class", json={"code": "x = 1\n", "others": ["x = 1\n"] * 101}
    )
    none = client.post("/internal/similarity/class", json={"code": "x = 1\n", "others": []})

    assert (big.status_code, big.json()["error"]["code"]) == (413, "PAYLOAD_TOO_LARGE")
    assert big.json()["error"]["message"].startswith("Solução comparada: ")
    assert many.status_code == 422
    assert none.status_code == 422


# --- Comparação com o gabarito (ADR-11, S32-03) -------------------------------------------------

GABARITO = "canario_gab = float(input())\nif canario_gab >= 7:\n    print('MARCADOR-GAB')\n"


def test_analysis_with_the_gabarito_returns_only_the_comparison(client: TestClient) -> None:
    code = "nota = float(input())\nif nota >= 7:\n    print('aprovado')\n"

    response = client.post(
        "/internal/analyze", json={"code": code, "list_number": 1, "gabarito": GABARITO}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["gabarito"]["percent"] == 100.0
    assert body["gabarito"]["student_lines"] == [{"first": 1, "last": 3}]
    assert "if" in body["gabarito"]["common"]
    # Nada do texto do gabarito volta (ADR-11, item 3).
    assert "canario_gab" not in response.text
    assert "MARCADOR-GAB" not in response.text


def test_analysis_without_the_gabarito_has_no_comparison(client: TestClient) -> None:
    response = client.post("/internal/analyze", json={"code": "x = 1\n", "list_number": 3})

    assert response.json()["gabarito"] is None


def test_similarity_with_the_gabarito_compares_each_side(client: TestClient) -> None:
    code = "nota = float(input())\nif nota >= 7:\n    print('aprovado')\n"

    response = client.post(
        "/internal/similarity",
        json={"first": code, "second": "print(1)\n", "gabarito": GABARITO},
    )

    body = response.json()
    assert body["gabarito"][0]["percent"] == 100.0
    assert body["gabarito"][1]["percent"] < 80.0
    assert "canario_gab" not in response.text


def test_an_oversized_gabarito_is_refused_without_its_content(client: TestClient) -> None:
    big = "x = 1\n" * 9_000

    response = client.post(
        "/internal/analyze", json={"code": "x = 1\n", "list_number": 1, "gabarito": big}
    )

    assert response.status_code == 413
    assert "gabarito" in response.json()["error"]["message"]

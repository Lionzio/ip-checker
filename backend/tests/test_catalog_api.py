"""O catálogo do período na página e o ``.zip`` dos enunciados (S50-06; ADR-19).

O catálogo é semeado pelas próprias rotas de importação (com o token), e a API conversa com o
analisador de verdade (em memória), que diz quais questões têm regras próprias no período.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_support import BASE_URL, COOKIE, make_app, member, open_session
from conftest import BASE_RULESET
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.accounts.models import Role
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.importing.hashing import Sample, content_hash
from ipc_api.importing.models import StoredQuestion
from ipc_api.importing.statements import statement_markdown

CATALOG = "/api/v1/periods/2026.2/catalog"
ZIP = f"{CATALOG}/statements.zip"
CLASS_ID = "TURMA-SI"
#: Um texto que só existe no enunciado: nunca pode aparecer na rota do catálogo.
CANARY = "CANARIO-DO-ENUNCIADO-50"


@pytest.fixture(scope="module")
def analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as client:
        yield client


@pytest.fixture
def api(analyzer: TestClient) -> Iterator[tuple[FastAPI, MemoryAccountStore, TestClient]]:
    def bridge(request: httpx2.Request) -> httpx2.Response:
        answer = analyzer.request(request.method, request.url.path, content=request.content)
        return httpx2.Response(
            answer.status_code,
            content=answer.content,
            headers={"Content-Type": answer.headers["content-type"]},
        )

    app, store = make_app(analyzer_transport=httpx2.MockTransport(bridge))
    with TestClient(app, base_url=BASE_URL) as client:
        yield app, store, client


def login(client: TestClient, store: MemoryAccountStore, role: Role | None) -> None:
    client.cookies.set(COOKIE, open_session(store, member(store, role=role)))


def question(question_id: str, number: int, title: str, kind: str = "lista") -> dict[str, Any]:
    texts = {
        "title": title,
        "description": f"Leia N e imprima N. {CANARY}",
        "input_description": "Um inteiro N.",
        "output_description": "O mesmo N.",
    }
    samples = [{"input": "1\n", "output": "1"}]
    return {
        "question_id": question_id,
        "dikastis_problem_id": f"P-{question_id}",
        "list_kind": kind,
        "list_number": number,
        **texts,
        "samples": samples,
        "time_limit_ms": 1000,
        "content_hash": content_hash(
            **texts, samples=[Sample(s["input"], s["output"]) for s in samples]
        ),
    }


def seed(client: TestClient, store: MemoryAccountStore, items: list[dict[str, Any]]) -> None:
    """Uma sincronização completa, como a extensão faria."""
    login(client, store, Role.MONITOR_CHEFE)
    token = client.post("/api/v1/profile/import-tokens", json={"label": "teste"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    lists: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for item in items:
        lists.setdefault((item["list_kind"], item["list_number"]), []).append(item)
    manifest = {
        "period": "2026.2",
        "classes": [{"dikastis_org_id": CLASS_ID, "name": "IP SI UFPE 2026.2", "course": "SI"}],
        "lists": [
            {
                "dikastis_task_id": f"T-{kind}-{number}",
                "class_org_id": CLASS_ID,
                "kind": kind,
                "number": number,
                "title": f"{kind.title()} {number}",
                "questions": [
                    {
                        "dikastis_problem_id": q["dikastis_problem_id"],
                        "question_id": q["question_id"],
                        "content_hash": q["content_hash"],
                    }
                    for q in questions
                ],
            }
            for (kind, number), questions in lists.items()
        ]
        + [
            {
                "dikastis_task_id": "T-treino",
                "class_org_id": CLASS_ID,
                "kind": "treino",
                "number": None,
                "title": "Lista de Treinamento",
                "questions": [],
            }
        ],
    }
    run = client.post("/api/v1/import/catalog/manifest", json=manifest, headers=headers).json()
    body = {"run_id": run["run_id"], "period": "2026.2", "questions": items}
    assert (
        client.put("/api/v1/import/catalog/questions", json=body, headers=headers).status_code
        == 200
    )


ITEMS = [
    question("L4-Q5", 4, "Hades: a fuga"),
    question("L4-Q4", 4, "Balatro: a aposta"),
    question("L1-Q1", 1, "Eco"),
    question("P1-Q1", 1, "Questão da prova", kind="prova"),
]


def test_the_team_sees_the_lists_with_the_stage_of_each_question(api: Any) -> None:
    app, store, client = api
    seed(client, store, ITEMS)
    app.state.gabaritos._items[("2026.2", "L1-Q1")] = "print(1)\n"
    login(client, store, Role.MONITOR)

    response = client.get(CATALOG)

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "2026.2"
    assert body["last_sync"] is not None
    assert [(item["kind"], item["number"]) for item in body["lists"]] == [
        ("lista", 1),
        ("lista", 4),
        ("prova", 1),
        ("treino", None),
    ]
    lista4 = body["lists"][1]
    assert lista4["classes"] == ["IP SI UFPE 2026.2"]
    assert [
        (q["question_id"], q["version"], q["has_rules"], q["has_gabarito"])
        for q in lista4["questions"]
    ] == [("L4-Q4", 1, True, False), ("L4-Q5", 1, True, False)]
    assert body["lists"][0]["questions"][0]["has_gabarito"] is True
    assert body["lists"][0]["questions"][0]["has_rules"] is False
    assert CANARY not in response.text
    assert "print(1)" not in response.text


def test_a_period_without_catalog_is_empty(api: Any) -> None:
    _, store, client = api
    login(client, store, Role.MONITOR)

    assert client.get("/api/v1/periods/2027.1/catalog").json() == {
        "period": "2027.1",
        "last_sync": None,
        "lists": [],
    }


def test_the_catalog_needs_a_session_and_a_valid_period(api: Any) -> None:
    _, store, client = api

    assert client.get(CATALOG).status_code == 401
    login(client, store, Role.MONITOR)
    assert client.get("/api/v1/periods/2026.3/catalog").json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize("role", [Role.MONITOR_CHEFE, Role.PROFESSOR, Role.DESENVOLVEDOR])
def test_leadership_downloads_the_statements_of_the_lists(api: Any, role: Role) -> None:
    _, store, client = api
    seed(client, store, ITEMS)
    login(client, store, role)

    response = client.get(ZIP)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    assert 'filename="enunciados-2026.2.zip"' in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert sorted(archive.namelist()) == ["L1-Q1.md", "L4-Q4.md", "L4-Q5.md"]
        text = archive.read("L1-Q1.md").decode("utf-8")
    assert text.startswith("# L1-Q1: Eco\n")
    assert "## Entrada\n\nUm inteiro N." in text
    assert "## Exemplo 1" in text


def test_monitors_do_not_download_the_statements(api: Any) -> None:
    _, store, client = api
    seed(client, store, ITEMS)
    login(client, store, Role.MONITOR)

    assert client.get(ZIP).json()["error"]["code"] == "FORBIDDEN"


def test_without_statements_the_zip_says_how_to_get_them(api: Any) -> None:
    _, store, client = api
    login(client, store, Role.PROFESSOR)

    response = client.get(ZIP)

    assert response.status_code == 422
    assert "sincronize pela extensão" in response.json()["error"]["message"]


def test_the_statement_file_is_what_the_reference_generator_reads() -> None:
    from datetime import UTC, datetime

    from ipc_api.referencias import QUESTION

    stored = StoredQuestion(
        question_id="L2-Q3",
        dikastis_problem_id="P",
        list_kind="lista",
        list_number=2,
        title="Soma",
        description="Some os números.\r\n",
        input_description="",
        output_description="A soma.",
        samples=(Sample("1 2\n", "3\n"), Sample("0 0", "0")),
        time_limit_ms=None,
        content_hash="a" * 64,
        version=1,
        first_seen=datetime(2026, 10, 1, tzinfo=UTC),
        updated_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    text = statement_markdown(stored)

    assert QUESTION.fullmatch(stored.question_id)
    assert text == (
        "# L2-Q3: Soma\n\nSome os números.\n\n## Saída\n\nA soma.\n\n"
        "## Exemplo 1\n\nEntrada:\n\n```text\n1 2\n```\n\nSaída:\n\n```text\n3\n```\n\n"
        "## Exemplo 2\n\nEntrada:\n\n```text\n0 0\n```\n\nSaída:\n\n```text\n0\n```\n"
    )

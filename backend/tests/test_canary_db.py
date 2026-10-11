"""O canário mensal (S35-04, NFR-11): a busca da marca em todas as colunas do banco.

A busca roda contra o PostgreSQL de teste (``IPC_TEST_DATABASE_URL``); a parte que planta a marca
pela página só roda no piloto.
"""

from __future__ import annotations

import ast
import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import asyncpg
import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database

SCRIPT = Path(__file__).parents[1] / "scripts" / "canary.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("canary", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


canary = _module()


def test_each_canary_has_its_own_marker() -> None:
    moment = datetime(2026, 11, 1, tzinfo=UTC)
    first, second = canary.new_marker(moment), canary.new_marker(moment)

    assert first.startswith("canario_20261101_")
    assert first != second


def test_the_planted_code_is_valid_python_with_the_marker_everywhere() -> None:
    code = canary.planted_code("canario_x")

    ast.parse(code)
    assert code.count("canario_x") == 4  # comentário, nome, condição e texto


def test_the_search_is_one_static_query() -> None:
    # Sem SQL montado com texto (Semgrep, P-20): a marca vai como parâmetro.
    assert "$1" in canary.SEARCH
    assert "{" not in canary.SEARCH


@requires_database
@pytest.mark.anyio
async def test_the_search_finds_the_marker_in_any_column() -> None:
    await fresh_schema()
    connection: Any = await asyncpg.connect(DATABASE_URL)
    try:
        await connection.execute("CREATE TABLE app.canario_teste (texto text, dados jsonb)")
        await connection.execute(
            "INSERT INTO app.canario_teste VALUES ($1, $2)",
            "x canario_achou y",
            '{"a": "canario_achou"}',
        )
        found = await canary.search(DATABASE_URL, "canario_achou")
        nothing = await canary.search(DATABASE_URL, "canario_ausente")
    finally:
        await connection.execute("DROP TABLE IF EXISTS app.canario_teste")
        await connection.close()

    assert found == [("app.canario_teste.dados", 1), ("app.canario_teste.texto", 1)]
    assert nothing == []

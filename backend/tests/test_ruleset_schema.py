"""Esquema JSON do ruleset e ruleset compilado (S35-05, C6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema_rs
import pytest
import yaml

from conftest import RULESETS
from ipc_analyzer.cli import main
from ipc_analyzer.engine.ruleset import PERIOD, load_ruleset
from ipc_analyzer.ruleset_schema import QUESTION_SCHEMA, RULESET_SCHEMA, render, schemas

SCHEMA_DIR = RULESETS / "schema"
PERIODS = sorted(p for p in RULESETS.iterdir() if p.is_dir() and PERIOD.fullmatch(p.name))
QUESTIONS = sorted(q for period in PERIODS for q in (period / "questions").glob("*.yaml"))


def validator(name: str) -> Any:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return jsonschema_rs.validator_for(schema)


def as_json(value: Any) -> Any:
    """Como um editor de YAML lê o arquivo: chaves sempre texto (``1:`` vira ``"1"``)."""
    if isinstance(value, dict):
        return {str(key): as_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [as_json(item) for item in value]
    return value


def read(path: Path) -> Any:
    return as_json(yaml.safe_load(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", [RULESET_SCHEMA, QUESTION_SCHEMA])
def test_the_committed_schema_is_the_generated_one(name: str) -> None:
    """Mudou o modelo do carregador? Rode ``uv run ipc-rules schema`` e faça o commit."""
    assert (SCHEMA_DIR / name).read_text(encoding="utf-8") == render(schemas()[name])


@pytest.mark.parametrize("period", PERIODS, ids=[p.name for p in PERIODS])
def test_every_period_follows_the_schema(period: Path) -> None:
    errors = [
        error.message for error in validator(RULESET_SCHEMA).iter_errors(read(period / "base.yaml"))
    ]

    assert errors == []


@pytest.mark.parametrize("question", QUESTIONS, ids=[q.stem for q in QUESTIONS])
def test_every_question_follows_the_schema(question: Path) -> None:
    errors = [error.message for error in validator(QUESTION_SCHEMA).iter_errors(read(question))]

    assert errors == []


def test_the_schema_catches_what_editors_should_flag() -> None:
    data = read(PERIODS[0] / "base.yaml")
    del data["ruleset_version"]
    data["regra_inventada"] = True

    assert not validator(RULESET_SCHEMA).is_valid(data)


def test_the_compiled_ruleset_has_the_manifest_sha256(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "ruleset.json"

    assert main(["compile", str(RULESETS), "--saida", str(output)]) == 0

    compiled = json.loads(output.read_text(encoding="utf-8"))
    loaded = load_ruleset(RULESETS)
    assert compiled["ruleset_sha256"] == loaded.sha256
    assert compiled["ruleset_version"] == loaded.version
    assert [q["question_id"] for q in compiled["questions"]] == sorted(loaded.questions)
    assert validator(RULESET_SCHEMA).is_valid(compiled["ruleset"])
    assert loaded.sha256 in capsys.readouterr().out


def test_compile_reports_an_invalid_ruleset(tmp_path: Path) -> None:
    (tmp_path / "base.yaml").write_text("period: 2027.1\n", encoding="utf-8")

    assert main(["compile", str(tmp_path / "base.yaml")]) == 1


def test_schema_writes_both_files(tmp_path: Path) -> None:
    assert main(["schema", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [QUESTION_SCHEMA, RULESET_SCHEMA]

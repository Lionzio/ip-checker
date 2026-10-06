"""``ipc-rules validate`` (S24-02; FR-21, US-14): o carregamento do analisador, num comando."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import BASE_RULESET
from ipc_analyzer.cli import main

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def period(tmp_path: Path) -> Path:
    shutil.copy(BASE_RULESET, tmp_path / "base.yaml")
    (tmp_path / "questions").mkdir()
    return tmp_path


def test_a_valid_ruleset_exits_zero(period: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(period)]) == 0

    out = capsys.readouterr().out
    assert "ruleset 2026.2.3 válido" in out
    assert "0 questões" in out


def test_the_base_file_can_be_given_directly(period: Path) -> None:
    assert main(["validate", str(period / "base.yaml")]) == 0


def test_an_invalid_ruleset_shows_the_field_and_exits_one(
    period: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = period / "base.yaml"
    base.write_text(
        base.read_text(encoding="utf-8").replace("since_list: 3", "since_list: 9", 1),
        encoding="utf-8",
    )

    assert main(["validate", str(period)]) == 1

    err = capsys.readouterr().err
    assert "ruleset inválido" in err
    assert "rules." in err
    assert "since_list" in err


def test_an_invalid_question_exits_one(period: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (period / "questions" / "L3-Q2.yaml").write_text(
        "question_id: L3-Q2\nlist: 3\ntitle: X\nsource: enunciado\nallow: ['R-99']\n",
        encoding="utf-8",
    )

    assert main(["validate", str(period)]) == 1
    assert "R-99 não existe" in capsys.readouterr().err


def test_releasing_a_general_prohibition_is_a_warning_not_a_failure(
    period: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    (period / "questions" / "L2-Q4.yaml").write_text(
        "question_id: L2-Q4\nlist: 2\ntitle: Busca\nsource: o enunciado permite break\n"
        "allow: ['R-11']\n",
        encoding="utf-8",
    )

    assert main(["validate", str(period)]) == 0

    out = capsys.readouterr().out
    assert "1 questões" in out
    # Na CI, vira uma anotação de aviso no PR (C-02: só com aprovação de professor).
    assert "::warning file=" in out
    assert "L2-Q4 libera proibição geral (R-11)" in out


def test_golden_cases_run_with_the_ruleset(
    period: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", str(period), "--golden", str(GOLDEN)]) == 0
    assert "casos golden: " in capsys.readouterr().out


def test_a_failing_golden_case_exits_one(
    period: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    golden = tmp_path / "golden"
    golden.mkdir()
    (golden / "casos.yaml").write_text(
        "- id: for-na-lista-1\n  rule: R-34\n  list: 1\n  code: |\n"
        "    for i in range(3):\n        print(i)\n  expect: []\n",
        encoding="utf-8",
    )

    assert main(["validate", str(period), "--golden", str(golden)]) == 1

    err = capsys.readouterr().err
    assert "casos.yaml for-na-lista-1" in err
    assert "R-34 FORA_DA_LISTA 1" in err


def test_wrong_usage_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["validar"])

    assert exit_info.value.code == 2

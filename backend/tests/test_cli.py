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
    assert "ruleset 2026.2.6 válido" in out
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
    assert "1 questão" in out
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


# --- ipc-rules calibrate (S29-04) ----------------------------------------------------------------

CANARY = "CANARIO_CALIBRACAO_51b2"
HIGH = (
    "for i in range(5):\n    if i == 1:\n        break\n"
    "    if i == 2:\n        continue\n    pass\n"
)
CLEAN = "x = int(input())\nif x > 0:\n    print(x)\n"


def solutions(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "solucoes"
    for relative, code in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {CANARY}\n{code}", encoding="utf-8")
    return root


def test_calibrate_counts_each_level_and_names_only_the_files(
    period: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = solutions(
        tmp_path,
        {"2022.1/lista-2/q01.py": HIGH, "2022.1/lista-1/q02.py": CLEAN, "2022.1/notas.txt": "x"},
    )

    assert main(["calibrate", str(period), str(root), "--max-alto", "60"]) == 0

    out = capsys.readouterr().out
    assert "soluções analisadas: 2" in out
    assert "  alto: 1" in out
    assert "  nenhum: 1" in out
    assert "faixa alta: 50.0% (limite: 60.0%)" in out
    assert "alto: 2022.1/lista-2/q01.py: variedade" in out
    assert CANARY not in out


def test_calibrate_fails_above_the_limit(
    period: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = solutions(tmp_path, {"2022.1/lista-2/q01.py": HIGH, "2022.1/lista-1/q02.py": CLEAN})

    assert main(["calibrate", str(period), str(root)]) == 1
    assert "limite: 5.0%" in capsys.readouterr().out


def test_calibrate_without_solutions_is_wrong_usage(
    period: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["calibrate", str(period), str(tmp_path / "vazia")]) == 2
    assert "nenhuma solução" in capsys.readouterr().out


def test_calibrate_counts_refused_files_apart(
    period: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = solutions(
        tmp_path, {"2022.1/lista-1/grande.py": "x = 1\n" * 1_100, "2022.1/lista-1/q.py": CLEAN}
    )

    assert main(["calibrate", str(period), str(root)]) == 0
    assert "recusadas pelos limites: 1" in capsys.readouterr().out

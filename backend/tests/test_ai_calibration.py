"""``ipc-rules calibrate`` com a base da Q-35 (S42-02): alarmes falsos nos gabaritos e acertos nas
soluções geradas por IA. Tudo sintético, em ``tmp_path``; a saída nunca mostra código."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import BASE_RULESET
from ipc_analyzer.cli import main

PERIOD = "2026.2"
CLEAN = (
    "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelse:\n    print('Reprovado')\n"
)
#: break, continue e pass juntos: faixa alta pelo sinal 1.
HIGH = (
    "for i in range(5):\n    if i == 1:\n        break\n    if i == 2:\n        continue\n"
    "    pass\n"
)
#: Duas proibições gerais diferentes: faixa média.
MEDIUM = "for i in range(3):\n    if i:\n        break\n    pass\n"
CANARY = "CANARIO_CALIBRACAO_42"


def write(root: Path, files: dict[str, str]) -> Path:
    for relative, code in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
    return root


def calibrate(*args: str) -> int:
    return main(["calibrate", str(BASE_RULESET.parent), *args])


def test_clean_gabaritos_meet_the_false_alarm_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gabaritos = write(
        tmp_path / "gabaritos",
        {
            f"{PERIOD}/lista-1/L1-Q1.py": CLEAN,
            f"{PERIOD}/lista-1/L1-Q2.py": f"# {CANARY}\n{CLEAN}",
            # Outro período e encerrados/ ficam de fora.
            "2025.2/lista-3/L3-Q1.py": HIGH,
            "encerrados/2023.1/lista-3/L3-Q1.py": HIGH,
        },
    )

    assert calibrate("--gabaritos", str(gabaritos)) == 0

    out = capsys.readouterr().out
    assert "gabaritos (alarmes falsos): 2 analisadas (recusadas" in out
    assert "faixa alta: 0 (meta: nenhum) — cumprida" in out
    assert CANARY not in out


def test_a_gabarito_in_the_high_band_fails_and_shows_only_path_and_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gabaritos = write(tmp_path / "g", {f"{PERIOD}/lista-3/L3-Q1.py": f"# {CANARY}\n{HIGH}"})

    assert calibrate("--gabaritos", str(gabaritos)) == 1

    out = capsys.readouterr().out
    assert "NÃO cumprida" in out
    assert f"alto: {PERIOD}/lista-3/L3-Q1.py: variedade" in out
    assert "sinais: variedade alto 1" in out
    assert "break" not in out
    assert CANARY not in out


@pytest.mark.parametrize(
    ("files", "status", "share"),
    [
        ({"a": HIGH, "b": MEDIUM, "c": CLEAN, "d": CLEAN}, 0, "50.0%"),
        ({"a": HIGH, "b": CLEAN, "c": CLEAN, "d": CLEAN}, 1, "25.0%"),
    ],
    ids=["metade", "um-quarto"],
)
def test_generated_solutions_need_half_in_medium_or_high(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    files: dict[str, str],
    status: int,
    share: str,
) -> None:
    generated = write(
        tmp_path / "geradas",
        {f"{PERIOD}/lista-3/L3-Q1-gemini-{name}.py": code for name, code in files.items()},
    )

    assert calibrate("--geradas", str(generated)) == status

    out = capsys.readouterr().out
    assert "geradas por IA (acertos): 4 analisadas" in out
    assert f"média ou alta: {share} (meta: pelo menos 50%)" in out


def test_both_sets_and_the_confidence_are_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gabaritos = write(tmp_path / "g", {f"{PERIOD}/lista-1/L1-Q1.py": CLEAN})
    generated = write(tmp_path / "a", {f"{PERIOD}/lista-3/L3-Q1-groq-1.py": HIGH})

    assert calibrate("--gabaritos", str(gabaritos), "--geradas", str(generated)) == 0

    out = capsys.readouterr().out
    assert "confiança: baixa 0, media 0, alta 1" in out


def test_nothing_to_measure_or_a_missing_folder_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert calibrate() == 2
    assert "diga o que medir" in capsys.readouterr().err
    assert calibrate("--geradas", str(tmp_path / "nao-existe")) == 2
    assert "não é uma pasta" in capsys.readouterr().err


def test_an_empty_set_does_not_meet_the_target(tmp_path: Path) -> None:
    (tmp_path / "vazia").mkdir()

    assert calibrate("--gabaritos", str(tmp_path / "vazia")) == 1


def test_a_generated_solution_that_is_not_python_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    generated = write(
        tmp_path / "a",
        {
            f"{PERIOD}/lista-3/L3-Q1-groq-1.py": HIGH,
            f"{PERIOD}/lista-3/L3-Q1-groq-2.py": "for i in range(3)\n    print(i)\n",
        },
    )

    assert calibrate("--geradas", str(generated)) == 0

    assert "1 analisadas (recusadas pelos limites ou com erro de sintaxe: 1)" in (
        capsys.readouterr().out
    )


# --- Referências redundantes com o gabarito (Sprint 42.1) ---------------------------------------


def test_references_that_repeat_the_gabarito_are_removed_and_the_rest_kept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    period = shutil.copytree(BASE_RULESET.parent, tmp_path / "rulesets" / PERIOD)
    references = period / "referencias" / "L1-Q1"
    # A solução padrão, com outro nome de variável: a mesma do gabarito para o motor de plágio.
    write(references, {"ia-1.py": CLEAN.replace("nota", "valor"), "ia-2.py": HIGH})
    gabaritos = write(
        tmp_path / "gabaritos", {f"{PERIOD}/lista-1/L1-Q1.py": f"# {CANARY}\n{CLEAN}"}
    )

    status = main(
        ["calibrate", str(period), "--gabaritos", str(gabaritos), "--remover-redundantes"]
    )

    out = capsys.readouterr().out
    assert status == 0
    assert "referência redundante com o gabarito removida: referencias/L1-Q1/ia-1.py" in out
    assert not (references / "ia-1.py").exists()
    assert (references / "ia-2.py").exists()
    assert "faixa alta: 0 (meta: nenhum) — cumprida" in out
    assert CANARY not in out
    assert "nota" not in out


def test_removing_redundant_references_needs_the_gabaritos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert calibrate("--remover-redundantes") == 2
    assert "--gabaritos" in capsys.readouterr().err

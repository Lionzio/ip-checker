"""``ipc-rules calibrate-gabarito`` (S33-07): o alerta de vazamento em soluções independentes.

Tudo aqui é sintético: o gabarito, as soluções e os nomes. O canário só existe nos arquivos e nunca
pode aparecer na saída do comando.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import RULESETS
from ipc_analyzer.cli import main
from ipc_analyzer.gabarito_calibration import (
    BANDS,
    DEFAULT_MIN_TOKENS,
    DEFAULT_THRESHOLD,
    band_of,
    discover,
)
from ipc_api.gabaritos import GabaritosConfig
from ipc_api.similarity import BANDS as API_BANDS

CANARY = "canario_calibracao_s33"
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
    print("muito", total)
else:
    print("pouco", total)
"""
COPY = GABARITO.replace(CANARY, "quantidade").replace("total", "soma")
OTHER_COPY = GABARITO.replace(CANARY, "n").replace("contador", "i")
INDEPENDENT = "n = int(input())\nif n > 0:\n    print('positivo')\nelse:\n    print('outro')\n"
ANOTHER = "x = input()\nfor letra in x:\n    if letra == 'a':\n        print(letra)\n"


def _write(root: Path, relative: str, code: str) -> None:
    file = root / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(code, encoding="utf-8")


@pytest.fixture
def folders(tmp_path: Path) -> tuple[Path, Path]:
    solutions, gabaritos = tmp_path / "solucoes", tmp_path / "gabaritos"
    _write(gabaritos, "2026.2/lista-1/L1-Q1.py", GABARITO)
    _write(solutions, "2026.2/lista-1/L1-Q1/ana.py", INDEPENDENT)
    _write(solutions, "2026.2/lista-1/L1-Q1/bia.py", ANOTHER)
    # Duas cópias do gabarito: o par que o alerta precisa pegar.
    _write(solutions, "2026.2/lista-1/L1-Q1/caio.py", COPY)
    _write(solutions, "2026.2/lista-1/L1-Q1_duda.py", OTHER_COPY)
    # Sem gabarito, e fora do formato (questão de outra lista e arquivo solto).
    _write(solutions, "2026.2/lista-2/L2-Q1/eva.py", INDEPENDENT)
    _write(solutions, "2026.2/lista-1/L2-Q1_fora.py", INDEPENDENT)
    _write(solutions, "solto.py", INDEPENDENT)
    return solutions, gabaritos


def test_the_bands_and_defaults_are_the_api_ones() -> None:
    assert [(name, minimum) for name, minimum in BANDS] == [
        (band.id, band.minimum) for band in API_BANDS
    ]
    defaults = GabaritosConfig()
    assert (defaults.alert_percent, defaults.alert_min_tokens) == (
        DEFAULT_THRESHOLD,
        DEFAULT_MIN_TOKENS,
    )
    assert band_of(99.04) == "plagio"
    assert band_of(94.96) == "altas_chances"


def test_discover_reads_both_layouts(folders: tuple[Path, Path]) -> None:
    found, ignored = discover(folders[0])

    assert sorted((s.question, s.relative) for s in found) == [
        ("L1-Q1", "2026.2/lista-1/L1-Q1/ana.py"),
        ("L1-Q1", "2026.2/lista-1/L1-Q1/bia.py"),
        ("L1-Q1", "2026.2/lista-1/L1-Q1/caio.py"),
        ("L1-Q1", "2026.2/lista-1/L1-Q1_duda.py"),
        ("L2-Q1", "2026.2/lista-2/L2-Q1/eva.py"),
    ]
    assert ignored == ["2026.2/lista-1/L2-Q1_fora.py", "solto.py"]


def test_the_copies_raise_a_false_alert_and_fail(
    folders: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    solutions, gabaritos = folders

    code = main(["calibrate-gabarito", str(RULESETS), str(solutions), str(gabaritos)])

    out = capsys.readouterr().out
    assert code == 1
    assert "soluções comparadas com o gabarito: 4 (sem gabarito: 1, recusadas: 0" in out
    assert "fora do formato: 2" in out
    assert "pares da mesma questão: 6" in out
    assert "alertas de vazamento (falsos, nestas soluções independentes): 1" in out
    assert "alerta: 2026.2/lista-1/L1-Q1/caio.py e 2026.2/lista-1/L1-Q1_duda.py" in out
    assert CANARY not in out
    assert "soma" not in out


def test_a_higher_limit_accepts_the_alert(
    folders: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    solutions, gabaritos = folders

    args = ["calibrate-gabarito", str(RULESETS), str(solutions), str(gabaritos)]
    assert main([*args, "--max-alertas", "1"]) == 0
    # Com um tamanho mínimo acima das cópias, não há alerta.
    assert main([*args, "--min-tokens", "500"]) == 0
    assert "alertas de vazamento" in capsys.readouterr().out


def test_without_solutions_or_gabaritos_it_is_wrong_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "vazia"
    empty.mkdir()

    assert main(["calibrate-gabarito", str(RULESETS), str(empty), str(empty)]) == 2
    assert "nenhuma solução" in capsys.readouterr().out
    assert main(["calibrate-gabarito", str(RULESETS), str(empty), str(tmp_path / "x")]) == 2

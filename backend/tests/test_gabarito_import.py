"""``ipc-rules import-gabaritos`` (S33-08) com uma exportação do Notion sintética.

Nenhum gabarito real: as páginas e os códigos são inventados. O destino é uma pasta temporária, e o
comando recusa este repositório como destino (NFR-27).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import REPO_ROOT
from ipc_analyzer.cli import main
from ipc_analyzer.gabarito_import import import_gabaritos, read_blocks

CANARY = "canario_importacao_s33"
HASH = "0123456789abcdef0123456789abcdef"


def _page(root: Path, relative: str, text: str) -> None:
    file = root / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


@pytest.fixture
def export(tmp_path: Path) -> Path:
    root = tmp_path / "notion"
    # A lista vem da pasta e a questão, do nome da página (como o Notion exporta).
    _page(
        root,
        f"Lista 1 {HASH}/Questão 1 {HASH}.md",
        f"# Questão 1\n\nEnunciado...\n\n```python\n{CANARY} = int(input())\n"
        f"print({CANARY})\n```\n",
    )
    # Uma página com duas questões, cada uma sob o próprio título; o bloco de texto é ignorado.
    _page(
        root,
        "Lista 2.md",
        "## L2-Q3\n```python\nfor i in range(3):\n    print(i)\n```\n"
        "```text\nsaída esperada\n```\n"
        "## L2 Q4\n~~~py\nx = 0\nwhile x < 3:\n    x += 1\n~~~\n",
    )
    # Duas soluções para a mesma questão: alguém decide à mão.
    _page(
        root,
        "L3-Q1 duas.md",
        "```python\na = [1]\nprint(a)\n```\n\n```python\nb = (1,)\nprint(b)\n```\n",
    )
    # Sem questão reconhecível.
    _page(root, "Rascunhos.md", "```python\nprint('?')\n```\n")
    return root


def test_each_python_block_gets_its_question(export: Path) -> None:
    found = sorted(
        ((block.question, block.where) for block in read_blocks(export)),
        key=lambda item: (item[0] or "", item[1]),
    )

    assert found == [
        (None, "Rascunhos.md"),
        ("L1-Q1", f"Lista 1 {HASH}/Questão 1 {HASH}.md (Questão 1)"),
        ("L2-Q3", "Lista 2.md (L2-Q3)"),
        ("L2-Q4", "Lista 2.md (L2 Q4)"),
        ("L3-Q1", "L3-Q1 duas.md"),
        ("L3-Q1", "L3-Q1 duas.md"),
    ]


def test_the_import_writes_the_official_layout(export: Path, tmp_path: Path) -> None:
    destination = tmp_path / "ip-checker-gabaritos"

    result = import_gabaritos(export, destination, "2025.2")

    assert result.written == [
        "2025.2/lista-1/L1-Q1.py",
        "2025.2/lista-2/L2-Q3.py",
        "2025.2/lista-2/L2-Q4.py",
    ]
    assert result.conflicts == ["L3-Q1: 2 blocos (L3-Q1 duas.md; L3-Q1 duas.md)"]
    assert result.unknown == ["Rascunhos.md"]
    assert (destination / "2025.2/lista-2/L2-Q4.py").read_text(encoding="utf-8") == (
        "x = 0\nwhile x < 3:\n    x += 1\n"
    )


def test_existing_gabaritos_are_kept_and_dry_run_writes_nothing(
    export: Path, tmp_path: Path
) -> None:
    destination = tmp_path / "ip-checker-gabaritos"
    (destination / "2025.2/lista-1").mkdir(parents=True)
    (destination / "2025.2/lista-1/L1-Q1.py").write_text("original\n", encoding="utf-8")

    kept = import_gabaritos(export, destination, "2025.2", dry_run=True)

    assert kept.skipped_existing == ["2025.2/lista-1/L1-Q1.py"]
    assert not (destination / "2025.2/lista-2").exists()
    replaced = import_gabaritos(export, destination, "2025.2", overwrite=True)
    assert "2025.2/lista-1/L1-Q1.py" in replaced.written
    assert CANARY in (destination / "2025.2/lista-1/L1-Q1.py").read_text(encoding="utf-8")


def test_the_main_repository_is_never_a_destination(export: Path) -> None:
    with pytest.raises(ValueError, match="NFR-27"):
        import_gabaritos(export, REPO_ROOT / "gabaritos-por-engano", "2025.2")
    with pytest.raises(ValueError, match="período inválido"):
        import_gabaritos(export, Path("x"), "2025")


def test_the_command_shows_paths_but_never_code(
    export: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "ip-checker-gabaritos"

    code = main(["import-gabaritos", str(export), str(destination), "--periodo", "2025.2"])

    captured = capsys.readouterr()
    assert code == 1  # há um conflito e um bloco sem questão para decidir
    assert "gabaritos gravados: 3" in captured.out
    assert "IPC_GABARITOS_DIR=" in captured.out
    assert "decida à mão: L3-Q1" in captured.out
    assert "sem questão reconhecida: Rascunhos.md" in captured.out
    assert CANARY not in captured.out + captured.err
    assert (
        main(["import-gabaritos", str(tmp_path / "nada"), str(destination), "--periodo", "2025.2"])
        == 2
    )

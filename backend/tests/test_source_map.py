"""O mapa de colunas (S38-05): a conversão nova dá o mesmo resultado que a antiga, byte a byte."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.facts.model import SourceMap
from ipc_analyzer.engine.guards import split_lines


def _old_column(source: str, line: int, byte_offset: int) -> int:
    """A conversão de antes da S38-05: decodificar a linha até o byte, a cada fato."""
    lines = split_lines(source)
    if not 1 <= line <= len(lines):
        return byte_offset + 1
    return len(lines[line - 1].encode("utf-8")[:byte_offset].decode("utf-8", errors="ignore")) + 1


SOURCES = [
    "x = 1\nprint(x)\n",
    "nome = 'José'\nprint(f'olá, {nome} 👋')\n",
    "s = 'ação'  # comentário com ç\nt = '中文' + s\n\n",
    "a = '\U0001d518\U0001d52b'; b = 'é'\n",  # 4 bytes por caractere
    "",
]


@pytest.mark.parametrize("source", SOURCES)
def test_every_byte_offset_gives_the_same_column_as_before(source: str) -> None:
    columns = SourceMap(source)
    lines = split_lines(source)
    for line in range(0, len(lines) + 2):
        width = len(lines[line - 1].encode("utf-8")) if 1 <= line <= len(lines) else 3
        for offset in range(width + 3):
            assert columns.column(line, offset) == _old_column(source, line, offset), (line, offset)


def test_an_ascii_line_is_not_decoded() -> None:
    columns = SourceMap("x = 1\ny = 'é'\n")

    assert columns.column(1, 4) == 5
    assert columns._tables[1] is None
    assert columns.column(2, 6) == 6
    assert columns._tables[2] is not None

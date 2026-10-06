"""Fato extraído da AST e o mapa de posições do código (5.2.3).

Um fato é ``<tipo>:<nome>`` com a posição em linha e coluna a partir de 1, a coluna contada em
caracteres e o fim exclusivo, mais o contexto que os predicados (``predicates.py``) consultam.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipc_analyzer.engine.guards import split_lines
from ipc_analyzer.engine.symbols import Position


@dataclass(frozen=True, slots=True)
class Fact:
    name: str
    line: int
    col: int
    end_line: int
    end_col: int
    #: Número de argumentos da chamada quando o fato é a função chamada (``type('C', (), {})``
    #: -> 3); ``None`` quando não é chamada. Usado pelos predicados (``engine/conditions.py``).
    call_args: int | None = None
    #: Número de sequências do ``zip()`` que é o iterável de um ``for``, no próprio ``builtin:zip``
    #: e no ``target:for_unpack`` desse ``for``; ``None`` fora desse caso (predicado da R-37).
    zip_header_args: int | None = None
    #: No ``target:for_unpack``: ``"enumerate"`` ou ``"items"`` quando o iterável do ``for`` é
    #: ``enumerate(...)`` (built-in) ou ``x.items()`` (predicados das R-63 e R-65, Sprint 23).
    for_header: str | None = None


class SourceMap:
    """Converte colunas da AST (bytes UTF-8, a partir de 0) em caracteres (a partir de 1)."""

    def __init__(self, source: str) -> None:
        self._lines = split_lines(source)
        self._encoded: dict[int, bytes] = {}

    def column(self, line: int, byte_offset: int) -> int:
        if not 1 <= line <= len(self._lines):
            return byte_offset + 1
        encoded = self._encoded.get(line)
        if encoded is None:
            encoded = self._lines[line - 1].encode("utf-8")
            self._encoded[line] = encoded
        return len(encoded[:byte_offset].decode("utf-8", errors="ignore")) + 1

    def fact(
        self,
        name: str,
        start: Position,
        end: Position,
        call_args: int | None = None,
        zip_header_args: int | None = None,
        for_header: str | None = None,
    ) -> Fact:
        return Fact(
            name,
            start[0],
            self.column(*start),
            end[0],
            self.column(*end),
            call_args,
            zip_header_args,
            for_header,
        )

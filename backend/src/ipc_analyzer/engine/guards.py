"""Limites de entrada aplicados antes e durante a análise (FR-04, NFR-08, P-04).

As mensagens das exceções são mostradas ao aluno; por isso estão em PT-BR e nunca repetem
trechos do código enviado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Limits:
    max_bytes: int = 51_200
    max_lines: int = 1_000
    max_depth: int = 200
    # Calibrado na S5-01: 50 KB geram no máximo ~53 mil nós (pior caso: 0,46 s e 74 MB).
    max_nodes: int = 60_000


DEFAULT_LIMITS = Limits()


class InputError(Exception):
    """Entrada recusada; ``code`` é o código de erro do contrato da API (5.2.2)."""

    code: ClassVar[str] = "INVALID_INPUT"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidInputError(InputError):
    code = "INVALID_INPUT"


class PayloadTooLargeError(InputError):
    code = "PAYLOAD_TOO_LARGE"


class AnalysisLimitError(InputError):
    code = "ANALYSIS_LIMIT"


# Quebras de linha reconhecidas pelo tokenizador do Python.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
# Caracteres de controle recusados. Tab, \n, \r e form feed (\x0c) são válidos em código Python.
_FORBIDDEN_CONTROL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")


def split_lines(text: str) -> list[str]:
    """Linhas físicas do texto, sem as quebras, na mesma numeração usada pela AST."""
    return _LINE_BREAK.split(text)


def count_lines(text: str) -> int:
    """Conta linhas físicas como o Python: a quebra final não abre uma linha nova."""
    parts = split_lines(text)
    if parts[-1] == "":
        parts.pop()
    return len(parts)


def line_at(text: str, index: int) -> int:
    """Número da linha (a partir de 1) do caractere na posição ``index``."""
    return len(_LINE_BREAK.findall(text, 0, index)) + 1


def thousands(value: int) -> str:
    return f"{value:_}".replace("_", ".")


def check_source(source: str, limits: Limits = DEFAULT_LIMITS) -> str:
    """Valida o texto enviado e devolve-o sem o BOM inicial. Nada é executado aqui."""
    if source.startswith("﻿"):
        source = source[1:]
    try:
        size = len(source.encode("utf-8"))
    except UnicodeEncodeError:
        raise InvalidInputError("O código contém caracteres que não são UTF-8 válido.") from None
    if size > limits.max_bytes:
        raise PayloadTooLargeError(
            f"O código tem {thousands(size)} bytes; o limite é {thousands(limits.max_bytes)} "
            "bytes (50 KB)."
        )
    if not source.strip():
        raise InvalidInputError("O código está vazio.")
    lines = count_lines(source)
    if lines > limits.max_lines:
        raise InvalidInputError(
            f"O código tem {thousands(lines)} linhas; o limite é {thousands(limits.max_lines)}."
        )
    if (match := _FORBIDDEN_CONTROL.search(source)) is not None:
        line = line_at(source, match.start())
        char = match.group()
        if char == "\x00":
            raise InvalidInputError(f"O código contém o caractere nulo na linha {line}.")
        raise InvalidInputError(
            f"O código contém um caractere de controle inválido (U+{ord(char):04X}) "
            f"na linha {line}."
        )
    return source

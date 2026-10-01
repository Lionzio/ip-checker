"""Validação do código na API, antes de chamar o analyzer (5.2.2, passo 3).

São os limites do contrato: o que passa daqui ainda é conferido pelo analyzer, que é a
autoridade sobre caracteres de controle e limites da árvore sintática. Recusar aqui poupa uma
viagem ao analyzer e mantém o contrato mesmo que ele mude.
"""

from __future__ import annotations

import re

from ipc_api.errors import ApiError, ErrorCode

MAX_CODE_BYTES = 51_200
MAX_LINES = 1_000

# A mesma contagem do analyzer: \r\n, \r e \n quebram linha, e a quebra final não abre outra.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_BOM = "﻿"


def _thousands(value: int) -> str:
    return f"{value:_}".replace("_", ".")


def count_lines(code: str) -> int:
    parts = _LINE_BREAK.split(code)
    if parts[-1] == "":
        parts.pop()
    return len(parts)


def check_code(code: str) -> None:
    if code.startswith(_BOM):
        code = code[1:]
    try:
        size = len(code.encode("utf-8"))
    except UnicodeEncodeError:
        raise ApiError(
            422, ErrorCode.INVALID_INPUT, "O código contém caracteres que não são UTF-8 válido."
        ) from None
    if size > MAX_CODE_BYTES:
        raise ApiError(
            413,
            ErrorCode.PAYLOAD_TOO_LARGE,
            f"O código tem {_thousands(size)} bytes; o limite é {_thousands(MAX_CODE_BYTES)} "
            "bytes (50 KB).",
        )
    if not code.strip():
        raise ApiError(422, ErrorCode.INVALID_INPUT, "O código está vazio.")
    if "\x00" in code:
        raise ApiError(422, ErrorCode.INVALID_INPUT, "O código contém o caractere nulo.")
    lines = count_lines(code)
    if lines > MAX_LINES:
        raise ApiError(
            422,
            ErrorCode.INVALID_INPUT,
            f"O código tem {_thousands(lines)} linhas; o limite é {_thousands(MAX_LINES)}.",
        )

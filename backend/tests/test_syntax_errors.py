"""Tradução das mensagens de erro de sintaxe do Python 3.13 (FR-05)."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.syntax_errors import translate_syntax_error


@pytest.mark.parametrize(
    ("python_message", "expected"),
    [
        ("invalid syntax", "sintaxe inválida"),
        (
            "invalid syntax. Maybe you meant '==' or ':=' instead of '='?",
            "sintaxe inválida. Você quis dizer '==' em vez de '='?",
        ),
        (
            "closing parenthesis ']' does not match opening parenthesis '(' on line 2",
            "o ']' não fecha o '(' aberto na linha 2",
        ),
        (
            "closing parenthesis ']' does not match opening parenthesis '('",
            "o ']' não fecha o '(' aberto antes",
        ),
        (
            "expected an indented block after 'for' statement on line 3",
            "faltou um bloco indentado depois do 'for' da linha 3",
        ),
        (
            "expected an indented block after class definition on line 1",
            "faltou um bloco indentado depois da definição de classe da linha 1",
        ),
        ("expected an indented block", "faltou um bloco indentado"),
        ("expected 'except' or 'finally' block", "faltou o bloco 'except' ou 'finally'"),
        (
            "unindent does not match any outer indentation level",
            "a indentação não corresponde a nenhum nível anterior",
        ),
        (
            "inconsistent use of tabs and spaces in indentation",
            "mistura de tabs e espaços na indentação",
        ),
        (
            "unterminated triple-quoted string literal (detected at line 4)",
            "string de aspas triplas não terminada (detectada na linha 4)",
        ),
        ("unterminated f-string literal (detected at line 1)", "f-string não terminada"),
        ("too many nested f-strings", "f-strings aninhadas demais"),
        ("invalid character '…' (U+2026)", "caractere inválido '…' (U+2026)"),
        ("invalid non-printable character U+00A0", "caractere invisível inválido (U+00A0)"),
        ("invalid hexadecimal literal", "número inválido"),
        (
            "leading zeros in decimal integer literals are not permitted; "
            "use an 0o prefix for octal integers",
            "números inteiros não podem começar com zero",
        ),
        (
            "cannot assign to function call here. Maybe you meant '==' instead of '='?",
            "não é possível atribuir a uma chamada de função aqui. "
            "Você quis dizer '==' em vez de '='?",
        ),
        ("cannot assign to literal", "não é possível atribuir a um valor literal"),
        ("'return' outside function", "'return' fora de uma função"),
        ("'break' outside loop", "'break' fora de um laço"),
        (
            "positional argument follows keyword argument",
            "argumento posicional depois de argumento nomeado",
        ),
        (
            "unexpected character after line continuation character",
            "caractere inesperado depois da barra invertida de continuação de linha",
        ),
        ("unexpected EOF while parsing", "o código terminou antes do esperado"),
    ],
)
def test_known_messages_are_translated(python_message: str, expected: str) -> None:
    assert translate_syntax_error(python_message) == expected


def test_unknown_message_keeps_the_original_text() -> None:
    assert translate_syntax_error("brand new error") == (
        "erro de sintaxe (mensagem do Python: brand new error)"
    )

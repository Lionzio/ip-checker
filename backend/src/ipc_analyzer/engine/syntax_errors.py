"""Tradução das mensagens de erro de sintaxe do Python 3.13 para PT-BR (FR-05).

Mensagens sem tradução são devolvidas com o texto original, para o aluno nunca ficar sem pista.
"""

from __future__ import annotations

import re

# Termos que aparecem dentro das mensagens (ex.: "cannot assign to comparison").
_TERMS = {
    "comparison": "uma comparação",
    "function call": "uma chamada de função",
    "literal": "um valor literal",
    "expression": "uma expressão",
    "attribute": "um atributo",
    "subscript": "um índice",
    "conditional expression": "uma expressão condicional",
    "f-string expression": "uma expressão de f-string",
    "function definition": "a definição de função",
    "class definition": "a definição de classe",
}

_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"invalid syntax\. Perhaps you forgot a comma\?",
        "sintaxe inválida. Talvez falte uma vírgula?",
    ),
    (
        r"invalid syntax\. Maybe you meant '==' or ':=' instead of '='\?",
        "sintaxe inválida. Você quis dizer '==' em vez de '='?",
    ),
    (r"invalid syntax", "sintaxe inválida"),
    (r"'(?P<c>.)' was never closed", "o '{c}' foi aberto e nunca fechado"),
    (r"unmatched '(?P<c>.)'", "'{c}' fechado sem ter sido aberto"),
    (
        r"closing parenthesis '(?P<a>.)' does not match opening parenthesis '(?P<b>.)' "
        r"on line (?P<n>\d+)",
        "o '{a}' não fecha o '{b}' aberto na linha {n}",
    ),
    (
        r"closing parenthesis '(?P<a>.)' does not match opening parenthesis '(?P<b>.)'",
        "o '{a}' não fecha o '{b}' aberto antes",
    ),
    (
        r"expected an indented block after '(?P<k>\w+)' statement on line (?P<n>\d+)",
        "faltou um bloco indentado depois do '{k}' da linha {n}",
    ),
    (
        r"expected an indented block after (?P<what>function definition|class definition) "
        r"on line (?P<n>\d+)",
        "faltou um bloco indentado depois d{what} da linha {n}",
    ),
    (r"expected an indented block.*", "faltou um bloco indentado"),
    (r"expected '(?P<t>[^']+)'", "faltou '{t}'"),
    (r"expected 'except' or 'finally' block", "faltou o bloco 'except' ou 'finally'"),
    (r"unexpected indent", "indentação inesperada"),
    (
        r"unindent does not match any outer indentation level",
        "a indentação não corresponde a nenhum nível anterior",
    ),
    (
        r"inconsistent use of tabs and spaces in indentation",
        "mistura de tabs e espaços na indentação",
    ),
    (
        r"unterminated string literal \(detected at line (?P<n>\d+)\)",
        "string não terminada (detectada na linha {n})",
    ),
    (
        r"unterminated triple-quoted string literal \(detected at line (?P<n>\d+)\)",
        "string de aspas triplas não terminada (detectada na linha {n})",
    ),
    (r"unterminated f-string literal.*", "f-string não terminada"),
    (r"too many nested f-strings", "f-strings aninhadas demais"),
    (r"invalid character '(?P<c>.)' \((?P<u>U\+[0-9A-F]+)\)", "caractere inválido '{c}' ({u})"),
    (r"invalid non-printable character (?P<u>U\+[0-9A-F]+)", "caractere invisível inválido ({u})"),
    (r"invalid decimal literal", "número decimal inválido"),
    (r"invalid (?:hexadecimal|octal|binary) literal", "número inválido"),
    (
        r"leading zeros in decimal integer literals are not permitted.*",
        "números inteiros não podem começar com zero",
    ),
    (
        r"Missing parentheses in call to '(?P<f>\w+)'\. Did you mean (?P=f)\(\.\.\.\)\?",
        "faltam parênteses na chamada de '{f}'. Você quis dizer {f}(...)?",
    ),
    (
        r"cannot assign to (?P<what>.+?) here\. Maybe you meant '==' instead of '='\?",
        "não é possível atribuir a {what} aqui. Você quis dizer '==' em vez de '='?",
    ),
    (r"cannot assign to (?P<what>.+)", "não é possível atribuir a {what}"),
    (r"'return' outside function", "'return' fora de uma função"),
    (r"'(?P<k>break|continue)' (?:not properly in|outside) loop", "'{k}' fora de um laço"),
    (
        r"positional argument follows keyword argument",
        "argumento posicional depois de argumento nomeado",
    ),
    (
        r"unexpected character after line continuation character",
        "caractere inesperado depois da barra invertida de continuação de linha",
    ),
    (r"unexpected EOF while parsing", "o código terminou antes do esperado"),
)

_COMPILED = tuple((re.compile(pattern), template) for pattern, template in _PATTERNS)


def translate_syntax_error(message: str) -> str:
    """Traduz a mensagem do ``SyntaxError``; sem tradução, devolve o texto original."""
    for pattern, template in _COMPILED:
        match = pattern.fullmatch(message)
        if match is not None:
            # "depois d{what}" + "a definição de função" -> "depois da definição de função"
            terms = {key: _TERMS.get(value, value) for key, value in match.groupdict().items()}
            return template.format(**terms)
    return f"erro de sintaxe (mensagem do Python: {message})"

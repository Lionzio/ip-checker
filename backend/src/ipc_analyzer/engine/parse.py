"""Análise sintática segura: o código vira AST e nunca é executado (ADR-01, FR-05).

Este é o único ponto do projeto que chama ``ast.parse``. A árvore é medida de forma iterativa
(sem recursão Python) para que entradas muito aninhadas não derrubem o processo.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass

from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    AnalysisLimitError,
    Limits,
    check_source,
    count_lines,
    thousands,
)
from ipc_analyzer.engine.syntax_errors import translate_syntax_error

FILENAME = "<submissão>"

# Limite fixo do tokenizador do CPython para parênteses, colchetes e chaves aninhados.
_TOKENIZER_NESTING_MESSAGE = "too many nested parentheses"


@dataclass(frozen=True, slots=True)
class ParsedSource:
    tree: ast.Module
    source: str
    line_count: int
    node_count: int
    depth: int


@dataclass(frozen=True, slots=True)
class SyntaxProblem:
    """Erro de sintaxe com linha e coluna a partir de 1, contadas em caracteres."""

    line: int
    col: int
    message: str
    python_message: str


def parse_source(
    source: str, *, target: tuple[int, int], limits: Limits = DEFAULT_LIMITS
) -> ParsedSource | SyntaxProblem:
    """Valida, analisa e mede o código.

    Levanta ``InvalidInputError``, ``PayloadTooLargeError`` ou ``AnalysisLimitError`` quando a
    entrada viola os limites; devolve ``SyntaxProblem`` quando o código não é Python válido.
    """
    text = check_source(source, limits)
    try:
        tree = ast.parse(text, filename=FILENAME, mode="exec", feature_version=target)
    except SyntaxError as exc:
        if exc.msg == _TOKENIZER_NESTING_MESSAGE:
            raise AnalysisLimitError(
                "O código tem parênteses, colchetes ou chaves aninhados em mais de 200 níveis "
                "e não pode ser analisado."
            ) from None
        return _syntax_problem(exc, text)
    except (RecursionError, MemoryError):
        raise AnalysisLimitError("O código é complexo demais para ser analisado.") from None
    node_count, depth = measure_tree(tree, limits)
    return ParsedSource(
        tree=tree,
        source=text,
        line_count=count_lines(text),
        node_count=node_count,
        depth=depth,
    )


def measure_tree(tree: ast.AST, limits: Limits = DEFAULT_LIMITS) -> tuple[int, int]:
    """Conta nós e mede a profundidade com pilha explícita; para no primeiro limite excedido."""
    count = 0
    deepest = 0
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > limits.max_nodes:
            raise AnalysisLimitError(
                f"O código tem mais de {thousands(limits.max_nodes)} elementos sintáticos "
                "e não pode ser analisado."
            )
        if depth > limits.max_depth:
            raise AnalysisLimitError(
                f"O código tem mais de {limits.max_depth} níveis de aninhamento "
                "e não pode ser analisado."
            )
        deepest = max(deepest, depth)
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return count, deepest


def require_runtime(target: tuple[int, int]) -> None:
    """Garante que o interpretador tem a mesma versão minor do Dikastis (NFR-21)."""
    current = (sys.version_info.major, sys.version_info.minor)
    if current != target:
        raise RuntimeError(
            f"o analisador precisa do Python {target[0]}.{target[1]}, "
            f"mas está rodando no {current[0]}.{current[1]}"
        )


def _syntax_problem(exc: SyntaxError, text: str) -> SyntaxProblem:
    python_message = exc.msg or "invalid syntax"
    last_line = max(count_lines(text), 1)
    return SyntaxProblem(
        line=min(max(exc.lineno or 1, 1), last_line),
        col=max(exc.offset or 1, 1),
        message=translate_syntax_error(python_message),
        python_message=python_message,
    )

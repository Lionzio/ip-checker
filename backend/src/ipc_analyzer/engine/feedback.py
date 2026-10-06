"""O que o feedback pode usar de uma solução (S18-02; FR-30, ADR-06, Q-16, Q-18).

A LLM nunca decide se houve violação: o motor decide, e daqui sai só o que a API precisa para
montar a frase obrigatória (cada construção pelo nome legível do ``display.py``) e o código sem
os comentários nem as docstrings, que é onde costumam aparecer nomes e matrículas (Q-16; S25-05).
É o único texto do aluno que pode ir a um provedor de LLM, e só depois de a API trocar o nome
dele por ``[ALUNO]`` e mascarar matrículas, e-mails e CPFs.
"""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from typing import Literal

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    AnalysisLimitError,
    Limits,
    check_source,
    split_lines,
)
from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.ruleset import Category, CompiledRuleset


@dataclass(frozen=True, slots=True)
class FeedbackItem:
    #: "uso": uma construção proibida que aparece; "falta": uma exigência da lista (R-02) ausente.
    kind: Literal["uso", "falta"]
    label: str


@dataclass(frozen=True, slots=True)
class FeedbackInput:
    status: Literal["valid", "invalid", "syntax_error"]
    #: Na ordem em que aparecem no resultado, sem repetição.
    items: tuple[FeedbackItem, ...]
    #: O código sem comentários nem docstrings; vazio quando há erro de sintaxe.
    code: str
    syntax_error: SyntaxProblem | None


def feedback_input(
    source: str,
    *,
    list_number: int,
    ruleset: CompiledRuleset,
    question_id: str | None = None,
    limits: Limits = DEFAULT_LIMITS,
) -> FeedbackInput:
    result = analyze_source(
        source, list_number=list_number, ruleset=ruleset, question_id=question_id, limits=limits
    )
    if result.status == "syntax_error":
        return FeedbackInput("syntax_error", (), "", result.syntax_error)
    requirements = {r.id: r for r in ruleset.requirements_for(list_number)}
    items: dict[FeedbackItem, None] = {}
    for violation in result.violations:
        requirement = requirements.get(violation.rule_id)
        if violation.category is Category.EXIGENCIA and requirement is not None:
            labels = dict.fromkeys(describe(fact) for fact in requirement.require_any)
            items[FeedbackItem("falta", " ou ".join(labels))] = None
        else:
            items[FeedbackItem("uso", describe(violation.construct))] = None
    code = strip_comments(strip_docstrings(check_source(source, limits)))
    return FeedbackInput(result.status, tuple(items), code, None)


def strip_docstrings(text: str) -> str:
    """Troca cada texto solto (docstrings e blocos de texto usados como comentário) por ``...``.

    O código continua válido: um corpo que só tinha a docstring passa a ter ``...``. O texto
    chega aqui depois da análise, então já se sabe que ele compila.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        raise AnalysisLimitError("Não foi possível preparar o código para o feedback.") from None
    loose = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ),
        key=lambda node: (node.lineno, node.col_offset),
        reverse=True,
    )
    # As colunas da AST contam bytes UTF-8.
    lines = [line.encode("utf-8") for line in split_lines(text)]
    for node in loose:
        first, last = node.lineno - 1, (node.end_lineno or node.lineno) - 1
        end_col = node.end_col_offset if node.end_col_offset is not None else len(lines[last])
        lines[first : last + 1] = [lines[first][: node.col_offset] + b"..." + lines[last][end_col:]]
    return "\n".join(line.decode("utf-8") for line in lines)


def strip_comments(text: str) -> str:
    """Tira os comentários e os espaços que sobram no fim das linhas; o resto fica igual."""
    lines = split_lines(text)
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                row, col = token.start
                lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, SyntaxError, RecursionError, MemoryError):
        raise AnalysisLimitError("Não foi possível preparar o código para o feedback.") from None
    return "\n".join(line.rstrip() for line in lines).strip("\n") + "\n"

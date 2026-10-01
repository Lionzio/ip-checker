"""Resultado da análise, no formato do contrato da API (FR-12, 5.2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.ruleset import Category

AnalysisStatus = Literal["valid", "invalid", "syntax_error"]

#: Número máximo de violações devolvidas por análise (P-04).
MAX_VIOLATIONS = 200


@dataclass(frozen=True, slots=True)
class Violation:
    rule_id: str
    category: Category
    #: Linha e coluna a partir de 1, coluna em caracteres e fim exclusivo.
    line: int
    col: int
    end_line: int
    end_col: int
    #: Fato que gerou a violação (ex.: ``node:For``).
    construct: str
    allowed_from_list: int | None
    message: str


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    status: AnalysisStatus
    ruleset_version: str
    list_number: int
    violations: tuple[Violation, ...] = ()
    syntax_error: SyntaxProblem | None = None
    #: Verdadeiro quando havia mais de ``MAX_VIOLATIONS`` violações e a lista foi cortada.
    truncated: bool = False

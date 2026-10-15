"""Resultado da análise, no formato do contrato da API (FR-12, 5.2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.ruleset import Category

if TYPE_CHECKING:
    from ipc_analyzer.engine.gabarito import GabaritoComparison
    from ipc_analyzer.engine.indicators import Indicators

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
    #: Por que a construção não vale e o que usar no lugar (S38-01), do ruleset.
    explanation: str = ""
    alternative: str = ""


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    status: AnalysisStatus
    ruleset_version: str
    list_number: int
    violations: tuple[Violation, ...] = ()
    syntax_error: SyntaxProblem | None = None
    #: Verdadeiro quando havia mais de ``MAX_VIOLATIONS`` violações e a lista foi cortada.
    truncated: bool = False
    #: Indícios de uso de IA (ADR-08), só quando pedidos e só para a equipe; ``None`` sem indício.
    indicators: Indicators | None = None
    #: Comparação com o gabarito da questão (ADR-11), quando a API mandou o gabarito.
    gabarito: GabaritoComparison | None = None

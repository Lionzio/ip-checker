"""Ponto de entrada do motor: código-fonte -> resultado da análise (sem executar nada)."""

from __future__ import annotations

from ipc_analyzer.engine.facts import extract_facts
from ipc_analyzer.engine.guards import DEFAULT_LIMITS, InvalidInputError, Limits
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import SyntaxProblem, parse_source
from ipc_analyzer.engine.policy import evaluate
from ipc_analyzer.engine.ruleset import CompiledRuleset


def analyze_source(
    source: str,
    *,
    list_number: int,
    ruleset: CompiledRuleset,
    limits: Limits = DEFAULT_LIMITS,
) -> AnalysisResult:
    """Analisa o código para a lista indicada.

    Levanta ``InvalidInputError``, ``PayloadTooLargeError`` ou ``AnalysisLimitError`` quando a
    entrada é recusada (FR-04, NFR-08).
    """
    if list_number not in ruleset.ruleset.lists:
        raise InvalidInputError(f"A Lista {list_number} não existe.")
    parsed = parse_source(source, target=ruleset.target_version, limits=limits)
    if isinstance(parsed, SyntaxProblem):
        return AnalysisResult(
            status="syntax_error",
            ruleset_version=ruleset.version,
            list_number=list_number,
            syntax_error=parsed,
        )
    violations, truncated = evaluate(extract_facts(parsed), ruleset, list_number)
    return AnalysisResult(
        status="invalid" if violations else "valid",
        ruleset_version=ruleset.version,
        list_number=list_number,
        violations=violations,
        truncated=truncated,
    )

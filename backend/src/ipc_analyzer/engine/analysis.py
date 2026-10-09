"""Ponto de entrada do motor: código-fonte -> resultado da análise (sem executar nada)."""

from __future__ import annotations

from ipc_analyzer.engine.facts import extract_facts
from ipc_analyzer.engine.gabarito import compare_with_gabarito
from ipc_analyzer.engine.guards import (
    DEFAULT_LIMITS,
    InvalidInputError,
    Limits,
    UnknownQuestionError,
)
from ipc_analyzer.engine.indicators import compute_indicators
from ipc_analyzer.engine.models import AnalysisResult
from ipc_analyzer.engine.parse import SyntaxProblem, parse_source
from ipc_analyzer.engine.policy import evaluate
from ipc_analyzer.engine.ruleset import CompiledQuestion, CompiledRuleset


def analyze_source(
    source: str,
    *,
    list_number: int,
    ruleset: CompiledRuleset,
    question_id: str | None = None,
    limits: Limits = DEFAULT_LIMITS,
    with_indicators: bool = False,
    gabarito: str | None = None,
) -> AnalysisResult:
    """Analisa o código para a lista indicada e, se houver, para a questão (R-01).

    Com ``with_indicators``, calcula também os indícios de uso de IA (ADR-08, S29-01), a partir das
    violações e da mesma árvore, sem guardar nada. Com ``gabarito``, compara o código com o
    gabarito oficial da questão (ADR-11), e a semelhança entra também nos indícios.

    Levanta ``InvalidInputError``, ``UnknownQuestionError``, ``PayloadTooLargeError`` ou
    ``AnalysisLimitError`` quando a entrada é recusada (FR-04, NFR-08).
    """
    question = resolve_question(ruleset, list_number, question_id)
    parsed = parse_source(source, target=ruleset.target_version, limits=limits)
    if isinstance(parsed, SyntaxProblem):
        return AnalysisResult(
            status="syntax_error",
            ruleset_version=ruleset.version,
            list_number=list_number,
            syntax_error=parsed,
        )
    violations, truncated = evaluate(extract_facts(parsed), ruleset, list_number, question=question)
    comparison = (
        compare_with_gabarito(
            source,
            gabarito,
            target=ruleset.target_version,
            structural=ruleset.structural_facts,
            limits=limits,
        )
        if gabarito is not None
        else None
    )
    indicators = (
        compute_indicators(
            parsed,
            violations,
            list_number=list_number,
            ruleset=ruleset,
            question_id=question_id,
            limits=limits,
            gabarito=comparison,
        )
        if with_indicators
        else None
    )
    return AnalysisResult(
        status="invalid" if violations else "valid",
        ruleset_version=ruleset.version,
        list_number=list_number,
        violations=violations,
        truncated=truncated,
        indicators=indicators,
        gabarito=comparison,
    )


def resolve_question(
    ruleset: CompiledRuleset, list_number: int, question_id: str | None
) -> CompiledQuestion | None:
    """A questão cadastrada, conferida contra a lista; ``None`` sem questão."""
    if list_number not in ruleset.ruleset.lists:
        raise InvalidInputError(f"A Lista {list_number} não existe.")
    if question_id is None:
        return None
    question = ruleset.questions.get(question_id)
    if question is None:
        raise UnknownQuestionError(f"A questão {question_id} não está cadastrada no IP-Checker.")
    if question.question.list_number != list_number:
        raise UnknownQuestionError(
            f"A questão {question_id} é da Lista {question.question.list_number}, "
            f"não da Lista {list_number}."
        )
    return question

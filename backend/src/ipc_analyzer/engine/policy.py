"""Avaliador de política v1 (5.2.3): transforma fatos em violações.

Para cada fato, na lista ``n``, vale a primeira situação verdadeira:

1. fato estrutural: aceito;
2. casa uma proibição geral cuja condição vale: ``ANULACAO`` (R-05 a R-14);
3. casa uma permissão válida na lista (``since_list <= n <= until_list``) cuja condição vale:
   aceito (cumulatividade, R-03);
4. casa uma permissão válida na lista, mas a condição não vale: ``NAO_CONSTA`` com o ID e a
   mensagem dessa regra (ex.: ``type()`` com 2 argumentos, R-33);
5. casa uma permissão de lista posterior: ``FORA_DA_LISTA``, com a primeira lista que permite;
6. nada casa: ``NAO_CONSTA`` pela R-04 (*default deny*).

Overrides de questão (R-01) entram na Sprint 17; exigências (R-02, R-68), nas Sprints 12 a 16.
"""

from __future__ import annotations

from collections.abc import Iterable

from ipc_analyzer.engine.conditions import holds
from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.facts import Fact
from ipc_analyzer.engine.models import MAX_VIOLATIONS, Violation
from ipc_analyzer.engine.ruleset import Category, CompiledRuleset, Effect, Rule, RuleMatch


def _violation(
    fact: Fact,
    rule_id: str,
    category: Category,
    template: str,
    allowed_from_list: int | None = None,
) -> Violation:
    message = template.format(
        allowed_from_list="" if allowed_from_list is None else allowed_from_list,
        construct=describe(fact.name),
    )
    return Violation(
        rule_id=rule_id,
        category=category,
        line=fact.line,
        col=fact.col,
        end_line=fact.end_line,
        end_col=fact.end_col,
        construct=fact.name,
        allowed_from_list=allowed_from_list,
        message=message,
    )


def _in_range(rule: Rule, list_number: int) -> bool:
    since = rule.since_list or 1
    until = rule.until_list or 6
    return since <= list_number <= until


def judge(fact: Fact, ruleset: CompiledRuleset, list_number: int) -> Violation | None:
    """Decide um único fato; ``None`` quando ele é permitido na lista."""
    if ruleset.is_structural(fact.name):
        return None
    matches = ruleset.matches_for(fact.name)

    for match in matches:
        if match.rule.effect is Effect.DENY and holds(match.condition, fact):
            return _violation(fact, match.rule.id, Category.ANULACAO, match.rule.message)

    allows = [match for match in matches if match.rule.effect is Effect.ALLOW]
    current = [match for match in allows if _in_range(match.rule, list_number)]
    if any(holds(match.condition, fact) for match in current):
        return None
    if current:
        failed: RuleMatch = current[0]
        template = (failed.condition.message if failed.condition else None) or failed.rule.message
        return _violation(fact, failed.rule.id, Category.NAO_CONSTA, template)

    later = [
        match
        for match in allows
        if (match.rule.since_list or 1) > list_number and holds(match.condition, fact)
    ]
    if later:
        first = min(later, key=lambda match: match.rule.since_list or 1)
        return _violation(
            fact,
            first.rule.id,
            Category.FORA_DA_LISTA,
            first.rule.message,
            allowed_from_list=first.rule.since_list,
        )

    default_deny = ruleset.default_deny
    return _violation(fact, default_deny.id, Category.NAO_CONSTA, default_deny.message or "")


def evaluate(
    facts: Iterable[Fact],
    ruleset: CompiledRuleset,
    list_number: int,
    *,
    max_violations: int = MAX_VIOLATIONS,
) -> tuple[tuple[Violation, ...], bool]:
    """Violações ordenadas e sem repetição por (regra, linha, coluna); indica se houve corte."""
    found: dict[tuple[str, int, int], Violation] = {}
    for fact in facts:
        violation = judge(fact, ruleset, list_number)
        if violation is not None:
            found.setdefault((violation.rule_id, violation.line, violation.col), violation)
    ordered = sorted(found.values(), key=lambda v: (v.line, v.col, v.rule_id))
    return tuple(ordered[:max_violations]), len(ordered) > max_violations

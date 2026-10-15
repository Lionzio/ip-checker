"""Avaliador de política v1 (5.2.3): transforma fatos em violações.

Para cada fato, na lista ``n`` e na questão ``q`` (se houver), vale a primeira situação verdadeira:

1. fato estrutural: aceito;
2. a questão proíbe o fato (``deny``): ``PROIBIDO_NA_QUESTAO`` pela R-01;
3. a questão libera o fato (``allow`` com a condição da regra, ou ``allow_facts``): aceito, acima
   até das proibições gerais (R-01, C-02);
4. casa uma proibição geral cuja condição vale: ``ANULACAO`` (R-05 a R-14);
5. casa uma permissão válida na lista (``since_list <= n <= until_list``) cuja condição vale:
   aceito (cumulatividade, R-03);
6. casa uma permissão válida na lista, mas a condição não vale: ``NAO_CONSTA`` com o ID e a
   mensagem dessa regra (ex.: ``type()`` com 2 argumentos, R-33);
7. casa uma permissão de lista posterior: ``FORA_DA_LISTA``, com a primeira lista que permite;
8. nada casa: ``NAO_CONSTA`` pela R-04 (*default deny*).

Depois, cada exigência da lista (R-02, Q-05; R-68, C-03) pede pelo menos um dos seus fatos no
código; se nenhum aparece, a solução inteira recebe uma violação ``EXIGENCIA`` (5.2.3, passo 6).

As exigências não mudam com a questão: uma questão não dispensa o assunto da lista (Sprint 24).
"""

from __future__ import annotations

from collections.abc import Iterable

from ipc_analyzer.engine.conditions import holds
from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.facts import Fact
from ipc_analyzer.engine.models import MAX_VIOLATIONS, Violation
from ipc_analyzer.engine.ruleset import (
    Category,
    CompiledQuestion,
    CompiledRuleset,
    Effect,
    Requirement,
    Rule,
    RuleMatch,
)

#: A regra específica da questão (catálogo R-01), em nome da qual a questão proíbe.
QUESTION_RULE = "R-01"
QUESTION_DENY_MESSAGE = "'{construct}' é proibido nesta questão ({question_id}), pelo enunciado."
#: A R-01 vem do enunciado, e não do documento de permissões: os textos dela ficam aqui (S38-01).
QUESTION_DENY_EXPLANATION = (
    "O enunciado desta questão proíbe a construção, e o que a questão define vale sobre as "
    "permissões gerais da lista."
)
QUESTION_DENY_ALTERNATIVE = (
    "Releia o enunciado e resolva com o que ele e a lista permitem; a mensagem diz o que a questão "
    "proíbe."
)

#: Uma exigência fala da solução inteira, e não de um trecho: aponta para o início do código.
REQUIREMENT_POSITION = (1, 1, 1, 1)


def _violation(
    fact: Fact,
    rule_id: str,
    category: Category,
    template: str,
    allowed_from_list: int | None = None,
    *,
    explanation: str = "",
    alternative: str = "",
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
        explanation=explanation,
        alternative=alternative,
    )


def _in_range(rule: Rule, list_number: int) -> bool:
    since = rule.since_list or 1
    until = rule.until_list or 6
    return since <= list_number <= until


def judge(
    fact: Fact,
    ruleset: CompiledRuleset,
    list_number: int,
    question: CompiledQuestion | None = None,
) -> Violation | None:
    """Decide um único fato; ``None`` quando ele é permitido na lista (e na questão)."""
    if ruleset.is_structural(fact.name):
        return None
    if question is not None:
        if fact.name in question.denied:
            template = question.question.message or QUESTION_DENY_MESSAGE
            return _violation(
                fact,
                QUESTION_RULE,
                Category.PROIBIDO_NA_QUESTAO,
                template.replace("{question_id}", question.id),
                explanation=QUESTION_DENY_EXPLANATION,
                alternative=QUESTION_DENY_ALTERNATIVE,
            )
        if any(holds(condition, fact) for condition in question.allowed.get(fact.name, ())):
            return None
    matches = ruleset.matches_for(fact.name)

    for match in matches:
        if match.rule.effect is Effect.DENY and holds(match.condition, fact):
            return _violation(
                fact,
                match.rule.id,
                Category.ANULACAO,
                match.rule.message,
                explanation=match.rule.explicacao,
                alternative=match.rule.alternativa,
            )

    allows = [match for match in matches if match.rule.effect is Effect.ALLOW]
    current = [match for match in allows if _in_range(match.rule, list_number)]
    if any(holds(match.condition, fact) for match in current):
        return None
    if current:
        failed: RuleMatch = current[0]
        template = (failed.condition.message if failed.condition else None) or failed.rule.message
        return _violation(
            fact,
            failed.rule.id,
            Category.NAO_CONSTA,
            template,
            explanation=failed.rule.explicacao,
            alternative=failed.rule.alternativa,
        )

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
            explanation=first.rule.explicacao,
            alternative=first.rule.alternativa,
        )

    default_deny = ruleset.default_deny
    return _violation(
        fact,
        default_deny.id,
        Category.NAO_CONSTA,
        default_deny.message or "",
        explanation=default_deny.explicacao or "",
        alternative=default_deny.alternativa or "",
    )


def unmet_requirements(
    facts: Iterable[Fact], ruleset: CompiledRuleset, list_number: int
) -> tuple[Violation, ...]:
    """Exigências da lista sem nenhum dos fatos que as comprovam no código."""
    present = {fact.name for fact in facts}
    return tuple(
        _requirement_violation(requirement)
        for requirement in ruleset.requirements_for(list_number)
        if present.isdisjoint(requirement.require_any)
    )


def _requirement_violation(requirement: Requirement) -> Violation:
    line, col, end_line, end_col = REQUIREMENT_POSITION
    return Violation(
        rule_id=requirement.id,
        category=Category.EXIGENCIA,
        line=line,
        col=col,
        end_line=end_line,
        end_col=end_col,
        construct=f"requirement:{requirement.id}",
        allowed_from_list=None,
        message=requirement.message,
        explanation=requirement.explicacao,
        alternative=requirement.alternativa,
    )


def evaluate(
    facts: Iterable[Fact],
    ruleset: CompiledRuleset,
    list_number: int,
    *,
    question: CompiledQuestion | None = None,
    max_violations: int = MAX_VIOLATIONS,
) -> tuple[tuple[Violation, ...], bool]:
    """Violações ordenadas e sem repetição por (regra, linha, coluna); indica se houve corte.

    As exigências não cumpridas vêm primeiro (linha 1, coluna 1) e nunca são cortadas.
    """
    facts = tuple(facts)
    found: dict[tuple[str, int, int], Violation] = {}
    for unmet in unmet_requirements(facts, ruleset, list_number):
        found[(unmet.rule_id, unmet.line, unmet.col)] = unmet
    for fact in facts:
        violation = judge(fact, ruleset, list_number, question)
        if violation is not None:
            found.setdefault((violation.rule_id, violation.line, violation.col), violation)
    ordered = sorted(found.values(), key=lambda v: (v.line, v.col, v.rule_id))
    return tuple(ordered[:max_violations]), len(ordered) > max_violations

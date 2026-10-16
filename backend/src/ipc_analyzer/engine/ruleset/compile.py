"""A compilação do ruleset validado (ADR-02): o índice imutável ``fato -> regras`` e as questões.

Um ruleset inválido levanta ``RulesetError`` e o analisador não fica pronto (fail-fast).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .schema import (
    _RULE_ID,
    QUESTION_ID,
    Condition,
    Effect,
    MetaKind,
    MetaRule,
    Question,
    Requirement,
    Rule,
    Ruleset,
)


@dataclass(frozen=True, slots=True)
class CompiledQuestion:
    question: Question
    #: Fato liberado -> condições (``None`` = sempre); a liberação vale se uma delas valer.
    allowed: Mapping[str, tuple[Condition | None, ...]]
    #: Fato proibido -> a regra (R-xx) que o enunciado proíbe, ou ``None`` se foi o fato.
    denied: Mapping[str, str | None]
    #: Proibições gerais (R-05 a R-14) que a questão libera: exigem professor (C-02, FR-21).
    releases: tuple[str, ...]

    @property
    def id(self) -> str:
        return self.question.question_id


def compile_question(question: Question, ruleset: Ruleset) -> CompiledQuestion:
    """Confere a questão contra o catálogo e monta os índices. Erros viram ``ValueError``."""
    rules = {rule.id: rule for rule in ruleset.rules}
    other_ids = {meta.id for meta in ruleset.meta_rules} | {r.id for r in ruleset.requirements}
    structural = set(ruleset.structural_facts)

    def rule(rule_id: str, field: str) -> Rule:
        if rule_id in other_ids:
            raise ValueError(
                f"{field}: {rule_id} não é uma regra de permissão (meta-regra ou exigência); "
                "uma questão não altera R-01 a R-04, R-02 nem R-68"
            )
        if rule_id not in rules:
            raise ValueError(f"{field}: {rule_id} não existe no catálogo")
        return rules[rule_id]

    allowed: dict[str, list[Condition | None]] = {}
    releases: list[str] = []
    for rule_id in question.allow:
        found = rule(rule_id, "allow")
        if found.effect is Effect.DENY:
            releases.append(rule_id)
        for fact, condition in found.matches():
            allowed.setdefault(fact, []).append(condition)
    general = {fact: r.id for r in ruleset.rules if r.effect is Effect.DENY for fact in r.facts}
    for fact in question.allow_facts:
        if fact in structural:
            raise ValueError(f"allow_facts: {fact} é estrutural e já é sempre aceito")
        allowed.setdefault(fact, []).append(None)
        if fact in general and general[fact] not in releases:
            releases.append(general[fact])

    denied: dict[str, str | None] = {}
    for item in question.deny:
        if _RULE_ID.fullmatch(item):
            found = rule(item, "deny")
            if found.effect is Effect.DENY:
                raise ValueError(f"deny: {item} já é proibida em todas as listas")
            for fact in found.facts:
                denied.setdefault(fact, item)
        elif item in structural:
            raise ValueError(f"deny: {item} é estrutural e não pode ser proibido sozinho")
        else:
            denied[item] = None
    if overlap := sorted(set(allowed) & set(denied)):
        raise ValueError(f"fatos liberados e proibidos ao mesmo tempo: {overlap}")
    return CompiledQuestion(
        question=question,
        allowed=MappingProxyType({fact: tuple(conds) for fact, conds in allowed.items()}),
        denied=MappingProxyType(denied),
        releases=tuple(sorted(releases)),
    )


# ---------------------------------------------------------------------------
# Ruleset compilado: imutável e indexado por fato.
# ---------------------------------------------------------------------------


class RulesetError(Exception):
    """Ruleset inválido ou ilegível: o analisador não deve ficar pronto (fail-fast)."""


@dataclass(frozen=True, slots=True)
class RuleMatch:
    """Uma regra que casa um fato, com a condição daquele fato (``None`` = casa sempre)."""

    rule: Rule
    condition: Condition | None


@dataclass(frozen=True, slots=True)
class Reference:
    """Uma solução de referência para uma questão, gerada pela equipe com uma IA a partir só do
    enunciado (ADR-08, item 2). ``label`` é o nome do arquivo, sem a extensão (``assistente-a``).
    """

    question_id: str
    label: str
    source: str


@dataclass(frozen=True, slots=True)
class CompiledRuleset:
    ruleset: Ruleset
    sha256: str
    by_fact: Mapping[str, tuple[RuleMatch, ...]]
    structural_facts: frozenset[str]
    #: Regras por questão do período (R-01), por ``question_id``.
    questions: Mapping[str, CompiledQuestion] = MappingProxyType({})
    #: Soluções de referência geradas por IA, por ``question_id`` (ADR-08, sinal 2; S29-02).
    references: Mapping[str, tuple[Reference, ...]] = MappingProxyType({})

    @property
    def version(self) -> str:
        return self.ruleset.ruleset_version

    @property
    def target_version(self) -> tuple[int, int]:
        """Versão do Python cuja gramática o parser usa, ex.: (3, 13) (NFR-21)."""
        major, minor = self.ruleset.target_python.split(".")
        return int(major), int(minor)

    @property
    def default_deny(self) -> MetaRule:
        return next(m for m in self.ruleset.meta_rules if m.kind is MetaKind.DEFAULT_DENY)

    def matches_for(self, fact: str) -> tuple[RuleMatch, ...]:
        return self.by_fact.get(fact, ())

    def rules_for(self, fact: str) -> tuple[Rule, ...]:
        return tuple(match.rule for match in self.matches_for(fact))

    def is_structural(self, fact: str) -> bool:
        return fact in self.structural_facts

    def questions_for(self, list_number: int) -> tuple[CompiledQuestion, ...]:
        """As questões cadastradas da lista, em ordem (L3-Q2 antes de L3-Q10)."""
        found = (q for q in self.questions.values() if q.question.list_number == list_number)
        return tuple(sorted(found, key=lambda q: _question_order(q.id)))

    def requirements_for(self, list_number: int) -> tuple[Requirement, ...]:
        """Exigências da lista: R-02 (assunto da lista) e, na Lista 6, R-68 (recursão)."""
        return tuple(req for req in self.ruleset.requirements if req.list_number == list_number)


def _question_order(question_id: str) -> tuple[int, int]:
    match = QUESTION_ID.fullmatch(question_id)
    assert match is not None  # noqa: S101 - garantido pela validação do modelo
    return int(match.group(1)), int(match.group(2))


def compile_ruleset(
    ruleset: Ruleset, raw: bytes, questions: Iterable[CompiledQuestion] = ()
) -> CompiledRuleset:
    index: dict[str, list[RuleMatch]] = {}
    for rule in ruleset.rules:
        for fact, condition in rule.matches():
            index.setdefault(fact, []).append(RuleMatch(rule=rule, condition=condition))
    return CompiledRuleset(
        ruleset=ruleset,
        sha256=hashlib.sha256(raw).hexdigest(),
        by_fact=MappingProxyType({fact: tuple(matches) for fact, matches in index.items()}),
        structural_facts=frozenset(ruleset.structural_facts),
        questions=MappingProxyType({question.id: question for question in questions}),
    )

"""Modelo, validação e carga do ruleset (ADR-02, FR-15).

As regras do catálogo R-xx são dados (``rulesets/<período>/base.yaml``), não código.
Este pacote só valida o arquivo e monta um índice imutável ``fato -> regras``.
Um ruleset inválido levanta ``RulesetError`` e o analisador não fica pronto (fail-fast).

Desde a S39-02, em três módulos: ``schema`` (a forma dos dados e a validação), ``compile`` (o
índice e as questões compiladas) e ``load`` (o período ativo e a leitura do disco). Os nomes
continuam importados daqui, como antes.
"""

from __future__ import annotations

from .compile import (
    CompiledQuestion,
    CompiledRuleset,
    Reference,
    RuleMatch,
    RulesetError,
    compile_question,
    compile_ruleset,
)
from .load import (
    ACTIVE_FILE,
    BASE_FILE,
    MAX_REFERENCES_PER_QUESTION,
    PERIOD,
    QUESTIONS_DIR,
    REFERENCES_DIR,
    RETIRED_DIR,
    WINDOW,
    LoadedRulesets,
    UnknownPeriod,
    active_period,
    load_ruleset,
    load_rulesets,
    resolve_ruleset_path,
)
from .schema import (
    KNOWN_PREDICATES,
    QUESTION_ID,
    Category,
    Condition,
    ConditionalFact,
    Effect,
    Fact,
    ListNumber,
    Message,
    MetaKind,
    MetaRule,
    Question,
    QuestionId,
    Requirement,
    Rule,
    RuleId,
    RuleOrFact,
    Ruleset,
    Text,
    is_valid_fact,
)

__all__ = [
    "ACTIVE_FILE",
    "BASE_FILE",
    "KNOWN_PREDICATES",
    "MAX_REFERENCES_PER_QUESTION",
    "PERIOD",
    "QUESTIONS_DIR",
    "QUESTION_ID",
    "REFERENCES_DIR",
    "RETIRED_DIR",
    "WINDOW",
    "Category",
    "CompiledQuestion",
    "CompiledRuleset",
    "Condition",
    "ConditionalFact",
    "Effect",
    "Fact",
    "ListNumber",
    "LoadedRulesets",
    "Message",
    "MetaKind",
    "MetaRule",
    "Question",
    "QuestionId",
    "Reference",
    "Requirement",
    "Rule",
    "RuleId",
    "RuleMatch",
    "RuleOrFact",
    "Ruleset",
    "RulesetError",
    "Text",
    "UnknownPeriod",
    "active_period",
    "compile_question",
    "compile_ruleset",
    "is_valid_fact",
    "load_ruleset",
    "load_rulesets",
    "resolve_ruleset_path",
]

"""Modelo, validação e carga do ruleset (ADR-02, FR-15).

As regras do catálogo R-xx são dados (``rulesets/<período>/base.yaml``), não código.
Este módulo só valida o arquivo e monta um índice imutável ``fato -> regras``.
Um ruleset inválido levanta ``RulesetError`` e o analisador não fica pronto (fail-fast).
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import re
import string
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal, Self

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Vocabulário de fatos (5.2.3): "<tipo>:<nome>", por exemplo "node:For" ou "kwarg:print.end".
# ---------------------------------------------------------------------------

# Nomes seguem as regras de identificador do Python, inclusive com acentos (ex.: method:média).
_FACT_RE = re.compile(r"(?P<kind>[a-z]+):(?P<name>\*\*|[^\W\d]\w*(?:\.[^\W\d]\w*)?)")

# Classes abstratas do módulo ast: nunca aparecem como nó concreto na árvore.
_ABSTRACT_NODES = frozenset(
    {
        "AST",
        "mod",
        "stmt",
        "expr",
        "expr_context",
        "boolop",
        "operator",
        "unaryop",
        "cmpop",
        "excepthandler",
        "pattern",
        "type_ignore",
        "type_param",
    }
)

# Classes antigas, mantidas só por compatibilidade; o parser do Python 3.13 não as gera.
_DEPRECATED_NODES = frozenset(
    {
        "Num",
        "Str",
        "Bytes",
        "NameConstant",
        "Ellipsis",
        "Index",
        "ExtSlice",
        "Suite",
        "AugLoad",
        "AugStore",
        "Param",
        "slice",
    }
)

_OPERATOR_BASES: tuple[type[ast.AST], ...] = (ast.operator, ast.unaryop, ast.boolop)
_CONST_TYPES = frozenset({"None", "bool", "int", "float", "complex", "str", "bytes", "Ellipsis"})


def _ast_class(name: str) -> type[ast.AST] | None:
    if name in _ABSTRACT_NODES or name in _DEPRECATED_NODES:
        return None
    cls = getattr(ast, name, None)
    if isinstance(cls, type) and issubclass(cls, ast.AST):
        return cls
    return None


def _is_node(name: str) -> bool:
    cls = _ast_class(name)
    return cls is not None and not issubclass(cls, (*_OPERATOR_BASES, ast.cmpop))


def _is_operator(name: str) -> bool:
    cls = _ast_class(name)
    return cls is not None and issubclass(cls, _OPERATOR_BASES)


def _is_comparison(name: str) -> bool:
    cls = _ast_class(name)
    return cls is not None and issubclass(cls, ast.cmpop)


_FACT_CHECKS: Mapping[str, Callable[[str], bool]] = MappingProxyType(
    {
        "node": _is_node,
        "op": _is_operator,
        "cmp": _is_comparison,
        "builtin": lambda name: "." not in name and hasattr(builtins, name),
        "method": lambda name: "." not in name and name != "**",
        "kwarg": lambda name: name == "**" or name.count(".") == 1,
        "const": lambda name: name in _CONST_TYPES,
        "param": lambda name: name in {"vararg", "kwarg", "default", "kwonly", "posonly"},
        "call": lambda name: name in {"user", "user_kwarg", "star_args"},
        "return": lambda name: name == "multi",
        "target": lambda name: name == "for_unpack",
        "derived": lambda name: (
            name in {"recursion", "loop_else", "decorator", "dict_unpack", "nested_function"}
        ),
    }
)


def _validate_fact(value: str) -> str:
    match = _FACT_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"fato malformado {value!r}: use '<tipo>:<nome>', por exemplo 'node:For'")
    check = _FACT_CHECKS.get(match["kind"])
    if check is None:
        kinds = ", ".join(sorted(_FACT_CHECKS))
        raise ValueError(f"tipo de fato desconhecido em {value!r}; tipos válidos: {kinds}")
    if not check(match["name"]):
        raise ValueError(f"fato inexistente {value!r}")
    return value


def is_valid_fact(value: str) -> bool:
    """Indica se o fato pertence ao vocabulário que as regras podem casar."""
    try:
        _validate_fact(value)
    except ValueError:
        return False
    return True


_PLACEHOLDERS = frozenset({"allowed_from_list", "construct"})


def _validate_message(value: str) -> str:
    for _, field_name, _, _ in string.Formatter().parse(value):
        if field_name is not None and field_name not in _PLACEHOLDERS:
            allowed = ", ".join(sorted(_PLACEHOLDERS))
            raise ValueError(
                f"marcador desconhecido {{{field_name}}} na mensagem; permitidos: {allowed}"
            )
    return value


#: Predicados contextuais implementados pelo motor (``engine/conditions.py``) e os parâmetros
#: que cada um aceita. Um predicado novo exige código e ADR (5.2.3).
_PREDICATE_PARAMS: Mapping[str, frozenset[str]] = MappingProxyType(
    {"call_args": frozenset({"min", "max"}), "zip_in_for_header": frozenset({"min"})}
)
KNOWN_PREDICATES: frozenset[str] = frozenset(_PREDICATE_PARAMS)

Fact = Annotated[str, AfterValidator(_validate_fact)]
RuleId = Annotated[str, StringConstraints(pattern=r"^R-\d{2}$")]
ListNumber = Annotated[int, Field(ge=1, le=6)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Message = Annotated[Text, AfterValidator(_validate_message)]


class Effect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class Category(StrEnum):
    """Categorias de violação devolvidas ao aluno (FR-12)."""

    ANULACAO = "ANULACAO"
    PROIBIDO_NA_QUESTAO = "PROIBIDO_NA_QUESTAO"
    FORA_DA_LISTA = "FORA_DA_LISTA"
    NAO_CONSTA = "NAO_CONSTA"
    EXIGENCIA = "EXIGENCIA"


class MetaKind(StrEnum):
    """Regras do catálogo que são semântica do motor, e não casamento de fatos."""

    QUESTION_PRECEDENCE = "question_precedence"  # R-01
    TOPIC_REQUIREMENT = "topic_requirement"  # R-02
    CUMULATIVE = "cumulative"  # R-03
    DEFAULT_DENY = "default_deny"  # R-04


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Condition(_Frozen):
    """Predicado contextual de um fato (ex.: ``type()`` com 3 argumentos cria classe, R-09)."""

    predicate: str
    params: dict[str, int] = Field(default_factory=dict)
    #: Mensagem mostrada quando a regra vale na lista, mas a condição não é atendida.
    message: Message | None = None

    @field_validator("predicate")
    @classmethod
    def _known_predicate(cls, value: str) -> str:
        if value not in KNOWN_PREDICATES:
            raise ValueError(f"predicado desconhecido {value!r}")
        return value

    @model_validator(mode="after")
    def _check_params(self) -> Self:
        if unknown := sorted(set(self.params) - _PREDICATE_PARAMS[self.predicate]):
            raise ValueError(f"parâmetro desconhecido para {self.predicate}: {unknown}")
        if self.predicate == "call_args":
            low, high = self.params.get("min"), self.params.get("max")
            if low is None and high is None:
                raise ValueError("call_args precisa de min ou max")
            if low is not None and high is not None and low > high:
                raise ValueError("call_args: min não pode ser maior que max")
        if self.predicate == "zip_in_for_header" and self.params.get("min", 0) < 1:
            raise ValueError("zip_in_for_header precisa de min maior ou igual a 1")
        return self


class ConditionalFact(_Frozen):
    """Fato que só casa com a regra quando a condição é verdadeira."""

    fact: Fact
    when: Condition


class Rule(_Frozen):
    """Regra do catálogo que casa fatos: proibição geral (deny) ou permissão cumulativa (allow)."""

    id: RuleId
    name: Text
    effect: Effect
    category: Category | None = None
    since_list: ListNumber | None = None
    until_list: ListNumber | None = None
    match: tuple[Fact | ConditionalFact, ...] = Field(min_length=1)
    message: Message
    source: Text

    def matches(self) -> tuple[tuple[str, Condition | None], ...]:
        """Pares (fato, condição); a condição é ``None`` quando o fato casa sempre."""
        return tuple(
            (item.fact, item.when) if isinstance(item, ConditionalFact) else (item, None)
            for item in self.match
        )

    @property
    def facts(self) -> tuple[str, ...]:
        return tuple(fact for fact, _ in self.matches())

    def unconditional_facts(self) -> set[str]:
        return {fact for fact, condition in self.matches() if condition is None}

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.effect is Effect.DENY:
            if self.category is not Category.ANULACAO:
                raise ValueError("regra 'deny' (proibição geral) deve ter category ANULACAO")
            if self.since_list is not None or self.until_list is not None:
                raise ValueError(
                    "regra 'deny' vale em todas as listas e não aceita since/until_list"
                )
        else:
            if self.category is not None:
                raise ValueError("regra 'allow' não tem category: quem decide é o motor")
            if self.since_list is None:
                raise ValueError("regra 'allow' precisa de since_list")
            if self.until_list is not None and self.until_list < self.since_list:
                raise ValueError("until_list não pode ser menor que since_list")
        if _duplicates(self.facts):
            raise ValueError(f"fato repetido em match: {_duplicates(self.facts)}")
        return self


class MetaRule(_Frozen):
    id: RuleId
    kind: MetaKind
    message: Message | None = None
    source: Text


class Requirement(_Frozen):
    """Exigência de construção numa lista (R-02 e R-68)."""

    id: RuleId
    list_number: ListNumber = Field(alias="list")
    require_any: tuple[Fact, ...] = Field(min_length=1)
    message: Message
    source: Text


class Ruleset(_Frozen):
    schema_version: Literal[2]
    ruleset_version: Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]\.\d+$")]
    period: Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]$")]
    source_document: Text
    target_python: Annotated[str, StringConstraints(pattern=r"^3\.\d{1,2}$")]
    lists: dict[ListNumber, Text]
    structural_facts: tuple[Fact, ...]
    meta_rules: tuple[MetaRule, ...]
    rules: tuple[Rule, ...] = Field(min_length=1)
    requirements: tuple[Requirement, ...] = ()

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if not self.ruleset_version.startswith(f"{self.period}."):
            raise ValueError("ruleset_version deve começar pelo período, por exemplo 2026.2.0")
        if set(self.lists) != set(range(1, 7)):
            raise ValueError("lists deve descrever exatamente as Listas 1 a 6")

        rule_ids = [rule.id for rule in self.rules]
        meta_ids = [meta.id for meta in self.meta_rules]
        if _duplicates(rule_ids):
            raise ValueError(f"id de regra repetido: {_duplicates(rule_ids)}")
        if _duplicates(meta_ids):
            raise ValueError(f"id de meta-regra repetido: {_duplicates(meta_ids)}")
        if clash := sorted(set(rule_ids) & set(meta_ids)):
            raise ValueError(f"id usado como regra e como meta-regra: {clash}")
        if clash := sorted({req.id for req in self.requirements} & set(rule_ids)):
            raise ValueError(f"id usado como regra e como exigência: {clash}")
        if repeated := _duplicates((req.id, req.list_number) for req in self.requirements):
            raise ValueError(f"exigência repetida na mesma lista: {repeated}")
        if _duplicates(meta.kind for meta in self.meta_rules):
            raise ValueError("cada tipo de meta-regra só pode aparecer uma vez")
        default_deny = [m for m in self.meta_rules if m.kind is MetaKind.DEFAULT_DENY]
        if not default_deny or default_deny[0].message is None:
            raise ValueError("é obrigatória a meta-regra default_deny (R-04) com mensagem")

        if _duplicates(self.structural_facts):
            raise ValueError(f"fato estrutural repetido: {_duplicates(self.structural_facts)}")
        structural = set(self.structural_facts)
        for rule in self.rules:
            if overlap := sorted(structural.intersection(rule.facts)):
                raise ValueError(f"{rule.id}: fato estrutural não pode estar numa regra: {overlap}")

        allowed: set[str] = set()
        denied: set[str] = set()
        for rule in self.rules:
            target = allowed if rule.effect is Effect.ALLOW else denied
            target.update(rule.unconditional_facts())
        if conflict := sorted(allowed & denied):
            raise ValueError(
                f"fatos permitidos e proibidos ao mesmo tempo, sem condição: {conflict}"
            )
        return self


def _duplicates(values: Iterable[object]) -> list[str]:
    return sorted(str(value) for value, count in Counter(values).items() if count > 1)


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
class CompiledRuleset:
    ruleset: Ruleset
    sha256: str
    by_fact: Mapping[str, tuple[RuleMatch, ...]]
    structural_facts: frozenset[str]

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

    def requirements_for(self, list_number: int) -> tuple[Requirement, ...]:
        """Exigências da lista: R-02 (assunto da lista) e, na Lista 6, R-68 (recursão)."""
        return tuple(req for req in self.ruleset.requirements if req.list_number == list_number)


def compile_ruleset(ruleset: Ruleset, raw: bytes) -> CompiledRuleset:
    index: dict[str, list[RuleMatch]] = {}
    for rule in ruleset.rules:
        for fact, condition in rule.matches():
            index.setdefault(fact, []).append(RuleMatch(rule=rule, condition=condition))
    return CompiledRuleset(
        ruleset=ruleset,
        sha256=hashlib.sha256(raw).hexdigest(),
        by_fact=MappingProxyType({fact: tuple(matches) for fact, matches in index.items()}),
        structural_facts=frozenset(ruleset.structural_facts),
    )


def load_ruleset(path: Path) -> CompiledRuleset:
    """Lê, valida e compila o ruleset. Qualquer problema vira ``RulesetError``."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RulesetError(f"não foi possível ler o ruleset {path}: {exc}") from exc
    try:
        # safe_load: o YAML nunca constrói objetos Python arbitrários.
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise RulesetError(f"YAML inválido em {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RulesetError(f"o ruleset {path} deve ser um mapeamento YAML no nível raiz")
    try:
        ruleset = Ruleset.model_validate(data)
    except ValidationError as exc:
        raise RulesetError(_describe(exc, path)) from exc
    return compile_ruleset(ruleset, raw)


def _describe(exc: ValidationError, path: Path) -> str:
    lines = [f"ruleset inválido: {path}"]
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<raiz>"
        lines.append(f"  - {location}: {error['msg']}")
    return "\n".join(lines)

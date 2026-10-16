"""O esquema do ruleset (ADR-02, FR-15): os fatos, as regras, as exigências e as questões.

Só a forma e a validação dos dados de ``rulesets/<período>/``; a compilação está em ``compile``, e a
carga do disco, em ``load`` (S39-02).
"""

from __future__ import annotations

import ast
import builtins
import re
import string
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ipc_analyzer.engine.predicates import REGISTRY

# ---------------------------------------------------------------------------
# Vocabulário de fatos (5.2.3): "<tipo>:<nome>", por exemplo "node:For" ou "kwarg:print.end".
# ---------------------------------------------------------------------------

# Nomes seguem as regras de identificador do Python, inclusive com acentos (ex.: method:média).
_FACT_RE = re.compile(r"(?P<kind>[a-z]+):(?P<name>\*\*|[^\W\d]\w*(?:\.(?:[^\W\d]\w*|\*))?)")

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


#: Predicados contextuais e os parâmetros de cada um, do registro único (``engine/predicates.py``).
#: Um predicado novo exige código e ADR (5.2.3).
_PREDICATE_PARAMS: Mapping[str, frozenset[str]] = MappingProxyType(
    {name: predicate.params for name, predicate in REGISTRY.items()}
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
    #: Por que a construção é proibida ou ainda não vale, e o que usar no lugar (S38-01). Saem do
    #: documento de permissões, sem criar regra, e quem revisa é a chefia ou o desenvolvedor (Q-31).
    explicacao: Text
    alternativa: Text
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
    #: Só a R-04 gera violação: ela precisa dos dois textos (S38-01).
    explicacao: Text | None = None
    alternativa: Text | None = None
    source: Text


class Requirement(_Frozen):
    """Exigência de construção numa lista (R-02 e R-68)."""

    id: RuleId
    list_number: ListNumber = Field(alias="list")
    require_any: tuple[Fact, ...] = Field(min_length=1)
    message: Message
    explicacao: Text
    alternativa: Text
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
        # Um id só é regra e exigência ao mesmo tempo quando o catálogo diz "permitido e
        # obrigatório" numa lista: a regra é uma permissão que começa exatamente na lista da
        # exigência (R-68, a recursão da Lista 6, Q-33).
        required_in: dict[str, set[int]] = {}
        for req in self.requirements:
            required_in.setdefault(req.id, set()).add(req.list_number)
        if clash := sorted(
            rule.id
            for rule in self.rules
            if rule.id in required_in
            and not (rule.effect is Effect.ALLOW and {rule.since_list} == required_in[rule.id])
        ):
            raise ValueError(f"id usado como regra e como exigência: {clash}")
        if repeated := _duplicates((req.id, req.list_number) for req in self.requirements):
            raise ValueError(f"exigência repetida na mesma lista: {repeated}")
        if _duplicates(meta.kind for meta in self.meta_rules):
            raise ValueError("cada tipo de meta-regra só pode aparecer uma vez")
        default_deny = [m for m in self.meta_rules if m.kind is MetaKind.DEFAULT_DENY]
        if not default_deny or default_deny[0].message is None:
            raise ValueError("é obrigatória a meta-regra default_deny (R-04) com mensagem")
        if default_deny[0].explicacao is None or default_deny[0].alternativa is None:
            raise ValueError("a meta-regra default_deny (R-04) precisa de explicacao e alternativa")

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
# Regras por questão (R-01, FR-11): rulesets/<período>/questions/L<n>-Q<m>.yaml.
# ---------------------------------------------------------------------------

#: Numeração oficial das questões, que reinicia a cada período (P-07): ex. L3-Q2.
QUESTION_ID = re.compile(r"L([1-6])-Q([1-9]\d?)")
_RULE_ID = re.compile(r"R-\d{2}")

QuestionId = Annotated[str, StringConstraints(pattern=f"^{QUESTION_ID.pattern}$")]
_QUESTION_PLACEHOLDERS = frozenset({"construct", "question_id"})


def _validate_question_message(value: str) -> str:
    for _, field_name, _, _ in string.Formatter().parse(value):
        if field_name is not None and field_name not in _QUESTION_PLACEHOLDERS:
            allowed = ", ".join(sorted(_QUESTION_PLACEHOLDERS))
            raise ValueError(
                f"marcador desconhecido {{{field_name}}} na mensagem; permitidos: {allowed}"
            )
    return value


def _validate_rule_or_fact(value: str) -> str:
    return value if _RULE_ID.fullmatch(value) else _validate_fact(value)


RuleOrFact = Annotated[str, AfterValidator(_validate_rule_or_fact)]


class Question(_Frozen):
    """O que o enunciado de uma questão permite ou proíbe explicitamente (R-01, US-13).

    ``allow`` libera regras inteiras do catálogo (com as condições delas), mesmo antes da lista
    em que entram e mesmo as proibições gerais (C-02, só com aprovação de professor).
    ``allow_facts`` libera fatos que o documento de permissões não cita. ``deny`` proíbe regras
    ou fatos que a lista permitiria. ``source`` é o trecho do enunciado que justifica o cadastro.
    """

    question_id: QuestionId
    list_number: ListNumber = Field(alias="list")
    title: Annotated[Text, StringConstraints(max_length=80)]
    source: Text
    allow: tuple[RuleId, ...] = ()
    allow_facts: tuple[Fact, ...] = ()
    deny: tuple[RuleOrFact, ...] = ()
    #: Mensagem das violações por ``deny``; marcadores: {construct} e {question_id}.
    message: Annotated[Text, AfterValidator(_validate_question_message)] | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        match = QUESTION_ID.fullmatch(self.question_id)
        if match is not None and int(match.group(1)) != self.list_number:
            raise ValueError(
                f"{self.question_id} é da Lista {match.group(1)}, não da {self.list_number}"
            )
        if not (self.allow or self.allow_facts or self.deny):
            raise ValueError(
                "a questão precisa de pelo menos um item em allow, allow_facts ou deny"
            )
        for name, items in (
            ("allow", self.allow),
            ("allow_facts", self.allow_facts),
            ("deny", self.deny),
        ):
            if repeated := _duplicates(items):
                raise ValueError(f"item repetido em {name}: {repeated}")
        if overlap := sorted(set(self.allow + self.allow_facts) & set(self.deny)):
            raise ValueError(f"liberado e proibido ao mesmo tempo: {overlap}")
        return self

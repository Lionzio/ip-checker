"""Indícios de uso de IA, nunca veredito (ADR-08, Q-21; S29-01 e S29-02).

Três sinais explicáveis, cada um com o motivo e as linhas, para a equipe decidir com quem
conversar. Nada aqui diz que o código foi gerado por IA: a única confirmação é a conversa com o
aluno (ADR-08, item 4). Nada é guardado (item 6).

1. **Múltiplas violações** (pedido do autor, Q-21): o padrão das violações que o motor já achou,
   sem análise nova do código:

   - *variedade*: proibições gerais diferentes (R-05 a R-14) no mesmo código;
   - *repetição*: a mesma proibição geral várias vezes;
   - *salto de lista*: construções liberadas só duas ou mais listas depois da escolhida;
   - *fora do documento*: construções que o documento de permissões não cita (R-04).

2. **Semelhança com soluções de referência geradas por IA** para a questão (S29-02): o motor de
   plágio da ADR-07 compara a submissão com as referências de ``rulesets/<período>/referencias/``.

3. **Marcadores de estilo** (ADR-08, item 3): docstrings, anotações de tipo, ``if __name__``,
   identificadores e comentários em inglês. São fatos, sem faixa própria: alguns alunos escrevem
   assim por conta própria.

As faixas são valores iniciais [PREMISSA, ADR-08 item 1], a calibrar com soluções anteriores a 2023
(``ipc-rules calibrate``, S29-04): a meta é no máximo 5% delas com faixa alta.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Literal

from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.gabarito import GabaritoComparison
from ipc_analyzer.engine.guards import DEFAULT_LIMITS, InputError, Limits
from ipc_analyzer.engine.models import Violation
from ipc_analyzer.engine.parse import ParsedSource, SyntaxProblem
from ipc_analyzer.engine.ruleset import Category, CompiledRuleset, Reference
from ipc_analyzer.engine.similarity import Prepared, compare_prepared, prepare

Signal = Literal["multiplas_violacoes", "referencia_ia", "gabarito", "estilo"]
LevelName = Literal["baixo", "medio", "alto"]


class Level(IntEnum):
    """Faixa de um indício; a do conjunto é a maior delas."""

    BAIXO = 1
    MEDIO = 2
    ALTO = 3

    @property
    def label(self) -> LevelName:
        names: dict[Level, LevelName] = {
            Level.BAIXO: "baixo",
            Level.MEDIO: "medio",
            Level.ALTO: "alto",
        }
        return names[self]


@dataclass(frozen=True, slots=True)
class Indicator:
    signal: Signal
    #: O que foi observado: variedade, repeticao, salto_de_lista, fora_do_documento, referencia,
    #: docstring, anotacao_de_tipo, main_guard, identificadores_em_ingles, comentarios_em_ingles.
    kind: str
    #: ``None`` nos marcadores de estilo, que não pesam na faixa (ADR-08, item 3).
    level: Level | None
    #: Por que é um indício, em PT-BR, com as construções envolvidas.
    reason: str
    #: Linhas do código da submissão, a partir de 1, em ordem.
    lines: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Indicators:
    level: Level | None
    items: tuple[Indicator, ...]
    #: 2 ou 3 perguntas para a conversa com o aluno (ADR-08, item 4).
    questions: tuple[str, ...]


# --- Faixas iniciais [PREMISSA, ADR-08 item 1] --------------------------------------------------

#: Proibições gerais diferentes no mesmo código: 2 é médio, 3 ou mais é alto.
VARIETY_MEDIUM, VARIETY_HIGH = 2, 3
#: A mesma proibição geral: 2 vezes é baixo, 3 ou mais é alto.
REPEAT_LOW, REPEAT_HIGH = 2, 3
#: Salto de lista: a construção só é liberada pelo menos 2 listas depois da escolhida.
JUMP_MIN_DISTANCE = 2
#: Construções com salto: 1 é médio, 2 ou mais é alto.
JUMP_HIGH = 2
#: Construções fora do documento (R-04): 1 ou 2 é baixo, 3 ou mais é médio.
OUTSIDE_MEDIUM = 3
#: Semelhança com uma referência de IA, nas faixas do painel de plágio (FR-29).
REFERENCE_LEVELS = ((95.0, Level.ALTO), (90.0, Level.MEDIO), (80.0, Level.BAIXO))
#: Identificadores em inglês: pelo menos 2, e a maioria dos nomes do aluno.
ENGLISH_NAMES_MIN = 2

#: Proibições gerais da lista (R-05 a R-14): anulam a questão em todas as listas.
GENERAL_RULES = frozenset(f"R-{n:02d}" for n in range(5, 15))
DEFAULT_DENY_RULE = "R-04"
MAX_QUESTIONS = 3
#: Linhas por indício e construções citadas por motivo, para o motivo caber na tela e no
#: contrato da API.
MAX_LINES = 200
MAX_NAMED = 6

NOTICE = (
    "Indícios não são prova de uso de IA. Eles servem para decidir com quem conversar; a "
    "confirmação é sempre uma conversa em que o aluno explica ou modifica o próprio código."
)


def compute_indicators(
    parsed: ParsedSource,
    violations: Sequence[Violation],
    *,
    list_number: int,
    ruleset: CompiledRuleset,
    question_id: str | None = None,
    limits: Limits = DEFAULT_LIMITS,
    gabarito: GabaritoComparison | None = None,
) -> Indicators | None:
    """Os indícios de uma submissão já analisada; ``None`` quando não há nenhum."""
    items = [
        *_violation_signals(violations, list_number),
        *_reference_signal(parsed.source, ruleset, question_id, limits),
        *_gabarito_signal(gabarito, question_id),
        *_style_signals(parsed),
    ]
    if not items:
        return None
    items = [replace(item, lines=item.lines[:MAX_LINES]) for item in items]
    weighted = [item.level for item in items if item.level is not None]
    level = max(weighted) if weighted else None
    return Indicators(level=level, items=tuple(items), questions=_questions(items, violations))


# --- Sinal 1: múltiplas violações --------------------------------------------------------------


def _violation_signals(violations: Sequence[Violation], list_number: int) -> list[Indicator]:
    items: list[Indicator] = []
    general = [
        v for v in violations if v.category is Category.ANULACAO and v.rule_id in GENERAL_RULES
    ]
    # Por construção, e não por regra: break e continue são a mesma regra (R-11), mas duas coisas.
    by_construct: dict[str, list[Violation]] = {}
    for violation in general:
        by_construct.setdefault(violation.construct, []).append(violation)

    if len(by_construct) >= VARIETY_MEDIUM:
        names = _names(occurrences[0] for occurrences in by_construct.values())
        items.append(
            Indicator(
                signal="multiplas_violacoes",
                kind="variedade",
                level=Level.ALTO if len(by_construct) >= VARIETY_HIGH else Level.MEDIO,
                reason=(
                    f"{len(by_construct)} proibições gerais diferentes no mesmo código: {names}. "
                    "Cada uma anula a questão, e juntas são raras numa solução escrita para a "
                    "lista."
                ),
                lines=_lines(general),
            )
        )
    for occurrences in by_construct.values():
        if len(occurrences) >= REPEAT_LOW:
            name = describe(occurrences[0].construct)
            items.append(
                Indicator(
                    signal="multiplas_violacoes",
                    kind="repeticao",
                    level=Level.ALTO if len(occurrences) >= REPEAT_HIGH else Level.BAIXO,
                    reason=(
                        f"'{name}' aparece {len(occurrences)} vezes, e é proibido em todas as "
                        "listas."
                    ),
                    lines=_lines(occurrences),
                )
            )

    jumps = [
        v
        for v in violations
        if v.category is Category.FORA_DA_LISTA
        and v.allowed_from_list is not None
        and v.allowed_from_list - list_number >= JUMP_MIN_DISTANCE
    ]
    if jumps:
        farthest = max(v.allowed_from_list or 0 for v in jumps) - list_number
        described = _names(jumps, with_list=True)
        items.append(
            Indicator(
                signal="multiplas_violacoes",
                kind="salto_de_lista",
                level=Level.ALTO if len(_distinct(jumps)) >= JUMP_HIGH else Level.MEDIO,
                reason=(
                    f"Construções de listas bem posteriores numa solução da Lista {list_number}: "
                    f"{described}; o maior salto é de {farthest} listas."
                ),
                lines=_lines(jumps),
            )
        )

    outside = [v for v in violations if v.rule_id == DEFAULT_DENY_RULE]
    if outside:
        items.append(
            Indicator(
                signal="multiplas_violacoes",
                kind="fora_do_documento",
                level=Level.MEDIO if len(_distinct(outside)) >= OUTSIDE_MEDIUM else Level.BAIXO,
                reason=(
                    f"Construções que não constam no documento de permissões: {_names(outside)}."
                ),
                lines=_lines(outside),
            )
        )
    return items


def _distinct(violations: Iterable[Violation]) -> list[Violation]:
    seen: dict[str, Violation] = {}
    for violation in violations:
        seen.setdefault(violation.construct, violation)
    return list(seen.values())


def _names(violations: Iterable[Violation], *, with_list: bool = False) -> str:
    parts = []
    for violation in _distinct(violations):
        name = f"'{describe(violation.construct)}'"
        if with_list and violation.allowed_from_list is not None:
            name += f" (Lista {violation.allowed_from_list})"
        parts.append(name)
    if len(parts) > MAX_NAMED:
        parts = [*parts[: MAX_NAMED - 1], f"mais {len(parts) - MAX_NAMED + 1}"]
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " e " + parts[-1]


def _lines(violations: Iterable[Violation]) -> tuple[int, ...]:
    return tuple(sorted({violation.line for violation in violations}))


# --- Sinal 2: semelhança com referências de IA (S29-02) ----------------------------------------

#: Referências já preparadas, por questão, na memória do worker (o ruleset não muda em execução).
_PREPARED: dict[str, tuple[tuple[Reference, Prepared], ...]] = {}


def _prepared_references(
    ruleset: CompiledRuleset, question_id: str, limits: Limits
) -> tuple[tuple[Reference, Prepared], ...]:
    key = f"{ruleset.sha256}:{question_id}"
    cached = _PREPARED.get(key)
    if cached is None:
        pairs = []
        for reference in ruleset.references.get(question_id, ()):
            prepared = prepare(reference.source, target=ruleset.target_version, limits=limits)
            if isinstance(prepared, Prepared):  # o carregador já recusou referência inválida
                pairs.append((reference, prepared))
        cached = tuple(pairs)
        _PREPARED[key] = cached
    return cached


def _reference_signal(
    source: str, ruleset: CompiledRuleset, question_id: str | None, limits: Limits
) -> list[Indicator]:
    if question_id is None or question_id not in ruleset.references:
        return []
    references = _prepared_references(ruleset, question_id, limits)
    if not references:
        return []
    try:
        submission = prepare(source, target=ruleset.target_version, limits=limits)
    except InputError:
        return []
    if isinstance(submission, SyntaxProblem):
        return []
    best: tuple[float, Reference, tuple[int, ...]] | None = None
    for reference, prepared in references:
        result = compare_prepared(submission, prepared)
        lines = tuple(
            sorted({n for match in result.matches for n in range(match.a.first, match.a.last + 1)})
        )
        if best is None or result.percent > best[0]:
            best = (result.percent, reference, lines)
    if best is None:
        return []
    percent, reference, lines = best
    level = next((lvl for minimum, lvl in REFERENCE_LEVELS if percent >= minimum), None)
    if level is None:
        return []
    return [
        Indicator(
            signal="referencia_ia",
            kind="referencia",
            level=level,
            reason=(
                f"{_percent(percent)}% de semelhança com uma solução gerada por IA para a questão "
                f"{question_id} (referência '{reference.label}'), pelo motor do painel de plágio."
            ),
            lines=lines,
        )
    ]


def _gabarito_signal(
    comparison: GabaritoComparison | None, question_id: str | None
) -> list[Indicator]:
    """A semelhança com o gabarito oficial (ADR-11, item 4; S32-08), nas faixas da referência."""
    if comparison is None:
        return []
    level = next((lvl for minimum, lvl in REFERENCE_LEVELS if comparison.percent >= minimum), None)
    if level is None:
        return []
    lines = tuple(n for first, last in comparison.student_lines for n in range(first, last + 1))
    return [
        Indicator(
            signal="gabarito",
            kind="gabarito",
            level=level,
            reason=(
                f"{_percent(comparison.percent)}% de semelhança com o gabarito oficial "
                f"{f'da questão {question_id}' if question_id else 'da questão escolhida'}: a "
                "solução pode ter vindo de um gabarito que circula entre os alunos, ou de uma IA "
                "que chegou à mesma solução."
            ),
            lines=lines,
        )
    ]


def _percent(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


# --- Sinal 3: marcadores de estilo -------------------------------------------------------------

#: Palavras de programação em inglês que não existem em português [PREMISSA: lista inicial].
ENGLISH_WORDS = frozenset(
    [
        "add",
        "amount",
        "answer",
        "append",
        "array",
        "average",
        "avg",
        "calc",
        "calculate",
        "char",
        "chars",
        "check",
        "compute",
        "count",
        "counter",
        "current",
        "data",
        "digit",
        "digits",
        "element",
        "elements",
        "even",
        "factorial",
        "fib",
        "fibonacci",
        "find",
        "first",
        "flag",
        "found",
        "get",
        "grade",
        "grades",
        "greater",
        "helper",
        "index",
        "is",
        "item",
        "items",
        "key",
        "keys",
        "last",
        "left",
        "length",
        "line",
        "lines",
        "list",
        "lower",
        "main",
        "matrix",
        "message",
        "new",
        "next",
        "num",
        "number",
        "numbers",
        "odd",
        "old",
        "output",
        "previous",
        "price",
        "process",
        "result",
        "results",
        "reverse",
        "reversed",
        "right",
        "row",
        "rows",
        "score",
        "scores",
        "search",
        "second",
        "sorted",
        "square",
        "start",
        "step",
        "string",
        "swap",
        "temp",
        "text",
        "third",
        "upper",
        "user",
        "value",
        "values",
        "word",
        "words",
    ]
)
#: Palavras de comentário típicas do inglês e do português, para comparar as duas.
ENGLISH_COMMENT_WORDS = frozenset(
    [
        "the",
        "of",
        "and",
        "to",
        "is",
        "are",
        "this",
        "that",
        "with",
        "from",
        "for",
        "if",
        "else",
        "loop",
        "function",
        "return",
        "returns",
        "value",
        "values",
        "number",
        "numbers",
        "check",
        "calculate",
        "calculates",
        "get",
        "gets",
        "read",
        "reads",
        "print",
        "prints",
        "user",
        "input",
        "list",
        "each",
        "all",
        "store",
        "stores",
        "result",
        "sum",
        "count",
        "main",
    ]
)
PORTUGUESE_COMMENT_WORDS = frozenset(
    [
        "o",
        "a",
        "os",
        "as",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "que",
        "para",
        "com",
        "um",
        "uma",
        "se",
        "é",
        "não",
        "no",
        "na",
        "nos",
        "nas",
        "por",
        "cada",
        "todos",
        "valor",
        "número",
        "numero",
        "lista",
        "soma",
        "média",
        "media",
        "calcula",
        "verifica",
        "lê",
        "le",
        "imprime",
        "usuário",
        "usuario",
        "resultado",
    ]
)

_WORD = re.compile(r"[A-Za-zÀ-ÿ]+")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _style_signals(parsed: ParsedSource) -> list[Indicator]:
    tree = parsed.tree
    items: list[Indicator] = []

    docstrings = []
    annotations = []
    main_guard = []
    names: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.append(body[0].lineno)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.setdefault(node.name, node.lineno)
            if node.returns is not None:
                annotations.append(node.lineno)
        if isinstance(node, ast.arg):
            names.setdefault(node.arg, node.lineno)
            if node.annotation is not None:
                annotations.append(node.lineno)
        if isinstance(node, ast.AnnAssign):
            annotations.append(node.lineno)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.setdefault(node.id, node.lineno)
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            main_guard.append(node.lineno)

    if docstrings:
        items.append(
            Indicator(
                signal="estilo",
                kind="docstring",
                level=None,
                reason="Docstring (texto entre aspas triplas no início da função ou do programa), "
                "incomum nas soluções das listas.",
                lines=tuple(sorted(set(docstrings))),
            )
        )
    if annotations:
        items.append(
            Indicator(
                signal="estilo",
                kind="anotacao_de_tipo",
                level=None,
                reason=(
                    "Anotações de tipo (como 'x: int' ou '-> float'), que a disciplina não ensina."
                ),
                lines=tuple(sorted(set(annotations))),
            )
        )
    if main_guard:
        items.append(
            Indicator(
                signal="estilo",
                kind="main_guard",
                level=None,
                reason='if __name__ == "__main__", que a disciplina não ensina.',
                lines=tuple(main_guard),
            )
        )

    english = {name: line for name, line in names.items() if _is_english(name)}
    meaningful = [name for name in names if len(name) > 2]
    if len(english) >= ENGLISH_NAMES_MIN and len(english) * 2 > len(meaningful):
        shown = ", ".join(f"'{name}'" for name in list(english)[:5])
        items.append(
            Indicator(
                signal="estilo",
                kind="identificadores_em_ingles",
                level=None,
                reason=f"A maioria dos nomes está em inglês ({shown}) num curso em português.",
                lines=tuple(sorted(set(english.values()))),
            )
        )

    comments = _english_comments(parsed.source)
    if comments:
        items.append(
            Indicator(
                signal="estilo",
                kind="comentarios_em_ingles",
                level=None,
                reason="Comentários em inglês num curso em português.",
                lines=comments,
            )
        )
    return items


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare) or len(test.comparators) != 1:
        return False
    sides = [test.left, test.comparators[0]]
    has_name = any(isinstance(side, ast.Name) and side.id == "__name__" for side in sides)
    has_main = any(isinstance(side, ast.Constant) and side.value == "__main__" for side in sides)
    return has_name and has_main


def _is_english(name: str) -> bool:
    words = [word.lower() for word in _CAMEL.sub("_", name).split("_") if word]
    return any(word in ENGLISH_WORDS for word in words) and not any(
        word in PORTUGUESE_COMMENT_WORDS for word in words
    )


def _english_comments(source: str) -> tuple[int, ...]:
    lines: list[int] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return ()
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        words = Counter(word.lower() for word in _WORD.findall(token.string))
        english = sum(count for word, count in words.items() if word in ENGLISH_COMMENT_WORDS)
        portuguese = sum(count for word, count in words.items() if word in PORTUGUESE_COMMENT_WORDS)
        if english >= 2 and english > portuguese:
            lines.append(token.start[0])
    return tuple(lines)


# --- Perguntas para a conversa (ADR-08, item 4) ------------------------------------------------


def _questions(items: Sequence[Indicator], violations: Sequence[Violation]) -> tuple[str, ...]:
    questions: list[str] = []
    kinds = {item.kind: item for item in items}
    if "salto_de_lista" in kinds:
        item = kinds["salto_de_lista"]
        questions.append(
            f"Na linha {item.lines[0]}, você usou uma construção que a disciplina só apresenta "
            "mais adiante. Onde você aprendeu e por que escolheu usá-la aqui?"
        )
    general = next(
        (v for v in violations if v.category is Category.ANULACAO and v.rule_id in GENERAL_RULES),
        None,
    )
    if general is not None and ("variedade" in kinds or "repeticao" in kinds):
        questions.append(
            f"O que o '{describe(general.construct)}' da linha {general.line} faz? Como você "
            "escreveria esse trecho sem ele?"
        )
    if "referencia" in kinds:
        item = kinds["referencia"]
        span = f"linhas {item.lines[0]} a {item.lines[-1]}" if item.lines else "o código"
        questions.append(
            f"Explique, com as suas palavras, o que acontece nas {span}, e o que mudaria se a "
            "entrada fosse diferente."
        )
    if "comentarios_em_ingles" in kinds or "identificadores_em_ingles" in kinds:
        questions.append(
            "Por que os nomes ou os comentários estão em inglês? Você pode explicar o que cada um "
            "deles significa no programa?"
        )
    if "docstring" in kinds or "anotacao_de_tipo" in kinds or "main_guard" in kinds:
        questions.append(
            "Algumas partes do código usam recursos que a disciplina não ensina. Você pode "
            "explicar para que servem e como funcionam?"
        )
    if len(questions) < 2:
        questions.append(
            "Faça uma pequena mudança no programa (por exemplo, outro formato de saída) e explique "
            "o que precisou alterar."
        )
    return tuple(questions[:MAX_QUESTIONS])

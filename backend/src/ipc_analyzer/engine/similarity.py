"""Similaridade entre duas soluções (S17-01; FR-29, ADR-05, NFR-25), sem executar nada.

Os dois códigos passam pela mesma análise segura do motor (``parse.py``, com os limites de
``guards.py``) e são comparados por duas métricas:

- **A, tokens** (peso ``TOKEN_WEIGHT``): o ``tokenize`` gera os tokens; comentários, linhas em
  branco e espaços saem; o conteúdo das strings vira ``STR``; os nomes ligados pelo aluno
  (variáveis, funções, parâmetros e classes, coletados pelo ``symbols.py``) viram marcadores
  numerados por ordem de aparição. A numeração recomeça em cada comando do nível do módulo, para
  que reordenar funções ou blocos independentes não renumere os nomes de dentro deles. Built-ins,
  métodos, atributos e palavras-chave ficam como estão.
- **B, estrutura** (peso ``AST_WEIGHT``): a sequência dos tipos de nó da AST, sem nomes nem
  literais.

As duas sequências são separadas por comando do nível do módulo (uma função, um ``if``, uma
atribuição), e cada bloco vira *fingerprints* por *winnowing* (k-gramas de ``K`` itens e janela de
``WINDOW``, como no MOSS); um bloco menor que ``K`` vira um *fingerprint* só. A métrica é o
coeficiente de Dice entre as uniões dos dois lados. Como nenhum k-grama atravessa dois blocos e
conjuntos não têm ordem, reordenar funções ou blocos independentes não muda o resultado. Códigos
com menos de ``K`` itens no total são comparados diretamente, pela razão do ``difflib``.

Pesos, ``K`` e ``WINDOW`` foram calibrados no corpus de pares (``tests/similarity/``) e só mudam
junto com ele. A classificação pelas faixas do FR-29 fica na API.
"""

from __future__ import annotations

import ast
import hashlib
import io
import keyword
import tokenize
from bisect import bisect_right
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from ipc_analyzer.engine.guards import DEFAULT_LIMITS, AnalysisLimitError, InputError, Limits
from ipc_analyzer.engine.parse import ParsedSource, SyntaxProblem, parse_source
from ipc_analyzer.engine.symbols import collect_bindings

#: Pesos das métricas (ADR-05): a de tokens pesa mais, porque também capta a ordem dos operandos.
TOKEN_WEIGHT = 0.6
AST_WEIGHT = 0.4
#: Tamanho dos k-gramas e da janela do *winnowing* (MOSS).
K = 5
WINDOW = 4

_SKIPPED = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.TYPE_COMMENT,
    }
)
_STRING_PARTS = frozenset(
    {tokenize.STRING, tokenize.FSTRING_START, tokenize.FSTRING_MIDDLE, tokenize.FSTRING_END}
)
#: Contextos de carga e gravação não dizem nada sobre a estrutura.
_CONTEXTS = (ast.Load, ast.Store, ast.Del)


Blocks = tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class Normalized:
    #: Um bloco por comando do nível do módulo.
    tokens: Blocks
    nodes: Blocks


@dataclass(frozen=True, slots=True)
class Similarity:
    #: Porcentagem com uma casa decimal, de 0,0 a 100,0.
    percent: float
    token_score: float
    ast_score: float
    #: Quantos tokens normalizados cada código tem (a API avisa quando são poucos).
    token_counts: tuple[int, int]


@dataclass(frozen=True, slots=True)
class InvalidSide:
    """Um dos dois códigos não é Python válido: ``side`` é 1 ou 2."""

    side: int
    problem: SyntaxProblem


def compare_sources(
    first: str,
    second: str,
    *,
    target: tuple[int, int],
    limits: Limits = DEFAULT_LIMITS,
) -> Similarity | InvalidSide:
    """Compara dois códigos.

    Levanta os mesmos ``InputError`` da análise (FR-04), com a mensagem dizendo qual dos dois
    códigos (A ou B) foi recusado.
    """
    normalized: list[Normalized] = []
    for side, source in enumerate((first, second), start=1):
        try:
            result = parse_source(source, target=target, limits=limits)
            if isinstance(result, SyntaxProblem):
                return InvalidSide(side, result)
            normalized.append(normalize(result))
        except InputError as exc:
            raise type(exc)(f"Código {'AB'[side - 1]}: {exc.message}") from None
    left, right = normalized
    token_score = _similarity(left.tokens, right.tokens)
    ast_score = _similarity(left.nodes, right.nodes)
    percent = round(100 * (TOKEN_WEIGHT * token_score + AST_WEIGHT * ast_score), 1)
    return Similarity(
        percent=percent,
        token_score=token_score,
        ast_score=ast_score,
        token_counts=(_size(left.tokens), _size(right.tokens)),
    )


def normalize(parsed: ParsedSource) -> Normalized:
    tokens: dict[int, list[str]] = {}
    for block, text in _tokens(parsed):
        tokens.setdefault(block, []).append(text)
    return Normalized(
        tokens=tuple(tuple(items) for _, items in sorted(tokens.items())),
        nodes=tuple(tuple(_node_types(statement)) for statement in parsed.tree.body),
    )


def _size(blocks: Blocks) -> int:
    return sum(len(block) for block in blocks)


def _tokens(parsed: ParsedSource) -> Iterator[tuple[int, str]]:
    """Os tokens normalizados, cada um com o índice do comando do nível do módulo a que pertence."""
    bindings = collect_bindings(parsed.tree)
    student = set(bindings.module)
    for names in bindings.scopes.values():
        student.update(names)
    # Linha inicial de cada comando do nível do módulo: a numeração dos nomes recomeça neles.
    starts = [statement.lineno for statement in parsed.tree.body]
    block = -1
    markers: dict[str, str] = {}
    previous = ""
    readline = io.StringIO(parsed.source).readline
    try:
        for token in tokenize.generate_tokens(readline):
            if token.type in _SKIPPED:
                continue
            # O DEDENT que fecha um bloco vem na linha do comando seguinte; fica com o que fecha.
            if token.type != tokenize.DEDENT:
                current = bisect_right(starts, token.start[0]) - 1
                if current != block:
                    block, markers, previous = current, {}, ""
            if token.type in _STRING_PARTS:
                # Uma f-string vira várias partes; todas viram um único STR.
                if previous != "STR":
                    previous = "STR"
                    yield block, previous
                continue
            text = token.string
            if token.type == tokenize.NAME and text in student and not keyword.iskeyword(text):
                text = markers.setdefault(text, f"V{len(markers)}")
            elif token.type == tokenize.NEWLINE:
                text = "NEWLINE"
            elif token.type == tokenize.INDENT:
                text = "INDENT"
            elif token.type == tokenize.DEDENT:
                text = "DEDENT"
            previous = text
            yield block, text
    except (tokenize.TokenError, SyntaxError, RecursionError, MemoryError):
        # O código já passou pelo ast.parse; um tokenizador que ainda assim falhe é um limite.
        raise AnalysisLimitError("O código não pôde ser comparado.") from None


def _node_types(statement: ast.stmt) -> Iterator[str]:
    """Os tipos de nó em pré-ordem, com pilha explícita (sem recursão Python)."""
    stack: list[ast.AST] = [statement]
    while stack:
        node = stack.pop()
        if isinstance(node, _CONTEXTS):
            continue
        yield type(node).__name__
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _similarity(left: Blocks, right: Blocks) -> float:
    if _size(left) < K or _size(right) < K:
        flat_left = [item for block in left for item in block]
        flat_right = [item for block in right for item in block]
        if not flat_left and not flat_right:
            return 1.0
        return SequenceMatcher(None, flat_left, flat_right, autojunk=False).ratio()
    first = frozenset().union(*(_fingerprints(block) for block in left))
    second = frozenset().union(*(_fingerprints(block) for block in right))
    return 2 * len(first & second) / (len(first) + len(second))


def _fingerprints(items: Sequence[str]) -> frozenset[int]:
    """*Winnowing*: o menor hash de cada janela de ``WINDOW`` k-gramas seguidos."""
    if len(items) < K:
        # Um comando curto (``x = 1``) ainda conta, como um fingerprint só.
        return frozenset({_hash(items)}) if items else frozenset()
    hashes = [_hash(items[index : index + K]) for index in range(len(items) - K + 1)]
    if len(hashes) <= WINDOW:
        return frozenset(hashes)
    return frozenset(
        min(hashes[start : start + WINDOW]) for start in range(len(hashes) - WINDOW + 1)
    )


def _hash(gram: Sequence[str]) -> int:
    # blake2b em vez de hash(): estável entre processos e execuções.
    digest = hashlib.blake2b("\x1f".join(gram).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")

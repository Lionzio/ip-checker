"""Similaridade entre duas soluções (S17-01, S27-01; FR-29, ADR-05, ADR-07, NFR-25), sem executar
nada.

Desde a Sprint 27, a similaridade é o maior de três números: a métrica da ADR-05 (abaixo), o Dice
da árvore canonizada da ADR-07 (``similarity_tree.py``) e, quando o menor código tem pelo menos
``CONTAINMENT_MIN_RATIO`` do tamanho do maior, a contenção da árvore, que denuncia o enchimento
com código morto. A resposta traz os três e os trechos em comum. A comparação de uma solução com a
turma (``compare_many``) usa só a árvore, com o peso de cada subárvore pela raridade na turma.

Os dois códigos passam pela mesma análise segura do motor (``parse.py``, com os limites de
``guards.py``) e, na ADR-05, são comparados por duas métricas:

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
from ipc_analyzer.engine.similarity_tree import (
    Match,
    TreeFingerprint,
    TreeScores,
    class_idf,
    fingerprint,
    matches,
    scores,
)
from ipc_analyzer.engine.symbols import collect_bindings

#: Pesos das métricas (ADR-05): a de tokens pesa mais, porque também capta a ordem dos operandos.
TOKEN_WEIGHT = 0.6
AST_WEIGHT = 0.4
#: Tamanho dos k-gramas e da janela do *winnowing* (MOSS).
K = 5
WINDOW = 4
#: A contenção só conta quando o menor código tem pelo menos esta fração do maior: um código de
#: três linhas sempre "cabe" num programa grande.
CONTAINMENT_MIN_RATIO = 0.25

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
    #: Porcentagem com uma casa decimal, de 0,0 a 100,0: a maior das métricas abaixo.
    percent: float
    token_score: float
    ast_score: float
    #: Quantos tokens normalizados cada código tem (a API avisa quando são poucos).
    token_counts: tuple[int, int]
    #: ADR-05: a combinação de tokens e estrutura, de 0 a 1.
    sequence_score: float
    #: ADR-07: Dice e contenção da árvore canonizada, de 0 a 1.
    tree: TreeScores
    #: Os trechos em comum, na ordem do código A (S27-03).
    matches: tuple[Match, ...]


@dataclass(frozen=True, slots=True)
class Prepared:
    """Um código pronto para comparar: as duas representações e o tamanho."""

    normalized: Normalized
    tree: TreeFingerprint

    @property
    def tokens(self) -> int:
        return _size(self.normalized.tokens)

    @property
    def weight(self) -> int:
        return sum(self.tree.weights.values())


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
    prepared: list[Prepared] = []
    for side, source in enumerate((first, second), start=1):
        try:
            result = prepare(source, target=target, limits=limits)
        except InputError as exc:
            raise type(exc)(f"Código {'AB'[side - 1]}: {exc.message}") from None
        if isinstance(result, SyntaxProblem):
            return InvalidSide(side, result)
        prepared.append(result)
    left, right = prepared
    token_score = _similarity(left.normalized.tokens, right.normalized.tokens)
    ast_score = _similarity(left.normalized.nodes, right.normalized.nodes)
    sequence = TOKEN_WEIGHT * token_score + AST_WEIGHT * ast_score
    tree = scores(left.tree, right.tree)
    return Similarity(
        percent=round(100 * max(sequence, _tree_score(left, right, tree)), 1),
        token_score=token_score,
        ast_score=ast_score,
        token_counts=(left.tokens, right.tokens),
        sequence_score=sequence,
        tree=tree,
        matches=tuple(matches(left.tree, right.tree)),
    )


def prepare(
    source: str, *, target: tuple[int, int], limits: Limits = DEFAULT_LIMITS
) -> Prepared | SyntaxProblem:
    """Analisa um código como o motor e monta as duas representações (a da ADR-05 primeiro: a da
    ADR-07 altera a árvore)."""
    result = parse_source(source, target=target, limits=limits)
    if isinstance(result, SyntaxProblem):
        return result
    normalized = normalize(result)
    return Prepared(normalized=normalized, tree=fingerprint(result.tree))


def _tree_score(left: Prepared, right: Prepared, tree: TreeScores) -> float:
    """O Dice da árvore, ou a contenção, quando os tamanhos são comparáveis."""
    sizes = sorted((left.weight, right.weight))
    comparable = sizes[1] == 0 or sizes[0] / sizes[1] >= CONTAINMENT_MIN_RATIO
    return max(tree.dice, tree.containment) if comparable else tree.dice


#: Quantas soluções da turma uma comparação aceita (S27-02).
MAX_CLASS = 100


@dataclass(frozen=True, slots=True)
class ClassRejected:
    """Uma solução da turma recusada pelos limites da análise (tamanho, linhas, complexidade)."""

    message: str


def compare_class(
    target_code: str,
    others: Sequence[str],
    *,
    target: tuple[int, int],
    limits: Limits = DEFAULT_LIMITS,
) -> SyntaxProblem | list[ClassMatch | SyntaxProblem | ClassRejected]:
    """Compara a solução de um aluno com as da turma (S27-02).

    Um erro de sintaxe na solução do aluno é a resposta inteira; nas da turma, só daquela. Os
    limites da análise valem para cada código: a solução do aluno recusada levanta o
    ``InputError``; uma da turma recusada vira ``ClassRejected``.
    """
    try:
        prepared = prepare(target_code, target=target, limits=limits)
    except InputError as exc:
        raise type(exc)(f"Solução comparada: {exc.message}") from None
    if isinstance(prepared, SyntaxProblem):
        return prepared
    class_items: list[Prepared | SyntaxProblem | ClassRejected] = []
    for source in others[:MAX_CLASS]:
        try:
            class_items.append(prepare(source, target=target, limits=limits))
        except InputError as exc:
            class_items.append(ClassRejected(exc.message))
    compared = iter(
        compare_many(
            prepared, [item for item in class_items if not isinstance(item, ClassRejected)]
        )
    )
    return [item if isinstance(item, ClassRejected) else next(compared) for item in class_items]


@dataclass(frozen=True, slots=True)
class ClassMatch:
    """Uma solução da turma comparada com a do aluno (S27-02)."""

    percent: float
    tree: TreeScores
    token_count: int


def compare_many(
    target_code: Prepared, others: Sequence[Prepared | SyntaxProblem]
) -> list[ClassMatch | SyntaxProblem]:
    """Compara uma solução com as da turma, com o peso de cada subárvore pelo IDF da turma.

    O que todas as soluções escrevem (a leitura da entrada, o laço óbvio) quase não conta; só a
    árvore entra, porque a métrica da ADR-05 não tem como pesar pela turma.
    """
    valid = [item for item in others if isinstance(item, Prepared)]
    idf = class_idf([target_code.tree, *(item.tree for item in valid)])
    results: list[ClassMatch | SyntaxProblem] = []
    for item in others:
        if isinstance(item, SyntaxProblem):
            results.append(item)
            continue
        tree = scores(target_code.tree, item.tree, idf)
        results.append(
            ClassMatch(
                percent=round(100 * _tree_score(target_code, item, tree), 1),
                tree=tree,
                token_count=item.tokens,
            )
        )
    return results


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

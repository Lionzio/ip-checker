"""Similaridade por árvore canonizada, insensível à ordem (S27-01; ADR-07, FR-29, NFR-25).

A árvore que o motor já analisa (``parse.py``, com os limites de ``guards.py``) passa por três
camadas, todas determinísticas e lineares no tamanho do código:

1. **Reescritas**, na própria árvore: ``x op= y`` vira ``x = x op y``; ``if not c`` e ``!=`` com
   ``else`` viram a forma positiva com os ramos trocados; ``if c: return X`` seguido do resto vira
   ``if c: return X`` / ``else: resto``; e os laços viram um laço genérico com o que eles
   percorrem: ``for x in v``, ``for i in range(len(v))`` com ``v[i]`` e ``while i < len(v)`` com
   ``v[i]`` e ``i += 1`` são o mesmo laço sobre ``v``; ``for i in range(n)`` e ``while i < n``,
   o mesmo laço até ``n``.
2. **Hash canônico** de cada subárvore, de baixo para cima (estilo Merkle): os nomes do aluno viram
   ``V`` (built-ins, atributos e palavras-chave ficam), o texto das strings vira ``STR``, e os
   operandos de ``+``, ``*``, ``and``, ``or``, ``==``, ``!=``, ``is`` ficam em ordem canônica;
   ``a > b`` é o mesmo que ``b < a``. Em cada bloco, comandos vizinhos sem dependência de dados
   entre si são ordenados pelo hash (ordenação topológica): trocar duas linhas independentes não
   muda nada. Entrada e saída (``input``, ``print`` e chamadas de funções do aluno) mantêm a ordem
   entre si, e ``return``, laços, ``break`` e ``try`` são barreiras.
3. **Multiconjunto** dos hashes de todas as subárvores com ``MIN_SUBTREE`` nós ou mais, cada uma
   pesada pelo tamanho (como no Deckard). Dele saem o **Dice** (a similaridade) e a **contenção**
   (quanto do menor código está no maior), que denuncia o enchimento com código morto. Com uma
   turma inteira, cada subárvore pesa também pelo inverso da frequência na turma (IDF): o que todos
   escrevem quase não conta (ameaça 20). Um comando com blocos (``if``, laço, ``def``, ``with``,
   ``try``) não entra inteiro: entram o **cabeçalho** dele (sem os blocos) e cada **comando de
   dentro**, junto com o cabeçalho e o bloco em que está; um bloco dentro de outro entra pelo
   cabeçalho. Assim, uma linha acrescentada dentro de um laço copiado só acrescenta, e não apaga o
   laço inteiro do multiconjunto (S35-07; antes, uma linha a mais no laço baixava a cópia a 83%).

Os trechos em comum (pares de intervalos de linhas) saem dos comandos com o mesmo hash nos dois
códigos, dos maiores para os menores, sem sobreposição.
"""

from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import heapq
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ipc_analyzer.engine.guards import AnalysisLimitError

#: Subárvores menores que isto (um nome, uma constante, um operador) não contam.
MIN_SUBTREE = 3
#: Um trecho em comum precisa ter pelo menos tantos nós para ser realçado.
MIN_MATCH = 6
#: No máximo tantos trechos em comum na resposta.
MAX_MATCHES = 30
#: Teto de nós visitados para achar dependências; acima dele, os blocos ficam na ordem original.
DEPENDENCY_BUDGET = 400_000

_BUILTINS = frozenset(dir(builtins))
#: Built-ins sem efeito colateral: chamá-los não impede reordenar o comando.
_PURE = frozenset(
    {
        "abs", "all", "any", "bin", "bool", "chr", "dict", "divmod", "enumerate", "float",
        "format", "frozenset", "hex", "int", "isinstance", "len", "list", "map", "max", "min",
        "oct", "ord", "pow", "range", "repr", "reversed", "round", "set", "sorted", "str", "sum",
        "tuple", "type", "zip",
    }
)  # fmt: skip
_COMMUTATIVE = (ast.Add, ast.Mult, ast.BitAnd, ast.BitOr, ast.BitXor)
_SYMMETRIC = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)
_FLIPPED: dict[type[ast.cmpop], type[ast.cmpop]] = {ast.Gt: ast.Lt, ast.GtE: ast.LtE}
_NEGATED: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.NotEq: ast.Eq,
    ast.NotIn: ast.In,
    ast.IsNot: ast.Is,
}
#: Comandos que encerram um bloco: tudo depois de um ``if`` que termina com eles é o "senão".
_EXITS = (ast.Return, ast.Raise, ast.Continue, ast.Break)
#: Comandos que nunca trocam de lugar com os vizinhos.
_BARRIERS = (
    ast.Return, ast.Raise, ast.Continue, ast.Break, ast.While, ast.For, ast.AsyncFor, ast.Try,
    ast.TryStar, ast.With, ast.AsyncWith, ast.Global, ast.Nonlocal, ast.Match,
)  # fmt: skip
_BLOCK_FIELDS = ("body", "orelse", "finalbody")
#: Campos de texto que fazem parte da estrutura (o resto dos nomes é do aluno).
_KEPT_TEXT: dict[type[ast.AST], str] = {
    ast.Attribute: "attr",
    ast.keyword: "arg",
    ast.alias: "name",
    ast.ImportFrom: "module",
}
_LOOP = "__laco__"


@dataclass(frozen=True, slots=True)
class Span:
    """Linhas de um trecho, a partir de 1, inclusivas."""

    first: int
    last: int


@dataclass(frozen=True, slots=True)
class TreeFingerprint:
    #: Peso de cada subárvore canônica (o tamanho dela vezes quantas vezes aparece) e, nos comandos
    #: com blocos, do cabeçalho e de cada comando de dentro (S35-07).
    weights: Mapping[bytes, int]
    #: Onde aparece cada comando, pelo hash, na ordem do código.
    spans: Mapping[bytes, tuple[Span, ...]]
    #: Tamanho de cada comando, pelo hash.
    sizes: Mapping[bytes, int]


@dataclass(frozen=True, slots=True)
class TreeScores:
    dice: float
    containment: float


@dataclass(frozen=True, slots=True)
class Match:
    """Um trecho do código A que tem a mesma estrutura de um trecho do código B."""

    a: Span
    b: Span
    size: int


def fingerprint(tree: ast.Module) -> TreeFingerprint:
    """A impressão digital de uma árvore. A árvore é alterada: use-a depois das outras análises."""
    try:
        _rewrite(tree)
        return _hash(tree)
    except (RecursionError, MemoryError):
        raise AnalysisLimitError("O código não pôde ser comparado.") from None


def scores(
    first: TreeFingerprint, second: TreeFingerprint, idf: Mapping[bytes, float] | None = None
) -> TreeScores:
    """Dice e contenção entre dois códigos; com ``idf``, cada subárvore pesa pela raridade."""

    def weight(item: bytes, value: int) -> float:
        return value * (idf.get(item, 1.0) if idf is not None else 1.0)

    left = sum(weight(item, value) for item, value in first.weights.items())
    right = sum(weight(item, value) for item, value in second.weights.items())
    if left == 0 or right == 0:
        same = left == right
        return TreeScores(1.0 if same else 0.0, 1.0 if same else 0.0)
    common = sum(
        weight(item, min(value, second.weights[item]))
        for item, value in first.weights.items()
        if item in second.weights
    )
    return TreeScores(dice=2 * common / (left + right), containment=common / min(left, right))


def class_idf(fingerprints: Sequence[TreeFingerprint]) -> dict[bytes, float]:
    """O inverso da frequência de cada subárvore na turma: ``ln((N + 1) / df)``.

    Uma subárvore que aparece em todas as soluções pesa ``ln(1 + 1/N)``, quase nada; uma que só
    aparece em duas pesa ``ln((N + 1) / 2)``. Os pesos são normalizados para que a mais rara pese 1.
    """
    count = len(fingerprints)
    frequency: Counter[bytes] = Counter()
    for item in fingerprints:
        frequency.update(item.weights.keys())
    raw = {item: math.log((count + 1) / df) for item, df in frequency.items()}
    top = max(raw.values(), default=1.0) or 1.0
    return {item: value / top for item, value in raw.items()}


def matches(first: TreeFingerprint, second: TreeFingerprint) -> list[Match]:
    """Os trechos em comum, dos maiores para os menores, sem sobreposição, na ordem do código A."""
    common = sorted(
        (item for item in first.spans if item in second.spans and first.sizes[item] >= MIN_MATCH),
        key=lambda item: (-first.sizes[item], first.spans[item][0].first),
    )
    taken_a: list[Span] = []
    taken_b: list[Span] = []
    found: list[Match] = []
    for item in common:
        for a, b in zip(first.spans[item], second.spans[item], strict=False):
            if _overlaps(a, taken_a) or _overlaps(b, taken_b):
                continue
            taken_a.append(a)
            taken_b.append(b)
            found.append(Match(a, b, first.sizes[item]))
            if len(found) == MAX_MATCHES:
                return sorted(found, key=lambda match: match.a.first)
    return sorted(found, key=lambda match: match.a.first)


def _overlaps(span: Span, taken: Iterable[Span]) -> bool:
    return any(span.first <= other.last and other.first <= span.last for other in taken)


# ---------------------------------------------------------------------------------------------
# 1. Reescritas
# ---------------------------------------------------------------------------------------------


def _rewrite(tree: ast.Module) -> None:
    """Reescreve os blocos de dentro para fora (as listas mais fundas primeiro)."""
    holders = [node for node in ast.walk(tree) if any(_block(node, f) for f in _BLOCK_FIELDS)]
    for node in reversed(holders):
        for field in _BLOCK_FIELDS:
            block = _block(node, field)
            if block:
                setattr(node, field, _rewrite_block(block))


def _block(node: ast.AST, field: str) -> list[ast.stmt] | None:
    value = getattr(node, field, None)
    if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
        return value
    return None


def _rewrite_block(block: list[ast.stmt]) -> list[ast.stmt]:
    rewritten: list[ast.stmt] = []
    for statement in block:
        if isinstance(statement, ast.AugAssign):
            statement = _expand_augmented(statement)
        elif isinstance(statement, ast.If):
            _positive_if(statement)
        elif isinstance(statement, (ast.For, ast.While)):
            loop, counter = _generic_loop(statement)
            # O "i = 0" logo antes de um laço com índice é parte do laço.
            if counter is not None and rewritten and _is_zero_init(rewritten[-1], counter):
                rewritten.pop()
            statement = loop
        rewritten.append(statement)
    return _guards_to_else(rewritten)


def _expand_augmented(node: ast.AugAssign) -> ast.Assign:
    target = copy.deepcopy(node.target)
    value = ast.BinOp(left=_as_load(target), op=node.op, right=node.value)
    assign = ast.Assign(targets=[node.target], value=ast.copy_location(value, node))
    return ast.copy_location(assign, node)


def _as_load(node: ast.expr) -> ast.expr:
    for item in ast.walk(node):
        if hasattr(item, "ctx"):
            item.ctx = ast.Load()
    return node


def _positive_if(node: ast.If) -> None:
    """Com ``else``, o teste fica numa forma só, e os ramos trocam quando ele é negado.

    ``not c`` vira ``c``; ``!=``, ``not in`` e ``is not`` viram ``==``, ``in`` e ``is``; e as
    comparações de ordem viram sempre ``<``: ``a > b`` é ``b < a``, e ``a <= b`` é a negação de
    ``b < a``. Assim ``if x >= 7: A else: B`` e ``if x < 7: B else: A`` dão a mesma árvore.
    """
    if not node.orelse:
        return
    if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
        node.test = node.test.operand
        node.body, node.orelse = node.orelse, node.body
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return
    op = type(test.ops[0])
    if op in _NEGATED:
        test.ops = [_NEGATED[op]()]
        node.body, node.orelse = node.orelse, node.body
        return
    if op in (ast.Gt, ast.GtE):
        test.left, test.comparators = test.comparators[0], [test.left]
        op = ast.Lt if op is ast.Gt else ast.LtE
        test.ops = [op()]
    if op is ast.LtE:
        test.left, test.comparators = test.comparators[0], [test.left]
        test.ops = [ast.Lt()]
        node.body, node.orelse = node.orelse, node.body


def _guards_to_else(block: list[ast.stmt]) -> list[ast.stmt]:
    """``if c: ...; return`` seguido do resto vira ``if c: ...; return`` / ``else: resto``.

    Feito de trás para frente, sem recursão: cada guarda recebe o que vem depois dela.
    """
    tail: list[ast.stmt] = []
    for statement in reversed(block):
        if (
            tail
            and isinstance(statement, ast.If)
            and not statement.orelse
            and isinstance(statement.body[-1], _EXITS)
        ):
            statement.orelse = list(tail)
            tail = [statement]
        else:
            tail.insert(0, statement)
    return tail


def _generic_loop(node: ast.For | ast.While) -> tuple[ast.While, str | None]:
    """O laço genérico: ``while __laco__tipo(o que percorre): corpo``, e o nome do índice."""
    body, orelse, counter = node.body, node.orelse, None
    if isinstance(node, ast.For):
        kind, header = "seq", node.iter
        index = node.target.id if isinstance(node.target, ast.Name) else None
        size = _range_bound(node.iter)
        if index is not None and size is not None:
            sequence = _len_argument(size)
            if sequence is not None:
                kind, header = "seq", sequence
                body = _replace_items(body, sequence, index)
            else:
                kind, header = "range", size
    else:
        kind, header = "while", node.test
        index_bound = _index_bound(node)
        if index_bound is not None:
            counter, bound = index_bound
            body = [statement for statement in body if not _is_increment(statement, counter)]
            sequence = _len_argument(bound)
            if sequence is not None:
                kind, header = "seq", sequence
                body = _replace_items(body, sequence, counter)
                body = _drop_alias(body, counter)
            else:
                kind, header = "range", bound
    marker = ast.Name(id=f"{_LOOP}{kind}", ctx=ast.Load())
    test = ast.Call(func=marker, args=[header], keywords=[])
    loop = ast.While(test=ast.copy_location(test, node), body=body or [ast.Pass()], orelse=orelse)
    return ast.copy_location(loop, node), counter


def _range_bound(node: ast.expr) -> ast.expr | None:
    """O ``n`` de ``range(n)``, ou ``None``."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "range"
        and len(node.args) == 1
        and not node.keywords
    ):
        return node.args[0]
    return None


def _len_argument(node: ast.expr) -> ast.expr | None:
    """O ``v`` de ``len(v)``, ou ``None``."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and not node.keywords
    ):
        return node.args[0]
    return None


def _index_bound(node: ast.While) -> tuple[str, ast.expr] | None:
    """``while i < limite`` com ``i += 1`` no corpo: o índice e o limite."""
    test = node.test
    if (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Lt)
        and isinstance(test.left, ast.Name)
        and any(_is_increment(statement, test.left.id) for statement in node.body)
    ):
        return test.left.id, test.comparators[0]
    return None


def _is_increment(node: ast.stmt, name: str) -> bool:
    one = ast.Constant(1)
    if isinstance(node, ast.AugAssign):
        return (
            _is_name(node.target, name) and isinstance(node.op, ast.Add) and _same(node.value, one)
        )
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and _is_name(node.targets[0], name):
        value = node.value
        return (
            isinstance(value, ast.BinOp)
            and isinstance(value.op, ast.Add)
            and {ast.dump(value.left), ast.dump(value.right)}
            == {ast.dump(ast.Name(id=name, ctx=ast.Load())), ast.dump(one)}
        )
    return False


def _is_zero_init(node: ast.stmt, name: str) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and _is_name(node.targets[0], name)
        and _same(node.value, ast.Constant(0))
    )


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _same(first: ast.AST, second: ast.AST) -> bool:
    return ast.dump(first) == ast.dump(second)


def _replace_items(body: list[ast.stmt], sequence: ast.expr, index: str) -> list[ast.stmt]:
    """Troca ``v[i]`` pelo nome do índice: no laço sobre ``v``, é o elemento da vez."""
    target = ast.dump(sequence)
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                if _is_item(value, target, index):
                    setattr(
                        node, field, ast.copy_location(ast.Name(id=index, ctx=ast.Load()), value)
                    )
                else:
                    stack.append(value)
            elif isinstance(value, list):
                for position, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        if _is_item(item, target, index):
                            value[position] = ast.copy_location(
                                ast.Name(id=index, ctx=ast.Load()), item
                            )
                        else:
                            stack.append(item)
    return body


def _is_item(node: ast.AST, sequence: str, index: str) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and _is_name(node.slice, index)
        and ast.dump(node.value) == sequence
    )


def _drop_alias(body: list[ast.stmt], index: str) -> list[ast.stmt]:
    """``x = v[i]`` no começo do laço é o ``x`` de ``for x in v``: some."""
    first = body[0] if body else None
    if (
        isinstance(first, ast.Assign)
        and len(first.targets) == 1
        and isinstance(first.targets[0], ast.Name)
        and _is_name(first.value, index)
    ):
        return body[1:]
    return body


# ---------------------------------------------------------------------------------------------
# 2. Hash canônico e reordenação
# ---------------------------------------------------------------------------------------------


def _digest(*parts: bytes) -> bytes:
    return hashlib.blake2b(b"\x1f".join(parts), digest_size=8).digest()


def _label(node: ast.AST) -> bytes:
    kind = type(node).__name__
    if isinstance(node, ast.Name):
        kept = node.id in _BUILTINS or node.id.startswith(_LOOP)
        return f"Name:{node.id if kept else 'V'}".encode()
    if isinstance(node, ast.Constant):
        value = node.value
        text = (
            "STR"
            if isinstance(value, str)
            else "BYTES"
            if isinstance(value, bytes)
            else repr(value)
        )
        return f"Constant:{text}".encode()
    field_name = _KEPT_TEXT.get(type(node))
    if field_name is not None:
        return f"{kind}:{getattr(node, field_name, None)}".encode()
    if isinstance(node, ast.FormattedValue):
        return f"{kind}:{node.conversion}".encode()
    if isinstance(node, ast.ImportFrom | ast.comprehension):
        return f"{kind}:{getattr(node, 'level', None)}:{getattr(node, 'is_async', 0)}".encode()
    return kind.encode()


class _Hasher:
    def __init__(self) -> None:
        self.digests: dict[int, bytes] = {}
        self.sizes: dict[int, int] = {}
        self.budget = DEPENDENCY_BUDGET

    def children(self, node: ast.AST) -> list[ast.AST]:
        return [
            child for child in ast.iter_child_nodes(node) if not isinstance(child, ast.expr_context)
        ]

    def combine(self, node: ast.AST) -> None:
        for field in _BLOCK_FIELDS:
            block = _block(node, field)
            if block is not None and len(block) > 1:
                setattr(node, field, self.reorder(block))
        children = self.children(node)
        parts = [self.digests[id(child)] for child in children]
        if isinstance(node, ast.BinOp) and isinstance(node.op, _COMMUTATIVE):
            parts = [
                self.digests[id(node.op)],
                *sorted((self.digests[id(node.left)], self.digests[id(node.right)])),
            ]
        elif isinstance(node, ast.BoolOp):
            parts = [
                self.digests[id(node.op)],
                *sorted(self.digests[id(value)] for value in node.values),
            ]
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            op, left, right = node.ops[0], node.left, node.comparators[0]
            flipped = _FLIPPED.get(type(op))
            operands = [self.digests[id(left)], self.digests[id(right)]]
            if flipped is not None:
                op_digest = _digest(flipped.__name__.encode())
                operands.reverse()
            else:
                op_digest = self.digests[id(op)]
                if isinstance(op, _SYMMETRIC):
                    operands.sort()
            parts = [op_digest, *operands]
        self.digests[id(node)] = _digest(_label(node), *parts)
        self.sizes[id(node)] = 1 + sum(self.sizes[id(child)] for child in children)

    def inner(self, node: ast.AST) -> list[tuple[str, ast.stmt]]:
        """Os comandos dos blocos de um comando composto, com o nome do bloco (S35-07)."""
        found: list[tuple[str, ast.stmt]] = []
        for field in _BLOCK_FIELDS:
            block = _block(node, field)
            if block:
                found.extend((field, statement) for statement in block)
        if isinstance(node, ast.Try | ast.TryStar):
            for handler in node.handlers:
                found.extend(("except", statement) for statement in handler.body)
        return found

    def header(self, node: ast.AST, inner: list[tuple[str, ast.stmt]]) -> tuple[bytes, int]:
        """O hash e o tamanho do comando sem os blocos: a condição, o que o laço percorre, a
        assinatura da função."""
        inside = {id(statement) for _, statement in inner}
        parts = [
            child
            for child in self.children(node)
            if id(child) not in inside and not isinstance(child, ast.excepthandler)
        ]
        digest = _digest(b"cabecalho", _label(node), *(self.digests[id(child)] for child in parts))
        return digest, 1 + sum(self.sizes[id(child)] for child in parts)

    def shape(self, statement: ast.stmt) -> bytes:
        """Um comando dentro de um bloco: os simples pelo hash; os compostos, pelo cabeçalho."""
        inner = self.inner(statement)
        return self.header(statement, inner)[0] if inner else self.digests[id(statement)]

    def reorder(self, block: list[ast.stmt]) -> list[ast.stmt]:
        """Ordenação topológica: entre os comandos prontos, o de menor hash vem primeiro."""
        effects = [self.effects(statement) for statement in block]
        if self.budget < 0:
            return block
        last_write: dict[str, int] = {}
        readers: dict[str, list[int]] = {}
        after: list[list[int]] = [[] for _ in block]
        pending = [0] * len(block)
        for position, (reads, writes) in enumerate(effects):
            before: set[int] = set()
            for name in reads | writes:
                if name in last_write:
                    before.add(last_write[name])
            for name in writes:
                before.update(readers.get(name, ()))
            before.discard(position)
            for earlier in before:
                after[earlier].append(position)
            pending[position] = len(before)
            for name in writes:
                last_write[name] = position
                readers[name] = []
            for name in reads:
                readers.setdefault(name, []).append(position)
        ready = [(self.digests[id(block[i])], i) for i, count in enumerate(pending) if count == 0]
        heapq.heapify(ready)
        ordered: list[ast.stmt] = []
        while ready:
            _, position = heapq.heappop(ready)
            ordered.append(block[position])
            for later in after[position]:
                pending[later] -= 1
                if pending[later] == 0:
                    heapq.heappush(ready, (self.digests[id(block[later])], later))
        return ordered

    def effects(self, statement: ast.stmt) -> tuple[set[str], set[str]]:
        """Os nomes que o comando lê e escreve; ``<io>`` e ``<barreira>`` mantêm a ordem."""
        if isinstance(statement, _BARRIERS):
            return {"<barreira>", "<io>"}, {"<barreira>", "<io>"}
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            # A definição só liga o nome; o corpo roda depois, quando a função é chamada.
            return {"<barreira>"}, {statement.name}
        reads: set[str] = {"<barreira>"}
        writes: set[str] = set()
        for node in ast.walk(statement):
            self.budget -= 1
            if isinstance(node, ast.Name):
                (writes if isinstance(node.ctx, ast.Store | ast.Del) else reads).add(node.id)
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
                    # Um método pode alterar o objeto (append, pop, sort).
                    writes.add(function.value.id)
                if not (isinstance(function, ast.Name) and function.id in _PURE):
                    reads.add("<io>")
                    writes.add("<io>")
        return reads, writes


def _hash(tree: ast.Module) -> TreeFingerprint:
    hasher = _Hasher()
    # Pós-ordem com pilha explícita: os filhos são resolvidos antes dos pais.
    stack: list[tuple[ast.AST, bool]] = [(tree, False)]
    while stack:
        node, expanded = stack.pop()
        if expanded:
            hasher.combine(node)
            continue
        stack.append((node, True))
        stack.extend((child, False) for child in hasher.children(node))
    weights: Counter[bytes] = Counter()
    spans: dict[bytes, list[Span]] = {}
    sizes: dict[bytes, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.expr_context):
            continue
        size = hasher.sizes[id(node)]
        if size < MIN_SUBTREE:
            continue
        digest = hasher.digests[id(node)]
        inner = hasher.inner(node) if isinstance(node, ast.stmt) else []
        if inner:
            head, head_size = hasher.header(node, inner)
            weights[head] += head_size
            # Cada comando entra com o anterior do mesmo bloco: a ordem continua contando (o que
            # a reordenação por dependência não trocou), e uma linha inserida só desfaz um par.
            previous: dict[str, bytes] = {}
            for field, statement in inner:
                shape = hasher.shape(statement)
                pair = _digest(b"dentro", head, field.encode(), previous.get(field, b""), shape)
                weights[pair] += hasher.sizes[id(statement)]
                previous[field] = shape
        else:
            weights[digest] += size
        if isinstance(node, ast.stmt):
            sizes[digest] = size
            spans.setdefault(digest, []).append(Span(node.lineno, node.end_lineno or node.lineno))
    return TreeFingerprint(
        weights=dict(weights),
        spans={
            item: tuple(sorted(found, key=lambda span: span.first)) for item, found in spans.items()
        },
        sizes=sizes,
    )

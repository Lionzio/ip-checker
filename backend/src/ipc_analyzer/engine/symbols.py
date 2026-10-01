"""Nomes ligados pelo aluno: distingue ``len`` (built-in) de uma variável do aluno chamada ``len``.

A resolução segue a ordem de execução do Python, para que o aluno não consiga esconder um built-in
proibido atribuindo o mesmo nome depois (5.4, ameaça 8):

- dentro de função, lambda, classe ou compreensão, um nome ligado em qualquer ponto daquele escopo
  é local (como no Python);
- dentro desses escopos, um built-in que não é local continua sendo o built-in, mesmo que o módulo
  tenha uma variável com o mesmo nome (a função pode ser chamada antes da atribuição);
- no nível do módulo, um nome só é do aluno se uma ligação acontecer antes do uso. A ligação vale a
  partir do fim do valor atribuído: em ``len = len(x)``, o ``len(x)`` ainda é o built-in.
"""

from __future__ import annotations

import ast
import builtins
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

#: Posição (linha, coluna em bytes) no sistema de coordenadas da AST.
Position = tuple[int, int]

SCOPE_NODES: tuple[type[ast.AST], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.ClassDef,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)

_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def is_builtin_name(name: str) -> bool:
    return hasattr(builtins, name)


def start_of(node: ast.AST) -> Position:
    return (getattr(node, "lineno", 1), getattr(node, "col_offset", 0))


def end_of(node: ast.AST) -> Position:
    line = getattr(node, "end_lineno", None)
    col = getattr(node, "end_col_offset", None)
    if line is None or col is None:
        return start_of(node)
    return (line, col)


def stored_names(target: ast.AST) -> Iterator[str]:
    """Nomes ligados por um alvo de atribuição (``a``, ``a, b``, ``[a, *b]``)."""
    for node in ast.walk(target):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id


def _argument_names(arguments: ast.arguments) -> Iterator[str]:
    for arg in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
        yield arg.arg
    if arguments.vararg is not None:
        yield arguments.vararg.arg
    if arguments.kwarg is not None:
        yield arguments.kwarg.arg


def _bindings_of(node: ast.AST) -> Iterator[tuple[str, Position]]:
    """Ligações que um nó faz no escopo onde aparece, com a posição a partir da qual valem."""
    match node:
        case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
            yield node.name, end_of(node)
        case ast.Import() | ast.ImportFrom():
            for alias in node.names:
                if alias.name != "*":
                    yield (alias.asname or alias.name.split(".")[0]), end_of(node)
        case ast.Assign():
            for target in node.targets:
                for name in stored_names(target):
                    yield name, end_of(node)
        case ast.AugAssign() | ast.AnnAssign():
            for name in stored_names(node.target):
                yield name, end_of(node)
        case ast.For() | ast.AsyncFor():
            for name in stored_names(node.target):
                yield name, end_of(node.iter)
        case ast.With() | ast.AsyncWith():
            for item in node.items:
                if item.optional_vars is not None:
                    for name in stored_names(item.optional_vars):
                        yield name, end_of(item.context_expr)
        case ast.NamedExpr():
            yield node.target.id, end_of(node)
        case ast.ExceptHandler(name=str(name)):
            yield name, (start_of(node.body[0]) if node.body else end_of(node))
        case ast.MatchAs(name=str(name)) | ast.MatchStar(name=str(name)):
            yield name, end_of(node)
        case ast.MatchMapping(rest=str(name)):
            yield name, end_of(node)
        case ast.TypeAlias():
            for name in stored_names(node.name):
                yield name, end_of(node)


def _scope_locals(scope: ast.AST) -> Iterator[str]:
    """Nomes que já nascem locais ao entrar no escopo: parâmetros e alvos de compreensão."""
    if isinstance(scope, _FUNCTIONS):
        yield from _argument_names(scope.args)
    elif isinstance(scope, _COMPREHENSIONS):
        for generator in scope.generators:
            yield from stored_names(generator.target)


@dataclass(frozen=True, slots=True)
class Bindings:
    #: Nomes ligados no nível do módulo -> posição da primeira ligação.
    module: Mapping[str, Position]
    #: id do nó de escopo -> nomes ligados naquele escopo (sem contar escopos internos).
    scopes: Mapping[int, frozenset[str]]

    def is_student_name(self, name: str, scopes: tuple[ast.AST, ...], position: Position) -> bool:
        """Indica se ``name``, usado em ``position`` dentro de ``scopes``, é um nome do aluno."""
        for scope in reversed(scopes):
            if name in self.scopes.get(id(scope), frozenset()):
                return True
        if scopes:
            return not is_builtin_name(name) and name in self.module
        first = self.module.get(name)
        return first is not None and first < position


def collect_bindings(tree: ast.Module) -> Bindings:
    """Percorre a árvore de forma iterativa e registra as ligações por escopo."""
    module: dict[str, Position] = {}
    scopes: dict[int, set[str]] = {}
    stack: list[tuple[ast.AST, tuple[ast.AST, ...]]] = [(tree, ())]
    while stack:
        node, chain = stack.pop()
        for name, position in _bindings_of(node):
            if chain:
                scopes.setdefault(id(chain[-1]), set()).add(name)
            elif name not in module or position < module[name]:
                module[name] = position
        if isinstance(node, SCOPE_NODES):
            scopes.setdefault(id(node), set()).update(_scope_locals(node))
            chain = (*chain, node)
        stack.extend((child, chain) for child in ast.iter_child_nodes(node))
    return Bindings(
        module=MappingProxyType(module),
        scopes=MappingProxyType({key: frozenset(names) for key, names in scopes.items()}),
    )

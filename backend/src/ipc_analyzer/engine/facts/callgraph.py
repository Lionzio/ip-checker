"""Grafo de chamadas entre as funções do aluno, para a recursão (R-68, C-03).

Uma função está em recursão quando está num ciclo do grafo: direto (``f`` chama ``f``) ou mútuo
(``f`` chama ``g``, que chama ``f``). As chamadas são pelo nome, como ``call:user``; um ``lambda``
não entra no grafo. Os componentes fortemente conexos saem pelo algoritmo de Tarjan, iterativo.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping, Sequence


def recursive_functions(
    defs: Mapping[str, Sequence[ast.AST]], calls: Iterable[tuple[ast.AST, str]]
) -> list[ast.AST]:
    """Os ``def`` que estão num ciclo do grafo de chamadas, na ordem dos componentes."""
    graph: dict[int, set[int]] = {}
    nodes: dict[int, ast.AST] = {}
    for definitions in defs.values():
        for definition in definitions:
            nodes[id(definition)] = definition
            graph.setdefault(id(definition), set())
    for caller, name in calls:
        for callee in defs.get(name, ()):
            graph[id(caller)].add(id(callee))
    found: list[ast.AST] = []
    for component in strongly_connected(graph):
        first = component[0]
        if len(component) > 1 or first in graph[first]:
            found.extend(nodes[member] for member in component)
    return found


def enclosing_function(scopes: tuple[ast.AST, ...]) -> ast.AST | None:
    """O ``def`` mais interno em volta da chamada; ``None`` no módulo ou dentro de um ``lambda``."""
    for scope in reversed(scopes):
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return scope
        if isinstance(scope, ast.Lambda):
            return None
    return None


def strongly_connected(graph: dict[int, set[int]]) -> list[list[int]]:
    """Componentes fortemente conexos (Tarjan, iterativo): linear no tamanho do grafo."""
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    on_stack: set[int] = set()
    stack: list[int] = []
    components: list[list[int]] = []
    counter = 0
    for root in graph:
        if root in index:
            continue
        work: list[tuple[int, list[int]]] = [(root, sorted(graph[root]))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, pending = work[-1]
            if pending:
                target = pending.pop()
                if target not in index:
                    index[target] = low[target] = counter
                    counter += 1
                    stack.append(target)
                    on_stack.add(target)
                    work.append((target, sorted(graph[target])))
                elif target in on_stack:
                    low[node] = min(low[node], index[target])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                component: list[int] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(component)
    return components

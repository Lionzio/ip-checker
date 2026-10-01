"""Extração de fatos da AST (5.2.3): cada construção do código vira um fato ``<tipo>:<nome>``.

A travessia é iterativa. Fatos contextuais substituem o fato genérico do nó: ``*x`` numa chamada
vira ``call:star_args`` (e não ``node:Starred``); ``a, b`` como alvo de ``for`` vira
``target:for_unpack`` (e não ``node:Tuple``). A posição é dada em linha e coluna a partir de 1,
com a coluna contada em caracteres e o fim exclusivo.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ipc_analyzer.engine.guards import split_lines
from ipc_analyzer.engine.parse import ParsedSource
from ipc_analyzer.engine.symbols import (
    SCOPE_NODES,
    Bindings,
    Position,
    collect_bindings,
    end_of,
    is_builtin_name,
    start_of,
)

_OPERATORS = (ast.operator, ast.unaryop, ast.boolop)


@dataclass(frozen=True, slots=True)
class Fact:
    name: str
    line: int
    col: int
    end_line: int
    end_col: int
    #: Número de argumentos da chamada quando o fato é a função chamada (``type('C', (), {})``
    #: -> 3); ``None`` quando não é chamada. Usado pelos predicados (``engine/conditions.py``).
    call_args: int | None = None


@dataclass(frozen=True, slots=True)
class _Visit:
    node: ast.AST
    scopes: tuple[ast.AST, ...]
    #: Nó mais próximo com posição; operadores e contextos herdam a posição do pai.
    anchor: ast.AST
    role: str = ""
    callee: str = ""
    callee_is_student: bool = False
    #: Preenchido só para o nó que é a função de uma chamada.
    call_args: int | None = None


class _SourceMap:
    """Converte colunas da AST (bytes UTF-8, a partir de 0) em caracteres (a partir de 1)."""

    def __init__(self, source: str) -> None:
        self._lines = split_lines(source)
        self._encoded: dict[int, bytes] = {}

    def column(self, line: int, byte_offset: int) -> int:
        if not 1 <= line <= len(self._lines):
            return byte_offset + 1
        encoded = self._encoded.get(line)
        if encoded is None:
            encoded = self._lines[line - 1].encode("utf-8")
            self._encoded[line] = encoded
        return len(encoded[:byte_offset].decode("utf-8", errors="ignore")) + 1

    def fact(self, name: str, start: Position, end: Position, call_args: int | None = None) -> Fact:
        return Fact(name, start[0], self.column(*start), end[0], self.column(*end), call_args)


def _const_kind(value: object) -> str:
    if value is None:
        return "None"
    if value is Ellipsis:
        return "Ellipsis"
    if isinstance(value, bool):
        return "bool"
    return type(value).__name__


def _callee_name(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return "_"


def _attribute_name_start(node: ast.Attribute) -> Position:
    """O nome do atributo é o último trecho do nó: ``s.upper`` aponta para ``upper``."""
    line, col = end_of(node)
    return (line, max(col - len(node.attr.encode("utf-8")), 0))


class _Extractor:
    def __init__(self, parsed: ParsedSource) -> None:
        self._bindings: Bindings = collect_bindings(parsed.tree)
        self._map = _SourceMap(parsed.source)
        self.facts: list[Fact] = []

    def emit(
        self,
        name: str,
        anchor: ast.AST,
        start: Position | None = None,
        call_args: int | None = None,
    ) -> None:
        self.facts.append(
            self._map.fact(name, start or start_of(anchor), end_of(anchor), call_args)
        )

    def is_student(self, name: str, visit: _Visit, node: ast.AST) -> bool:
        return self._bindings.is_student_name(name, visit.scopes, start_of(node))

    def run(self, tree: ast.Module) -> tuple[Fact, ...]:
        stack = [_Visit(node=tree, scopes=(), anchor=tree)]
        while stack:
            visit = stack.pop()
            self._visit(visit)
            stack.extend(self._children(visit))
        return tuple(
            sorted(self.facts, key=lambda f: (f.line, f.col, f.end_line, f.end_col, f.name))
        )

    def _visit(self, visit: _Visit) -> None:
        node = visit.node
        # Nós sem posição (operadores, contextos, ``arguments``) herdam a do pai.
        anchor = node if hasattr(node, "lineno") else visit.anchor
        if isinstance(node, _OPERATORS):
            self.emit(f"op:{type(node).__name__}", anchor)
        elif isinstance(node, ast.cmpop):
            self.emit(f"cmp:{type(node).__name__}", anchor)
        elif visit.role == "call_arg":
            self.emit("call:star_args", node)
        elif visit.role == "for_target":
            self.emit("target:for_unpack", node)
        else:
            self.emit(f"node:{type(node).__name__}", anchor)
        self._specific_facts(visit)

    def _specific_facts(self, visit: _Visit) -> None:
        node = visit.node
        match node:
            case ast.Name(ctx=ast.Load()):
                if is_builtin_name(node.id) and not self.is_student(node.id, visit, node):
                    self.emit(f"builtin:{node.id}", node, call_args=visit.call_args)
            case ast.Attribute():
                self.emit(
                    f"method:{node.attr}",
                    node,
                    start=_attribute_name_start(node),
                    call_args=visit.call_args,
                )
            case ast.Constant():
                self.emit(f"const:{_const_kind(node.value)}", node)
            case ast.keyword():
                if node.arg is None:
                    self.emit("kwarg:**", node)
                elif visit.callee_is_student:
                    self.emit("call:user_kwarg", node)
                else:
                    self.emit(f"kwarg:{visit.callee}.{node.arg}", node)
            case ast.Call(func=ast.Name(id=name)) if self.is_student(name, visit, node):
                self.emit("call:user", node)
            case ast.Return(value=ast.Tuple()):
                self.emit("return:multi", node)
            case ast.arguments():
                self._parameter_facts(node)

    def _parameter_facts(self, arguments: ast.arguments) -> None:
        if arguments.vararg is not None:
            self.emit("param:vararg", arguments.vararg)
        if arguments.kwarg is not None:
            self.emit("param:kwarg", arguments.kwarg)
        if arguments.posonlyargs:
            self.emit("param:posonly", arguments.posonlyargs[0])
        if arguments.kwonlyargs:
            self.emit("param:kwonly", arguments.kwonlyargs[0])
        for default in (*arguments.defaults, *arguments.kw_defaults):
            if default is not None:
                self.emit("param:default", default)

    def _children(self, visit: _Visit) -> list[_Visit]:
        node = visit.node
        scopes = (*visit.scopes, node) if isinstance(node, SCOPE_NODES) else visit.scopes
        anchor = node if hasattr(node, "lineno") else visit.anchor
        star_args: set[int] = set()
        for_target = -1
        func, call_args = -1, 0
        callee, callee_is_student = "", False
        if isinstance(node, ast.Call):
            func, call_args = id(node.func), len(node.args) + len(node.keywords)
            star_args = {id(arg) for arg in node.args if isinstance(arg, ast.Starred)}
            callee = _callee_name(node.func)
            callee_is_student = isinstance(node.func, ast.Name) and self.is_student(
                node.func.id, visit, node
            )
        elif isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(
            node.target, (ast.Tuple, ast.List)
        ):
            for_target = id(node.target)

        children: list[_Visit] = []
        for child in ast.iter_child_nodes(node):
            role = ""
            if id(child) in star_args:
                role = "call_arg"
            elif id(child) == for_target:
                role = "for_target"
            elif isinstance(child, ast.keyword):
                role = "keyword"
            children.append(
                _Visit(
                    node=child,
                    scopes=scopes,
                    anchor=anchor,
                    role=role,
                    callee=callee,
                    callee_is_student=callee_is_student,
                    call_args=call_args if id(child) == func else None,
                )
            )
        return children


def extract_facts(parsed: ParsedSource) -> tuple[Fact, ...]:
    """Fatos do código, ordenados por posição. A árvore já foi limitada pelo parser (NFR-08)."""
    return _Extractor(parsed).run(parsed.tree)

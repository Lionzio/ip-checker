"""Extração de fatos da AST (5.2.3): cada construção do código vira um fato ``<tipo>:<nome>``.

A travessia é iterativa. Fatos contextuais substituem o fato genérico do nó: ``*x`` numa chamada
vira ``call:star_args`` (e não ``node:Starred``); ``a, b`` como alvo de ``for`` vira
``target:for_unpack`` (e não ``node:Tuple``). A posição é dada em linha e coluna a partir de 1,
com a coluna contada em caracteres e o fim exclusivo.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ipc_analyzer.engine.facts.callgraph import enclosing_function, recursive_functions
from ipc_analyzer.engine.facts.model import Fact, SourceMap
from ipc_analyzer.engine.parse import ParsedSource
from ipc_analyzer.engine.symbols import (
    SCOPE_NODES,
    Bindings,
    Position,
    collect_bindings,
    end_of,
    evaluated_outside,
    is_builtin_name,
    start_of,
)

_OPERATORS = (ast.operator, ast.unaryop, ast.boolop)
_FUNCTION_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


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


def _const_kind(value: object) -> str:
    if value is None:
        return "None"
    if value is Ellipsis:
        return "Ellipsis"
    if isinstance(value, bool):
        return "bool"
    return type(value).__name__


#: Funções cujos argumentos nomeados são chaves de dicionário: ``dict(a=1)`` e ``d.update(a=1)``.
_FREE_KEYWORDS = frozenset({"dict", "update"})


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
        self._map = SourceMap(parsed.source)
        #: ``id`` do nome ``zip`` e do alvo de cada ``for`` cujo iterável é ``zip(...)`` -> número
        #: de sequências. O ``for`` é visitado antes dos filhos, então a marca chega a tempo.
        self._zip_header: dict[int, int] = {}
        #: ``id`` do alvo de cada ``for`` cujo iterável é ``enumerate(...)`` ou ``x.items()``.
        self._for_header: dict[int, str] = {}
        #: Funções do aluno (``def``) e as chamadas de cada uma, para achar a recursão (C-03).
        self._defs: dict[str, list[ast.AST]] = {}
        self._calls: list[tuple[ast.AST, str]] = []
        #: ``id`` das partes de um escopo que o Python avalia no escopo de fora -> esses escopos:
        #: o iterável do 1º ``for`` de uma compreensão, valores padrão e decoradores. Sem isso,
        #: ``[v for map in [map(s)] for v in map]`` esconderia o built-in ``map`` (ameaça 8).
        self._outer_scopes: dict[int, tuple[ast.AST, ...]] = {}
        self.facts: list[Fact] = []

    def emit(
        self,
        name: str,
        anchor: ast.AST,
        start: Position | None = None,
        call_args: int | None = None,
        zip_header_args: int | None = None,
        for_header: str | None = None,
    ) -> None:
        self.facts.append(
            self._map.fact(
                name,
                start or start_of(anchor),
                end_of(anchor),
                call_args,
                zip_header_args,
                for_header,
            )
        )

    def is_student(self, name: str, visit: _Visit, node: ast.AST) -> bool:
        return self._bindings.is_student_name(name, visit.scopes, start_of(node))

    def run(self, tree: ast.Module) -> tuple[Fact, ...]:
        stack = [_Visit(node=tree, scopes=(), anchor=tree)]
        while stack:
            visit = stack.pop()
            self._visit(visit)
            stack.extend(self._children(visit))
        self._mark_recursion()
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
            self.emit(
                "target:for_unpack",
                node,
                zip_header_args=self._zip_header.get(id(node)),
                for_header=self._for_header.get(id(node)),
            )
        else:
            self.emit(f"node:{type(node).__name__}", anchor)
        self._specific_facts(visit)

    def _specific_facts(self, visit: _Visit) -> None:
        node = visit.node
        match node:
            case ast.Name(ctx=ast.Load()):
                if is_builtin_name(node.id) and not self.is_student(node.id, visit, node):
                    self.emit(
                        f"builtin:{node.id}",
                        node,
                        call_args=visit.call_args,
                        zip_header_args=self._zip_header.get(id(node)),
                    )
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
                elif visit.callee in _FREE_KEYWORDS:
                    # Em dict(a=1) e d.update(a=1), o nome é uma chave do dicionário, não uma
                    # opção da função: qualquer nome vale o mesmo fato (caso 7 do Marco 2).
                    self.emit(f"kwarg:{visit.callee}.*", node)
                else:
                    self.emit(f"kwarg:{visit.callee}.{node.arg}", node)
            case ast.Call(func=ast.Name(id=name)) if self.is_student(name, visit, node):
                self.emit("call:user", node)
                caller = enclosing_function(visit.scopes)
                # Um parâmetro ou variável local com o nome de um def não é esse def:
                # em ``def f(f): return f(1)`` não há recursão.
                if caller is not None and not self._bindings.is_local(name, visit.scopes):
                    self._calls.append((caller, name))
            case ast.Return(value=ast.Tuple()):
                self.emit("return:multi", node)
            case (
                ast.For(orelse=[first, *_])
                | ast.AsyncFor(orelse=[first, *_])
                | ast.While(orelse=[first, *_])
            ):
                # O 'else' do laço não é nó na AST; o fato aponta para o 1º comando dele (Q-02 g).
                self.emit("derived:loop_else", first)
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                if not isinstance(node, ast.ClassDef):
                    self._defs.setdefault(node.name, []).append(node)
                if not isinstance(node, ast.ClassDef) and any(
                    isinstance(scope, _FUNCTION_SCOPES) for scope in visit.scopes
                ):
                    # Função dentro de função não consta (Q-02 f): o def aninhado leva este fato,
                    # que nenhuma regra permite, além do node:FunctionDef.
                    self.emit("derived:nested_function", node)
                # '@d' é uma chamada implícita sem nó próprio; sem este fato, um decorador do
                # aluno passaria despercebido quando funções forem permitidas (DoD, item 9).
                for decorator in node.decorator_list:
                    self.emit("derived:decorator", decorator)
            case ast.Dict():
                # '{**d}' aparece só como chave None; o fato aponta para a expressão desempacotada.
                for key, value in zip(node.keys, node.values, strict=True):
                    if key is None:
                        self.emit("derived:dict_unpack", value)
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
        if isinstance(node, SCOPE_NODES):
            for part in evaluated_outside(node):
                self._outer_scopes[id(part)] = visit.scopes
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
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if isinstance(node.target, (ast.Tuple, ast.List)):
                for_target = id(node.target)
            if isinstance(node, ast.For):
                self._mark_for_header(node, visit)
        elif isinstance(node, ast.comprehension) and not node.is_async:
            # O for de uma compreensão conta como comando for para o zip() da R-37 (caso 5 do
            # Marco 2, decisão do autor de 09/10/2026): [a + b for a, b in zip(x, y)].
            self._mark_for_header(node, visit)

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
                    scopes=self._outer_scopes.pop(id(child), scopes),
                    anchor=anchor,
                    role=role,
                    callee=callee,
                    callee_is_student=callee_is_student,
                    call_args=call_args if id(child) == func else None,
                )
            )
        return children

    def _mark_for_header(self, loop: ast.For | ast.comprehension, visit: _Visit) -> None:
        """Marca o iterável do ``for`` que libera vários nomes no alvo.

        ``zip()`` built-in (R-37 e R-64): o próprio ``zip`` e o alvo levam o número de sequências.
        ``enumerate()`` built-in (R-63) e ``x.items()`` (R-65): o alvo leva o nome. Contam o comando
        ``for`` e, desde 09/10/2026, o ``for`` de uma compreensão (caso 5 do Marco 2); dentro de
        outra chamada do cabeçalho, nada é marcado.
        """
        match loop.iter:
            case ast.Call(func=ast.Name(id="zip" | "enumerate" as name) as func, args=args):
                if self.is_student(name, visit, func):
                    return
                if name == "zip":
                    count = len(args) + len(loop.iter.keywords)
                    self._zip_header[id(func)] = count
                    self._zip_header[id(loop.target)] = count
                else:
                    self._for_header[id(loop.target)] = name
            case ast.Call(func=ast.Attribute(attr="items"), args=[], keywords=[]):
                self._for_header[id(loop.target)] = "items"

    def _mark_recursion(self) -> None:
        """Cada ``def`` num ciclo do grafo de chamadas leva ``derived:recursion`` (R-68, C-03)."""
        for definition in recursive_functions(self._defs, self._calls):
            self.emit("derived:recursion", definition)


def extract_facts(parsed: ParsedSource) -> tuple[Fact, ...]:
    """Fatos do código, ordenados por posição. A árvore já foi limitada pelo parser (NFR-08)."""
    return _Extractor(parsed).run(parsed.tree)

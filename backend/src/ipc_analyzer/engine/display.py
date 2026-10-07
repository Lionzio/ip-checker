"""Nome legível de um fato, usado nas mensagens ao aluno (ex.: ``node:Lambda`` -> ``lambda``)."""

from __future__ import annotations

_NODES = {
    "AnnAssign": "atribuição com anotação de tipo",
    "Assert": "assert",
    "AsyncFor": "async for",
    "AsyncFunctionDef": "async def",
    "AsyncWith": "async with",
    "Await": "await",
    "Break": "break",
    "ClassDef": "class",
    "Continue": "continue",
    "Delete": "del",
    "Del": "del",
    "Dict": "dicionário",
    "DictComp": "dict comprehension",
    "For": "for",
    "FunctionDef": "def",
    "GeneratorExp": "expressão geradora",
    "Global": "global",
    "If": "if",
    "IfExp": "operador ternário",
    "Import": "import",
    "ImportFrom": "from ... import",
    "Lambda": "lambda",
    "List": "lista",
    "ListComp": "list comprehension",
    "Match": "match",
    "NamedExpr": ":= (operador morsa)",
    "Nonlocal": "nonlocal",
    "Pass": "pass",
    "Raise": "raise",
    "Return": "return",
    "Set": "set",
    "SetComp": "set comprehension",
    "Slice": "fatiamento",
    "Starred": "* (desempacotamento)",
    "Subscript": "indexação",
    "Try": "try",
    "TryStar": "try/except*",
    "Tuple": "tupla",
    "TypeAlias": "type",
    "While": "while",
    "With": "with",
    "withitem": "with",
    "Yield": "yield",
    "YieldFrom": "yield from",
}

_OPERATORS = {
    "Add": "+",
    "Sub": "-",
    "Mult": "*",
    "Div": "/",
    "FloorDiv": "//",
    "Mod": "%",
    "Pow": "**",
    "MatMult": "@",
    "BitAnd": "&",
    "BitOr": "|",
    "BitXor": "^",
    "LShift": "<<",
    "RShift": ">>",
    "Invert": "~",
    "Not": "not",
    "And": "and",
    "Or": "or",
    "UAdd": "+",
    "USub": "-",
    "Eq": "==",
    "NotEq": "!=",
    "Lt": "<",
    "LtE": "<=",
    "Gt": ">",
    "GtE": ">=",
    "Is": "is",
    "IsNot": "is not",
    "In": "in",
    "NotIn": "not in",
}

_OTHERS = {
    "const:None": "None",
    "const:complex": "número complexo",
    "const:bytes": "bytes",
    "const:Ellipsis": "...",
    "param:vararg": "*args",
    "param:kwarg": "**kwargs",
    "param:default": "valor padrão de parâmetro",
    "param:kwonly": "parâmetro somente nomeado (*)",
    "param:posonly": "parâmetro somente posicional (/)",
    "call:user": "chamada de função",
    "call:user_kwarg": "argumento nomeado",
    "call:star_args": "* em chamada",
    "kwarg:**": "** em chamada",
    "return:multi": "retorno de vários valores",
    "target:for_unpack": "desempacotamento no for",
    "derived:recursion": "recursão",
    "derived:loop_else": "else em laço",
    "derived:nested_function": "função dentro de função",
    "derived:decorator": "decorador (@)",
    "derived:dict_unpack": "** em dicionário",
}


def describe(fact: str) -> str:
    """Texto curto que o aluno reconhece no próprio código."""
    if fact in _OTHERS:
        return _OTHERS[fact]
    kind, _, name = fact.partition(":")
    match kind:
        case "node":
            return _NODES.get(name, name)
        case "op" | "cmp":
            return _OPERATORS.get(name, name)
        case "builtin":
            return f"{name}()"
        case "method":
            return f".{name}()"
        case "kwarg":
            function, _, argument = name.partition(".")
            return f"{argument}= em {function}()" if function != "_" else f"{argument}="
        case "const":
            return name
        case _:
            return fact

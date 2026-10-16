"""Extrator de fatos e ligações de nomes (S3-01, 5.2.3)."""

from __future__ import annotations

import time

import pytest

from ipc_analyzer.engine.facts import Fact, extract_facts
from ipc_analyzer.engine.parse import ParsedSource, parse_source
from ipc_analyzer.engine.ruleset import is_valid_fact


def facts(source: str) -> tuple[Fact, ...]:
    parsed = parse_source(source, target=(3, 13))
    assert isinstance(parsed, ParsedSource)
    return extract_facts(parsed)


def names(source: str) -> set[str]:
    return {fact.name for fact in facts(source)}


def located(source: str, name: str) -> list[tuple[int, int, int, int]]:
    return [(f.line, f.col, f.end_line, f.end_col) for f in facts(source) if f.name == name]


# --- Critérios da S3-01 -----------------------------------------------------------------------


def test_attribute_without_call_is_a_method_fact() -> None:
    assert "method:split" in names("s = input()\nf = s.split\n")


def test_student_variable_named_len_is_not_the_builtin() -> None:
    found = names("len = 3\nprint(len)\n")

    assert "builtin:len" not in found
    assert "builtin:print" in found


# --- Resolução de nomes e evasão (5.4, ameaça 8) --------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "eval('1')\neval = 2\n",  # uso antes da atribuição chama o built-in
        "len = len('abc')\n",  # o valor é avaliado antes da ligação
        "for len in range(len('abc')):\n    x = 1\n",  # o iterável vem antes do alvo
        "def f():\n    return len('abc')\nlen = 5\n",  # dentro de função, o global pode vir depois
    ],
)
def test_builtin_used_before_shadowing_is_still_the_builtin(source: str) -> None:
    builtin = "builtin:eval" if "eval" in source else "builtin:len"

    assert builtin in names(source)


@pytest.mark.parametrize(
    ("source", "builtin"),
    [
        ("def f():\n    len = 1\n    return len\n", "builtin:len"),
        ("def f(max):\n    return max\n", "builtin:max"),
        ("g = lambda sum: sum\n", "builtin:sum"),
        ("x = [sum for sum in range(3)]\n", "builtin:sum"),
        ("for max in [1, 2]:\n    print(max)\n", "builtin:max"),
        ("with open('a') as input:\n    print(input)\n", "builtin:input"),
        ("try:\n    x = 1\nexcept ValueError as abs:\n    print(abs)\n", "builtin:abs"),
        ("if (len := 3) > 2:\n    print(len)\n", "builtin:len"),
        ("import math as round\nprint(round)\n", "builtin:round"),
        ("type int = str\nprint(int)\n", "builtin:int"),
        ("def len(x):\n    return 1\nprint(len('a'))\n", "builtin:len"),
    ],
)
def test_student_bindings_shadow_builtins(source: str, builtin: str) -> None:
    assert builtin not in names(source)


@pytest.mark.parametrize(
    "source",
    [
        "getattr('a', 'upper')()",
        "__import__('os')",
        "globals()",
        "exec('x = 1')",
    ],
)
def test_dynamic_access_produces_builtin_facts(source: str) -> None:
    found = names(source + "\n")

    assert any(name.startswith("builtin:") for name in found)


def test_dunder_attributes_are_method_facts() -> None:
    found = names("x = ().__class__.__bases__\n")

    assert {"method:__class__", "method:__bases__"} <= found


def test_undefined_names_produce_no_fact() -> None:
    found = names("x = valor_inexistente\nfuncao_inexistente()\n")

    assert not any(name.startswith(("builtin:", "call:")) for name in found)


# --- Fatos por tipo -------------------------------------------------------------------------


def test_operators_and_comparisons() -> None:
    found = names("x = a + b * -c\ny = a < b == c\nz = x not in y and not x is not None\n")

    assert {"op:Add", "op:Mult", "op:USub", "node:BinOp", "node:UnaryOp"} <= found
    assert {"cmp:Lt", "cmp:Eq", "cmp:NotIn", "cmp:IsNot", "op:And", "op:Not"} <= found


def test_augmented_assignment() -> None:
    assert {"node:AugAssign", "op:Add", "const:int"} <= names("x = 1\nx += 1\n")


@pytest.mark.parametrize(
    ("literal", "fact"),
    [
        ("None", "const:None"),
        ("True", "const:bool"),
        ("1", "const:int"),
        ("1.5", "const:float"),
        ("1j", "const:complex"),
        ("'s'", "const:str"),
        ("b'x'", "const:bytes"),
        ("...", "const:Ellipsis"),
    ],
)
def test_constant_kinds(literal: str, fact: str) -> None:
    assert fact in names(f"x = {literal}\n")


def test_bool_is_not_reported_as_int() -> None:
    assert "const:int" not in names("x = True\n")


@pytest.mark.parametrize(
    ("source", "fact"),
    [
        ("print('a', end='')", "kwarg:print.end"),
        ("print('a', sep='')", "kwarg:print.sep"),
        ("sorted([1], reverse=True)", "kwarg:sorted.reverse"),
        ("'a,b'.split(sep=',')", "kwarg:split.sep"),
        ("(lambda: print)()(end='')", "kwarg:_.end"),
        ("print(**{'end': ''})", "kwarg:**"),
    ],
)
def test_keyword_arguments(source: str, fact: str) -> None:
    assert fact in names(source + "\n")


def test_star_in_call_replaces_the_starred_node() -> None:
    found = names("print(*[1, 2])\n")

    assert "call:star_args" in found
    assert "node:Starred" not in found


def test_star_outside_call_is_a_starred_node() -> None:
    found = names("a, *b = [1, 2, 3]\n")

    assert "node:Starred" in found
    assert "call:star_args" not in found


def test_tuple_target_of_for_is_for_unpack() -> None:
    loop = names("for a, b in zip('ab', 'cd'):\n    print(a, b)\n")
    assignment = names("a, b = 1, 2\n")

    assert "target:for_unpack" in loop
    assert "node:Tuple" not in loop
    assert "node:Tuple" in assignment


def zip_marks(source: str) -> list[tuple[str, int, int | None]]:
    return [
        (fact.name, fact.col, fact.zip_header_args)
        for fact in facts(source)
        if fact.name in {"builtin:zip", "target:for_unpack"}
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # zip() como o iterável do for: o zip e o alvo levam o número de sequências (R-37).
        (
            "for a, b in zip('ab', 'cd'):\n    print(a, b)\n",
            [("target:for_unpack", 5, 2), ("builtin:zip", 13, 2)],
        ),
        ("for a in zip('ab'):\n    print(a)\n", [("builtin:zip", 10, 1)]),
        # Fora do cabeçalho, ou dentro de outra chamada no cabeçalho, não há marca.
        ("z = zip('ab', 'cd')\n", [("builtin:zip", 5, None)]),
        (
            "for a, b in zip(zip('a', 'b'), 'c'):\n    print(a)\n",
            [("target:for_unpack", 5, 2), ("builtin:zip", 13, 2), ("builtin:zip", 17, None)],
        ),
        # O for de uma compreensão conta como comando for (caso 5 do Marco 2); o alvo é um
        # node:Tuple comum.
        ("x = [a for a, b in zip('ab', 'cd')]\n", [("builtin:zip", 20, 2)]),
        # Um zip do aluno não é o built-in: o alvo fica sem marca.
        ("zip = 3\nfor a, b in zip:\n    print(a)\n", [("target:for_unpack", 5, None)]),
        ("for a, b in 'ab':\n    print(a)\n", [("target:for_unpack", 5, None)]),
    ],
    ids=["header", "one-sequence", "outside", "nested", "comprehension", "shadowed", "no-zip"],
)
def test_zip_in_the_for_header_is_marked(
    source: str, expected: list[tuple[str, int, int | None]]
) -> None:
    assert zip_marks(source) == expected


@pytest.mark.parametrize(
    ("source", "fact"),
    [
        ("def f(*args):\n    return 1\n", "param:vararg"),
        ("def f(**kwargs):\n    return 1\n", "param:kwarg"),
        ("def f(x=1):\n    return x\n", "param:default"),
        ("def f(*, k):\n    return k\n", "param:kwonly"),
        ("def f(a, /):\n    return a\n", "param:posonly"),
        ("g = lambda *a: a\n", "param:vararg"),
    ],
)
def test_parameter_facts(source: str, fact: str) -> None:
    assert fact in names(source)


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("for i in range(2):\n    x = i\nelse:\n    x = 9\n", 4),
        ("x = 0\nwhile x < 2:\n    x += 1\nelse:\n    x = 9\n", 5),
    ],
)
def test_loop_else_is_a_derived_fact(source: str, line: int) -> None:
    (position,) = located(source, "derived:loop_else")

    assert position[0] == line


def test_loop_without_else_has_no_loop_else_fact() -> None:
    assert "derived:loop_else" not in names("for i in range(2):\n    x = i\n")


@pytest.mark.parametrize(
    "definition",
    ["def g():\n    return 1\n", "async def g():\n    return 1\n", "class C:\n    x = 1\n"],
    ids=["funcao", "async", "classe"],
)
def test_decorator_is_a_derived_fact(definition: str) -> None:
    source = "def d(f):\n    return f\n\n\n@d\n" + definition

    # O fato aponta para a expressão depois do '@' (linha 5, coluna 2).
    assert located(source, "derived:decorator") == [(5, 2, 5, 3)]


def test_each_decorator_is_a_fact() -> None:
    source = "def d(f):\n    return f\n\n\n@d\n@d\ndef g():\n    return 1\n"

    assert [position[0] for position in located(source, "derived:decorator")] == [5, 6]


def test_dict_unpacking_is_a_derived_fact() -> None:
    source = "a = {1: 2}\nb = {**a, 3: 4, **a}\n"

    assert located(source, "derived:dict_unpack") == [(2, 8, 2, 9), (2, 19, 2, 20)]
    assert "derived:dict_unpack" not in names("a = {1: 2}\n")


def test_multiple_return_values() -> None:
    assert {"return:multi", "node:Tuple"} <= names("def f():\n    return 1, 2\n")


def test_calls_to_student_functions() -> None:
    found = names("def f(x):\n    return x\ny = f(1)\nz = f(x=2)\n")

    assert {"call:user", "call:user_kwarg"} <= found
    assert "kwarg:f.x" not in found


def test_call_before_definition_is_not_a_student_call() -> None:
    assert "call:user" not in names("y = f(1)\ndef f(x):\n    return x\n")


def test_fstrings_and_imports() -> None:
    found = names("import math\nx = f'{math.pi!r:>10}'\n")

    assert {"node:Import", "node:alias", "node:JoinedStr", "node:FormattedValue"} <= found
    assert "method:pi" in found
    assert "builtin:math" not in found


# --- Posições ------------------------------------------------------------------------------


def test_method_fact_points_to_the_attribute_name() -> None:
    assert located("if x:\n    print(s.upper())\n", "method:upper") == [(2, 13, 2, 18)]


def test_columns_are_counted_in_characters() -> None:
    assert located("s = 'ação'; t = s.upper()\n", "method:upper") == [(1, 19, 1, 24)]


def test_node_facts_take_their_own_position() -> None:
    source = "x = 3\nwhile x > 0:\n    x -= 1\n"

    assert located(source, "node:While") == [(2, 1, 3, 11)]
    assert located(source, "node:AugAssign") == [(3, 5, 3, 11)]
    assert located(source, "node:Module") == [(1, 1, 1, 1)]


def test_context_nodes_take_the_position_of_their_parent() -> None:
    assert located("x = 1\n", "node:Store") == [(1, 1, 1, 2)]


def test_operator_takes_the_position_of_its_expression() -> None:
    assert located("x = 1 + 2\n", "op:Add") == [(1, 5, 1, 10)]


def test_facts_are_sorted_by_position() -> None:
    found = facts("x = 1\nif x:\n    print(x)\n")

    assert list(found) == sorted(
        found, key=lambda f: (f.line, f.col, f.end_line, f.end_col, f.name)
    )


# --- Vocabulário e desempenho --------------------------------------------------------------

CORPUS = """
import math
from os import path as p
nota = float(input("Nota: "))
if nota >= 7 and not nota > 10:
    print(f"Aprovado {nota:.1f}", end="")
elif nota is None:
    pass
else:
    x = [i ** 2 for i in range(10) if i % 2]
    y = {k: v for k, v in zip("ab", "cd")}
    z = {1, 2}
    w = (j for j in x)
    del x[0]
for a, b in enumerate(y):
    while a < b:
        a += 1
        break
def media(*valores, peso=1, **extras):
    global nota
    return sum(valores) / len(valores), peso
class C:
    pass
try:
    r = media(1, 2)
except (ValueError, TypeError) as erro:
    raise RuntimeError("falhou") from erro
with open("a") as arquivo:
    texto = arquivo.read()
match nota:
    case 1 | 2:
        n = ...
    case {"k": v, **resto}:
        n = resto
    case [primeiro, *demais]:
        n = demais
lambda q, /, *, k=2: q
assert nota, "msg"
s = 'ação'.média()
"""


def test_every_emitted_fact_belongs_to_the_rule_vocabulary() -> None:
    invalid = sorted({f.name for f in facts(CORPUS) if not is_valid_fact(f.name)})

    assert invalid == []


@pytest.mark.timing
def test_extraction_of_1000_lines_is_fast() -> None:
    source = "x = int(input())\nif x > 0:\n    print(x * 2, end='')\n" * 333

    start = time.perf_counter()
    found = facts(source)

    assert time.perf_counter() - start < 1.0
    assert len(found) > 1_000


@pytest.mark.parametrize(
    ("source", "nested"),
    [
        ("def f():\n    def g():\n        return 1\n    return g()\n", [(2, 5)]),
        ("def f():\n    return 1\ndef g():\n    return 2\n", []),
        ("g = lambda: 1\ndef f():\n    return g()\n", []),
        ("def f():\n    h = lambda: 1\n    return h()\n", []),
        ("class C:\n    def m(self):\n        return 1\n", []),
    ],
    ids=["def-in-def", "two-defs", "def-after-lambda", "lambda-in-def", "method"],
)
def test_function_inside_function_is_marked(source: str, nested: list[tuple[int, int]]) -> None:
    # Q-02 (f): função aninhada não consta; o def de dentro leva derived:nested_function.
    assert [(f.line, f.col) for f in facts(source) if f.name == "derived:nested_function"] == nested


def header_marks(source: str) -> list[tuple[int, str | None, int | None]]:
    return [
        (fact.col, fact.for_header, fact.zip_header_args)
        for fact in facts(source)
        if fact.name == "target:for_unpack"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # enumerate() built-in e x.items() como o iterável do for marcam o alvo (R-63 e R-65).
        ("for i, x in enumerate('ab'):\n    print(i)\n", [(5, "enumerate", None)]),
        ("d = {}\nfor k, v in d.items():\n    print(k)\n", [(5, "items", None)]),
        ("for a, b in zip('a', 'b'):\n    print(a)\n", [(5, None, 2)]),
        # Um enumerate do aluno, .items() com argumento e .values() não marcam.
        ("enumerate = 1\nfor i, x in enumerate:\n    print(i)\n", [(5, None, None)]),
        ("d = {}\nfor k, v in d.items(1):\n    print(k)\n", [(5, None, None)]),
        ("d = {}\nfor k, v in d.values():\n    print(k)\n", [(5, None, None)]),
        # Dentro de outra chamada do cabeçalho, ou numa compreensão, não é o comando for.
        ("for i, x in list(enumerate('ab')):\n    print(i)\n", [(5, None, None)]),
        ("x = [i for i, c in enumerate('ab')]\n", []),
    ],
    ids=[
        "enumerate",
        "items",
        "zip",
        "shadowed",
        "items-with-arg",
        "values",
        "wrapped",
        "comprehension",
    ],
)
def test_enumerate_and_items_in_the_for_header_are_marked(
    source: str, expected: list[tuple[int, str | None, int | None]]
) -> None:
    assert header_marks(source) == expected


def recursive_lines(source: str) -> list[int]:
    return [fact.line for fact in facts(source) if fact.name == "derived:recursion"]


@pytest.mark.parametrize(
    ("source", "lines"),
    [
        ("def f(n):\n    return f(n - 1)\n", [1]),
        # Recursão mútua (C-03): cada def do ciclo leva o fato.
        ("def a(n):\n    return b(n)\ndef b(n):\n    return a(n)\n", [1, 3]),
        (
            "def a():\n    return b()\ndef b():\n    return c()\ndef c():\n    return a()\n",
            [1, 3, 5],
        ),
        # Só quem está no ciclo: g chama f, mas ninguém chama g.
        ("def f(n):\n    return f(n)\ndef g():\n    return f(1)\n", [1]),
        # Não é recursão: chamada no módulo, referência sem chamada, parâmetro e lambda.
        ("def f(n):\n    return n\nprint(f(f(1)))\n", []),
        ("def f(n):\n    return f\n", []),
        ("def f(g):\n    return g(1)\n", []),
        # Um parâmetro ou uma variável local com o nome da função esconde o def.
        ("def f(f):\n    return f(1)\n", []),
        ("def f(n):\n    f = abs\n    return f(n)\n", []),
        ("f = lambda n: f(n - 1)\n", []),
        ("def f():\n    g = lambda: f()\n    return g\n", []),
    ],
    ids=[
        "direct",
        "mutual",
        "cycle-of-three",
        "only-the-cycle",
        "module-call",
        "reference",
        "parameter",
        "parameter-named-like-the-function",
        "local-named-like-the-function",
        "lambda",
        "call-inside-lambda",
    ],
)
def test_recursion_is_a_cycle_in_the_call_graph(source: str, lines: list[int]) -> None:
    assert recursive_lines(source) == lines


@pytest.mark.timing
def test_long_call_chain_does_not_recurse_in_the_extractor() -> None:
    # Um ciclo com 400 funções (800 linhas): o grafo é percorrido sem recursão do Python.
    count = 400
    source = "".join(f"def f{i}():\n    return f{(i + 1) % count}()\n" for i in range(count))

    start = time.perf_counter()
    lines = recursive_lines(source)

    assert time.perf_counter() - start < 1.0
    assert lines == [2 * i + 1 for i in range(count)]

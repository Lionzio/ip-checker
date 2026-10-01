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


def test_extraction_of_1000_lines_is_fast() -> None:
    source = "x = int(input())\nif x > 0:\n    print(x * 2, end='')\n" * 333

    start = time.perf_counter()
    found = facts(source)

    assert time.perf_counter() - start < 1.0
    assert len(found) > 1_000

"""Árvore canonizada (S27-01, ADR-07): cada camada, a turma (S27-02) e os trechos (S27-03).

O corpus de pares (``pares.yaml``) cobre as reescritas de ponta a ponta; aqui ficam as
propriedades de cada camada, medidas direto na árvore.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from conftest import BASE_RULESET
from ipc_analyzer.engine.guards import PayloadTooLargeError
from ipc_analyzer.engine.parse import SyntaxProblem, parse_source
from ipc_analyzer.engine.similarity import (
    CONTAINMENT_MIN_RATIO,
    MAX_CLASS,
    ClassMatch,
    ClassRejected,
    compare_class,
    compare_sources,
)
from ipc_analyzer.engine.similarity_tree import (
    MIN_MATCH,
    TreeFingerprint,
    class_idf,
    fingerprint,
    matches,
    scores,
)
from ipc_analyzer.runtime.pool import AnalyzerPool, PoolConfig
from similarity.test_similarity import _big_program

TARGET = (3, 13)


def tree(code: str) -> TreeFingerprint:
    parsed = parse_source(code, target=TARGET)
    assert not isinstance(parsed, SyntaxProblem)
    return fingerprint(parsed.tree)


def dice(first: str, second: str) -> float:
    return scores(tree(first), tree(second)).dice


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("x = a + b * c\n", "x = c * b + a\n"),
        ("ok = a and b or c\n", "ok = c or b and a\n"),
        ("if a == b:\n    print(1)\n", "if b == a:\n    print(1)\n"),
        ("if a > b:\n    print(1)\n", "if b < a:\n    print(1)\n"),
        ("t = 0\nt += n\nprint(t)\n", "t = 0\nt = t + n\nprint(t)\n"),
        (
            "if x != 0:\n    print('a')\nelse:\n    print('b')\n",
            "if x == 0:\n    print('b')\nelse:\n    print('a')\n",
        ),
        (
            "if x >= 7:\n    print('a')\nelse:\n    print('b')\n",
            "if 7 > x:\n    print('b')\nelse:\n    print('a')\n",
        ),
        (
            "def f(x):\n    if x < 0:\n        return 0\n    return x\n",
            "def f(x):\n    if x < 0:\n        return 0\n    else:\n        return x\n",
        ),
        ("for i in range(n):\n    print(i)\n", "i = 0\nwhile i < n:\n    print(i)\n    i += 1\n"),
        (
            "for x in v:\n    print(x)\n",
            "for i in range(len(v)):\n    print(v[i])\n",
        ),
        (
            "for x in v:\n    print(x)\n",
            "i = 0\nwhile i < len(v):\n    x = v[i]\n    print(x)\n    i = i + 1\n",
        ),
    ],
    ids=[
        "comutativos",
        "and-or",
        "igualdade",
        "maior-menor",
        "aumentada",
        "if-diferente",
        "if-ordem",
        "retorno-antecipado",
        "range-while",
        "range-len",
        "while-indice",
    ],
)
def test_equivalent_forms_have_the_same_tree(first: str, second: str) -> None:
    assert dice(first, second) == 1.0


def test_names_strings_and_comments_do_not_matter_but_builtins_and_numbers_do() -> None:
    base = "total = sum(v)  # soma\nprint('total', total * 2)\n"

    assert dice(base, "s = sum(lista)\nprint('resultado', s * 2)\n") == 1.0
    assert dice(base, "total = max(v)\nprint('total', total * 2)\n") < 1.0
    assert dice(base, "total = sum(v)\nprint('total', total * 3)\n") < 1.0


def inside(body: str) -> str:
    """O mesmo código dentro de uma função: no nível do módulo a ordem nunca conta, porque o
    módulo não entra no multiconjunto; dentro de um bloco, conta a ordem canônica."""
    lines = "".join(f"    {line}\n" for line in body.splitlines())
    return f"def main():\n{lines}"


def test_independent_lines_are_reordered_but_input_and_output_keep_their_order() -> None:
    swapped = dice(inside("a = 1\nb = 2\nprint(a, b)"), inside("b = 2\na = 1\nprint(a, b)"))
    reads = dice(
        inside("a = int(input())\nb = float(input())\nprint(a, b)"),
        inside("b = float(input())\na = int(input())\nprint(a, b)"),
    )
    dependent = dice(inside("a = 1\nb = a + 1\nprint(b)"), inside("b = a + 1\na = 1\nprint(b)"))

    assert swapped == 1.0
    # Ler na outra ordem muda o programa: a primeira linha da entrada vai para outra variável.
    assert reads < 1.0
    assert dependent < 1.0


def test_at_module_level_the_order_of_statements_never_counts() -> None:
    assert dice("a = int(input())\nb = input()\n", "b = input()\na = int(input())\n") == 1.0


def test_a_method_call_keeps_its_place_before_the_object_is_read() -> None:
    first = inside("v = []\nv.append(1)\nn = len(v)\nprint(n)")
    second = inside("v = []\nn = len(v)\nv.append(1)\nprint(n)")

    assert dice(first, second) < 1.0


def test_a_loop_is_a_barrier() -> None:
    first = inside("t = 0\nfor x in v:\n    t = t + x\nm = 2\nprint(t, m)")
    second = inside("t = 0\nm = 2\nfor x in v:\n    t = t + x\nprint(t, m)")

    assert dice(first, second) < 1.0


def test_containment_catches_padding_only_when_sizes_are_comparable() -> None:
    copy = "n = int(input())\nif n % 2 == 0:\n    print('par')\nelse:\n    print('impar')\n"
    padded = copy + "".join(f"lixo_{i} = [{i}, {i + 1}, {i + 2}]\n" for i in range(3))
    huge = copy + "".join(f"lixo_{i} = [{i}, {i + 1}, {i * 7}]\n" for i in range(200))

    padded_result = compare_sources(copy, padded, target=TARGET)
    huge_result = compare_sources(copy, huge, target=TARGET)

    assert padded_result.tree.containment == 1.0  # type: ignore[union-attr]
    assert padded_result.percent == 100.0  # type: ignore[union-attr]
    # Um código pequeno sempre "cabe" num grande: abaixo da razão mínima, vale o Dice.
    assert huge_result.tree.containment == 1.0  # type: ignore[union-attr]
    assert huge_result.percent < 80.0  # type: ignore[union-attr]
    assert 0 < CONTAINMENT_MIN_RATIO < 1


def test_the_scores_are_symmetric_and_deterministic() -> None:
    first = "def f(v):\n    return sum(v) / len(v)\nprint(f([1, 2]))\n"
    second = "def g(v):\n    t = sum(v)\n    return t / len(v)\nprint(g([3]))\n"

    forward, backward = scores(tree(first), tree(second)), scores(tree(second), tree(first))

    assert forward.dice == backward.dice
    assert forward == scores(tree(first), tree(second))


def test_matches_pair_the_same_structure_in_both_codes_without_overlap() -> None:
    first = (
        "def media(v):\n"
        "    return sum(v) / len(v)\n"
        "\n"
        "notas = [float(x) for x in input().split()]\n"
        "print(media(notas))\n"
    )
    second = (
        "notas = [float(x) for x in input().split()]\n"
        "\n"
        "\n"
        "def media(v):\n"
        "    return sum(v) / len(v)\n"
        "print(media(notas))\n"
    )

    found = matches(tree(first), tree(second))

    pairs = {(m.a.first, m.a.last, m.b.first, m.b.last) for m in found}
    assert (1, 2, 4, 5) in pairs
    assert (4, 4, 1, 1) in pairs
    assert all(m.size >= MIN_MATCH for m in found)
    assert [m.a.first for m in found] == sorted(m.a.first for m in found)
    lines = [line for m in found for line in range(m.a.first, m.a.last + 1)]
    assert len(lines) == len(set(lines))


def test_the_class_idf_makes_what_everybody_writes_count_little() -> None:
    common = "n = int(input())\nprint(n * 2 + 1)\n"
    target = common + "if n > 10:\n    print('grande')\n"
    copy = common + "if n > 10:\n    print('enorme')\n"
    others = [common + f"for i in range({k}):\n    print(i * {k})\n" for k in range(2, 12)]

    alone = scores(tree(target), tree(others[0]))
    results = compare_class(target, [*others, copy], target=TARGET)

    assert isinstance(results, list)
    by_class = [item.percent for item in results if isinstance(item, ClassMatch)]
    # Sozinho, o par divide metade do código; com a turma, a leitura comum quase não conta.
    assert alone.dice > 0.4
    assert max(by_class[:-1]) < 20.0
    assert by_class[-1] == 100.0


def test_class_idf_weights_are_between_zero_and_one() -> None:
    weights = class_idf([tree("x = int(input())\nprint(x)\n"), tree("y = int(input())\nz = 2\n")])

    assert weights
    assert all(0 < value <= 1.0 for value in weights.values())
    assert max(weights.values()) == 1.0


def test_the_class_reports_each_solution_in_order() -> None:
    results = compare_class(
        "x = int(input())\nprint(x)\n",
        ["y = int(input())\nprint(y)\n", "if True\n    pass\n", "", "#" + "a" * 51_200],
        target=TARGET,
    )

    assert isinstance(results, list)
    compared, broken, empty, huge = results
    assert isinstance(compared, ClassMatch)
    assert compared.percent == 100.0
    assert isinstance(broken, SyntaxProblem)
    assert isinstance(empty, ClassRejected)
    assert "vazio" in empty.message
    assert isinstance(huge, ClassRejected)


def test_the_compared_solution_with_a_syntax_error_or_too_big_is_the_whole_answer() -> None:
    assert isinstance(compare_class("if x\n", ["x = 1\n"], target=TARGET), SyntaxProblem)
    with pytest.raises(PayloadTooLargeError, match="Solução comparada"):
        compare_class("#" + "a" * 51_200, ["x = 1\n"], target=TARGET)


def test_the_class_has_a_ceiling() -> None:
    results = compare_class("x = 1\n", ["y = 2\n"] * (MAX_CLASS + 5), target=TARGET)

    assert isinstance(results, list)
    assert len(results) == MAX_CLASS


@pytest.mark.timing
def test_two_50_kb_codes_are_compared_in_under_one_second() -> None:
    """S27-01: as três métricas e os trechos, em menos de 1 s, medidos no worker do analisador.

    O worker roda em outro processo, sem o rastreamento da cobertura do pytest, que deixa o
    Python várias vezes mais lento: é o tempo que a equipe sente. Vale o melhor de três, para a
    medida ser do código e não da carga da máquina durante a suíte.
    """
    big = _big_program()
    other = big.replace("valor_", "saida_")
    pool = AnalyzerPool(BASE_RULESET, PoolConfig(workers=1, timeout_s=10.0))
    try:
        asyncio.run(pool.compare("x = 1\n", "y = 1\n"))  # aquece o worker
        timings = []
        for _ in range(3):
            start = time.perf_counter()
            result, _ = asyncio.run(pool.compare(big, other))
            timings.append(time.perf_counter() - start)
    finally:
        pool.close()

    assert result.percent == 100.0  # type: ignore[union-attr]
    assert min(timings) < 1.0, f"{min(timings):.2f} s"

"""Todos contra todos (S40-02): uma turma sintética de 30 soluções com dois grupos de cópias."""

from __future__ import annotations

import itertools
import time

from ipc_analyzer.engine.parse import SyntaxProblem
from ipc_analyzer.engine.similarity import MAX_MATRIX, ClassRejected, compare_all

TARGET = (3, 13)
ATTENTION = 90.0

COPY_A = [
    "nota = float(input())\nfaltas = int(input())\nif faltas > 10:\n    print('reprovado por falta')\n"  # noqa: E501
    "elif nota >= 7:\n    print('aprovado')\nelif nota >= 3:\n    print('final')\nelse:\n    print('reprovado')\n",  # noqa: E501
    "n = float(input())\nf = int(input())\nif f > 10:\n    print('reprovado por falta')\n"
    "elif n >= 7:\n    print('aprovado')\nelif n >= 3:\n    print('final')\nelse:\n    print('reprovado')\n",  # noqa: E501
    "x = float(input())\ny = int(input())\nif y > 10:\n    print('reprovado por falta')\n"
    "elif x >= 7:\n    print('aprovado')\nelif x >= 3:\n    print('final')\nelse:\n    print('reprovado')\n",  # noqa: E501
]
# Grupo B: as mesmas instruções independentes em outra ordem e com outros nomes.
COPY_B = [
    "a = int(input())\nb = int(input())\nc = int(input())\nmaior = max(a, b, c)\nmenor = min(a, b, c)\n"  # noqa: E501
    "meio = a + b + c - maior - menor\nprint(menor, meio, maior)\n",
    "p = int(input())\nq = int(input())\nr = int(input())\nlo = min(p, q, r)\nhi = max(p, q, r)\n"
    "mid = p + q + r - hi - lo\nprint(lo, mid, hi)\n",
    "u = int(input())\nv = int(input())\nw = int(input())\ntopo = max(u, v, w)\nbase = min(u, v, w)\n"  # noqa: E501
    "centro = u + v + w - topo - base\nprint(base, centro, topo)\n",
]
SNIPPETS = [
    "if n % 2 == 0:\n    print('par')\nelse:\n    print('ímpar')\n",
    "print(abs(n - 10))\n",
    "if n > 100:\n    n = 100\nprint(n)\n",
    "t = n * 1.8 + 32\nprint(round(t, 1))\n",
    "print('positivo' if n > 0 else 'não positivo')\n",
    "s = str(n)\nprint(len(s))\n",
    "if n % 3 == 0 and n % 5 == 0:\n    print('FizzBuzz')\nelif n % 3 == 0:\n    print('Fizz')\n",
    "h = n // 60\nm = n % 60\nprint(f'{h}h{m}min')\n",
    "if 18 <= n <= 65:\n    print('obrigatório')\n",
    "print(n ** 2 - 2 * n + 1)\n",
]


def _independent() -> list[str]:
    combos = itertools.combinations(range(len(SNIPPETS)), 2)
    return [
        "n = int(input())\n" + SNIPPETS[i] + SNIPPETS[j] for i, j in itertools.islice(combos, 24)
    ]


def test_all_against_all_finds_the_two_groups_of_copies_in_a_class_of_30() -> None:
    sources = COPY_A + _independent()[:12] + COPY_B + _independent()[12:]
    assert len(sources) == 30

    started = time.perf_counter()
    result = compare_all(sources, target=TARGET, group_min=ATTENTION)
    elapsed = time.perf_counter() - started

    a = (0, 1, 2)
    b = (15, 16, 17)
    assert sorted(result.groups) == sorted([a, b])
    assert len(result.pairs) == 30 * 29 // 2
    assert result.pairs[0].percent >= result.pairs[-1].percent
    assert all(problem is None for problem in result.problems)
    # Na máquina da CI a turma de 30 leva bem menos que o prazo de 10 s do analisador.
    assert elapsed < 5.0


def test_a_chain_of_similar_solutions_is_one_group() -> None:
    sources = [COPY_A[0], COPY_A[1], COPY_B[0]]

    result = compare_all(sources, target=TARGET, group_min=ATTENTION)

    assert result.groups == ((0, 1),)


def test_invalid_and_rejected_solutions_stay_out_of_the_pairs() -> None:
    sources = [COPY_A[0], "if x\n", COPY_A[1], "x = 1\n" * 1_100]

    result = compare_all(sources, target=TARGET, group_min=ATTENTION)

    assert isinstance(result.problems[1], SyntaxProblem)
    assert isinstance(result.problems[3], ClassRejected)
    assert [(pair.first, pair.second) for pair in result.pairs] == [(0, 2)]
    assert result.groups == ((0, 2),)


def test_the_class_is_capped() -> None:
    result = compare_all(
        [f"x = {n}\nprint(x)\n" for n in range(MAX_MATRIX + 5)], target=TARGET, group_min=ATTENTION
    )

    assert len(result.problems) == MAX_MATRIX

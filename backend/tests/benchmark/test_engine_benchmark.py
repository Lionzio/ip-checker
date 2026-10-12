"""Benchmark do motor no CI (S35-01, NFR-02). Só roda com ``IPC_BENCHMARK`` definido (``1`` confere,
``atualizar`` grava a linha de base), num passo próprio da CI: a medida leva cerca de 1 minuto.
"""

from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path

import pytest

from conftest import RULESETS
from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.ruleset import load_ruleset
from ipc_analyzer.engine.similarity import compare_sources

from .engine_benchmark import (
    LARGE_RUNS,
    MAX_CHECKED_BYTES,
    RUNS,
    measure,
    regressions,
    too_slow,
)

MODE = os.environ.get("IPC_BENCHMARK", "")
BASELINE = Path(__file__).with_name("linha-de-base.json")

pytestmark = pytest.mark.skipif(
    MODE not in {"1", "atualizar"}, reason="defina IPC_BENCHMARK=1 para medir o motor"
)


def _large() -> str:
    """Perto do limite de 50 KB e de 1.000 linhas, com condicionais em todas as linhas."""
    lines = [
        f"x{i} = (a{i % 7} + b{i % 5}) * c{i % 3} - d{i % 11} // 2 if a{i % 7} > b{i % 5} else {i}"
        for i in range(960)
    ]
    code = "\n".join(lines) + "\n"
    assert 45_000 < len(code.encode()) <= 51_200
    return code


INPUTS: dict[str, tuple[int, str]] = {
    "lista1_condicionais": (
        1,
        "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelif nota >= 3:\n"
        "    print('Final')\nelse:\n    print('Reprovado')\n",
    ),
    "lista2_laco": (
        2,
        "n = int(input())\ntotal = 0\nfor i in range(n):\n    x = int(input())\n"
        "    if x % 2 == 0:\n        total += x\nprint(total)\n",
    ),
    "lista4_funcoes": (
        4,
        "def media(v):\n    s = 0\n    for x in v:\n        s += x\n    return s / len(v)\n"
        "def maior(v):\n    m = v[0]\n    for x in v:\n        if x > m:\n            m = x\n"
        "    return m\nnotas = [float(x) for x in input().split()]\n"
        "print(media(notas), maior(notas))\n",
    ),
    "lista6_recursao": (
        6,
        "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"
        "print(fib(int(input())))\n",
    ),
    "proibicoes_variadas": (
        1,
        "import os\nx = None\ntry:\n    print({1, 2})\nexcept Exception:\n    exit()\n",
    ),
    "grande_50kb": (1, _large()),
}


def test_the_engine_stays_within_the_budget_and_the_baseline() -> None:
    ruleset = load_ruleset(RULESETS)
    measures = {
        name: measure(
            partial(analyze_source, code, list_number=lst, ruleset=ruleset),
            LARGE_RUNS if len(code.encode()) > MAX_CHECKED_BYTES else RUNS,
        )
        for name, (lst, code) in INPUTS.items()
    }
    big = INPUTS["grande_50kb"][1]
    measures["plagio_50kb"] = measure(
        lambda: compare_sources(big, big, target=ruleset.target_version), LARGE_RUNS
    )
    for name, value in measures.items():
        print(f"{name}: P95 {value.p95_ms:.2f} ms, razão {value.ratio:.2f}")

    if MODE == "atualizar":
        BASELINE.write_text(
            json.dumps(
                {name: round(value.ratio, 3) for name, value in sorted(measures.items())},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    p95s = {
        name: measures[name].p95_ms
        for name, (_, code) in INPUTS.items()
        if len(code.encode()) <= MAX_CHECKED_BYTES
    }
    problems = too_slow(p95s) + regressions(
        baseline,
        {name: value.ratio for name, value in measures.items()},
        reference_ms={name: value.reference_ms for name, value in measures.items()},
    )

    assert problems == [], "\n".join(problems)
    assert set(baseline) == set(measures), "entrada nova: grave a linha de base de novo"

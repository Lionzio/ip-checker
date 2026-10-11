"""Benchmark do motor (S35-01, NFR-02): o P95 da análise por entrada, contra uma linha de base.

O tempo absoluto muda de máquina para máquina (esta, os runners do GitHub, o Render). Por isso a
linha de base guarda, para cada entrada, a **razão** entre a mediana do tempo da análise e a de uma
carga de calibração (``ast.parse`` e ``ast.walk`` de um código fixo, cerca de 10 ms), medida na
mesma rodada: a razão não depende da velocidade da máquina, e um motor 30% mais lento aparece como
uma razão 30% maior. A mediana é mais estável que o P95 com poucas amostras; cada número final é a
mediana de 5 rodadas (os runners variam).

Dois critérios: o P95 de cada entrada de até 5 KB (o tamanho do NFR-01) fica em até 50 ms, e a razão
de toda entrada não passa de 120% da linha de base. A entrada de 50 KB fica só com a linha de base:
medida em 11/10/2026, ela leva cerca de 250 ms nesta máquina, de forma linear no tamanho, acima dos
50 ms que o NFR-02 pede para entradas de até 50 KB (Q-25, decisão do autor).

Para gravar uma linha de base nova (depois de uma mudança aceita no motor), rode de ``backend/``
com ``IPC_BENCHMARK=atualizar``.
"""

from __future__ import annotations

import ast
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

#: NFR-02: P95 da análise de uma entrada; conferido até ``MAX_CHECKED_BYTES`` (Q-25).
MAX_P95_MS = 50.0
MAX_CHECKED_BYTES = 5 * 1024
#: Repetições por rodada nas entradas grandes, para o passo da CI não passar de 1 minuto.
LARGE_RUNS = 10
#: Uma razão até 20% acima da linha de base é variação; acima disso, regressão.
TOLERANCE = 1.20
ROUNDS = 5
RUNS = 30

_CALIBRATION_CODE = "\n".join(
    f"def f{i}(a, b):\n    if a > b:\n        return [a * x for x in range({i})]\n    return b"
    for i in range(400)
)


@dataclass(frozen=True, slots=True)
class Measure:
    p95_ms: float
    ratio: float


@dataclass(frozen=True, slots=True)
class Timing:
    p95_ms: float
    median_ms: float


def p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


def timed(action: Callable[[], object], runs: int = RUNS) -> Timing:
    """O P95 e a mediana, em milissegundos, de ``runs`` execuções (depois de uma de aquecimento)."""
    action()
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    return Timing(p95(samples), statistics.median(samples))


def calibration() -> None:
    for _ in ast.walk(ast.parse(_CALIBRATION_CODE)):
        pass


def measure(action: Callable[[], object], runs: int = RUNS) -> Measure:
    """A mediana de 5 rodadas do P95 da ação e da razão das medianas contra a calibração."""
    values, ratios = [], []
    for _ in range(ROUNDS):
        reference = timed(calibration, 10)
        value = timed(action, runs)
        values.append(value.p95_ms)
        ratios.append(value.median_ms / reference.median_ms)
    return Measure(statistics.median(values), statistics.median(ratios))


def regressions(
    baseline: dict[str, float], current: dict[str, float], tolerance: float = TOLERANCE
) -> list[str]:
    """As entradas cuja razão passou da linha de base com a tolerância, com os números."""
    return [
        f"{name}: razão {current[name]:.2f} > {baseline[name]:.2f} * {tolerance:.2f}"
        for name in sorted(baseline)
        if name in current and current[name] > baseline[name] * tolerance
    ]


def too_slow(p95s: dict[str, float], limit: float = MAX_P95_MS) -> list[str]:
    return [
        f"{name}: P95 {value:.1f} ms > {limit:.0f} ms (NFR-02)"
        for name, value in sorted(p95s.items())
        if value > limit
    ]

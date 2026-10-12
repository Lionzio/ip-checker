"""Benchmark do motor (S35-01, NFR-02): o P95 da análise por entrada, contra uma linha de base.

O tempo absoluto muda de máquina para máquina (esta, os runners do GitHub, o Render). Por isso a
linha de base guarda, para cada entrada, a **razão** entre a mediana do tempo da análise e a de uma
carga de calibração (``ast.parse`` e ``ast.walk`` de um código fixo, cerca de 10 ms), medida na
mesma rodada: a razão não depende da velocidade da máquina, e um motor 30% mais lento aparece como
uma razão 30% maior. A mediana é mais estável que o P95 com poucas amostras; cada número final é a
mediana de 5 rodadas (os runners variam).

Dois critérios: o P95 de cada entrada de até 5 KB (o tamanho do NFR-01) fica em até 50 ms, e a razão
de toda entrada não passa de 120% da linha de base, com uma diferença de mais de 0,5 ms (S36-10: nas
entradas pequenas, décimos de milissegundo são ruído). A entrada de 50 KB fica só com a linha de
base: medida em 11/10/2026, ela leva cerca de 250 ms nesta máquina, de forma linear no tamanho,
dentro do NFR-02 revisto pela Q-25 (até 50 ms para 5 KB e linear até 50 KB, cerca de 500 ms, com o
teto de 2 s por análise). No piloto, com 0,1 CPU, leva cerca de 3 s (S36-06, ADR-03).

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
#: E só se a diferença também passar deste tempo (S36-10): nas entradas pequenas, que levam décimos
#: de milissegundo, o ruído da máquina passa dos 20% sem nenhuma mudança no motor. O teto de 50 ms
#: do NFR-02 continua valendo para elas; nas grandes, 20% já é muito mais que este piso.
MIN_DELTA_MS = 0.5
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
    #: A mediana da calibração na mesma rodada, para converter a razão em milissegundos.
    reference_ms: float = 0.0


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
    values, ratios, references = [], [], []
    for _ in range(ROUNDS):
        reference = timed(calibration, 10)
        value = timed(action, runs)
        values.append(value.p95_ms)
        ratios.append(value.median_ms / reference.median_ms)
        references.append(reference.median_ms)
    return Measure(
        statistics.median(values), statistics.median(ratios), statistics.median(references)
    )


def regressions(
    baseline: dict[str, float],
    current: dict[str, float],
    tolerance: float = TOLERANCE,
    reference_ms: dict[str, float] | None = None,
    min_delta_ms: float = MIN_DELTA_MS,
) -> list[str]:
    """As entradas cuja razão passou da linha de base com a tolerância, com os números.

    Com ``reference_ms`` (a calibração de cada entrada, em milissegundos), a diferença também
    precisa passar de ``min_delta_ms`` (S36-10): décimos de milissegundo são ruído, não regressão.
    """
    problems = []
    for name in sorted(baseline):
        if name not in current or current[name] <= baseline[name] * tolerance:
            continue
        message = f"{name}: razão {current[name]:.2f} > {baseline[name]:.2f} * {tolerance:.2f}"
        if reference_ms is not None and name in reference_ms:
            delta_ms = (current[name] - baseline[name]) * reference_ms[name]
            if delta_ms <= min_delta_ms:
                continue
            message += f" (+{delta_ms:.2f} ms)"
        problems.append(message)
    return problems


def too_slow(p95s: dict[str, float], limit: float = MAX_P95_MS) -> list[str]:
    return [
        f"{name}: P95 {value:.1f} ms > {limit:.0f} ms (NFR-02)"
        for name, value in sorted(p95s.items())
        if value > limit
    ]

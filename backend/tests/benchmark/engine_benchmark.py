"""Benchmark do motor (S35-01, NFR-02): o P95 da análise por entrada, contra uma linha de base.

O tempo absoluto muda de máquina para máquina (esta, os runners do GitHub, o Render). Por isso a
linha de base guarda, para cada entrada, a **razão** entre o tempo da análise e o de uma carga de
calibração (``ast.parse`` e ``ast.walk`` de um código fixo, cerca de 10 ms): a razão não depende da
velocidade da máquina, e um motor 30% mais lento aparece como uma razão 30% maior.

Desde a S40-04, a razão é **pareada**: cada amostra mede uma calibração, a ação e outra
calibração, e divide a ação pela média das duas. Antes, a calibração (10 execuções de 10 ms) era
medida toda antes da ação (10 execuções de 500 ms, na entrada de 50 KB), e as duas pegavam momentos
diferentes da carga da máquina: em 15/10/2026, com o notebook ocupado, a razão do ``plagio_50kb``
subiu de 41 para 52 sem nenhuma mudança no motor. Com as calibrações em volta da ação, as três
medidas sentem a mesma carga. A mediana é mais estável que o P95 com poucas amostras; cada número
final é a mediana de 5 rodadas (os runners variam).

Dois critérios: o P95 de cada entrada de até 5 KB (o tamanho do NFR-01) fica em até 50 ms, e a razão
de toda entrada não passa de 120% da linha de base, com uma diferença de mais de 0,5 ms (S36-10: nas
entradas pequenas, décimos de milissegundo são ruído). Uma entrada que passa da tolerância é medida
de novo, até 2 vezes, e só é regressão se passar nas três medidas (S40-04): a carga só deixa o motor
mais lento, nunca mais rápido, então uma regressão de verdade estoura nas três, e o ruído raramente
estoura. A entrada de 50 KB fica só com a linha de base: medida em 11/10/2026, ela leva cerca de
250 ms nesta máquina, de forma linear no tamanho, dentro do NFR-02 revisto pela Q-25 (até 50 ms para
5 KB e linear até 50 KB, cerca de 500 ms, com o teto de 2 s por análise). No piloto, com 0,1 CPU,
leva cerca de 3 s (S36-06, ADR-03).

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
#: Novas medidas de uma entrada que passou da tolerância (S40-04): ela só é regressão se passar
#: em todas.
ATTEMPTS = 2
ROUNDS = 5
RUNS = 30

Clock = Callable[[], float]

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


def _elapsed_ms(action: Callable[[], object], clock: Clock) -> float:
    started = clock()
    action()
    return (clock() - started) * 1000


def timed(
    action: Callable[[], object], runs: int = RUNS, clock: Clock = time.perf_counter
) -> Timing:
    """O P95 e a mediana, em milissegundos, de ``runs`` execuções (depois de uma de aquecimento)."""
    action()
    samples = [_elapsed_ms(action, clock) for _ in range(runs)]
    return Timing(p95(samples), statistics.median(samples))


def calibration() -> None:
    for _ in ast.walk(ast.parse(_CALIBRATION_CODE)):
        pass


def paired(
    action: Callable[[], object],
    runs: int = RUNS,
    *,
    calibrate: Callable[[], object] = calibration,
    clock: Clock = time.perf_counter,
) -> Measure:
    """Uma rodada: o P95 da ação e a mediana das razões de cada amostra (S40-04).

    Cada amostra mede uma calibração, a ação e outra calibração, e a razão é a ação dividida pela
    média das duas calibrações: as três medidas sentem a mesma carga da máquina.
    """
    action()
    calibrate()
    samples, ratios, references = [], [], []
    for _ in range(runs):
        before = _elapsed_ms(calibrate, clock)
        value = _elapsed_ms(action, clock)
        after = _elapsed_ms(calibrate, clock)
        reference = (before + after) / 2
        samples.append(value)
        ratios.append(value / reference)
        references.append(reference)
    return Measure(p95(samples), statistics.median(ratios), statistics.median(references))


def measure(
    action: Callable[[], object],
    runs: int = RUNS,
    *,
    calibrate: Callable[[], object] = calibration,
    clock: Clock = time.perf_counter,
) -> Measure:
    """A mediana de 5 rodadas pareadas: P95 da ação, razão e calibração."""
    rounds = [paired(action, runs, calibrate=calibrate, clock=clock) for _ in range(ROUNDS)]
    return Measure(
        statistics.median(value.p95_ms for value in rounds),
        statistics.median(value.ratio for value in rounds),
        statistics.median(value.reference_ms for value in rounds),
    )


def _exceeds(
    baseline: float,
    ratio: float,
    tolerance: float,
    reference_ms: float | None,
    min_delta_ms: float,
) -> bool:
    """A razão passou da linha de base com a tolerância e, com a calibração, do piso em ms."""
    if ratio <= baseline * tolerance:
        return False
    return reference_ms is None or (ratio - baseline) * reference_ms > min_delta_ms


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
        if name not in current:
            continue
        reference = reference_ms.get(name) if reference_ms is not None else None
        if not _exceeds(baseline[name], current[name], tolerance, reference, min_delta_ms):
            continue
        message = f"{name}: razão {current[name]:.2f} > {baseline[name]:.2f} * {tolerance:.2f}"
        if reference is not None:
            message += f" (+{(current[name] - baseline[name]) * reference:.2f} ms)"
        problems.append(message)
    return problems


def confirmed_regressions(
    baseline: dict[str, float],
    current: dict[str, Measure],
    remeasure: Callable[[str], Measure],
    *,
    attempts: int = ATTEMPTS,
    tolerance: float = TOLERANCE,
    min_delta_ms: float = MIN_DELTA_MS,
    report: Callable[[str], object] | None = None,
) -> list[str]:
    """As regressões confirmadas (S40-04): só as entradas que passaram da tolerância são medidas
    de novo, até ``attempts`` vezes, e uma entrada só é regressão se passar em todas as medidas.

    A carga da máquina só deixa o motor mais lento, nunca mais rápido: uma regressão de verdade
    estoura em todas as medidas, e o ruído raramente estoura em três seguidas. ``report`` recebe
    cada nova medida, para o log da CI mostrar o que foi medido de novo, inclusive o que passou.
    """
    problems = []
    for name in sorted(baseline):
        if name not in current:
            continue
        taken = [current[name]]
        while len(taken) <= attempts and _exceeds(
            baseline[name], taken[-1].ratio, tolerance, taken[-1].reference_ms, min_delta_ms
        ):
            again = remeasure(name)
            taken.append(again)
            if report is not None:
                report(
                    f"{name}: medida de novo ({len(taken)} de {attempts + 1}): "
                    f"razão {again.ratio:.2f} (máximo {baseline[name] * tolerance:.2f})"
                )
        if not all(
            _exceeds(baseline[name], value.ratio, tolerance, value.reference_ms, min_delta_ms)
            for value in taken
        ):
            continue
        least = min(taken, key=lambda value: value.ratio)
        ratios = " / ".join(f"{value.ratio:.2f}" for value in taken)
        problems.append(
            f"{name}: razões {ratios} > {baseline[name]:.2f} * {tolerance:.2f}"
            f" (+{(least.ratio - baseline[name]) * least.reference_ms:.2f} ms)"
        )
    return problems


def too_slow(p95s: dict[str, float], limit: float = MAX_P95_MS) -> list[str]:
    return [
        f"{name}: P95 {value:.1f} ms > {limit:.0f} ms (NFR-02)"
        for name, value in sorted(p95s.items())
        if value > limit
    ]

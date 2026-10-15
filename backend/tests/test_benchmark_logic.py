"""A lógica do benchmark do motor (S35-01): o que é regressão e o que é variação."""

from __future__ import annotations

import pytest

from benchmark.engine_benchmark import (
    Measure,
    confirmed_regressions,
    p95,
    paired,
    regressions,
    timed,
    too_slow,
)


def test_a_30_percent_slower_engine_fails_and_10_percent_does_not() -> None:
    baseline = {"lista1": 2.0, "grande": 10.0}

    assert regressions(baseline, {"lista1": 2.6, "grande": 10.0}) == [
        "lista1: razão 2.60 > 2.00 * 1.20"
    ]
    assert regressions(baseline, {"lista1": 2.2, "grande": 11.0}) == []


def test_noise_of_tenths_of_a_millisecond_is_not_a_regression() -> None:
    """S36-10: na CI de 12/10/2026, 0,035 virou 0,045 (0,1 ms) numa entrada pequena."""
    baseline = {"lista6": 0.035, "grande": 17.6}
    references = {"lista6": 10.0, "grande": 10.0}

    assert regressions(baseline, {"lista6": 0.045, "grande": 17.6}, reference_ms=references) == []
    assert regressions(baseline, {"lista6": 0.2, "grande": 17.6}, reference_ms=references) == [
        "lista6: razão 0.20 > 0.04 * 1.20 (+1.65 ms)"
    ]
    assert regressions(baseline, {"lista6": 0.035, "grande": 22.0}, reference_ms=references) == [
        "grande: razão 22.00 > 17.60 * 1.20 (+44.00 ms)"
    ]


def test_a_new_input_without_baseline_is_not_a_regression() -> None:
    assert regressions({"lista1": 2.0}, {"lista1": 2.0, "nova": 99.0}) == []


def test_the_absolute_limit_is_the_nfr_02() -> None:
    assert too_slow({"lista1": 3.0, "grande": 51.0}) == ["grande: P95 51.0 ms > 50 ms (NFR-02)"]


def test_p95_and_timing() -> None:
    assert p95([float(i) for i in range(1, 101)]) == 95.0
    timing = timed(lambda: sum(range(100)), runs=5)
    assert 0.0 <= timing.median_ms <= timing.p95_ms


class _LoadedMachine:
    """Um relógio falso: a calibração leva 10 ms e a ação, ``action_ms``, ambos multiplicados pela
    carga da máquina, que dobra a partir da operação ``switch_at`` (contando aquecimentos)."""

    def __init__(self, action_ms: float = 100.0, switch_at: int | None = None) -> None:
        self.now = 0.0
        self.ops = 0
        self.action_ms = action_ms
        self.switch_at = switch_at

    def clock(self) -> float:
        return self.now

    def _run(self, ms: float) -> None:
        load = 2.0 if self.switch_at is not None and self.ops >= self.switch_at else 1.0
        self.ops += 1
        self.now += ms * load / 1000

    def calibrate(self) -> None:
        self._run(10.0)

    def action(self) -> None:
        self._run(self.action_ms)


def test_the_paired_ratio_ignores_load_that_changes_during_the_round() -> None:
    """S40-04: a carga dobra na 6ª de 10 amostras (2 aquecimentos + 5 amostras de 3 operações)."""
    machine = _LoadedMachine(switch_at=17)

    value = paired(machine.action, 10, calibrate=machine.calibrate, clock=machine.clock)

    assert value.ratio == pytest.approx(10.0)
    assert value.p95_ms == pytest.approx(200.0)  # a ação levou 200 ms na metade carregada
    assert value.reference_ms == pytest.approx(15.0)  # a mediana das calibrações, entre 10 e 20

    # O método anterior (toda a calibração antes da ação) via 15: 50% de "regressão" sem nenhuma.
    before = _LoadedMachine(switch_at=17)
    reference = timed(before.calibrate, 10, clock=before.clock)
    action = timed(before.action, 10, clock=before.clock)
    assert action.median_ms / reference.median_ms == pytest.approx(15.0)


def test_a_30_percent_slower_engine_fails_under_load_too() -> None:
    machine = _LoadedMachine(action_ms=130.0, switch_at=17)

    value = paired(machine.action, 10, calibrate=machine.calibrate, clock=machine.clock)

    assert value.ratio == pytest.approx(13.0)
    assert regressions({"grande": 10.0}, {"grande": value.ratio}) == [
        "grande: razão 13.00 > 10.00 * 1.20"
    ]


def _measure(ratio: float) -> Measure:
    return Measure(p95_ms=ratio * 10, ratio=ratio, reference_ms=10.0)


def test_noise_that_passes_when_measured_again_is_not_a_regression() -> None:
    """S40-04: estourou na 1ª medida e passou na 2ª; a 3ª não acontece."""
    again = iter([_measure(11.0)])
    remeasured: list[str] = []
    reports: list[str] = []

    def remeasure(name: str) -> Measure:
        remeasured.append(name)
        return next(again)

    problems = confirmed_regressions(
        {"grande": 10.0, "lista1": 2.0},
        {"grande": _measure(13.0), "lista1": _measure(2.0)},
        remeasure,
        report=reports.append,
    )

    assert problems == []
    assert remeasured == ["grande"]  # só o que estourou, e uma vez só
    assert reports == ["grande: medida de novo (2 de 3): razão 11.00 (máximo 12.00)"]


def test_a_regression_in_all_three_measures_fails_with_the_three_ratios() -> None:
    again = iter([_measure(12.5), _measure(13.2)])

    problems = confirmed_regressions(
        {"grande": 10.0}, {"grande": _measure(13.0)}, lambda _name: next(again)
    )

    assert problems == ["grande: razões 13.00 / 12.50 / 13.20 > 10.00 * 1.20 (+25.00 ms)"]


def test_at_most_two_new_measures_and_the_last_one_can_still_clear() -> None:
    again = iter([_measure(13.0), _measure(11.9), _measure(99.0)])
    remeasured: list[str] = []

    def remeasure(name: str) -> Measure:
        remeasured.append(name)
        return next(again)

    problems = confirmed_regressions({"grande": 10.0}, {"grande": _measure(13.0)}, remeasure)

    assert problems == []
    assert remeasured == ["grande", "grande"]


def test_the_confirmation_keeps_the_floor_of_half_a_millisecond() -> None:
    """S36-10 continua valendo: 0,035 → 0,045 (0,1 ms) não é medido de novo."""
    small = Measure(p95_ms=0.45, ratio=0.045, reference_ms=10.0)

    problems = confirmed_regressions(
        {"lista6": 0.035}, {"lista6": small}, lambda _name: _measure(99.0)
    )

    assert problems == []

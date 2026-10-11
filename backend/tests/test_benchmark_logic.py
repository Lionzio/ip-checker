"""A lógica do benchmark do motor (S35-01): o que é regressão e o que é variação."""

from __future__ import annotations

from benchmark.engine_benchmark import p95, regressions, timed, too_slow


def test_a_30_percent_slower_engine_fails_and_10_percent_does_not() -> None:
    baseline = {"lista1": 2.0, "grande": 10.0}

    assert regressions(baseline, {"lista1": 2.6, "grande": 10.0}) == [
        "lista1: razão 2.60 > 2.00 * 1.20"
    ]
    assert regressions(baseline, {"lista1": 2.2, "grande": 11.0}) == []


def test_a_new_input_without_baseline_is_not_a_regression() -> None:
    assert regressions({"lista1": 2.0}, {"lista1": 2.0, "nova": 99.0}) == []


def test_the_absolute_limit_is_the_nfr_02() -> None:
    assert too_slow({"lista1": 3.0, "grande": 51.0}) == ["grande: P95 51.0 ms > 50 ms (NFR-02)"]


def test_p95_and_timing() -> None:
    assert p95([float(i) for i in range(1, 101)]) == 95.0
    timing = timed(lambda: sum(range(100)), runs=5)
    assert 0.0 <= timing.median_ms <= timing.p95_ms

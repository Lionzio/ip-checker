"""Pool isolado de workers (S5-01): processo separado, tempo limite, memória e reciclagem.

As funções abaixo rodam dentro dos workers; por isso ficam no nível do módulo, para que o
processo filho consiga importá-las.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from conftest import BASE_RULESET
from ipc_analyzer.engine.guards import AnalysisLimitError, InvalidInputError
from ipc_analyzer.runtime.limits import MIB, ResourceLimits
from ipc_analyzer.runtime.pool import AnalyzerPool, PoolConfig

linux_only = pytest.mark.skipif(
    sys.platform == "win32", reason="limites de recursos (módulo resource) só existem em Unix"
)


def _pid() -> int:
    return os.getpid()


def _sleep(seconds: float) -> str:
    time.sleep(seconds)
    return "acordou"


def _raise_memory_error() -> None:
    raise MemoryError


def _die() -> None:
    os._exit(3)


def _allocate(megabytes: int) -> int:
    return len(bytearray(megabytes * MIB))


def _limits() -> tuple[int, int, int, int, int]:
    import resource

    return (
        resource.getrlimit(resource.RLIMIT_AS)[0],
        resource.getrlimit(resource.RLIMIT_FSIZE)[0],
        resource.getrlimit(resource.RLIMIT_NOFILE)[0],
        resource.getrlimit(resource.RLIMIT_NPROC)[0],
        resource.getrlimit(resource.RLIMIT_CORE)[0],
    )


def _write_file(path: str) -> str:
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("invadido")
    except OSError as exc:
        return type(exc).__name__
    return "gravou"


#: Código válido na Lista 1: usa o assunto da lista, um comando condicional (R-02).
VALID_L1 = "x = int(input())\nif x > 0:\n    print(x)\n"


def run(pool: AnalyzerPool, function: Any, *args: Any) -> Any:
    return asyncio.run(pool.run(function, *args))


@pytest.fixture(scope="module")
def pool() -> Iterator[AnalyzerPool]:
    analyzer_pool = AnalyzerPool(BASE_RULESET, PoolConfig(workers=1, timeout_s=1.0))
    yield analyzer_pool
    analyzer_pool.close()


def test_analysis_runs_in_another_process(pool: AnalyzerPool) -> None:
    result = asyncio.run(pool.analyze("x = None\n", 1))

    assert result.status == "invalid"
    assert [v.rule_id for v in result.violations] == ["R-02", "R-13"]
    assert run(pool, _pid) != os.getpid()


def test_input_errors_cross_the_process_boundary(pool: AnalyzerPool) -> None:
    with pytest.raises(InvalidInputError, match="vazio"):
        asyncio.run(pool.analyze("  ", 1))


@pytest.mark.timing
def test_timeout_kills_and_replaces_the_worker(pool: AnalyzerPool) -> None:
    before = run(pool, _pid)
    start = time.perf_counter()

    with pytest.raises(AnalysisLimitError, match="tempo limite de 1 s"):
        run(pool, _sleep, 30)

    assert time.perf_counter() - start < 5
    assert run(pool, _pid) != before
    assert asyncio.run(pool.analyze(VALID_L1, 1)).status == "valid"


def test_memory_error_becomes_analysis_limit(pool: AnalyzerPool) -> None:
    with pytest.raises(AnalysisLimitError, match="memória demais"):
        run(pool, _raise_memory_error)


def test_dead_worker_becomes_analysis_limit(pool: AnalyzerPool) -> None:
    with pytest.raises(AnalysisLimitError, match="interrompida"):
        run(pool, _die)

    assert asyncio.run(pool.analyze(VALID_L1, 1)).status == "valid"


def test_workers_are_recycled_after_max_tasks() -> None:
    recycling = AnalyzerPool(BASE_RULESET, PoolConfig(workers=1, max_tasks=1))
    try:
        pids = {run(recycling, _pid) for _ in range(3)}
    finally:
        recycling.close()

    assert len(pids) == 3


@linux_only
def test_resource_limits_are_applied(pool: AnalyzerPool) -> None:
    defaults = ResourceLimits()

    assert run(pool, _limits) == (defaults.memory_bytes, 0, defaults.max_open_files, 0, 0)


@linux_only
def test_worker_cannot_write_files(pool: AnalyzerPool, tmp_path: Path) -> None:
    target = tmp_path / "canario.txt"

    assert run(pool, _write_file, str(target)) == "OSError"
    assert not target.exists() or target.stat().st_size == 0


@linux_only
def test_large_allocation_hits_the_memory_limit(pool: AnalyzerPool) -> None:
    with pytest.raises(AnalysisLimitError, match="memória demais"):
        run(pool, _allocate, 2048)

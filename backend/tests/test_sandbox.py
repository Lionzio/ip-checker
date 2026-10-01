"""Filtro seccomp dos workers (S11-01, NFR-07 na Fase 1).

Os testes que instalam o filtro de verdade rodam num processo do pool, para não fechar o
processo do pytest. Os que dependem do Linux são pulados no Windows e rodam na CI.
"""

from __future__ import annotations

import asyncio
import errno
import os
import socket
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures.process import BrokenProcessPool
from typing import Any

import pytest
from fastapi.testclient import TestClient

from conftest import BASE_RULESET
from ipc_analyzer.engine.guards import AnalysisLimitError
from ipc_analyzer.runtime import sandbox
from ipc_analyzer.runtime.pool import AnalyzerPool, PoolConfig
from ipc_analyzer.runtime.sandbox import SandboxMode, SandboxUnavailable, enforce
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings

linux_only = pytest.mark.skipif(
    sys.platform != "linux", reason="seccomp e libseccomp só existem em Linux"
)


# --- Modos -------------------------------------------------------------------------------------


@pytest.fixture
def unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "apply_sandbox", lambda: False)


@pytest.fixture
def available(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    calls: list[bool] = []

    def apply() -> bool:
        calls.append(True)
        return True

    monkeypatch.setattr(sandbox, "apply_sandbox", apply)
    return calls


def test_off_never_installs_the_filter(available: list[bool]) -> None:
    assert enforce(SandboxMode.OFF) is False
    assert available == []


@pytest.mark.parametrize("mode", [SandboxMode.OPTIONAL, SandboxMode.REQUIRED])
def test_filter_is_installed_when_the_system_allows(
    available: list[bool], mode: SandboxMode
) -> None:
    assert enforce(mode) is True
    assert available == [True]


@pytest.mark.usefixtures("unavailable")
def test_optional_mode_tolerates_a_system_without_seccomp() -> None:
    assert enforce(SandboxMode.OPTIONAL) is False


@pytest.mark.usefixtures("unavailable")
def test_required_mode_refuses_a_system_without_seccomp() -> None:
    with pytest.raises(SandboxUnavailable, match="IPC_SANDBOX=required"):
        enforce(SandboxMode.REQUIRED)


def test_without_libseccomp_the_filter_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyseccomp", None)  # importação falha, como no Windows

    assert sandbox.apply_sandbox() is False


def test_blocked_syscalls_cover_network_and_program_execution() -> None:
    assert set(sandbox.BLOCKED_SYSCALLS) == {"socket", "socketpair", "execve", "execveat"}


@pytest.mark.parametrize(
    ("value", "mode"),
    [(None, SandboxMode.OPTIONAL), ("off", SandboxMode.OFF), ("required", SandboxMode.REQUIRED)],
)
def test_mode_comes_from_the_environment(value: str | None, mode: SandboxMode) -> None:
    env = {} if value is None else {"IPC_SANDBOX": value}

    assert AnalyzerSettings.from_env(env).pool.sandbox is mode


def test_unknown_mode_prevents_startup() -> None:
    with pytest.raises(ValueError, match="talvez"):
        AnalyzerSettings.from_env({"IPC_SANDBOX": "talvez"})


# --- O filtro de verdade, dentro de um worker --------------------------------------------------


def _try_everything() -> dict[str, str]:
    """Roda no worker: o que um código malicioso tentaria depois de escapar do parser."""
    results: dict[str, str] = {}
    attempts: dict[str, Any] = {
        "tcp": lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM),
        "udp": lambda: socket.socket(socket.AF_INET6, socket.SOCK_DGRAM),
        "unix": lambda: socket.socket(socket.AF_UNIX, socket.SOCK_STREAM),
        "socketpair": socket.socketpair,
        "subprocess": lambda: subprocess.run(["/bin/true"], check=True),
        "exec": lambda: os.execv("/bin/true", ["true"]),  # noqa: S606
    }
    for name, attempt in attempts.items():
        try:
            attempt()
            results[name] = "permitido"
        except OSError as exc:
            results[name] = errno.errorcode.get(exc.errno or 0, str(exc.errno))
    results["filters"] = str(_seccomp_filters())
    return results


def _seccomp_filters() -> int:
    """Filtros seccomp do processo atual. O Docker já instala um; o worker soma o dele."""
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("Seccomp_filters:"):
                return int(line.split(":")[1])
    return 0


@pytest.fixture(scope="module")
def sandboxed_pool() -> Iterator[AnalyzerPool]:
    pool = AnalyzerPool(BASE_RULESET, PoolConfig(workers=1, sandbox=SandboxMode.REQUIRED))
    yield pool
    pool.close()


@linux_only
def test_worker_cannot_open_sockets_or_run_programs(sandboxed_pool: AnalyzerPool) -> None:
    results = asyncio.run(sandboxed_pool.run(_try_everything))

    assert results == {
        "tcp": "EPERM",
        "udp": "EPERM",
        "unix": "EPERM",
        "socketpair": "EPERM",
        "subprocess": "EPERM",
        "exec": "EPERM",
        # O worker tem um filtro a mais que o processo que o criou: o do IP-Checker.
        "filters": str(_seccomp_filters() + 1),
    }


@linux_only
def test_sandboxed_worker_still_analyzes(sandboxed_pool: AnalyzerPool) -> None:
    result = asyncio.run(sandboxed_pool.analyze("for i in range(3):\n    print(i)\n", 1))

    assert [v.rule_id for v in result.violations] == ["R-34", "R-35"]
    with pytest.raises(AnalysisLimitError):
        asyncio.run(sandboxed_pool.analyze("(" * 1_000 + ")" * 1_000, 1))


@linux_only
def test_recycled_workers_get_the_filter_again() -> None:
    pool = AnalyzerPool(
        BASE_RULESET, PoolConfig(workers=1, max_tasks=1, sandbox=SandboxMode.REQUIRED)
    )
    try:
        first = asyncio.run(pool.run(_try_everything))
        second = asyncio.run(pool.run(_try_everything))
    finally:
        pool.close()

    assert first["filters"] == second["filters"] == str(_seccomp_filters() + 1)
    assert second["tcp"] == "EPERM"


@linux_only
def test_main_process_is_not_filtered(sandboxed_pool: AnalyzerPool) -> None:
    # O processo do serviço precisa de sockets para atender a API; só o worker é fechado.
    asyncio.run(sandboxed_pool.analyze("x = 1\n", 1))

    socket.socket(socket.AF_INET, socket.SOCK_STREAM).close()


@pytest.mark.skipif(sys.platform == "linux", reason="no Linux o filtro existe e o serviço sobe")
def test_required_sandbox_without_seccomp_keeps_the_service_from_starting() -> None:
    # Fail-closed: sem o filtro, nenhum worker nasce, o aquecimento falha e o serviço não sobe.
    settings = AnalyzerSettings(
        ruleset_path=BASE_RULESET,
        pool=PoolConfig(workers=1, sandbox=SandboxMode.REQUIRED),
        json_logs=False,
    )

    with pytest.raises(BrokenProcessPool), TestClient(create_app(settings)):
        pass

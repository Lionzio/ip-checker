"""Os limites de cada worker (ADR-01, NFR-08), conferidos com um ``resource`` falso.

O worker aplica os limites num processo filho, que a cobertura não acompanha, e o módulo
``resource`` não existe no Windows. Aqui, um ``resource`` falso registra cada limite pedido, em
qualquer sistema, sem limitar o processo dos testes (S35-03: cobertura de ``runtime/`` ≥ 80%).
"""

from __future__ import annotations

import signal
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from ipc_analyzer.runtime.limits import MIB, ResourceLimits, apply_limits, forbid_new_processes


@pytest.fixture
def fake_resource(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {}
    module = SimpleNamespace(
        RLIMIT_AS="AS",
        RLIMIT_FSIZE="FSIZE",
        RLIMIT_NOFILE="NOFILE",
        RLIMIT_CORE="CORE",
        RLIMIT_NPROC="NPROC",
        setrlimit=lambda kind, value: calls.__setitem__(kind, value),
    )
    monkeypatch.setitem(sys.modules, "resource", module)
    # SIGXFSZ não existe no Windows; o sinal fica só registrado, sem mudar o processo.
    monkeypatch.setattr(signal, "SIGXFSZ", 25, raising=False)
    monkeypatch.setattr(
        signal,
        "signal",
        lambda number, handler: calls.__setitem__("sinal", (number, handler)),
    )
    return calls


def test_the_worker_limits_are_all_applied(fake_resource: dict[str, Any]) -> None:
    assert apply_limits(ResourceLimits(memory_bytes=160 * MIB, max_open_files=16)) is True

    assert fake_resource == {
        "AS": (160 * MIB, 160 * MIB),
        "FSIZE": (0, 0),  # nada gravado em disco
        "NOFILE": (16, 16),
        "CORE": (0, 0),  # nenhum core dump com o código do aluno
        "sinal": (25, signal.SIG_IGN),  # gravar falha com erro, sem matar o worker
    }


def test_no_new_process_or_thread_in_the_worker(fake_resource: dict[str, Any]) -> None:
    assert forbid_new_processes() is True
    assert fake_resource == {"NPROC": (0, 0)}


def test_without_resource_the_limits_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    # No Windows (desenvolvimento), sem o módulo; a produção roda em Linux.
    monkeypatch.setitem(sys.modules, "resource", None)

    assert apply_limits(ResourceLimits()) is False
    assert forbid_new_processes() is False

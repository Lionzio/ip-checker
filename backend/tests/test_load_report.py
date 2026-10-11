"""Os vereditos do ``deploy/load/run_load.py`` (S34-01 e S34-03), com resumos do k6 sintéticos.

A carga em si roda à mão (minutos de Docker); aqui só se confere que cada critério do NFR-04 e do
NFR-05 aprova e reprova o que deve, e que o script do k6 conhece os mesmos cenários.
"""

from __future__ import annotations

import importlib.util
import re
from types import ModuleType
from typing import Any

import pytest

from conftest import REPO_ROOT

LOAD = REPO_ROOT / "deploy/load"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_load", LOAD / "run_load.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_load = _module()


def summary(statuses: dict[str, int], **metrics: dict[str, float]) -> dict[str, Any]:
    data: dict[str, Any] = {
        f"status_{name}": {"values": {"count": total}} for name, total in statuses.items()
    }
    for name, values in metrics.items():
        data[name] = {"values": values}
    data["http_req_duration{nome:verificar,expected_response:true}"] = {
        "values": {"med": 40.0, "p(95)": 120.0, "p(99)": 300.0}
    }
    return {"metrics": data}


def failures(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("REPROVADO")]


def test_the_k6_script_knows_every_scenario() -> None:
    script = (LOAD / "pilot-load.js").read_text(encoding="utf-8")
    known = re.search(r'\[("vespera", "nfr04", "nfr05")\]', script)

    assert known is not None
    # "degraus" é o vespera em várias taxas, montado pelo run_load.py.
    assert set(run_load.SCENARIOS) - {"degraus"} == {"vespera", "nfr04", "nfr05"}
    # Os status que o k6 conta são os que o relatório lê.
    statuses = re.search(r"const STATUSES = \[([^\]]*)\]", script)
    assert statuses is not None
    assert [s.strip(' "') for s in statuses.group(1).split(",")] == [
        name for name in run_load.statuses({}) if name != "outro"
    ]


def test_nfr04_passes_only_without_5xx_429_or_lost_requests() -> None:
    assert failures(run_load.check_nfr04(summary({"200": 7500}))) == []

    overloaded = run_load.check_nfr04(summary({"200": 6400, "503": 1100}))
    assert len(failures(overloaded)) == 1
    assert "503 = 1100" in failures(overloaded)[0]

    limited = run_load.check_nfr04(summary({"200": 7490, "429": 10}))
    assert "429 = 10" in failures(limited)[0]

    # 0,1% sem resposta já reprova (meta: menos de 0,1%).
    lost = run_load.check_nfr04(summary({"200": 9990, "0": 10}))
    assert "sem resposta = 10" in failures(lost)[0]
    assert failures(run_load.check_nfr04(summary({}))) != []


def test_nfr05_needs_fast_503s_with_retry_after_and_a_quick_recovery() -> None:
    good = summary(
        {"200": 1200, "503": 3300},
        recusa_ms={"count": 3300, "med": 8.0, "p(95)": 900.0, "max": 1050.0},
        recuperacao_erro_s={"count": 3, "max": 12.5},
        recuperacao_verificacoes={"count": 30},
    )
    assert failures(run_load.check_nfr05(good)) == []

    generic = summary(
        {"200": 1200, "503": 3000, "502": 1},
        recusa_ms={"count": 3000, "max": 50.0},
    )
    assert "500/502/504 = 1" in failures(run_load.check_nfr05(generic))[0]

    slow = summary(
        {"200": 1200, "503": 3000},
        recusa_ms={"count": 3000, "max": 2500.0},
        recusa_sem_retry_after={"count": 2},
        recuperacao_erro_s={"count": 1, "max": 75.0},
    )
    reasons = " ".join(failures(run_load.check_nfr05(slow)))
    assert "sem Retry-After = 2" in reasons
    assert "2500 ms" in reasons
    assert "75.0 s" in reasons

    # Sem nenhum 503, a sobrecarga não aconteceu: o teste não provou nada (como no Starter).
    unsaturated = run_load.check_nfr05(summary({"200": 4500}))
    assert failures(unsaturated) == []
    assert run_load.exit_code(unsaturated) == 2
    assert run_load.exit_code(run_load.check_nfr05(slow)) == 1
    assert run_load.exit_code(run_load.check_nfr05(good)) == 0


def test_the_steps_report_the_highest_rate_without_refusals(
    capsys: pytest.CaptureFixture[str],
) -> None:
    steps = [
        (100, summary({"200": 300})),
        (150, summary({"200": 450})),
        (200, summary({"200": 580, "503": 20})),
        # Um degrau acima sem recusa (acaso) não conta: um abaixo já recusou.
        (300, summary({"200": 900})),
    ]

    assert run_load.report_steps(steps) == 0
    out = capsys.readouterr().out
    assert "Maior taxa sem nenhuma recusa 503: 150 por minuto." in out
    assert "| 200 | 600 | 120 ms | 300 ms | 20 (3.3%) | 0 | 0 |" in out

    assert run_load.report_steps([(100, summary({"200": 290, "500": 10}))]) == 1
    assert "REPROVADO" in capsys.readouterr().out

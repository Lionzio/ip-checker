"""Vários períodos carregados no analisador (S43-01; ADR-12, Q-34).

O analisador carrega o período do ``ATIVO`` e os até 5 anteriores presentes em ``rulesets/``, e
cada pedido escolhe o seu (sem período, vale o ativo, como antes). Os períodos posteriores ao ativo
(em preparação) e a pasta ``encerrados/`` ficam de fora.
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import BASE_RULESET
from ipc_analyzer.engine.ruleset import (
    RETIRED_DIR,
    WINDOW,
    RulesetError,
    UnknownPeriod,
    load_ruleset,
    load_rulesets,
)
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings

ACTIVE = "2026.2"
#: Do mais antigo ao mais novo: 8 períodos até o ativo, mais um em preparação.
PRESENT = ["2023.1", "2023.2", "2024.1", "2024.2", "2025.1", "2025.2", "2026.1", "2026.2", "2027.1"]
LOADED = ["2026.2", "2026.1", "2025.2", "2025.1", "2024.2", "2024.1"]


def _period_copy(root: Path, period: str, version: int = 0) -> None:
    """Uma cópia do base.yaml do 2026.2 com o período trocado (sem as questões)."""
    folder = root / period
    folder.mkdir(parents=True)
    text = BASE_RULESET.read_text(encoding="utf-8")
    text = text.replace('ruleset_version: "2026.2.7"', f'ruleset_version: "{period}.{version}"')
    text = text.replace('period: "2026.2"', f'period: "{period}"')
    (folder / "base.yaml").write_text(text, encoding="utf-8")


@pytest.fixture
def rulesets(tmp_path: Path) -> Path:
    root = tmp_path / "rulesets"
    for period in PRESENT:
        _period_copy(root, period)
    _period_copy(root / RETIRED_DIR, "2026.1", version=9)  # um encerrado com o mesmo nome
    (root / "schema").mkdir()  # uma pasta qualquer, sem base.yaml
    (root / "ATIVO").write_text(f"{ACTIVE}\n", encoding="utf-8")
    return root


def test_the_active_and_the_five_previous_periods_are_loaded(rulesets: Path) -> None:
    loaded = load_rulesets(rulesets)

    assert WINDOW == 6
    assert loaded.active == ACTIVE
    assert list(loaded.periods) == LOADED  # do mais novo ao mais antigo; 2023.x e 2027.1 de fora
    assert loaded.get().version == "2026.2.0"
    assert loaded.get("2024.1").version == "2024.1.0"
    assert loaded.get("2026.1").version == "2026.1.0"  # o da raiz, nunca o de encerrados/


def test_each_period_has_its_own_hash(rulesets: Path) -> None:
    loaded = load_rulesets(rulesets)

    assert len({ruleset.sha256 for ruleset in loaded.periods.values()}) == len(LOADED)


@pytest.mark.parametrize(
    "period", ["2023.2", "2027.1", "2019.1"], ids=["antigo", "futuro", "inexistente"]
)
def test_a_period_out_of_the_window_is_unknown(rulesets: Path, period: str) -> None:
    loaded = load_rulesets(rulesets)

    with pytest.raises(UnknownPeriod) as caught:
        loaded.get(period)

    assert caught.value.period == period
    assert caught.value.loaded == tuple(LOADED)


def test_a_single_base_or_period_folder_still_loads_only_itself() -> None:
    loaded = load_rulesets(BASE_RULESET)

    assert list(loaded.periods) == [load_ruleset(BASE_RULESET).ruleset.period]
    assert loaded.get().sha256 == load_ruleset(BASE_RULESET).sha256


def test_an_invalid_period_in_the_window_stops_the_start(rulesets: Path) -> None:
    (rulesets / "2025.1" / "base.yaml").write_text("ruleset_version: 1\n", encoding="utf-8")

    with pytest.raises(RulesetError):
        load_rulesets(rulesets)


@pytest.mark.timing
def test_loading_the_window_takes_at_most_two_seconds_more_than_one_period(rulesets: Path) -> None:
    """Premissa validada pelo autor em 12/10/2026: a subida até +2 s em relação a um período."""
    started = time.perf_counter()
    load_ruleset(rulesets / ACTIVE / "base.yaml")
    one = time.perf_counter() - started
    started = time.perf_counter()
    load_rulesets(rulesets)
    window = time.perf_counter() - started

    assert window - one < 2.0, f"um período {one:.2f} s, a janela {window:.2f} s"


@pytest.fixture
def service(rulesets: Path) -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=rulesets, pool=PoolConfig(workers=1))
    with TestClient(create_app(settings)) as client:
        yield client


def test_the_manifest_lists_every_loaded_period(service: TestClient) -> None:
    body = service.get("/internal/ruleset/manifest").json()

    assert body["period"] == ACTIVE  # os campos de cima continuam sendo os do ativo
    assert [(item["period"], item["active"]) for item in body["periods"]] == [
        (period, period == ACTIVE) for period in LOADED
    ]
    assert [item["ruleset_version"] for item in body["periods"]] == [f"{p}.0" for p in LOADED]
    assert all(len(item["lists"]) == 6 for item in body["periods"])


def test_an_analysis_uses_the_rules_of_the_requested_period(service: TestClient) -> None:
    code = {"code": "n = int(input())\nprint(n)\n", "list_number": 1}

    default = service.post("/internal/analyze", json=code).json()
    earlier = service.post("/internal/analyze", json={**code, "period": "2024.1"}).json()

    assert default["ruleset_version"] == "2026.2.0"
    assert earlier["ruleset_version"] == "2024.1.0"


def test_a_period_out_of_the_window_is_refused_with_422(service: TestClient) -> None:
    code = {"code": "x = 1\n", "list_number": 1}

    for path in ("/internal/analyze", "/internal/feedback-input"):
        answer = service.post(path, json={**code, "period": "2023.2"})
        assert answer.status_code == 422
        assert answer.json()["error"]["code"] == "UNKNOWN_PERIOD"
        assert "2023.2" in answer.json()["error"]["message"]
    similarity = service.post(
        "/internal/similarity", json={"first": "x = 1\n", "second": "y = 2\n", "period": "2027.1"}
    )
    assert similarity.json()["error"]["code"] == "UNKNOWN_PERIOD"


def test_the_period_must_look_like_a_period(service: TestClient) -> None:
    answer = service.post(
        "/internal/analyze", json={"code": "x = 1\n", "list_number": 1, "period": "26"}
    )

    assert answer.status_code == 422
    assert answer.json()["error"]["code"] == "INVALID_INPUT"


def test_the_copy_helper_really_changes_the_period(tmp_path: Path) -> None:
    _period_copy(tmp_path, "2024.2")

    assert load_ruleset(tmp_path / "2024.2" / "base.yaml").version == "2024.2.0"
    shutil.rmtree(tmp_path / "2024.2")

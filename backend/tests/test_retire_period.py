"""Encerrar um período antigo (S43-04, ADR-12) e o aviso de ATIVO defasado no /health/slo.

``ipc-rules retire-period`` move a pasta para ``rulesets/encerrados/``, de onde o analisador nunca
carrega, e recusa o ativo, os da janela dos 6 carregados e os posteriores ao ativo. O /health/slo
só avisa quando o ATIVO parece ter ficado para trás: trocar o período continua com a coordenação.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import httpx2
import pytest

from api_support import authed_client, make_app
from conftest import BASE_RULESET
from ipc_analyzer.cli import main
from ipc_analyzer.engine.ruleset import ACTIVE_FILE, RETIRED_DIR, load_rulesets, window_periods
from ipc_api.gabaritos import Gabaritos, GabaritosConfig, load
from ipc_api.settings import ApiSettings
from ipc_api.slo import active_looks_stale
from test_api import MANIFEST, VALID, FakeAnalyzer, reply

#: Do mais antigo ao ativo, mais um em preparação (2027.1).
PRESENT = ["2023.1", "2023.2", "2024.1", "2024.2", "2025.1", "2025.2", "2026.1", "2026.2", "2027.1"]
ACTIVE = "2026.2"
WINDOW = ["2026.2", "2026.1", "2025.2", "2025.1", "2024.2", "2024.1"]


@pytest.fixture
def rulesets(tmp_path: Path) -> Path:
    """Nove pastas de período só com o ``base.yaml``: o comando não carrega as regras."""
    root = tmp_path / "rulesets"
    for period in PRESENT:
        (root / period / "questions").mkdir(parents=True)
        shutil.copy(BASE_RULESET, root / period / "base.yaml")
        (root / period / "questions" / "lista-1.yaml").write_text("{}\n", encoding="utf-8")
    (root / ACTIVE_FILE).write_text(f"{ACTIVE}\n", encoding="utf-8")
    return root


def retire(root: Path, *args: str) -> int:
    return main(["retire-period", *args, "--rulesets", str(root)])


# --- ipc-rules retire-period -------------------------------------------------------------------


def test_the_window_is_the_active_and_the_five_before_it(rulesets: Path) -> None:
    assert window_periods(rulesets, ACTIVE) == WINDOW


def test_dry_run_only_shows_what_would_leave(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert retire(rulesets, "2023.1", "--dry-run") == 0

    out = capsys.readouterr().out
    assert "2023.1 sairia" in out
    assert "(2 arquivos)" in out
    assert "nada foi movido" in out
    assert (rulesets / "2023.1" / "base.yaml").is_file()
    assert not (rulesets / RETIRED_DIR).exists()


def test_retiring_moves_the_folder_and_keeps_its_files(
    rulesets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (rulesets / "2023.1" / "base.yaml").read_bytes()

    assert retire(rulesets, "2023.1") == 0

    assert "git status" in capsys.readouterr().out
    assert not (rulesets / "2023.1").exists()
    assert (rulesets / RETIRED_DIR / "2023.1" / "base.yaml").read_bytes() == before
    assert (rulesets / RETIRED_DIR / "2023.1" / "questions" / "lista-1.yaml").is_file()
    # Um segundo período encerrado vai para a mesma pasta, e a janela não muda.
    assert retire(rulesets, "2023.2") == 0
    assert sorted(path.name for path in (rulesets / RETIRED_DIR).iterdir()) == ["2023.1", "2023.2"]
    assert window_periods(rulesets, ACTIVE) == WINDOW


def test_the_analyzer_never_loads_a_retired_period(tmp_path: Path) -> None:
    root = tmp_path / "rulesets"
    for period in ("2026.1", "2026.2"):
        (root / period).mkdir(parents=True)
        text = BASE_RULESET.read_text(encoding="utf-8")
        version = f"{period}.7"
        text = text.replace('ruleset_version: "2026.2.7"', f'ruleset_version: "{version}"')
        text = text.replace('period: "2026.2"', f'period: "{period}"')
        (root / period / "base.yaml").write_text(text, encoding="utf-8")
    (root / ACTIVE_FILE).write_text("2026.2\n", encoding="utf-8")
    (root / RETIRED_DIR).mkdir()
    shutil.move(str(root / "2026.1"), str(root / RETIRED_DIR / "2026.1"))

    assert list(load_rulesets(root).periods) == ["2026.2"]


@pytest.mark.parametrize(
    ("period", "message"),
    [
        ("2026.2", "é o período ativo"),
        ("2024.1", "está na janela dos 6 períodos carregados"),
        ("2026.1", "está na janela dos 6 períodos carregados"),
        ("2027.1", "é posterior ao ativo (2026.2)"),
        ("2020.1", "não existe"),
    ],
)
def test_retire_refuses_what_is_still_in_use(
    rulesets: Path, capsys: pytest.CaptureFixture[str], period: str, message: str
) -> None:
    assert retire(rulesets, period) == 1

    assert message in capsys.readouterr().err
    if (rulesets / period).exists():
        assert (rulesets / period / "base.yaml").is_file()
    assert not (rulesets / RETIRED_DIR).exists()


def test_retire_refuses_a_bad_period(rulesets: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert retire(rulesets, "2023.3") == 2

    assert "período inválido" in capsys.readouterr().err


def test_retire_needs_the_active_file(rulesets: Path) -> None:
    (rulesets / ACTIVE_FILE).unlink()

    assert retire(rulesets, "2023.1") == 2
    assert (rulesets / "2023.1").is_dir()


def test_retire_never_overwrites(rulesets: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (rulesets / RETIRED_DIR / "2023.1").mkdir(parents=True)

    assert retire(rulesets, "2023.1") == 1

    assert "nunca sobrescreve" in capsys.readouterr().err
    assert (rulesets / "2023.1" / "base.yaml").is_file()


# --- os gabaritos de um período encerrado ------------------------------------------------------


def test_the_gabaritos_index_ignores_retired_periods(tmp_path: Path) -> None:
    for folder in ("2026.2/lista-1", f"{RETIRED_DIR}/2023.1/lista-1"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "2026.2" / "lista-1" / "L1-Q2.py").write_text("print(1)\n", encoding="utf-8")
    retired = tmp_path / RETIRED_DIR / "2023.1" / "lista-1" / "L1-Q1.py"
    retired.write_text("print(2)\n", encoding="utf-8")
    gabaritos = Gabaritos()

    asyncio.run(load(GabaritosConfig(local_dir=tmp_path), gabaritos))

    assert gabaritos.status == "loaded"
    assert gabaritos.count == 1
    assert gabaritos.questions("2023.1") == {}


# --- /health/slo: o aviso de ATIVO defasado ----------------------------------------------------


@pytest.mark.parametrize(
    ("period", "today", "stale"),
    [
        ("2026.2", date(2026, 10, 16), False),
        ("2026.2", date(2027, 3, 1), False),  # 31/12 + 60 dias
        ("2026.2", date(2027, 3, 2), True),
        ("2026.1", date(2026, 9, 29), False),  # 31/07 + 60 dias
        ("2026.1", date(2026, 9, 30), True),
        ("2027.1", date(2027, 3, 2), False),
    ],
)
def test_the_active_period_looks_stale_60_days_after_its_semester(
    period: str, today: date, stale: bool
) -> None:
    assert active_looks_stale(period, today) is stale


class Clock:
    """O relógio da API: o de agora até a verificação, depois a data que o teste quiser."""

    def __init__(self) -> None:
        self.fixed: datetime | None = None

    def __call__(self) -> datetime:
        return self.fixed or datetime.now(UTC)


def _slo(clock: Clock, when: datetime, *, validate: bool) -> dict[str, object]:
    analyzer = FakeAnalyzer(
        {"/internal/analyze": reply(200, VALID), "/internal/ruleset/manifest": reply(200, MANIFEST)}
    )
    app, store = make_app(
        ApiSettings(analyzer_url="http://analyzer.test"),
        analyzer_transport=httpx2.MockTransport(analyzer),
        clock=clock,
    )
    with authed_client(app, store) as client:
        if validate:
            body = {"code": "x = 1\n", "list_number": 1, "question_id": None}
            assert client.post("/api/v1/validate", json=body).status_code == 200
        clock.fixed = when
        response = client.get("/health/slo")
    assert response.status_code == 200
    payload: dict[str, object] = response.json()
    return payload


def test_health_slo_warns_when_the_active_period_looks_stale() -> None:
    body = _slo(Clock(), datetime(2027, 3, 15, tzinfo=UTC), validate=True)

    assert body["warnings"] == ["ativo_defasado"]
    assert body["status"] == "ok"  # só aviso: o status e o alerta do UptimeRobot não mudam


def test_health_slo_has_no_warning_inside_the_semester() -> None:
    body = _slo(Clock(), datetime(2026, 11, 20, tzinfo=UTC), validate=True)

    assert body["warnings"] == []


def test_health_slo_has_no_warning_before_any_verification() -> None:
    body = _slo(Clock(), datetime(2027, 3, 15, tzinfo=UTC), validate=False)

    assert body["warnings"] == []

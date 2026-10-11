"""O passo de cobertura por pasta (S35-03, NFR-16), com relatórios do ``coverage`` sintéticos."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "coverage_by_folder.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("coverage_by_folder", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _module()


def report(**files: tuple[int, int]) -> dict[str, Any]:
    return {
        "files": {
            path.replace("__", "/") + ".py": {
                "summary": {"covered_lines": covered, "num_statements": total}
            }
            for path, (covered, total) in files.items()
        }
    }


def test_the_engine_and_its_subfolders_are_one_folder() -> None:
    assert gate.folder_of("src/ipc_analyzer/engine/policy.py") == "ipc_analyzer/engine"
    assert gate.folder_of("src\\ipc_analyzer\\engine\\facts\\calls.py") == "ipc_analyzer/engine"
    assert gate.folder_of("src/ipc_api/routes/auth.py") == "ipc_api/routes"
    assert gate.folder_of("src/ipc_api/app.py") == "ipc_api"


def test_everything_at_the_limits_passes(capsys: pytest.CaptureFixture[str]) -> None:
    data = report(
        src__ipc_analyzer__engine__policy=(90, 100),
        src__ipc_api__routes__auth=(80, 100),
    )

    assert gate.check(data) == []
    assert "ok" in capsys.readouterr().out


def test_the_engine_below_90_fails_even_with_a_good_total() -> None:
    data = report(
        src__ipc_analyzer__engine__policy=(89, 100),
        src__ipc_api__app=(1000, 1000),
    )

    assert gate.check(data) == ["ipc_analyzer/engine: 89.00% < 90%"]


def test_another_folder_below_80_fails() -> None:
    data = report(src__ipc_api__accounts__postgres=(79, 100))

    assert gate.check(data) == ["ipc_api/accounts: 79.00% < 80%"]


def test_branches_count_when_the_report_has_them(tmp_path: Path) -> None:
    data: dict[str, Any] = {
        "files": {
            "src/ipc_api/app.py": {
                "summary": {
                    "covered_lines": 80,
                    "num_statements": 80,
                    "covered_branches": 0,
                    "num_branches": 20,
                }
            }
        }
    }
    file = tmp_path / "coverage.json"
    file.write_text(json.dumps(data), encoding="utf-8")

    assert gate.main(["coverage_by_folder.py", str(file)]) == 0
    data["files"]["src/ipc_api/app.py"]["summary"]["num_branches"] = 30
    file.write_text(json.dumps(data), encoding="utf-8")
    assert gate.main(["coverage_by_folder.py", str(file)]) == 1

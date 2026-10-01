"""Peças da API sem HTTP: configuração, identificador de requisição e contagem de linhas."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from ipc_api import openapi
from ipc_api.ids import new_request_id
from ipc_api.settings import ApiSettings, parse_lists
from ipc_api.validation import count_lines


def test_settings_defaults() -> None:
    settings = ApiSettings.from_env({})

    assert settings == ApiSettings()
    assert settings.enabled_lists == {1}
    assert settings.analyzer_timeout_s == 3.0
    assert settings.max_body_bytes == 128 * 1024


def test_settings_from_environment() -> None:
    settings = ApiSettings.from_env(
        {
            "IPC_ANALYZER_URL": "http://analyzer:8001",
            "IPC_ENABLED_LISTS": "1, 2",
            "IPC_ANALYZER_TIMEOUT_S": "2.5",
            "IPC_MAX_BODY_BYTES": "65536",
        }
    )

    assert settings.analyzer_url == "http://analyzer:8001"
    assert settings.enabled_lists == {1, 2}
    assert settings.analyzer_timeout_s == 2.5
    assert settings.max_body_bytes == 65_536


@pytest.mark.parametrize("value", ["", "0", "7", "1,x", ",", "1;2"])
def test_invalid_enabled_lists_prevent_startup(value: str) -> None:
    with pytest.raises(ValueError, match="IPC_ENABLED_LISTS"):
        parse_lists(value)


def test_request_ids_are_ulids_ordered_by_time() -> None:
    first = new_request_id()
    time.sleep(0.002)
    second = new_request_id()

    assert len(first) == len(second) == 26
    assert first < second
    assert len({new_request_id() for _ in range(1_000)}) == 1_000


@pytest.mark.parametrize(
    ("code", "lines"),
    [("x", 1), ("x\n", 1), ("x\ny", 2), ("x\r\ny\r\n", 2), ("x\ry", 2), ("\n\n", 2)],
)
def test_lines_are_counted_like_the_analyzer(code: str, lines: int) -> None:
    assert count_lines(code) == lines


def test_openapi_export_writes_the_contract(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    assert openapi.main([str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["info"]["title"] == "IP-Checker"


def test_openapi_export_requires_a_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert openapi.main([]) == 2
    assert "uso:" in capsys.readouterr().err

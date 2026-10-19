"""Carregamento dos gabaritos na memória da API (ADR-11, S32-02; revisto na Sprint 51).

Desde a Sprint 51 (ADR-17), o banco é a fonte da verdade, e a API não baixa nada do GitHub: só
lê uma pasta local (``IPC_GABARITOS_DIR``, no desenvolvimento e no e2e) com a organização de
sempre. Nada aqui usa gabaritos reais: os arquivos são sintéticos, com um canário que nunca pode
aparecer em log.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from ipc_api.gabaritos import MAX_FILE_BYTES, Gabaritos, GabaritosConfig, load, read_folder

CANARY = "CANARIO_GABARITO_91c2"


def _load(config: GabaritosConfig) -> Gabaritos:
    target = Gabaritos()
    asyncio.run(load(config, target))
    return target


def _write(root: Path, files: dict[str, bytes]) -> Path:
    for relative, raw in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return root


def test_only_official_paths_are_read_from_the_folder(tmp_path: Path) -> None:
    folder = _write(
        tmp_path,
        {
            "2026.2/lista-1/L1-Q1.py": f"print('{CANARY}')\n".encode(),
            "2026.2/lista-3/L3-Q10.py": b"x = [1]\n",
            "2025.2/lista-2/L2-Q1.py": b"\xef\xbb\xbfprint(2)\n",
            # Fora do padrão: a questão de outra lista, um nome solto e um arquivo grande demais.
            "2026.2/lista-1/L2-Q1.py": b"print(3)\n",
            "2026.2/lista-1/rascunho.py": b"print(4)\n",
            "README.md": b"# gabaritos\n",
            "2026.2/lista-2/L2-Q2.py": b"x = 1\n" * (MAX_FILE_BYTES // 6 + 1),
        },
    )

    gabaritos = _load(GabaritosConfig(local_dir=folder))

    assert gabaritos.status == "loaded"
    assert gabaritos.count == 3
    assert gabaritos.get("2026.2", "L1-Q1") == f"print('{CANARY}')\n"
    # O BOM do UTF-8 sai, como no harness dos gabaritos.
    assert gabaritos.get("2025.2", "L2-Q1") == "print(2)\n"
    assert gabaritos.questions("2026.2") == {1: ["L1-Q1"], 3: ["L3-Q10"]}
    assert gabaritos.questions("2027.1") == {}
    assert read_folder(folder)[("2026.2", "L3-Q10")] == "x = [1]\n"


def test_the_log_says_only_how_many_were_loaded(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    folder = _write(tmp_path, {"2026.2/lista-1/L1-Q1.py": f"# {CANARY}\n".encode()})

    _load(GabaritosConfig(local_dir=folder))

    assert "gabaritos carregados: 1" in caplog.text
    assert CANARY not in caplog.text
    assert "L1-Q1" not in caplog.text


def test_without_a_folder_the_local_loading_is_off() -> None:
    assert _load(GabaritosConfig()).status == "disabled"


def test_the_old_repository_variables_are_ignored_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Sprint 51: a API não baixa mais do GitHub; as variáveis só avisam até saírem do Render.
    caplog.set_level(logging.WARNING)
    token = "github_pat_token-de-teste-que-nunca-aparece"
    config = GabaritosConfig.from_env(
        {"IPC_GABARITOS_REPO": "Lionzio/ip-checker-gabaritos", "IPC_GABARITOS_TOKEN": token}
    )

    gabaritos = _load(config)

    assert gabaritos.status == "disabled"
    assert config.legacy_variables
    assert "não são mais lidas" in caplog.text
    assert token not in caplog.text
    assert token not in repr(config)


def test_a_local_folder_works_for_development(tmp_path: Path) -> None:
    (tmp_path / "2026.2" / "lista-1").mkdir(parents=True)
    (tmp_path / "2026.2" / "lista-1" / "L1-Q2.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "excecoes.yaml").write_text("{}\n", encoding="utf-8")

    gabaritos = _load(GabaritosConfig(local_dir=tmp_path))

    assert gabaritos.status == "loaded"
    assert gabaritos.questions("2026.2") == {1: ["L1-Q2"]}


def test_a_missing_local_folder_fails(tmp_path: Path) -> None:
    assert _load(GabaritosConfig(local_dir=tmp_path / "nao-existe")).status == "failed"


def test_too_many_bytes_in_total_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ipc_api.gabaritos.MAX_TOTAL_BYTES", 10)
    (tmp_path / "2026.2" / "lista-1").mkdir(parents=True)
    for n in (1, 2):
        (tmp_path / "2026.2" / "lista-1" / f"L1-Q{n}.py").write_text("print(1)\n", "utf-8")

    assert _load(GabaritosConfig(local_dir=tmp_path)).status == "failed"


def test_the_configuration_reads_the_environment(tmp_path: Path) -> None:
    config = GabaritosConfig.from_env(
        {"IPC_GABARITOS_DIR": str(tmp_path), "IPC_GABARITO_ALERT_PERCENT": "97.5"}
    )

    assert config.enabled
    assert config.local_dir == tmp_path
    assert config.alert_percent == 97.5
    assert not config.legacy_variables


def test_the_cache_keeps_both_kinds_and_prefers_notion() -> None:
    # Sprint 51: até dois por questão; o get devolve o preferido, o pair devolve os dois.
    cache = Gabaritos()
    cache.put("2026.2", "L2-Q4", "ip_cc", "print('ip cc')\n")
    assert cache.get("2026.2", "L2-Q4") == "print('ip cc')\n"

    cache.put("2026.2", "L2-Q4", "notion", "print('notion')\n")

    assert cache.status == "loaded"
    assert cache.get("2026.2", "L2-Q4") == "print('notion')\n"
    assert [kind for kind, _code in cache.pair("2026.2", "L2-Q4")] == ["notion", "ip_cc"]
    cache.remove("2026.2", "L2-Q4", "notion")
    assert cache.pair("2026.2", "L2-Q4") == (("ip_cc", "print('ip cc')\n"),)
    cache.remove("2026.2", "L2-Q4", "ip_cc")
    assert cache.get("2026.2", "L2-Q4") is None
    assert cache.questions("2026.2") == {}

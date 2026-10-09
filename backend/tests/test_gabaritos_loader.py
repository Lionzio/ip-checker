"""Carregamento dos gabaritos na memória da API (ADR-11, S32-02), com repositório falso.

Nada aqui usa gabaritos reais: os arquivos são sintéticos, e a "API do GitHub" é um transporte em
memória. O token e o conteúdo nunca podem aparecer em log.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

import httpx2
import pytest

from ipc_api.gabaritos import (
    MAX_FILE_BYTES,
    Gabaritos,
    GabaritosConfig,
    load,
)

TOKEN = "github_pat_token-de-teste-que-nunca-aparece"
CANARY = "CANARIO_GABARITO_91c2"


def _github(files: dict[str, bytes], *, status: int = 200) -> httpx2.MockTransport:
    shas = {path: f"sha{index}" for index, path in enumerate(files)}

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        if status != 200:
            return httpx2.Response(status, json={"message": "Bad credentials"})
        if "/git/trees/" in request.url.path:
            tree = [
                {"path": path, "type": "blob", "sha": shas[path], "size": len(raw)}
                for path, raw in files.items()
            ]
            tree.append({"path": "2026.2/lista-1", "type": "tree", "sha": "d1"})
            return httpx2.Response(200, json={"tree": tree, "truncated": False})
        sha = request.url.path.rsplit("/", 1)[-1]
        path = next(p for p, s in shas.items() if s == sha)
        content = base64.b64encode(files[path]).decode()
        return httpx2.Response(200, json={"encoding": "base64", "content": content})

    return httpx2.MockTransport(handler)


def _load(config: GabaritosConfig, transport: httpx2.MockTransport | None = None) -> Gabaritos:
    target = Gabaritos()
    asyncio.run(load(config, target, transport))
    return target


GITHUB = GabaritosConfig(repo="Lionzio/ip-checker-gabaritos", token=TOKEN)


def test_only_official_paths_are_loaded_from_github() -> None:
    files = {
        "2026.2/lista-1/L1-Q1.py": f"print('{CANARY}')\n".encode(),
        "2026.2/lista-3/L3-Q10.py": b"x = [1]\n",
        "2025.2/lista-2/L2-Q1.py": b"\xef\xbb\xbfprint(2)\n",
        # Fora do padrão: a questão de outra lista, um nome solto e um arquivo grande demais.
        "2026.2/lista-1/L2-Q1.py": b"print(3)\n",
        "2026.2/lista-1/rascunho.py": b"print(4)\n",
        "README.md": b"# gabaritos\n",
        "2026.2/lista-2/L2-Q2.py": b"x = 1\n" * (MAX_FILE_BYTES // 6 + 1),
    }

    gabaritos = _load(GITHUB, _github(files))

    assert gabaritos.status == "loaded"
    assert gabaritos.count == 3
    assert gabaritos.get("2026.2", "L1-Q1") == f"print('{CANARY}')\n"
    # O BOM do UTF-8 sai, como no harness dos gabaritos.
    assert gabaritos.get("2025.2", "L2-Q1") == "print(2)\n"
    assert gabaritos.questions("2026.2") == {1: ["L1-Q1"], 3: ["L3-Q10"]}
    assert gabaritos.questions("2027.1") == {}


def test_a_github_failure_disables_the_comparison_without_leaking(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)

    gabaritos = _load(GITHUB, _github({}, status=401))

    assert gabaritos.status == "failed"
    assert gabaritos.count == 0
    assert "o GitHub respondeu 401" in caplog.text
    assert TOKEN not in caplog.text


def test_the_log_says_only_how_many_were_loaded(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    _load(GITHUB, _github({"2026.2/lista-1/L1-Q1.py": f"# {CANARY}\n".encode()}))

    assert "gabaritos carregados: 1" in caplog.text
    assert CANARY not in caplog.text
    assert "L1-Q1" not in caplog.text
    assert TOKEN not in caplog.text


def test_without_configuration_the_comparison_is_off() -> None:
    assert _load(GabaritosConfig()).status == "disabled"
    assert _load(GabaritosConfig(repo="dono/repo")).status == "disabled"


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


@pytest.mark.parametrize(
    ("env", "message"),
    [({"IPC_GABARITOS_REPO": "sem-barra"}, "dono/repositório")],
)
def test_an_invalid_repository_name_is_refused(env: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        GabaritosConfig.from_env(env)


def test_the_configuration_reads_the_environment() -> None:
    config = GabaritosConfig.from_env(
        {
            "IPC_GABARITOS_REPO": "Lionzio/ip-checker-gabaritos",
            "IPC_GABARITOS_TOKEN": TOKEN,
            "IPC_GABARITO_ALERT_PERCENT": "97.5",
        }
    )

    assert config.enabled
    assert config.alert_percent == 97.5
    assert TOKEN not in repr(config)
    assert json.dumps(config.repo) == '"Lionzio/ip-checker-gabaritos"'

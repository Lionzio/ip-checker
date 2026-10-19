"""Import e export dos gabaritos entre uma pasta e o banco (Sprint 51, S51-05).

Gabaritos sintéticos, com um canário: a saída do comando nunca o mostra. O caminho completo, com o
PostgreSQL, só roda com ``IPC_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database
from ipc_api.answer_keys.store import Actor, MemoryGabaritoStore
from ipc_api.answer_keys.transfer import REPO_ROOT, export_tree, import_folder, main

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
CANARY = "CANARIO_GABARITO_51"


def write(root: Path, files: dict[str, str]) -> Path:
    for relative, code in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
    return root


FOLDER = {
    "2026.2/lista-1/L1-Q1.py": f"# {CANARY}\nprint(1)\n",
    "2026.2/lista-2/L2-Q10.py": "print(2)\n",
    "2025.2/lista-1/L1-Q3.py": "print(3)\n",
    # Fora do padrão: fica de fora, como no harness.
    "2026.2/lista-1/rascunho.py": "print(4)\n",
}


def test_the_folder_enters_as_notion_imported_and_a_second_run_changes_nothing(
    tmp_path: Path,
) -> None:
    store = MemoryGabaritoStore()
    folder = write(tmp_path / "gabaritos", FOLDER)

    first = asyncio.run(import_folder(store, folder, now=NOW))
    again = asyncio.run(import_folder(store, folder, now=NOW))

    assert (first.created, first.updated, first.unchanged) == (3, 0, 0)
    assert (again.created, again.updated, again.unchanged) == (0, 0, 3)
    saved = asyncio.run(store.get("2026.2", "L1-Q1", "notion"))
    assert saved is not None
    assert (saved.source, saved.updated_by_name, saved.violations) == ("importado", None, ())
    assert len(store.entries) == 3


def test_a_changed_file_rewrites_and_a_period_can_be_chosen(tmp_path: Path) -> None:
    store = MemoryGabaritoStore()
    folder = write(tmp_path / "gabaritos", FOLDER)
    asyncio.run(import_folder(store, folder, now=NOW))
    write(folder, {"2026.2/lista-2/L2-Q10.py": "print(20)\n"})

    counts = asyncio.run(import_folder(store, folder, period="2026.2", now=NOW))

    assert (counts.created, counts.updated, counts.unchanged) == (0, 1, 1)


def test_the_export_writes_one_file_per_question_preferring_notion(tmp_path: Path) -> None:
    store = MemoryGabaritoStore()
    nobody = Actor(None, None)
    for kind, code in (("ip_cc", "print('ip cc')\n"), ("notion", "print('notion')\n")):
        asyncio.run(
            store.save(
                period="2026.2",
                question_id="L3-Q2",
                kind=kind,  # type: ignore[arg-type]
                source="painel",
                code=code,
                violations=(),
                actor=nobody,
                now=NOW,
            )
        )
    asyncio.run(
        store.save(
            period="2026.2",
            question_id="L4-Q1",
            kind="ip_cc",
            source="painel",
            code="print('so ip cc')\n",
            violations=(),
            actor=nobody,
            now=NOW,
        )
    )

    written = asyncio.run(export_tree(store, tmp_path / "exportados"))

    assert written == 2
    assert (tmp_path / "exportados/2026.2/lista-3/L3-Q2.py").read_text(encoding="utf-8") == (
        "print('notion')\n"
    )
    assert (tmp_path / "exportados/2026.2/lista-4/L4-Q1.py").exists()


def test_the_export_never_writes_inside_the_repository() -> None:
    with pytest.raises(ValueError, match="dentro do repositório"):
        asyncio.run(export_tree(MemoryGabaritoStore(), REPO_ROOT / "gabaritos"))


def test_without_the_admin_url_the_command_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("IPC_DATABASE_ADMIN_URL", raising=False)

    assert main(["importar", str(tmp_path)]) == 2
    assert "IPC_DATABASE_ADMIN_URL" in capsys.readouterr().err


@requires_database
def test_import_then_export_through_the_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    asyncio.run(fresh_schema())
    monkeypatch.setenv("IPC_DATABASE_ADMIN_URL", DATABASE_URL)
    folder = write(tmp_path / "gabaritos", FOLDER)

    assert main(["importar", str(folder), "--periodo", "2026.2"]) == 0
    assert main(["importar", str(folder), "--periodo", "2026.2"]) == 0
    assert main(["exportar", str(tmp_path / "exportados")]) == 0

    out = capsys.readouterr().out
    assert "gabaritos importados: 2 novos, 0 alterados, 0 iguais" in out
    assert "gabaritos importados: 0 novos, 0 alterados, 2 iguais" in out
    assert "gabaritos exportados: 2" in out
    assert CANARY not in out
    exported = tmp_path / "exportados/2026.2/lista-1/L1-Q1.py"
    assert exported.read_text(encoding="utf-8") == FOLDER["2026.2/lista-1/L1-Q1.py"]

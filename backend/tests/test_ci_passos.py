"""A impressão digital das entradas da CI local (S49-01, ADR-20): ``scripts/ci-passos.py``.

Tudo num repositório Git temporário: o mesmo conteúdo dá o mesmo hash, um byte muda o hash, um
arquivo não rastreado conta, um ignorado não conta, e o verde registrado é reconhecido, invalidado
pela mudança e pela idade. Nenhum comando de shell: o script roda por ``subprocess`` com uma lista.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci-passos.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 - argumentos fixos, só no repositório temporário
        ["git", *args],  # noqa: S607 - o git do PATH
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


def passos(repo: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(  # noqa: S603 - o próprio script, com argumentos fixos
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Um repositório Git em ``tmp_path/repo``; ``tmp_path`` é o lado de fora dele."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "ci@exemplo.test")
    git(root, "config", "user.name", "CI")
    (root / "backend").mkdir()
    (root / "backend" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "a.md").write_text("# a\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "inicio")
    return root


def test_same_content_same_hash_and_one_byte_changes_it(repo: Path) -> None:
    _, first = passos(repo, "hash", "backend")
    _, again = passos(repo, "hash", "backend")
    (repo / "backend" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _, changed = passos(repo, "hash", "backend")

    assert first == again
    assert len(first) == 64
    assert changed != first


def test_untracked_counts_and_ignored_does_not(repo: Path) -> None:
    _, before = passos(repo, "hash", "backend")
    (repo / "backend" / "saida.log").write_text("ignorado\n", encoding="utf-8")
    _, with_ignored = passos(repo, "hash", "backend")
    (repo / "backend" / "novo_test.py").write_text("y = 1\n", encoding="utf-8")
    _, with_new = passos(repo, "hash", "backend")

    assert with_ignored == before
    assert with_new != before


def test_other_paths_do_not_change_the_hash(repo: Path) -> None:
    _, before = passos(repo, "hash", "backend")
    (repo / "docs" / "a.md").write_text("# mudou\n", encoding="utf-8")
    _, after = passos(repo, "hash", "backend")

    assert after == before


def test_a_deleted_tracked_file_changes_the_hash(repo: Path) -> None:
    _, before = passos(repo, "hash", "backend")
    (repo / "backend" / "a.py").unlink()
    _, after = passos(repo, "hash", "backend")

    assert after != before


def test_exclusion_pathspec_is_respected(repo: Path) -> None:
    _, everything = passos(repo, "hash", ".")
    _, without_docs = passos(repo, "hash", ".", ":!docs")
    (repo / "docs" / "a.md").write_text("# mudou\n", encoding="utf-8")
    _, without_docs_after = passos(repo, "hash", ".", ":!docs")
    _, everything_after = passos(repo, "hash", ".")

    assert without_docs_after == without_docs
    assert everything_after != everything


def test_a_folder_outside_the_repository_counts(repo: Path) -> None:
    outside = repo.parent / "gabaritos"
    (outside / ".git").mkdir(parents=True)
    (outside / ".git" / "HEAD").write_text("ref: x\n", encoding="utf-8")
    (outside / "L1-Q1.py").write_text("print(1)\n", encoding="utf-8")
    _, before = passos(repo, "hash", "backend", "../gabaritos")
    (outside / "L1-Q1.py").write_text("print(2)\n", encoding="utf-8")
    _, after = passos(repo, "hash", "backend", "../gabaritos")
    (outside / ".git" / "HEAD").write_text("ref: y\n", encoding="utf-8")
    _, after_git = passos(repo, "hash", "backend", "../gabaritos")

    assert after != before
    assert after_git == after


def test_a_recorded_green_is_recognized_until_the_inputs_change(repo: Path) -> None:
    _, digest = passos(repo, "hash", "backend")
    assert passos(repo, "check", "pytest", digest)[0] == 1

    assert passos(repo, "record", "pytest", digest, "abc1234def", "backend")[0] == 0
    code, out = passos(repo, "check", "pytest", digest)
    assert code == 0
    assert out.startswith("abc1234 ")

    (repo / "backend" / "a.py").write_text("x = 3\n", encoding="utf-8")
    _, new_digest = passos(repo, "hash", "backend")
    assert passos(repo, "check", "pytest", new_digest)[0] == 1
    # O registro fica fora da árvore de trabalho, no .git.
    record = Path(git(repo, "rev-parse", "--git-common-dir").strip())
    record = record if record.is_absolute() else repo / record
    assert (record / "ci-local-passos.json").is_file()
    assert not (repo / "ci-local-passos.json").exists()


def test_a_green_older_than_the_limit_does_not_count(repo: Path) -> None:
    _, digest = passos(repo, "hash", "backend")
    passos(repo, "record", "pip-audit", digest, "abc1234", "backend")
    record = Path(git(repo, "rev-parse", "--git-common-dir").strip())
    record = record if record.is_absolute() else repo / record
    path = record / "ci-local-passos.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pip-audit"]["quando"] = (datetime.now(UTC) - timedelta(days=8)).isoformat(
        timespec="minutes"
    )
    path.write_text(json.dumps(data), encoding="utf-8")

    assert passos(repo, "check", "pip-audit", digest)[0] == 0
    assert passos(repo, "check", "pip-audit", digest, "--max-age-days", "7")[0] == 1


def test_changed_lists_only_what_differs_from_the_manifest(repo: Path) -> None:
    code, out = passos(repo, "changed", "semgrep", "backend", "docs")
    assert code == 0
    assert out.splitlines() == ["backend/a.py", "docs/a.md"]  # sem manifesto, tudo

    _, digest = passos(repo, "hash", "backend", "docs")
    passos(repo, "record", "semgrep", digest, "abc1234", "--manifest", "backend", "docs")
    assert passos(repo, "changed", "semgrep", "backend", "docs")[1] == "."

    (repo / "backend" / "a.py").write_text("x = 9\n", encoding="utf-8")
    (repo / "backend" / "b.py").write_text("z = 1\n", encoding="utf-8")
    _, out = passos(repo, "changed", "semgrep", "backend", "docs")
    assert out.splitlines() == ["backend/a.py", "backend/b.py"]


def test_verify_recomputes_from_the_recorded_paths(repo: Path) -> None:
    _, digest = passos(repo, "hash", "backend")
    passos(repo, "record", "pytest", digest, "abc1234", "backend")
    _, docs_digest = passos(repo, "hash", "docs")
    passos(repo, "record", "links", docs_digest, "abc1234", "docs")

    assert passos(repo, "verify", "pytest", "links")[0] == 0
    code, out = passos(repo, "verify", "pytest", "links", "lighthouse")
    assert code == 1
    assert out == "lighthouse: sem verde registrado"

    (repo / "backend" / "a.py").write_text("x = 4\n", encoding="utf-8")
    code, out = passos(repo, "verify", "pytest", "links")
    assert code == 1
    assert out == "pytest: as entradas mudaram desde o verde de abc1234"


def test_forget_removes_records(repo: Path) -> None:
    _, digest = passos(repo, "hash", "backend")
    passos(repo, "record", "pytest", digest, "abc1234", "backend")
    passos(repo, "record", "mypy", digest, "abc1234", "backend")

    assert passos(repo, "forget", "mypy")[0] == 0
    assert passos(repo, "check", "mypy", digest)[0] == 1
    assert passos(repo, "check", "pytest", digest)[0] == 0
    assert passos(repo, "forget")[0] == 0
    assert passos(repo, "check", "pytest", digest)[0] == 1


def test_the_script_never_prints_file_contents(repo: Path) -> None:
    canary = "CANARIO_CI_PASSOS_49"
    (repo / "backend" / "a.py").write_text(f"x = '{canary}'\n", encoding="utf-8")
    outputs = [passos(repo, "hash", "backend")[1], passos(repo, "changed", "semgrep", "backend")[1]]
    _, digest = passos(repo, "hash", "backend")
    passos(repo, "record", "semgrep", digest, "abc1234", "--manifest", "backend")
    record = Path(git(repo, "rev-parse", "--git-common-dir").strip())
    record = record if record.is_absolute() else repo / record
    outputs.append((record / "ci-local-passos.json").read_text(encoding="utf-8"))

    assert all(canary not in out for out in outputs)

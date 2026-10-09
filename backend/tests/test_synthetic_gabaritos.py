"""NFR-27: nenhum gabarito oficial entra neste repositório (ADR-10, ADR-11).

Os gabaritos do e2e e do ambiente local (``frontend/e2e/gabaritos-sinteticos``) são inventados, e
cada arquivo diz isso na primeira linha. Um arquivo sem a marca, ou com o formato de um gabarito em
qualquer outra pasta, faz este teste falhar: um gabarito oficial copiado por engano não passa.
"""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SYNTHETIC = REPO_ROOT / "frontend" / "e2e" / "gabaritos-sinteticos"
MARK = "# Gabarito SINTÉTICO"
OFFICIAL_NAME = re.compile(r"L[1-6]-Q[1-9]\d?\.py")
IGNORED = {".git", ".venv", "node_modules", "dist", ".vercel", "test-results"}


def test_the_synthetic_gabaritos_say_so() -> None:
    files = sorted(SYNTHETIC.rglob("*.py"))

    assert files, "os gabaritos sintéticos do e2e sumiram"
    for file in files:
        first = file.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith(MARK), f"{file.relative_to(REPO_ROOT)} sem a marca de sintético"


def test_no_file_named_like_a_gabarito_outside_the_synthetic_folder() -> None:
    found = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in REPO_ROOT.rglob("*.py")
        if OFFICIAL_NAME.fullmatch(path.name)
        and not IGNORED & set(path.relative_to(REPO_ROOT).parts)
        and SYNTHETIC not in path.parents
    ]

    assert found == []

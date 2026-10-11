"""Cobertura por pasta (S35-03, NFR-16): o motor com 90% ou mais, cada outra pasta com 80% ou mais.

O ``pytest`` já exige 90% no total (``--cov-fail-under``); este passo lê o relatório JSON do
``coverage`` e falha se o motor (``ipc_analyzer/engine`` e as subpastas) ou qualquer outra pasta
de código ficar abaixo do limite. De ``backend/``, depois do ``pytest``:

    uv run coverage json -o coverage.json
    uv run python scripts/coverage_by_folder.py coverage.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

#: O motor de regras e de similaridade, com as subpastas.
ENGINE = "ipc_analyzer/engine"
ENGINE_MINIMUM = 90.0
#: Qualquer outra pasta de código.
FOLDER_MINIMUM = 80.0


def folder_of(path: str) -> str:
    """A pasta que responde pelo arquivo: o motor inteiro, ou a pasta onde o arquivo está."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    start = next(i for i, part in enumerate(parts) if part in {"ipc_analyzer", "ipc_api"})
    folder = "/".join(parts[start:-1])
    return ENGINE if folder == ENGINE or folder.startswith(ENGINE + "/") else folder


def by_folder(report: dict[str, Any]) -> dict[str, tuple[int, int]]:
    """Itens cobertos e totais (linhas e ramos) por pasta."""
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path, data in report["files"].items():
        summary = data["summary"]
        covered = summary["covered_lines"] + summary.get("covered_branches", 0)
        total = summary["num_statements"] + summary.get("num_branches", 0)
        folder = totals[folder_of(path)]
        folder[0] += covered
        folder[1] += total
    return {name: (covered, total) for name, (covered, total) in sorted(totals.items())}


def check(report: dict[str, Any]) -> list[str]:
    """As pastas abaixo do limite, com a porcentagem; vazio quando tudo passa."""
    failures = []
    for name, (covered, total) in by_folder(report).items():
        if total == 0:
            continue
        percent = 100 * covered / total
        minimum = ENGINE_MINIMUM if name == ENGINE else FOLDER_MINIMUM
        status = "ok" if percent >= minimum else "ABAIXO"
        print(f"{status:6} {percent:6.2f}%  (mínimo {minimum:.0f}%)  {name}")
        if percent < minimum:
            failures.append(f"{name}: {percent:.2f}% < {minimum:.0f}%")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: coverage_by_folder.py coverage.json", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as file:
        report = json.load(file)
    failures = check(report)
    if failures:
        print(
            "cobertura por pasta abaixo do limite (NFR-16):", *failures, sep="\n  ", file=sys.stderr
        )
        return 1
    print("cobertura por pasta: todas as pastas no limite (NFR-16)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

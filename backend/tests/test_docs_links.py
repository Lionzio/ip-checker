"""Os links relativos da documentação levam a arquivos que existem (S39-05).

Lê todo ``.md`` do repositório (fora de ``node_modules``, ``.venv`` e pastas geradas) e confere cada
link ``[texto](caminho)`` que não é endereço da web, e-mail nem âncora da própria página. Só o
arquivo é conferido; a âncora (``#secao``) depois dele, não, porque o GitHub gera os nomes das
seções com regras próprias.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {
    "node_modules",
    ".venv",
    ".git",
    "dist",
    "coverage",
    "test-results",
    "playwright-report",
    ".pytest_cache",
}
#: [texto](destino), sem pegar imagens externas nem o texto entre crases com colchetes.
LINK = re.compile(r"(?<!\\)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_BLOCK = re.compile(r"^```.*?^```", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def _documents() -> list[Path]:
    found = []
    for path in REPO_ROOT.rglob("*.md"):
        if not SKIP_DIRS.intersection(path.relative_to(REPO_ROOT).parts):
            found.append(path)
    return sorted(found)


def _broken(path: Path) -> list[str]:
    text = INLINE_CODE.sub("", CODE_BLOCK.sub("", path.read_text(encoding="utf-8")))
    problems = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue  # https:, mailto:, claude: e âncoras da própria página
        file_part = unquote(target.split("#", 1)[0])
        if not file_part:
            continue
        if not (path.parent / file_part).exists():
            problems.append(target)
    return problems


def test_there_are_documents_to_check() -> None:
    names = {path.relative_to(REPO_ROOT).as_posix() for path in _documents()}
    assert {"README.md", "CHANGELOG.md", "docs/blueprint.md", "docs/README.md"} <= names


@pytest.mark.parametrize(
    "path", _documents(), ids=lambda path: path.relative_to(REPO_ROOT).as_posix()
)
def test_relative_links_point_to_existing_files(path: Path) -> None:
    assert _broken(path) == []

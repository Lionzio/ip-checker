"""``ipc-rules import-gabaritos`` (S33-08): leva os gabaritos de uma exportação do Notion para o
repositório privado dos gabaritos (ADR-10), no formato ``<período>/lista-<n>/L<n>-Q<m>.py``.

O Notion exporta cada página em Markdown (**Export > Markdown & CSV**), com o código em blocos
```` ```python ````. A questão de cada bloco vem, nesta ordem, do título mais próximo acima dele, do
nome do arquivo e das pastas: ``L3-Q2``, ``L3 Q2`` ou "Lista 3" numa parte e "Questão 2" em outra.
Um bloco sem questão reconhecida, ou duas soluções para a mesma questão, ficam de fora e aparecem
na saída para alguém decidir à mão.

O destino nunca pode ser este repositório (NFR-27): o comando recusa uma pasta que tenha
``rulesets/`` e ``backend/`` acima dela. Ele não sobrescreve um gabarito existente sem
``--sobrescrever``, e a saída traz só caminhos e contagens, nunca código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PERIOD = re.compile(r"^\d{4}\.[12]$")
_FENCE = re.compile(r"^(`{3,}|~{3,})\s*([\w+-]*)\s*$")
_FULL_ID = re.compile(r"\bL\s*([1-6])\s*[-_ ]?\s*Q\s*0*([1-9]\d?)\b", re.IGNORECASE)
_LIST = re.compile(r"\blista\s*0*([1-6])\b", re.IGNORECASE)
_QUESTION = re.compile(
    r"\bquest(?:ão|ao|ões|oes)?\s*0*([1-9]\d?)\b|\bQ\s*0*([1-9]\d?)\b", re.IGNORECASE
)
_PYTHON = {"python", "py", "python3"}


@dataclass(frozen=True, slots=True)
class Block:
    source: str
    question: str | None
    #: Onde o bloco estava: o arquivo e o título acima dele (nunca o código).
    where: str


def _identify(*texts: str) -> str | None:
    """``L<n>-Q<m>`` dos títulos, do nome do arquivo e das pastas, do mais próximo ao mais longe."""
    for text in texts:
        match = _FULL_ID.search(text)
        if match:
            return f"L{match.group(1)}-Q{match.group(2)}"
    listing = next((m.group(1) for text in texts if (m := _LIST.search(text))), None)
    question = next(
        (m.group(1) or m.group(2) for text in texts if (m := _QUESTION.search(text))), None
    )
    if listing and question:
        return f"L{listing}-Q{question}"
    return None


def read_blocks(export: Path) -> list[Block]:
    """Os blocos de Python de cada página exportada, com a questão de cada um."""
    blocks: list[Block] = []
    for file in sorted(export.rglob("*.md")):
        relative = file.relative_to(export)
        # O Notion acrescenta um identificador ao nome: "L3-Q2 1a2b3c....md". As pastas vão da
        # mais próxima à mais longe.
        names = [
            re.sub(r"\s+[0-9a-f]{32}$", "", part)
            for part in (file.stem, *reversed(relative.parts[:-1]))
        ]
        heading = ""
        fence: str | None = None
        language = ""
        lines: list[str] = []
        for line in file.read_text(encoding="utf-8-sig").splitlines():
            if fence is None:
                if line.lstrip().startswith("#"):
                    heading = line.lstrip("# ").strip()
                    continue
                opening = _FENCE.match(line.strip())
                if opening:
                    fence, language, lines = opening.group(1), opening.group(2).lower(), []
                continue
            if line.strip().startswith(fence) and line.strip().strip(fence[0]) == "":
                if language in _PYTHON:
                    source = "\n".join(lines).rstrip() + "\n"
                    where = f"{relative.as_posix()}" + (f" ({heading})" if heading else "")
                    blocks.append(Block(source, _identify(heading, *names), where))
                fence = None
                continue
            lines.append(line)
    return blocks


@dataclass(frozen=True, slots=True)
class ImportResult:
    written: list[str]
    skipped_existing: list[str]
    conflicts: list[str]
    unknown: list[str]


def _inside_main_repository(path: Path) -> bool:
    for folder in (path, *path.parents):
        if (folder / "rulesets").is_dir() and (folder / "backend").is_dir():
            return True
    return False


def import_gabaritos(
    export: Path, destination: Path, period: str, *, overwrite: bool = False, dry_run: bool = False
) -> ImportResult:
    if not PERIOD.fullmatch(period):
        raise ValueError(f"período inválido: {period!r} (use o formato 2025.2)")
    if _inside_main_repository(destination.resolve()):
        raise ValueError(
            "o destino fica dentro do repositório do IP-Checker: os gabaritos só vão para o "
            "repositório privado (NFR-27)"
        )
    by_question: dict[str, list[Block]] = {}
    unknown: list[str] = []
    for block in read_blocks(export):
        if block.question is None:
            unknown.append(block.where)
        else:
            by_question.setdefault(block.question, []).append(block)
    written: list[str] = []
    existing: list[str] = []
    conflicts: list[str] = []
    for question, found in sorted(by_question.items()):
        if len(found) > 1:
            places = "; ".join(block.where for block in found)
            conflicts.append(f"{question}: {len(found)} blocos ({places})")
            continue
        relative = f"{period}/lista-{question[1]}/{question}.py"
        target = destination / relative
        if target.exists() and not overwrite:
            existing.append(relative)
            continue
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(found[0].source, encoding="utf-8", newline="\n")
        written.append(relative)
    return ImportResult(written, existing, conflicts, unknown)

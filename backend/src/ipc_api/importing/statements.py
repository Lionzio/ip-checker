"""O ``.zip`` dos enunciados (S50-06) para o gerador de referências da Sprint 42.

Um ``L1-Q1.md`` por questão de lista do período (as provas e o treino ficam de fora, e as que
sumiram do Dikastis também), no formato que ``python -m ipc_api.referencias --enunciados`` lê: o
arquivo inteiro é o enunciado, em texto. Gerado em memória; nada vai para o disco.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence

from ipc_api.importing.models import StoredQuestion

#: Uma data fixa nos arquivos: o mesmo catálogo dá sempre o mesmo .zip.
_ZIP_DATE = (2026, 1, 1, 0, 0, 0)


def statement_markdown(question: StoredQuestion) -> str:
    """O enunciado em Markdown simples: título, descrição, entrada, saída e os exemplos."""
    parts = [f"# {question.question_id}: {question.title}", "", question.description.strip()]
    if question.input_description.strip():
        parts += ["", "## Entrada", "", question.input_description.strip()]
    if question.output_description.strip():
        parts += ["", "## Saída", "", question.output_description.strip()]
    for number, sample in enumerate(question.samples, start=1):
        parts += [
            "",
            f"## Exemplo {number}",
            "",
            "Entrada:",
            "",
            "```text",
            sample.input.rstrip("\n"),
            "```",
            "",
            "Saída:",
            "",
            "```text",
            sample.output.rstrip("\n"),
            "```",
        ]
    return "\n".join(parts).strip() + "\n"


def statements_zip(questions: Sequence[StoredQuestion]) -> tuple[bytes, int]:
    """O ``.zip`` e quantos arquivos ele tem."""
    buffer = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for question in questions:
            if question.list_kind != "lista" or question.missing_since is not None:
                continue
            info = zipfile.ZipInfo(f"{question.question_id}.md", date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, statement_markdown(question).encode("utf-8"))
            count += 1
    return buffer.getvalue(), count

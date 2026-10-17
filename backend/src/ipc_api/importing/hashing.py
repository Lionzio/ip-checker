"""O hash do enunciado de uma questão (S50-05): o contrato entre a extensão e a API.

A extensão (``extensao/src/catalogo/hash.ts``) e a API calculam o mesmo valor; a API recalcula e
recusa o que não bate. O arquivo ``extensao/test/vetores-hash.json`` traz casos lidos pelos dois
lados (pytest e Vitest), para as duas implementações nunca divergirem.

Regra: cada texto em NFC, com ``\\r\\n`` e ``\\r`` trocados por ``\\n``, os espaços no fim de cada
linha removidos e o texto inteiro sem espaço, tab ou quebra de linha nas pontas (só esses três:
o ``strip()`` do Python e o ``trim()`` do JavaScript tiram outros); depois, o JSON de
``{title, description, input_description, output_description, samples:[{input, output}]}`` com
as chaves em ordem, sem espaços entre os separadores, sem escapar acentos, em UTF-8; o hash é o
SHA-256 em hexadecimal.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_TRAILING = re.compile(r"[ \t]+$", re.MULTILINE)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return _TRAILING.sub("", text).strip(" \t\n")


@dataclass(frozen=True, slots=True)
class Sample:
    input: str
    output: str


def content_hash(
    *,
    title: str,
    description: str,
    input_description: str,
    output_description: str,
    samples: Sequence[Sample],
) -> str:
    document = {
        "description": normalize_text(description),
        "input_description": normalize_text(input_description),
        "output_description": normalize_text(output_description),
        "samples": [
            {"input": normalize_text(s.input), "output": normalize_text(s.output)} for s in samples
        ],
        "title": normalize_text(title),
    }
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

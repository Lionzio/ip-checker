"""Esquema JSON e ruleset compilado (S35-05, C6): para editores, para a CI e para conferir o deploy.

O esquema sai dos próprios modelos do carregador (``Ruleset`` e ``Question``), então nunca diverge
do que o analisador aceita; o ``ipc-rules validate`` continua sendo a validação completa (fatos,
mensagens e referências cruzadas, que um esquema JSON não expressa).

O compilado é o ruleset de um período já validado, em JSON, com o mesmo SHA-256 que o analisador
publica no manifesto (``ruleset_sha256``): comparar os dois confere que o deploy carregou
exatamente os arquivos do repositório.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ipc_analyzer.engine.ruleset import CompiledRuleset, Question, Ruleset

#: Onde os esquemas ficam no repositório, a partir de ``backend/``.
SCHEMA_DIR = Path("../rulesets/schema")
RULESET_SCHEMA = "ruleset.schema.json"
QUESTION_SCHEMA = "question.schema.json"
_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def schemas() -> dict[str, dict[str, Any]]:
    """Os dois esquemas, pelo nome do arquivo."""
    ruleset = Ruleset.model_json_schema()
    question = Question.model_json_schema()
    ruleset = {**ruleset, "$schema": _DRAFT, "title": "Ruleset de um período do IP-Checker"}
    question = {
        **question,
        "$schema": _DRAFT,
        "title": "Regras de uma questão do IP-Checker (R-01)",
    }
    return {RULESET_SCHEMA: ruleset, QUESTION_SCHEMA: question}


def render(schema: dict[str, Any]) -> str:
    """O texto do arquivo: estável, para a CI comparar com o gerado."""
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_schemas(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for name, schema in schemas().items():
        path = destination / name
        path.write_text(render(schema), encoding="utf-8", newline="\n")
        written.append(path)
    return written


def compiled(ruleset: CompiledRuleset) -> dict[str, Any]:
    """O ruleset compilado de um período, com o SHA-256 do manifesto."""
    questions = sorted(ruleset.questions.values(), key=lambda q: q.id)
    return {
        "period": ruleset.ruleset.period,
        "ruleset_version": ruleset.version,
        "ruleset_sha256": ruleset.sha256,
        "ruleset": ruleset.ruleset.model_dump(mode="json", by_alias=True),
        "questions": [
            question.question.model_dump(mode="json", by_alias=True) for question in questions
        ],
    }

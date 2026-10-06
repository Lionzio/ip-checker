"""``ipc-rules``: valida o ruleset de um período antes do PR e na CI (FR-21, US-14; S24-02).

Uso::

    uv run ipc-rules validate ../rulesets/2026.2
    uv run ipc-rules validate ../rulesets/2026.2 --golden tests/golden

Confere o ``base.yaml`` e as questões de ``questions/`` exatamente como o analisador os carrega
(schema, R-xx existentes, ``since_list``/``until_list``, predicados e consistência), lista as
questões que liberam proibições gerais (só com aprovação de professor, C-02) e, com ``--golden``,
roda os casos golden. Sai com 0 se tudo passou, 1 se algo falhou e 2 se o comando foi mal usado.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.ruleset import CompiledRuleset, RulesetError, load_ruleset

BASE_FILE = "base.yaml"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ipc-rules", description="Ferramentas do ruleset do IP-Checker."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="valida o ruleset de um período (base.yaml e questions/)"
    )
    validate.add_argument("path", type=Path, help="pasta do período ou o base.yaml dela")
    validate.add_argument(
        "--golden", type=Path, help="pasta com os casos golden (*.yaml) para rodar também"
    )
    args = parser.parse_args(argv)
    return _validate(args.path, args.golden)


def _validate(path: Path, golden: Path | None) -> int:
    base = path / BASE_FILE if path.is_dir() else path
    try:
        ruleset = load_ruleset(base)
    except RulesetError as exc:
        _error(str(exc), base)
        return 1
    data = ruleset.ruleset
    questions = len(ruleset.questions)
    print(
        f"ruleset {data.ruleset_version} válido: {len(data.rules)} regras, "
        f"{len(data.requirements)} exigências e {questions} "
        f"{'questão' if questions == 1 else 'questões'}"
    )
    for question in sorted(ruleset.questions.values(), key=lambda q: q.id):
        if question.releases:
            released = ", ".join(question.releases)
            _warning(
                f"{question.id} libera proibição geral ({released}): o PR só entra com a "
                "aprovação de um professor (C-02).",
                base.parent / "questions" / f"{question.id}.yaml",
            )
    if golden is None:
        return 0
    failures = run_golden(ruleset, golden)
    for failure in failures:
        _error(failure, golden)
    return 1 if failures else 0


def run_golden(ruleset: CompiledRuleset, folder: Path) -> list[str]:
    """Roda os casos golden (``id``, ``list``, ``code``, ``expect``) e devolve as falhas."""
    failures: list[str] = []
    files = sorted(folder.glob("*.yaml"))
    if not files:
        return [f"nenhum caso golden em {folder}"]
    total = 0
    for file in files:
        cases: list[dict[str, Any]] = yaml.safe_load(file.read_text(encoding="utf-8")) or []
        for case in cases:
            total += 1
            try:
                result = analyze_source(case["code"], list_number=case["list"], ruleset=ruleset)
            except InputError as exc:
                failures.append(f"{file.name} {case['id']}: entrada recusada ({exc.message})")
                continue
            found = sorted(f"{v.rule_id} {v.category} {v.line}" for v in result.violations)
            if found != sorted(case["expect"]):
                failures.append(
                    f"{file.name} {case['id']}: esperado {sorted(case['expect'])}, veio {found}"
                )
    print(f"casos golden: {total - len(failures)} de {total} passaram")
    return failures


def _github() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _error(message: str, file: Path) -> None:
    if _github():
        # Anotação no PR: a primeira linha vira o título, o resto vai junto.
        print(f"::error file={file}::{message.replace(chr(10), '%0A')}")
    print(f"erro: {message}", file=sys.stderr)


def _warning(message: str, file: Path) -> None:
    if _github():
        print(f"::warning file={file}::{message}")
    print(f"atenção: {message}")


if __name__ == "__main__":
    raise SystemExit(main())

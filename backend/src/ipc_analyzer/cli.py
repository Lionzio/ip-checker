"""``ipc-rules``: valida o ruleset de um período antes do PR e na CI (FR-21, US-14; S24-02).

Uso::

    uv run ipc-rules validate ../rulesets/2026.2
    uv run ipc-rules validate ../rulesets/2026.2 --golden tests/golden

Confere o ``base.yaml`` e as questões de ``questions/`` exatamente como o analisador os carrega
(schema, R-xx existentes, ``since_list``/``until_list``, predicados e consistência), lista as
questões que liberam proibições gerais (só com aprovação de professor, C-02) e, com ``--golden``,
roda os casos golden. Sai com 0 se tudo passou, 1 se algo falhou e 2 se o comando foi mal usado.

``calibrate`` (S29-04) mede as faixas dos indícios de uso de IA (ADR-08) em soluções humanas, de
períodos anteriores a 2023, organizadas como os gabaritos (``<período>/lista-<n>/<arquivo>.py``)::

    uv run ipc-rules calibrate ../rulesets/2026.2 /caminho/das/solucoes --max-alto 5

Mostra quantas soluções caem em cada faixa e, para as de faixa alta, só o caminho e os tipos de
indício, nunca o código. Sai com 1 se a faixa alta passar do limite (meta da ADR-08: 5%).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.indicators import Level
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
    calibrate = commands.add_parser(
        "calibrate", help="mede as faixas dos indícios de IA em soluções humanas (S29-04)"
    )
    calibrate.add_argument("path", type=Path, help="pasta do período ou o base.yaml dela")
    calibrate.add_argument(
        "solutions", type=Path, help="pasta com <período>/lista-<n>/<arquivo>.py"
    )
    calibrate.add_argument(
        "--max-alto",
        type=float,
        default=5.0,
        help="porcentagem máxima de soluções com faixa alta (padrão: 5, a meta da ADR-08)",
    )
    args = parser.parse_args(argv)
    if args.command == "calibrate":
        return _calibrate(args.path, args.solutions, args.max_alto)
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
    if ruleset.references:
        total = sum(len(items) for items in ruleset.references.values())
        print(f"referências de IA: {total} em {len(ruleset.references)} questões (S29-02)")
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


_LIST_DIR = re.compile(r"^lista-([1-6])$")


def _calibrate(path: Path, solutions: Path, max_high: float) -> int:
    base = path / BASE_FILE if path.is_dir() else path
    try:
        ruleset = load_ruleset(base)
    except RulesetError as exc:
        _error(str(exc), base)
        return 1
    files = sorted(
        (file, int(match.group(1)))
        for file in solutions.rglob("*.py")
        if (match := _LIST_DIR.match(file.parent.name)) is not None
    )
    if not files:
        print(f"nenhuma solução em {solutions} (use <período>/lista-<n>/<arquivo>.py)")
        return 2
    counts = {"nenhum": 0, "baixo": 0, "medio": 0, "alto": 0, "recusado": 0}
    high: list[str] = []
    for file, list_number in files:
        relative = file.relative_to(solutions).as_posix()
        try:
            result = analyze_source(
                file.read_text(encoding="utf-8"),
                list_number=list_number,
                ruleset=ruleset,
                with_indicators=True,
            )
        except (InputError, UnicodeDecodeError):
            counts["recusado"] += 1
            continue
        level = result.indicators.level if result.indicators is not None else None
        counts["nenhum" if level is None else level.label] += 1
        if level is Level.ALTO and result.indicators is not None:
            kinds = sorted({item.kind for item in result.indicators.items if item.level})
            high.append(f"{relative}: {', '.join(kinds)}")
    analysed = len(files) - counts["recusado"]
    share = 100 * counts["alto"] / analysed if analysed else 0.0
    print(f"soluções analisadas: {analysed} (recusadas pelos limites: {counts['recusado']})")
    for name in ("nenhum", "baixo", "medio", "alto"):
        print(f"  {name}: {counts[name]}")
    print(f"faixa alta: {share:.1f}% (limite: {max_high:.1f}%)")
    for line in high:
        print(f"  alto: {line}")
    return 1 if share > max_high else 0


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

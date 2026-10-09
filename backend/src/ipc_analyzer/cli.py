"""``ipc-rules``: valida o ruleset de um período antes do PR e na CI (FR-21, US-14; S24-02).

Uso::

    uv run ipc-rules validate ../rulesets
    uv run ipc-rules validate ../rulesets --golden tests/golden

A raiz ``rulesets/`` vale pelo período ativo, a única linha do arquivo ``rulesets/ATIVO``
(S31-09); a pasta de um período (``../rulesets/2026.2``) ou o ``base.yaml`` dela também servem.
Confere o ``base.yaml`` e as questões de ``questions/`` exatamente como o analisador os carrega
(schema, R-xx existentes, ``since_list``/``until_list``, predicados e consistência), lista as
questões que liberam proibições gerais (só com aprovação de professor, C-02) e, com ``--golden``,
roda os casos golden. Sai com 0 se tudo passou, 1 se algo falhou e 2 se o comando foi mal usado.

``calibrate`` (S29-04) mede as faixas dos indícios de uso de IA (ADR-08) em soluções humanas, de
períodos anteriores a 2023, organizadas como os gabaritos (``<período>/lista-<n>/<arquivo>.py``)::

    uv run ipc-rules calibrate ../rulesets /caminho/das/solucoes --max-alto 5

Mostra quantas soluções caem em cada faixa e, para as de faixa alta, só o caminho e os tipos de
indício, nunca o código. Sai com 1 se a faixa alta passar do limite (meta da ADR-08: 5%).

``new-period`` (S31-10) cria a pasta de um período novo a partir de um anterior, com o mesmo
``base.yaml`` (só o período e a versão mudam) e sem questões, que reiniciam a cada período (P-07)::

    uv run ipc-rules new-period 2027.1 --from 2026.2

A pasta nova sai validada; ativar o período é trocar a linha de ``rulesets/ATIVO``, num PR.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.indicators import Level
from ipc_analyzer.engine.ruleset import (
    ACTIVE_FILE,
    BASE_FILE,
    PERIOD,
    QUESTIONS_DIR,
    REFERENCES_DIR,
    CompiledRuleset,
    RulesetError,
    active_period,
    load_ruleset,
    resolve_ruleset_path,
)

#: Onde ficam os rulesets quando o comando roda de ``backend/``, como na CI e no ``RULES.md``.
DEFAULT_ROOT = Path("../rulesets")
#: O texto de ajuda das questões, copiado para o período novo com o período trocado.
QUESTIONS_README = "LEIA-ME.md"
_PATH_HELP = "a raiz rulesets/ (período ativo), a pasta de um período ou o base.yaml dela"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ipc-rules", description="Ferramentas do ruleset do IP-Checker."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="valida o ruleset de um período (base.yaml e questions/)"
    )
    validate.add_argument("path", type=Path, help=_PATH_HELP)
    validate.add_argument(
        "--golden", type=Path, help="pasta com os casos golden (*.yaml) para rodar também"
    )
    calibrate = commands.add_parser(
        "calibrate", help="mede as faixas dos indícios de IA em soluções humanas (S29-04)"
    )
    calibrate.add_argument("path", type=Path, help=_PATH_HELP)
    calibrate.add_argument(
        "solutions", type=Path, help="pasta com <período>/lista-<n>/<arquivo>.py"
    )
    calibrate.add_argument(
        "--max-alto",
        type=float,
        default=5.0,
        help="porcentagem máxima de soluções com faixa alta (padrão: 5, a meta da ADR-08)",
    )
    new_period = commands.add_parser(
        "new-period", help="cria a pasta de um período novo a partir de um anterior (S31-10)"
    )
    new_period.add_argument("period", help="o período novo, como 2027.1")
    new_period.add_argument(
        "--from",
        dest="source",
        help="o período de onde copiar o base.yaml (padrão: o período ativo)",
    )
    new_period.add_argument(
        "--rulesets",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"a raiz dos rulesets (padrão: {DEFAULT_ROOT.as_posix()})",
    )
    args = parser.parse_args(argv)
    if args.command == "calibrate":
        return _calibrate(args.path, args.solutions, args.max_alto)
    if args.command == "new-period":
        return _new_period(args.rulesets, args.period, args.source)
    return _validate(args.path, args.golden)


def _validate(path: Path, golden: Path | None) -> int:
    base = path
    try:
        base = resolve_ruleset_path(path)
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
                base.parent / QUESTIONS_DIR / f"{question.id}.yaml",
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
    base = path
    try:
        base = resolve_ruleset_path(path)
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


_PERIOD_LINE = re.compile(r'^period: "?\d{4}\.[12]"?[ \t]*$', re.MULTILINE)
_VERSION_LINE = re.compile(r'^ruleset_version: "?\d{4}\.[12]\.\d+"?[ \t]*$', re.MULTILINE)


def _new_period(root: Path, period: str, source: str | None) -> int:
    """Copia ``<anterior>/base.yaml`` para ``<novo>/``, troca só o período e a versão
    (``<novo>.0``) e deixa ``questions/`` e ``referencias/`` vazias; a pasta nova sai validada
    ou não fica."""
    if not PERIOD.fullmatch(period):
        _error(f"período inválido: {period!r} (use o formato 2027.1)", root)
        return 2
    if source is None:
        try:
            source = active_period(root)
        except RulesetError as exc:
            _error(f"{exc}\n  - diga o período de origem com --from", root)
            return 2
    if not PERIOD.fullmatch(source):
        _error(f"período de origem inválido: {source!r} (use o formato 2026.2)", root)
        return 2
    origin, target = root / source, root / period
    if source == period:
        _error("o período novo precisa ser diferente do de origem", target)
        return 2
    if target.exists():
        _error(f"{target} já existe: o comando nunca sobrescreve um período", target)
        return 1
    try:
        text = (origin / BASE_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _error(f"não foi possível ler {origin / BASE_FILE}: {exc}", origin)
        return 1
    if len(_PERIOD_LINE.findall(text)) != 1 or len(_VERSION_LINE.findall(text)) != 1:
        _error(
            "o base.yaml de origem precisa ter uma linha 'period:' e uma 'ruleset_version:' "
            "no nível raiz",
            origin / BASE_FILE,
        )
        return 1
    text = _PERIOD_LINE.sub(f'period: "{period}"', text)
    text = _VERSION_LINE.sub(f'ruleset_version: "{period}.0"', text)
    text = text.replace(f"do período {source}", f"do período {period}")
    (target / QUESTIONS_DIR).mkdir(parents=True)
    (target / REFERENCES_DIR).mkdir()
    (target / REFERENCES_DIR / ".gitkeep").write_bytes(b"")
    (target / BASE_FILE).write_text(text, encoding="utf-8", newline="\n")
    readme = origin / QUESTIONS_DIR / QUESTIONS_README
    if readme.is_file():
        (target / QUESTIONS_DIR / QUESTIONS_README).write_text(
            readme.read_text(encoding="utf-8").replace(source, period),
            encoding="utf-8",
            newline="\n",
        )
    else:
        (target / QUESTIONS_DIR / ".gitkeep").write_bytes(b"")
    try:
        ruleset = load_ruleset(target / BASE_FILE)
    except RulesetError as exc:
        shutil.rmtree(target)
        _error(str(exc), origin / BASE_FILE)
        return 1
    data = ruleset.ruleset
    print(
        f"período {period} criado em {target.as_posix()} a partir de {source}: ruleset "
        f"{data.ruleset_version}, {len(data.rules)} regras e 0 questões"
    )
    print(
        "próximos passos: confira o base.yaml com o documento de permissões do período novo "
        f"(RULES.md), cadastre as questões em {QUESTIONS_DIR}/ e, para ativar, troque a linha "
        f"de {(root / ACTIVE_FILE).as_posix()} para {period}"
    )
    return 0


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

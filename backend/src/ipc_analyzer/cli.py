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

Desde a S42-02, com a base da Q-35 (``ai_calibration.py``): ``--gabaritos`` (alarmes falsos: nenhum
na faixa alta) e ``--geradas`` (soluções novas geradas por IA: pelo menos metade em média ou alta)::

    uv run ipc-rules calibrate ../rulesets/2026.2 --gabaritos ../../ip-checker-gabaritos \
        --geradas ../../calibracao

``calibrate-gabarito`` (S33-07) mede o alerta de possível vazamento do gabarito (ADR-11) em soluções
humanas independentes: a distribuição nas faixas do FR-29 e os alarmes falsos::

    uv run ipc-rules calibrate-gabarito ../rulesets /caminho/das/solucoes ../../ip-checker-gabaritos

``import-gabaritos`` (S33-08) leva os gabaritos de uma exportação do Notion (Markdown) para o
repositório privado, no formato ``<período>/lista-<n>/L<n>-Q<m>.py``; nunca para este::

    uv run ipc-rules import-gabaritos /caminho/da/exportacao ../../ip-checker-gabaritos \\
        --periodo 2025.2

``new-period`` (S31-10) cria a pasta de um período novo a partir de um anterior, com o mesmo
``base.yaml`` (só o período e a versão mudam) e sem questões, que reiniciam a cada período (P-07)::

    uv run ipc-rules new-period 2027.1 --from 2026.2

``retire-period`` (S43-04, ADR-12) encerra um período fora da janela dos 6 carregados: move a pasta
para ``rulesets/encerrados/``, de onde o analisador nunca carrega; o commit fica com quem roda, e o
Git guarda o histórico. ``--dry-run`` só mostra o que sairia::

    uv run ipc-rules retire-period 2020.1 --dry-run

A pasta nova sai validada; ativar o período é trocar a linha de ``rulesets/ATIVO``, num PR.

``schema`` (S35-05) gera os esquemas JSON do ruleset e das questões a partir dos modelos do
carregador (``rulesets/schema/``), e ``compile`` grava o ruleset de um período em JSON, com o
mesmo ``ruleset_sha256`` do manifesto do analisador::

    uv run ipc-rules schema
    uv run ipc-rules compile ../rulesets --saida ruleset.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from ipc_analyzer.ai_calibration import calibrate_q35, redundant_references
from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.indicators import Level
from ipc_analyzer.engine.ruleset import (
    ACTIVE_FILE,
    BASE_FILE,
    PERIOD,
    QUESTIONS_DIR,
    REFERENCES_DIR,
    RETIRED_DIR,
    WINDOW,
    CompiledRuleset,
    RulesetError,
    active_period,
    load_ruleset,
    resolve_ruleset_path,
    window_periods,
)
from ipc_analyzer.gabarito_calibration import (
    DEFAULT_MIN_TOKENS,
    DEFAULT_THRESHOLD,
    calibrate_gabarito,
)
from ipc_analyzer.gabarito_import import import_gabaritos
from ipc_analyzer.ruleset_schema import SCHEMA_DIR, compiled, write_schemas

#: Onde ficam os rulesets quando o comando roda de ``backend/``, como na CI e no ``RULES.md``.
DEFAULT_ROOT = Path("../rulesets")
#: O texto de ajuda das questões de um período novo. Não é copiado do período de origem, que lista
#: as questões dele: a numeração reinicia a cada período (P-07, S43-05).
QUESTIONS_README = "LEIA-ME.md"
QUESTIONS_README_TEXT = """\
# Regras por questão do período {period} (R-01)

Cada arquivo `L<lista>-Q<número>.yaml` desta pasta guarda o que o enunciado de uma questão permite
ou proíbe explicitamente. As regras da questão prevalecem sobre as da lista (C-02), e a questão
aparece no seletor da página assim que o ruleset é publicado.

A numeração das questões reinicia a cada período (P-07), e por isso esta pasta começa vazia. O
passo a passo do cadastro, com um exemplo comentado, está em [`RULES.md`](../../../RULES.md), na
raiz do repositório. Antes de abrir o PR, rode:

```bash
cd backend
uv run ipc-rules validate ../rulesets/{period}
```
"""
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
        "solutions",
        type=Path,
        nargs="?",
        help="soluções humanas antigas, em <período>/lista-<n>/<arquivo>.py (opcional)",
    )
    calibrate.add_argument(
        "--gabaritos", type=Path, help="os gabaritos da equipe: alarmes falsos (Q-35, S42-02)"
    )
    calibrate.add_argument(
        "--geradas",
        type=Path,
        help="soluções novas geradas por IA, diferentes das referências: acertos (Q-35)",
    )
    calibrate.add_argument(
        "--min-acerto",
        type=float,
        default=50.0,
        help="porcentagem mínima das geradas em média ou alta (padrão: 50, a meta da Q-35)",
    )
    calibrate.add_argument(
        "--remover-redundantes",
        action="store_true",
        help="apaga as referências de IA que repetem o gabarito da questão (Sprint 42.1)",
    )
    calibrate.add_argument(
        "--max-alto",
        type=float,
        default=5.0,
        help="porcentagem máxima de soluções com faixa alta (padrão: 5, a meta da ADR-08)",
    )
    leak = commands.add_parser(
        "calibrate-gabarito",
        help="mede o alerta de possível vazamento do gabarito em soluções humanas (S33-07)",
    )
    leak.add_argument("path", type=Path, help=_PATH_HELP)
    leak.add_argument(
        "solutions", type=Path, help="pasta com <período>/lista-<n>/L<n>-Q<m>/<arquivo>.py"
    )
    leak.add_argument("gabaritos", type=Path, help="pasta dos gabaritos (o repositório privado)")
    leak.add_argument(
        "--limiar",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"porcentagem do alerta (padrão: {DEFAULT_THRESHOLD:g}, a premissa da ADR-11)",
    )
    leak.add_argument(
        "--min-tokens",
        type=int,
        default=DEFAULT_MIN_TOKENS,
        help=f"tamanho mínimo dos códigos (padrão: {DEFAULT_MIN_TOKENS})",
    )
    leak.add_argument(
        "--max-alertas",
        type=int,
        default=0,
        help="alarmes falsos aceitos antes de falhar (padrão: 0, a meta da ADR-11)",
    )
    importing = commands.add_parser(
        "import-gabaritos",
        help="leva os gabaritos de uma exportação do Notion para o repositório privado (S33-08)",
    )
    importing.add_argument("export", type=Path, help="pasta da exportação do Notion (Markdown)")
    importing.add_argument("destino", type=Path, help="pasta do repositório privado dos gabaritos")
    importing.add_argument("--periodo", required=True, help="o período dos gabaritos, como 2025.2")
    importing.add_argument(
        "--sobrescrever", action="store_true", help="troca um gabarito que já existe no destino"
    )
    importing.add_argument(
        "--simular", action="store_true", help="só mostra o que faria, sem gravar nada"
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
    retire = commands.add_parser(
        "retire-period", help="encerra um período antigo: move a pasta para encerrados/ (S43-04)"
    )
    retire.add_argument("period", help="o período a encerrar, como 2020.1")
    retire.add_argument(
        "--dry-run", action="store_true", help="só mostra o que sairia, sem tocar no disco"
    )
    retire.add_argument(
        "--rulesets",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"a raiz dos rulesets (padrão: {DEFAULT_ROOT.as_posix()})",
    )
    schema = commands.add_parser(
        "schema", help="gera os esquemas JSON do ruleset e das questões (S35-05)"
    )
    schema.add_argument(
        "destino",
        type=Path,
        nargs="?",
        default=SCHEMA_DIR,
        help=f"pasta dos esquemas (padrão: {SCHEMA_DIR.as_posix()})",
    )
    compiling = commands.add_parser(
        "compile",
        help="grava o ruleset de um período em JSON, com o SHA-256 do manifesto (S35-05)",
    )
    compiling.add_argument("path", type=Path, help=_PATH_HELP)
    compiling.add_argument("--saida", type=Path, help="arquivo de saída (padrão: a tela)")
    args = parser.parse_args(argv)
    if args.command == "schema":
        for written in write_schemas(args.destino):
            print(f"esquema gravado: {written}")
        return 0
    if args.command == "compile":
        return _compile(args.path, args.saida)
    if args.command == "calibrate":
        return _calibrate(
            args.path,
            args.solutions,
            args.max_alto,
            args.gabaritos,
            args.geradas,
            args.min_acerto,
            args.remover_redundantes,
        )
    if args.command == "calibrate-gabarito":
        return _calibrate_gabarito(
            args.path,
            args.solutions,
            args.gabaritos,
            args.limiar,
            args.min_tokens,
            args.max_alertas,
        )
    if args.command == "import-gabaritos":
        return _import_gabaritos(
            args.export, args.destino, args.periodo, args.sobrescrever, args.simular
        )
    if args.command == "new-period":
        return _new_period(args.rulesets, args.period, args.source)
    if args.command == "retire-period":
        return _retire_period(args.rulesets, args.period, args.dry_run)
    return _validate(args.path, args.golden)


def _compile(path: Path, output: Path | None) -> int:
    try:
        ruleset = load_ruleset(path)
    except RulesetError as exc:
        print(exc, file=sys.stderr)
        return 1
    text = json.dumps(compiled(ruleset), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8", newline="\n")
        print(f"ruleset {ruleset.version} compilado em {output} (ruleset_sha256 {ruleset.sha256})")
    return 0


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


def _calibrate(
    path: Path,
    solutions: Path | None,
    max_high: float,
    gabaritos: Path | None = None,
    generated: Path | None = None,
    min_hits: float = 50.0,
    remove_redundant: bool = False,
) -> int:
    if solutions is None and gabaritos is None and generated is None:
        _error("diga o que medir: as soluções humanas, --gabaritos ou --geradas", path)
        return 2
    for folder in (gabaritos, generated):
        if folder is not None and not folder.is_dir():
            _error(f"{folder.as_posix()} não é uma pasta", folder)
            return 2
    base = path
    try:
        base = resolve_ruleset_path(path)
        ruleset = load_ruleset(base)
    except RulesetError as exc:
        _error(str(exc), base)
        return 1
    if remove_redundant:
        if gabaritos is None:
            _error("--remover-redundantes compara com os gabaritos: use também --gabaritos", path)
            return 2
        removed = redundant_references(ruleset, gabaritos)
        for item in removed:
            file = base.parent / "referencias" / item.question_id / f"{item.label}.py"
            file.unlink(missing_ok=True)
            print(
                f"referência redundante com o gabarito removida: "
                f"referencias/{item.question_id}/{item.label}.py ({item.percent:.0f}%)"
            )
        if removed:
            ruleset = load_ruleset(base)
    status = 0
    if gabaritos is not None or generated is not None:
        lines, ok = calibrate_q35(
            ruleset, gabaritos=gabaritos, generated=generated, min_hits=min_hits
        )
        print("\n".join(lines))
        status = 0 if ok else 1
    if solutions is None:
        return status
    return max(status, _calibrate_humans(ruleset, solutions, max_high))


def _calibrate_humans(ruleset: CompiledRuleset, solutions: Path, max_high: float) -> int:
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
    (target / QUESTIONS_DIR / QUESTIONS_README).write_text(
        QUESTIONS_README_TEXT.format(period=period), encoding="utf-8", newline="\n"
    )
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


def _calibrate_gabarito(
    path: Path, solutions: Path, gabaritos: Path, threshold: float, min_tokens: int, max_alerts: int
) -> int:
    base = path
    try:
        base = resolve_ruleset_path(path)
        ruleset = load_ruleset(base)
    except RulesetError as exc:
        _error(str(exc), base)
        return 1
    if not gabaritos.is_dir():
        _error(f"{gabaritos} não é uma pasta de gabaritos", gabaritos)
        return 2
    return calibrate_gabarito(
        ruleset,
        solutions,
        gabaritos,
        threshold=threshold,
        min_tokens=min_tokens,
        max_alerts=max_alerts,
    )


def _import_gabaritos(
    export: Path, destination: Path, period: str, overwrite: bool, dry_run: bool
) -> int:
    if not export.is_dir():
        _error(f"{export} não é uma pasta", export)
        return 2
    try:
        result = import_gabaritos(export, destination, period, overwrite=overwrite, dry_run=dry_run)
    except ValueError as exc:
        _error(str(exc), destination)
        return 2
    verb = "seriam gravados" if dry_run else "gravados"
    print(f"gabaritos {verb}: {len(result.written)}")
    for path in result.written:
        print(f"  {path}")
    if result.skipped_existing:
        print(f"já existiam (use --sobrescrever): {len(result.skipped_existing)}")
        for path in result.skipped_existing:
            print(f"  {path}")
    for conflict in result.conflicts:
        _warning(f"mais de uma solução para a mesma questão, decida à mão: {conflict}", export)
    for where in result.unknown:
        _warning(f"bloco de Python sem questão reconhecida: {where}", export)
    if result.written and not dry_run:
        print(
            "próximo passo: confira cada gabarito com o harness, de backend/: "
            f"IPC_GABARITOS_DIR={destination.as_posix()} uv run pytest tests/official_answers "
            "--no-cov"
        )
    return 1 if result.conflicts or result.unknown else 0


def _github() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _retire_period(root: Path, period: str, dry_run: bool) -> int:
    """Move ``<período>/`` para ``encerrados/<período>/``. Recusa o ativo, os da janela dos 6
    carregados, os posteriores ao ativo (em preparação) e um período que não existe."""
    if not PERIOD.fullmatch(period):
        _error(f"período inválido: {period!r} (use o formato 2020.1)", root)
        return 2
    try:
        active = active_period(root)
    except RulesetError as exc:
        _error(str(exc), root)
        return 2
    folder = root / period
    if not (folder / BASE_FILE).is_file():
        _error(f"o período {period} não existe em {root.as_posix()}", root)
        return 1
    if period == active:
        _error(f"{period} é o período ativo: troque o {ACTIVE_FILE} antes de encerrá-lo", folder)
        return 1
    if period > active:
        _error(f"{period} é posterior ao ativo ({active}): está em preparação", folder)
        return 1
    window = window_periods(root, active)
    if period in window:
        _error(
            f"{period} está na janela dos {WINDOW} períodos carregados ({', '.join(window)}): só "
            f"sai depois de haver {WINDOW} períodos mais novos (ADR-12)",
            folder,
        )
        return 1
    target = root / RETIRED_DIR / period
    if target.exists():
        _error(f"{target.as_posix()} já existe: o comando nunca sobrescreve", target)
        return 1
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    action = "sairia" if dry_run else "sai"
    print(
        f"{period} {action} de {folder.as_posix()} para {target.as_posix()} ({len(files)} arquivos)"
    )
    if dry_run:
        print("simulação: nada foi movido (--dry-run)")
        return 0
    target.parent.mkdir(exist_ok=True)
    shutil.move(str(folder), str(target))
    print(
        "movido. Confira com git status e faça o commit: o histórico do período continua no Git, "
        "e o analisador não o carrega mais"
    )
    return 0


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

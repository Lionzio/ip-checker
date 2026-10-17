"""``ipc-rules calibrate`` com a base da Q-35 (S42-02): alarmes falsos e acertos dos indícios de IA.

Sem as soluções anteriores a 2023 (descartadas em 12/10/2026), a base tem duas partes, as duas fora
deste repositório e organizadas como os gabaritos (``<período>/lista-<n>/<arquivo>.py``):

- **gabaritos da equipe** (``--gabaritos``): alarmes falsos. A meta é nenhum na faixa alta;
- **soluções novas geradas por IA** (``--geradas``), diferentes das referências do sinal 5 (senão o
  sinal acerta por construção; ``python -m ipc_api.referencias --para-calibracao``): acertos. A
  meta é pelo menos metade na faixa média ou alta.

A questão vem do começo do nome do arquivo (``L3-Q2.py`` ou ``L3-Q2-gemini-1.py``): com ela, as
regras da questão (se cadastradas) e as referências de IA entram na análise. Só os arquivos do
período do ruleset contam; ``encerrados/`` e outros períodos ficam de fora.

A saída traz contagens por faixa, por sinal e por confiança e, para os alarmes falsos, o caminho
e os tipos de indício, nunca o código.

**Referências redundantes (Sprint 42.1):** numa questão simples, a IA escreve a solução padrão, a
mesma do gabarito da equipe. Uma referência assim não distingue IA de quem resolve do jeito
padrão e põe o gabarito (e quem o escreve igual) na faixa alta. ``--remover-redundantes`` apaga
as referências que repetem o gabarito da questão a partir do limiar da faixa alta do sinal.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.guards import DEFAULT_LIMITS, InputError
from ipc_analyzer.engine.indicators import REFERENCE_LEVELS, Level
from ipc_analyzer.engine.ruleset import CompiledRuleset
from ipc_analyzer.engine.similarity import Prepared, compare_prepared, prepare

_LIST_DIR = re.compile(r"^lista-([1-6])$")
_QUESTION_PREFIX = re.compile(r"^(L([1-6])-Q[1-9]\d?)(?![0-9])")
LEVELS = ("nenhum", "baixo", "medio", "alto")
#: Uma referência que repete o gabarito a partir daqui (a faixa alta do sinal) é redundante.
REDUNDANT_PERCENT = REFERENCE_LEVELS[0][0]


@dataclass(slots=True)
class Tally:
    """O que os indícios acharam num conjunto de soluções."""

    analysed: int = 0
    refused: int = 0
    levels: Counter[str] = field(default_factory=Counter)
    #: (sinal, faixa) de cada indício com peso: quantas soluções o tiveram.
    signals: Counter[tuple[str, str]] = field(default_factory=Counter)
    confidence: Counter[str] = field(default_factory=Counter)
    #: Caminho relativo e tipos de indício das soluções na faixa alta.
    high: list[str] = field(default_factory=list)

    def share(self, *names: str) -> float:
        return (
            100 * sum(self.levels[name] for name in names) / self.analysed if self.analysed else 0
        )


def tally(ruleset: CompiledRuleset, folder: Path) -> Tally:
    """Analisa cada solução do período do ruleset com os indícios ligados."""
    result = Tally()
    period = ruleset.ruleset.period
    for file in sorted(folder.rglob("*.py")):
        parts = file.relative_to(folder).parts
        list_match = _LIST_DIR.match(file.parent.name)
        if list_match is None or parts[0] != period:
            continue
        list_number = int(list_match.group(1))
        question_match = _QUESTION_PREFIX.match(file.stem)
        question = None
        if question_match is not None and int(question_match.group(2)) == list_number:
            question = question_match.group(1)
        try:
            analysis = analyze_source(
                file.read_text(encoding="utf-8-sig"),
                list_number=list_number,
                ruleset=ruleset,
                question_id=question if question in ruleset.questions else None,
                with_indicators=True,
                reference_question=question,
            )
        except (InputError, UnicodeDecodeError):
            result.refused += 1
            continue
        if analysis.status == "syntax_error":
            # Uma solução gerada que nem é Python (S42-04 não confere a sintaxe) não conta.
            result.refused += 1
            continue
        result.analysed += 1
        indicators = analysis.indicators
        level = indicators.level if indicators is not None else None
        result.levels["nenhum" if level is None else level.label] += 1
        if indicators is None:
            continue
        for item in indicators.items:
            result.confidence[item.confidence] += 1
            if item.level is not None:
                result.signals[(item.kind, item.level.label)] += 1
        if level is Level.ALTO:
            kinds = sorted({item.kind for item in indicators.items if item.level is Level.ALTO})
            result.high.append(f"{Path(*parts).as_posix()}: {', '.join(kinds)}")
    return result


def report(title: str, found: Tally) -> list[str]:
    lines = [
        f"{title}: {found.analysed} analisadas "
        f"(recusadas pelos limites ou com erro de sintaxe: {found.refused})"
    ]
    lines.append("  faixas: " + ", ".join(f"{name} {found.levels[name]}" for name in LEVELS))
    by_signal = sorted(found.signals.items())
    if by_signal:
        lines.append(
            "  sinais: "
            + ", ".join(f"{kind} {level} {count}" for (kind, level), count in by_signal)
        )
    if found.confidence:
        lines.append(
            "  confiança: "
            + ", ".join(f"{name} {found.confidence[name]}" for name in ("baixa", "media", "alta"))
        )
    return lines


def calibrate_q35(
    ruleset: CompiledRuleset,
    *,
    gabaritos: Path | None,
    generated: Path | None,
    min_hits: float,
) -> tuple[list[str], bool]:
    """As linhas da saída e se as metas da Q-35 foram cumpridas."""
    lines: list[str] = []
    ok = True
    if gabaritos is not None:
        found = tally(ruleset, gabaritos)
        lines += report("gabaritos (alarmes falsos)", found)
        passed = found.analysed > 0 and found.levels["alto"] == 0
        lines.append(
            f"  faixa alta: {found.levels['alto']} (meta: nenhum) — "
            f"{'cumprida' if passed else 'NÃO cumprida'}"
        )
        lines += [f"  alto: {line}" for line in found.high]
        ok = ok and passed
    if generated is not None:
        found = tally(ruleset, generated)
        lines += report("geradas por IA (acertos)", found)
        hits = found.share("medio", "alto")
        passed = found.analysed > 0 and hits >= min_hits
        lines.append(
            f"  média ou alta: {hits:.1f}% (meta: pelo menos {min_hits:.0f}%) — "
            f"{'cumprida' if passed else 'NÃO cumprida'}"
        )
        ok = ok and passed
    return lines, ok


@dataclass(frozen=True, slots=True)
class Redundant:
    question_id: str
    label: str
    percent: float


def redundant_references(ruleset: CompiledRuleset, gabaritos: Path) -> list[Redundant]:
    """As referências que repetem o gabarito da própria questão (Sprint 42.1)."""
    found: list[Redundant] = []
    target = ruleset.target_version
    for file in sorted((gabaritos / ruleset.ruleset.period).glob("lista-*/*.py")):
        references = ruleset.references.get(file.stem, ())
        if not references:
            continue
        try:
            gabarito = prepare(
                file.read_text(encoding="utf-8-sig"), target=target, limits=DEFAULT_LIMITS
            )
        except (InputError, UnicodeDecodeError):
            continue
        if not isinstance(gabarito, Prepared):
            continue
        for reference in references:
            prepared = prepare(reference.source, target=target, limits=DEFAULT_LIMITS)
            if not isinstance(prepared, Prepared):
                continue
            percent = compare_prepared(gabarito, prepared).percent
            if percent >= REDUNDANT_PERCENT:
                found.append(Redundant(file.stem, reference.label, percent))
    return found

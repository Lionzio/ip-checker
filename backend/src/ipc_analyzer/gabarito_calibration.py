"""``ipc-rules calibrate-gabarito`` (S33-07): mede o alerta de possível vazamento do gabarito
(ADR-11, item 5) em soluções humanas independentes, antes de confiar no limiar.

O alerta do plágio aparece quando A com B, A com o gabarito e B com o gabarito passam do limiar e os
dois códigos têm o tamanho mínimo. Em soluções escritas de forma independente, cada alerta é um
alarme falso: a meta é nenhum. O comando também mostra como as soluções se distribuem nas faixas do
FR-29 em relação ao gabarito, para a leitura do bloco "Comparação com o gabarito".

Organização das soluções, fora deste repositório (nenhum código de aluno entra aqui, NFR-11)::

    <soluções>/<período>/lista-<n>/L<n>-Q<m>/<qualquer nome>.py
    <soluções>/<período>/lista-<n>/L<n>-Q<m>_<qualquer coisa>.py

e os gabaritos como no repositório privado: ``<gabaritos>/<período>/lista-<n>/L<n>-Q<m>.py``.

A saída traz só contagens, porcentagens e caminhos relativos, nunca código.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from ipc_analyzer.engine.gabarito import compare_with_gabarito
from ipc_analyzer.engine.guards import InputError
from ipc_analyzer.engine.ruleset import QUESTION_ID, CompiledRuleset
from ipc_analyzer.engine.similarity import InvalidSide, compare_sources

#: As faixas do FR-29, da maior para a menor: as de ``ipc_api.similarity`` (um teste confere).
BANDS = (
    ("plagio", 99.0),
    ("altas_chances", 95.0),
    ("requer_atencao", 90.0),
    ("ligeiramente_suspeito", 80.0),
    ("sem_suspeitas", 0.0),
)
#: Os valores iniciais do alerta [PREMISSA da ADR-11], os mesmos de ``ipc_api.gabaritos``.
DEFAULT_THRESHOLD = 95.0
DEFAULT_MIN_TOKENS = 60

_PERIOD = re.compile(r"^\d{4}\.[12]$")
_LIST = re.compile(r"^lista-([1-6])$")
_PREFIX = re.compile(r"^(L[1-6]-Q[1-9]\d?)(?:[_\-. ].*)?$")


@dataclass(frozen=True, slots=True)
class Solution:
    period: str
    question: str
    path: Path
    relative: str


def band_of(percent: float) -> str:
    shown = round(percent, 1)
    return next(name for name, minimum in BANDS if shown >= minimum)


def discover(root: Path) -> tuple[list[Solution], list[str]]:
    """As soluções com período e questão reconhecidos, e os arquivos ``.py`` ignorados."""
    found: list[Solution] = []
    ignored: list[str] = []
    for file in sorted(root.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        parts = file.relative_to(root).parts
        listing = _LIST.match(parts[1]) if len(parts) >= 3 else None
        question = None
        if listing is not None and _PERIOD.match(parts[0]):
            if len(parts) == 4 and QUESTION_ID.fullmatch(parts[2]):
                question = parts[2]
            elif len(parts) == 3 and (match := _PREFIX.match(file.stem)) is not None:
                question = match.group(1)
        # A questão precisa ser da lista da pasta: L3-Q2 só dentro de lista-3.
        if question is None or listing is None or question[1] != listing.group(1):
            ignored.append(relative)
            continue
        found.append(Solution(parts[0], question, file, relative))
    return found, ignored


def calibrate_gabarito(
    ruleset: CompiledRuleset,
    solutions: Path,
    gabaritos: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_alerts: int = 0,
) -> int:
    """Imprime a distribuição e os alarmes falsos; sai com 1 acima de ``max_alerts``."""
    found, ignored = discover(solutions)
    if not found:
        print(
            f"nenhuma solução em {solutions} (use <período>/lista-<n>/L<n>-Q<m>/<arquivo>.py "
            "ou <período>/lista-<n>/L<n>-Q<m>_<nome>.py)"
        )
        return 2
    target = ruleset.target_version
    structural = ruleset.structural_facts
    sources: dict[Path, str] = {}
    with_gabarito: dict[tuple[str, str], list[tuple[Solution, float, int]]] = defaultdict(list)
    bands: Counter[str] = Counter()
    missing = refused = 0
    for solution in found:
        gabarito_file = (
            gabaritos
            / solution.period
            / f"lista-{solution.question[1]}"
            / f"{solution.question}.py"
        )
        if not gabarito_file.is_file():
            missing += 1
            continue
        try:
            source = solution.path.read_text(encoding="utf-8-sig")
            gabarito = gabarito_file.read_text(encoding="utf-8-sig")
            comparison = compare_with_gabarito(
                source, gabarito, target=target, structural=structural
            )
        except (InputError, UnicodeDecodeError, OSError):
            comparison = None
        if comparison is None:
            refused += 1
            continue
        sources[solution.path] = source
        bands[band_of(comparison.percent)] += 1
        with_gabarito[(solution.period, solution.question)].append(
            (solution, comparison.percent, comparison.token_counts[0])
        )
    compared = sum(bands.values())
    print(
        f"soluções comparadas com o gabarito: {compared} (sem gabarito: {missing}, "
        f"recusadas: {refused}, fora do formato: {len(ignored)})"
    )
    for name, _minimum in BANDS:
        share = 100 * bands[name] / compared if compared else 0.0
        print(f"  {name}: {bands[name]} ({share:.1f}%)")
    near = sum(
        1 for items in with_gabarito.values() for _, percent, _ in items if percent >= threshold
    )
    print(f"acima do limiar de {threshold:g}% com o gabarito: {near}")

    pairs = 0
    alerts: list[str] = []
    for items in with_gabarito.values():
        for (first, p1, t1), (second, p2, t2) in combinations(items, 2):
            pairs += 1
            if min(p1, p2) < threshold or min(t1, t2) < min_tokens:
                continue
            try:
                result = compare_sources(sources[first.path], sources[second.path], target=target)
            except InputError:
                continue
            if isinstance(result, InvalidSide):
                continue
            if round(result.percent, 1) >= threshold and min(result.token_counts) >= min_tokens:
                alerts.append(f"{first.relative} e {second.relative}")
    print(
        f"pares da mesma questão: {pairs}; alertas de vazamento (falsos, nestas soluções "
        f"independentes): {len(alerts)} (limite: {max_alerts})"
    )
    for alert in alerts:
        print(f"  alerta: {alert}")
    return 1 if len(alerts) > max_alerts else 0

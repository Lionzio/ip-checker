"""Comparação do código do aluno com o gabarito oficial da questão (ADR-11, FR-32; S32-03).

A semelhança é a mesma do painel de plágio (ADR-07, ``similarity.py``). As construções vêm dos fatos
do motor, pelos nomes que o aluno reconhece (``display.describe``): as que os dois usam, as que só
o aluno usa e as que só o gabarito usa. As linhas são só as do aluno: nenhuma linha, nome ou trecho
do gabarito sai daqui (ADR-11, item 3), só nomes de construções.

O gabarito chega a cada chamada, vindo da memória da API; a preparação dele fica num cache pelo
hash, no próprio worker, para que a mesma questão não seja preparada de novo a cada verificação.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass

from ipc_analyzer.engine.display import describe
from ipc_analyzer.engine.facts import extract_facts
from ipc_analyzer.engine.guards import DEFAULT_LIMITS, InputError, Limits
from ipc_analyzer.engine.parse import ParsedSource, SyntaxProblem, parse_source
from ipc_analyzer.engine.similarity import Prepared, compare_prepared, normalize
from ipc_analyzer.engine.similarity_tree import fingerprint

#: Gabaritos preparados guardados por worker (uma lista tem até uns 10; sobra para o período).
CACHE_SIZE = 64
#: Construções citadas em cada grupo, para a resposta caber na tela.
MAX_CONSTRUCTS = 30


@dataclass(frozen=True, slots=True)
class GabaritoComparison:
    #: Semelhança com o gabarito, de 0,0 a 100,0, pela métrica do plágio (ADR-07).
    percent: float
    #: Tokens normalizados do aluno e do gabarito (a API avisa quando o código é curto).
    token_counts: tuple[int, int]
    common: tuple[str, ...]
    only_student: tuple[str, ...]
    only_gabarito: tuple[str, ...]
    #: Trechos do código do aluno (primeira e última linha) com a estrutura de um trecho do
    #: gabarito, na ordem do código.
    student_lines: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class _PreparedGabarito:
    prepared: Prepared
    constructs: frozenset[str]


_CACHE: OrderedDict[str, _PreparedGabarito | None] = OrderedDict()


def compare_with_gabarito(
    source: str,
    gabarito: str,
    *,
    target: tuple[int, int],
    structural: frozenset[str],
    limits: Limits = DEFAULT_LIMITS,
) -> GabaritoComparison | None:
    """Compara o código do aluno com o gabarito; ``None`` se um dos dois não puder ser analisado
    (o gabarito passa pelo harness, S20, e o aluno já foi analisado antes desta chamada).

    A preparação para a semelhança altera a árvore, então o código é analisado de novo aqui.
    """
    reference = _prepared_gabarito(gabarito, target, structural, limits)
    if reference is None:
        return None
    try:
        submission = parse_source(source, target=target, limits=limits)
    except InputError:
        return None
    if isinstance(submission, SyntaxProblem):
        return None
    constructs = _constructs(submission, structural)
    prepared = Prepared(normalized=normalize(submission), tree=fingerprint(submission.tree))
    result = compare_prepared(prepared, reference.prepared)
    return GabaritoComparison(
        percent=result.percent,
        token_counts=result.token_counts,
        common=_named(constructs & reference.constructs),
        only_student=_named(constructs - reference.constructs),
        only_gabarito=_named(reference.constructs - constructs),
        student_lines=_merge((match.a.first, match.a.last) for match in result.matches),
    )


def _prepared_gabarito(
    gabarito: str, target: tuple[int, int], structural: frozenset[str], limits: Limits
) -> _PreparedGabarito | None:
    key = hashlib.sha256(gabarito.encode("utf-8", errors="surrogatepass")).hexdigest()
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    try:
        parsed = parse_source(gabarito, target=target, limits=limits)
    except InputError:
        parsed = None
    value: _PreparedGabarito | None = None
    if isinstance(parsed, ParsedSource):
        constructs = _constructs(parsed, structural)
        value = _PreparedGabarito(
            prepared=Prepared(normalized=normalize(parsed), tree=fingerprint(parsed.tree)),
            constructs=constructs,
        )
    _CACHE[key] = value
    if len(_CACHE) > CACHE_SIZE:
        _CACHE.popitem(last=False)
    return value


def _constructs(parsed: ParsedSource, structural: frozenset[str]) -> frozenset[str]:
    """Os nomes das construções do código, sem os fatos estruturais e sem os tipos de literal."""
    return frozenset(
        describe(fact.name)
        for fact in extract_facts(parsed)
        if fact.name not in structural and not fact.name.startswith("const:")
    )


def _named(constructs: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(constructs, key=str.casefold)[:MAX_CONSTRUCTS])


def _merge(spans: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    merged: list[tuple[int, int]] = []
    for first, last in sorted(spans):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return tuple(merged)

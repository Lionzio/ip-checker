"""Comparação com o gabarito (ADR-11, FR-32; S32-03 e S32-08), com gabaritos sintéticos.

O canário é um nome e um texto que só existem no gabarito: nada da comparação pode trazê-los.
"""

from __future__ import annotations

from dataclasses import asdict

from ipc_analyzer.engine import gabarito as module
from ipc_analyzer.engine.analysis import analyze_source
from ipc_analyzer.engine.gabarito import GabaritoComparison, compare_with_gabarito
from ipc_analyzer.engine.ruleset import CompiledRuleset

CANARY = "canario_gabarito_7f3a"
GABARITO = f"""\
{CANARY} = input().split()
total = 0
for item in {CANARY}:
    total += int(item)
if total % 2 == 0:
    print("par: MARCADOR-DO-GABARITO")
else:
    print("ímpar")
"""
RENAMED = """\
valores = input().split()
soma = 0
for v in valores:
    soma += int(v)
if soma % 2 == 0:
    print("par")
else:
    print("ímpar")
"""
INDEPENDENT = """\
n = int(input())
while n > 0:
    print(n * n)
    n -= 2
"""


def _compare(
    code: str, ruleset: CompiledRuleset, gabarito: str = GABARITO
) -> GabaritoComparison | None:
    return compare_with_gabarito(
        code, gabarito, target=ruleset.target_version, structural=ruleset.structural_facts
    )


def test_the_gabarito_itself_is_identical(base_ruleset: CompiledRuleset) -> None:
    result = _compare(GABARITO, base_ruleset)

    assert result is not None
    assert result.percent == 100.0
    assert result.only_student == ()
    assert result.only_gabarito == ()


def test_a_renamed_copy_is_almost_identical(base_ruleset: CompiledRuleset) -> None:
    result = _compare(RENAMED, base_ruleset)

    assert result is not None
    assert result.percent >= 99.0
    # Os trechos são do código do aluno; atribuições curtas sozinhas não formam trecho.
    assert (3, 8) in result.student_lines


def test_an_independent_solution_is_far_and_the_constructs_differ(
    base_ruleset: CompiledRuleset,
) -> None:
    result = _compare(INDEPENDENT, base_ruleset)

    assert result is not None
    assert result.percent < 80.0
    assert "while" in result.only_student
    assert "for" in result.only_gabarito
    assert "print()" in result.common


def test_nothing_of_the_gabarito_text_leaves_the_comparison(
    base_ruleset: CompiledRuleset,
) -> None:
    for code in (GABARITO, RENAMED, INDEPENDENT):
        result = _compare(code, base_ruleset)
        assert result is not None
        dumped = repr(asdict(result))
        assert CANARY not in dumped
        assert "MARCADOR" not in dumped


def test_an_invalid_gabarito_or_student_code_gives_no_comparison(
    base_ruleset: CompiledRuleset,
) -> None:
    assert _compare(RENAMED, base_ruleset, gabarito="for x in\n") is None
    assert _compare("for x in\n", base_ruleset) is None


def test_the_prepared_gabarito_is_cached_by_hash(base_ruleset: CompiledRuleset) -> None:
    module._CACHE.clear()
    _compare(RENAMED, base_ruleset)
    _compare(INDEPENDENT, base_ruleset)

    assert len(module._CACHE) == 1


def test_the_analysis_returns_the_comparison_and_the_indicator(
    base_ruleset: CompiledRuleset,
) -> None:
    result = analyze_source(
        RENAMED, list_number=3, ruleset=base_ruleset, gabarito=GABARITO, with_indicators=True
    )

    assert result.gabarito is not None
    assert result.gabarito.percent >= 99.0
    assert result.indicators is not None
    signal = next(item for item in result.indicators.items if item.signal == "gabarito")
    assert signal.level is not None
    assert signal.level.label == "alto"
    assert CANARY not in signal.reason


def test_without_the_gabarito_nothing_changes(base_ruleset: CompiledRuleset) -> None:
    result = analyze_source(RENAMED, list_number=3, ruleset=base_ruleset, with_indicators=True)

    assert result.gabarito is None
    assert result.indicators is None or all(
        item.signal != "gabarito" for item in result.indicators.items
    )


def test_a_distant_solution_is_not_an_indicator(base_ruleset: CompiledRuleset) -> None:
    result = analyze_source(
        INDEPENDENT, list_number=3, ruleset=base_ruleset, gabarito=GABARITO, with_indicators=True
    )

    assert result.gabarito is not None
    assert result.indicators is None or all(
        item.signal != "gabarito" for item in result.indicators.items
    )

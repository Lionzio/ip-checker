"""Parser seguro (FR-05, NFR-08): AST sem execução, erros em PT-BR e limites de análise."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ipc_analyzer.engine.guards import AnalysisLimitError, InvalidInputError, Limits
from ipc_analyzer.engine.parse import (
    ParsedSource,
    SyntaxProblem,
    measure_tree,
    parse_source,
    require_runtime,
)
from ipc_analyzer.engine.ruleset import CompiledRuleset

TARGET = (3, 13)


def _parsed(source: str) -> ParsedSource:
    result = parse_source(source, target=TARGET)
    assert isinstance(result, ParsedSource)
    return result


def test_valid_code_is_parsed_and_measured() -> None:
    result = _parsed("x = int(input())\nif x > 0:\n    print('positivo')\n")

    assert result.line_count == 3
    assert result.node_count > 10
    assert result.depth >= 4


def test_code_is_never_executed(tmp_path: Path) -> None:
    canary = tmp_path / "canary"
    source = (
        f"open({str(canary)!r}, 'w').write('invadido')\n"
        "__import__('os').system('echo invadido')\n"
        "eval('1 + 1')\n"
    )

    _parsed(source)

    assert not canary.exists()


@pytest.mark.timing
def test_infinite_loop_is_only_parsed() -> None:
    start = time.perf_counter()

    _parsed("while True:\n    x = 1\n")

    assert time.perf_counter() - start < 0.1


def test_input_errors_propagate() -> None:
    with pytest.raises(InvalidInputError, match="vazio"):
        parse_source("   ", target=TARGET)


@pytest.mark.parametrize(
    ("source", "line", "col", "message"),
    [
        ("x = (1\n", 1, 5, "o '(' foi aberto e nunca fechado"),
        ("if x\n    y = 1\n", 1, 5, "faltou ':'"),
        (
            "print 'oi'\n",
            1,
            1,
            "faltam parênteses na chamada de 'print'. Você quis dizer print(...)?",
        ),
        ("x = 'abc\n", 1, 5, "string não terminada (detectada na linha 1)"),
        (
            "def f():\nreturn 1\n",
            2,
            1,
            "faltou um bloco indentado depois da definição de função da linha 1",
        ),
        ("x = 1\n  y = 2\n", 2, 2, "indentação inesperada"),  # o Python aponta o fim do recuo
        ("x == 1 = 2\n", 1, 1, "não é possível atribuir a uma comparação"),
        ("f(a b)\n", 1, 3, "sintaxe inválida. Talvez falte uma vírgula?"),
        ("x = 5a\n", 1, 5, "número decimal inválido"),
        (")\n", 1, 1, "')' fechado sem ter sido aberto"),
    ],
)
def test_syntax_errors_are_reported_in_portuguese(
    source: str, line: int, col: int, message: str
) -> None:
    result = parse_source(source, target=TARGET)

    assert isinstance(result, SyntaxProblem)
    assert (result.line, result.col, result.message) == (line, col, message)
    assert result.python_message


def test_syntax_error_column_counts_characters_not_bytes() -> None:
    result = parse_source("s = 'ação' + (\n", target=TARGET)

    assert isinstance(result, SyntaxProblem)
    assert result.col == 14  # em bytes UTF-8 seria 16


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("(" * 1_000 + ")" * 1_000, "200 níveis"),
        ("x = " + "[" * 250 + "]" * 250, "200 níveis"),
        ("x = " + "1+" * 25_000 + "1", "complexo demais|níveis de aninhamento"),
        ("x = " + "not " * 300 + "y", "níveis de aninhamento"),
    ],
    ids=["1000-parenteses", "250-colchetes", "cadeia-25k-somas", "300-not"],
)
@pytest.mark.timing
def test_pathological_inputs_hit_analysis_limits(source: str, expected: str) -> None:
    start = time.perf_counter()

    with pytest.raises(AnalysisLimitError, match=expected):
        parse_source(source, target=TARGET)

    assert time.perf_counter() - start < 2.0


@pytest.mark.parametrize("error", [RecursionError, MemoryError])
def test_parser_resource_errors_become_analysis_limit(
    monkeypatch: pytest.MonkeyPatch, error: type[Exception]
) -> None:
    def explode(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr("ipc_analyzer.engine.parse.ast.parse", explode)

    with pytest.raises(AnalysisLimitError, match="complexo demais"):
        parse_source("x = 1\n", target=TARGET)


def test_widest_input_within_50kb_fits_the_node_limit() -> None:
    # Calibração da S5-01: 1 mil linhas com tuplas de 24 nomes somam ~53 mil nós em 50 KB.
    source = "a = " + ",".join("bcdefghijklmnopqrstuvwxy") + "\n"
    result = _parsed(source * 980)

    assert 50_000 < result.node_count < 60_000


def test_node_limit_still_applies_with_custom_limits() -> None:
    source = "a = (b, c, d, e, f, g, h, i, j, k, l, m, n, o, p)\n" * 1_000

    with pytest.raises(AnalysisLimitError, match="elementos sintáticos"):
        parse_source(source, target=TARGET, limits=Limits(max_nodes=20_000))


def test_measure_tree_respects_custom_limits() -> None:
    tree = _parsed("x = 1\ny = 2\n").tree

    with pytest.raises(AnalysisLimitError, match="elementos sintáticos"):
        measure_tree(tree, Limits(max_nodes=3))
    with pytest.raises(AnalysisLimitError, match="níveis de aninhamento"):
        measure_tree(tree, Limits(max_depth=2))


def test_runtime_matches_the_ruleset_target(base_ruleset: CompiledRuleset) -> None:
    assert base_ruleset.target_version == TARGET

    require_runtime(base_ruleset.target_version)

    with pytest.raises(RuntimeError, match=r"Python 3\.12"):
        require_runtime((3, 12))

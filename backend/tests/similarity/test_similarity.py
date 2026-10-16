"""Detector de plágio (S17-01; FR-29, ADR-05, NFR-25): corpus de pares, limites e propriedades."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import yaml

from ipc_analyzer.engine.guards import (
    AnalysisLimitError,
    InputError,
    InvalidInputError,
    PayloadTooLargeError,
)
from ipc_analyzer.engine.similarity import (
    AST_WEIGHT,
    TOKEN_WEIGHT,
    WINDOW,
    InvalidSide,
    K,
    Similarity,
    compare_sources,
)

TARGET = (3, 13)
CORPUS: list[dict[str, Any]] = yaml.safe_load(
    (Path(__file__).with_name("pares.yaml")).read_text(encoding="utf-8")
)["pares"]


def compare(first: str, second: str) -> Similarity:
    result = compare_sources(first, second, target=TARGET)
    assert isinstance(result, Similarity), result
    return result


@pytest.mark.parametrize("pair", CORPUS, ids=[pair["nome"] for pair in CORPUS])
def test_the_corpus_of_pairs(pair: dict[str, Any]) -> None:
    percent = compare(pair["a"], pair["b"]).percent

    if "exato" in pair:
        assert percent == pair["exato"]
    assert pair.get("minimo", 0.0) <= percent <= pair.get("maximo", 100.0), percent


def test_the_parameters_are_the_documented_ones() -> None:
    # Mudar qualquer um deles exige recalibrar o corpus (ADR-05).
    assert (TOKEN_WEIGHT, AST_WEIGHT, K, WINDOW) == (0.6, 0.4, 5, 4)


@pytest.mark.parametrize("pair", CORPUS[:4], ids=[pair["nome"] for pair in CORPUS[:4]])
def test_the_comparison_is_symmetric_and_deterministic(pair: dict[str, Any]) -> None:
    forward = compare(pair["a"], pair["b"])
    backward = compare(pair["b"], pair["a"])

    assert forward.percent == backward.percent == compare(pair["a"], pair["b"]).percent


def test_identical_code_is_100_and_one_decimal_place() -> None:
    code = CORPUS[0]["a"]
    result = compare(code, code)

    assert result.percent == 100.0
    assert result.token_counts[0] == result.token_counts[1] > 50
    partial = compare(code, CORPUS[6]["a"]).percent
    assert partial == round(partial, 1)


def test_keywords_builtins_and_methods_are_not_treated_as_student_names() -> None:
    # Trocar print por outra função, ou append por insert, muda o código de verdade.
    base = "valores = []\nvalores.append(1)\nprint(len(valores))\n"
    changed = "valores = []\nvalores.insert(1)\nshow(sum(valores))\n"

    assert compare(base, changed).percent < 100.0
    assert compare(base, base.replace("valores", "lista")).percent == 100.0


def test_short_codes_are_compared_directly() -> None:
    assert compare("x = 1\n", "y = 1\n").percent == 100.0
    assert compare("x = 1\n", "print(2)\n").percent < 50.0
    assert compare("pass\n", "pass\n").percent == 100.0


def test_comments_only_code_and_empty_code() -> None:
    assert compare("# nada\n", "# outra coisa\n").percent == 100.0
    with pytest.raises(InvalidInputError):
        compare_sources("", "x = 1\n", target=TARGET)


@pytest.mark.parametrize("side", [1, 2])
def test_a_syntax_error_says_which_code_and_where(side: int) -> None:
    good, bad = "x = 1\n", "x = 1\nif x\n    y = 2\n"
    first, second = (bad, good) if side == 1 else (good, bad)

    result = compare_sources(first, second, target=TARGET)

    assert isinstance(result, InvalidSide)
    assert result.side == side
    assert (result.problem.line, result.problem.col) == (2, 5)
    assert result.problem.message


@pytest.mark.parametrize(
    ("source", "error"),
    [
        ("#" + "a" * 51_200, PayloadTooLargeError),
        ("x = 1\n" * 1_001, InvalidInputError),
        ("x = '\x00'\n", InvalidInputError),
        ("(" * 1_000 + ")" * 1_000, AnalysisLimitError),
        ("x = " + "+".join(["1"] * 25_000) + "\n", AnalysisLimitError),
    ],
    ids=["50kb", "1001-linhas", "byte-nulo", "aninhamento", "cadeia-de-somas"],
)
@pytest.mark.parametrize("side", [1, 2])
def test_malicious_inputs_on_either_side_are_refused_like_the_analysis(
    source: str, error: type[InputError], side: int
) -> None:
    pair = (source, "x = 1\n") if side == 1 else ("x = 1\n", source)

    with pytest.raises(error):
        compare_sources(*pair, target=TARGET)


def _big_program(size: int = 50_000) -> str:
    # Os nomes lidos também são ligados no programa: só assim são nomes do aluno (symbols.py).
    lines = [f"dado_{n} = resto_{n} = {n}" for n in range(7)]
    index = 0
    while sum(len(line) + 1 for line in lines) < size - 200 and len(lines) < 990:
        a, b, c = index % 7, index % 5, index % 3
        lines.append(
            f"valor_{index} = (dado_{a} * {index} + resto_{b}) % 97 if dado_{c} > {a} else {index}"
        )
        index += 1
    return "\n".join(lines) + "\n"


@contextmanager
def _without_coverage() -> Iterator[None]:
    """Pausa a medição de cobertura: a instrumentação deixa o código mais lento (no Windows, a
    comparação de 50 KB passava de 2 s só por ela), e o NFR-25 vale para o worker sem ela."""
    coverage = sys.modules.get("coverage")
    current = coverage.Coverage.current() if coverage is not None else None
    if current is not None:
        current.stop()
    try:
        yield
    finally:
        if current is not None:
            current.start()


@pytest.mark.timing
def test_two_50_kb_codes_are_compared_within_the_budget() -> None:
    big = _big_program()
    other = big.replace("valor_", "saida_").replace("dado_", "info_")
    assert 45_000 < len(big.encode()) == len(other.encode()) <= 51_200

    with _without_coverage():
        start = time.perf_counter()
        result = compare(big, other)
        elapsed = time.perf_counter() - start

    assert result.percent == 100.0
    # NFR-25: dois códigos de 50 KB em até 2 s no worker.
    assert elapsed < 2.0, f"{elapsed:.2f} s"


def test_a_lone_carriage_return_after_an_accent_is_a_line_break() -> None:
    # Achado pelo schemathesis: "Ý\rØ" passava pelo ast.parse e derrubava o tokenize (500).
    code = "número = int(input())\nmédia = número / 2\nprint(média)\n"
    other = "valor = int(input())\nprint(valor * 3)\n"

    assert compare(code.replace("\n", "\r"), other) == compare(code, other)
    assert compare(code.replace("\n", "\r"), code).percent == 100.0

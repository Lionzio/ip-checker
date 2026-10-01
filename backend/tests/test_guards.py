"""Limites de entrada (FR-04, NFR-08): tamanho, linhas, vazio, NUL, controle e UTF-8."""

from __future__ import annotations

import pytest

from ipc_analyzer.engine.guards import (
    AnalysisLimitError,
    InputError,
    InvalidInputError,
    Limits,
    PayloadTooLargeError,
    check_source,
    count_lines,
    line_at,
    thousands,
)


def test_valid_source_is_returned_unchanged() -> None:
    assert check_source("x = 1\n") == "x = 1\n"


def test_leading_bom_is_removed() -> None:
    assert check_source("\ufeffx = 1\n") == "x = 1\n"


def test_size_limit_is_51200_bytes() -> None:
    assert check_source("#" + "a" * 51_199)

    with pytest.raises(PayloadTooLargeError, match=r"51\.201 bytes"):
        check_source("#" + "a" * 51_200)


def test_size_limit_counts_utf8_bytes_not_characters() -> None:
    text = "#" + "é" * 25_600  # 25.601 caracteres, mas 51.201 bytes

    with pytest.raises(PayloadTooLargeError):
        check_source(text)


def test_line_limit_is_1000_lines() -> None:
    assert check_source("x = 1\n" * 1_000)

    with pytest.raises(InvalidInputError, match=r"1\.001 linhas"):
        check_source("x = 1\n" * 1_001)


@pytest.mark.parametrize("text", ["", "   \n\t\n"])
def test_empty_code_is_rejected(text: str) -> None:
    with pytest.raises(InvalidInputError, match="vazio"):
        check_source(text)


def test_null_byte_is_rejected_with_its_line() -> None:
    with pytest.raises(InvalidInputError, match="caractere nulo na linha 2"):
        check_source("x = 1\ny = '\x00'\n")


def test_control_character_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match=r"U\+0007\) na linha 1"):
        check_source("x = '\x07'\n")


def test_tab_form_feed_and_crlf_are_accepted() -> None:
    text = "if x:\r\n\ty = 1\x0c\r\n"

    assert check_source(text) == text


def test_lone_surrogate_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="UTF-8"):
        check_source("x = '\ud800'\n")


def test_custom_limits_are_respected() -> None:
    with pytest.raises(InvalidInputError, match="limite é 1"):
        check_source("x = 1\ny = 2\n", Limits(max_lines=1))


def test_error_codes_follow_the_api_contract() -> None:
    assert InvalidInputError.code == "INVALID_INPUT"
    assert PayloadTooLargeError.code == "PAYLOAD_TOO_LARGE"
    assert AnalysisLimitError.code == "ANALYSIS_LIMIT"
    error: InputError = AnalysisLimitError("mensagem")
    assert error.message == str(error) == "mensagem"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", 0), ("a", 1), ("a\n", 1), ("a\r\nb", 2), ("a\rb\nc\n", 3), ("\n\n", 2)],
)
def test_count_lines_follows_python_line_breaks(text: str, expected: int) -> None:
    assert count_lines(text) == expected


def test_line_at_and_thousands() -> None:
    assert line_at("a\nb\r\nc", 5) == 3
    assert thousands(51_200) == "51.200"

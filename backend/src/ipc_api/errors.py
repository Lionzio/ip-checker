"""Erros do contrato (5.2.2): sempre ``{"error": {"code", "message", "retry_after_s"}}``."""

from __future__ import annotations

from enum import StrEnum

from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    INVALID_INPUT = "INVALID_INPUT"
    LIST_NOT_ENABLED = "LIST_NOT_ENABLED"
    UNKNOWN_QUESTION = "UNKNOWN_QUESTION"
    ANALYSIS_LIMIT = "ANALYSIS_LIMIT"
    ANALYZER_UNAVAILABLE = "ANALYZER_UNAVAILABLE"


#: Espera sugerida ao cliente quando o analyzer não responde.
UNAVAILABLE_RETRY_S = 30


class ApiError(Exception):
    def __init__(
        self, status: int, code: ErrorCode, message: str, retry_after_s: int | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after_s = retry_after_s

    def response(self) -> JSONResponse:
        return error_response(self.status, self.code, self.message, self.retry_after_s)


def error_response(
    status: int, code: ErrorCode, message: str, retry_after_s: int | None = None
) -> JSONResponse:
    headers = {"Retry-After": str(retry_after_s)} if retry_after_s is not None else None
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "retry_after_s": retry_after_s}},
        headers=headers,
    )


def analyzer_unavailable() -> ApiError:
    return ApiError(
        503,
        ErrorCode.ANALYZER_UNAVAILABLE,
        "O analisador está indisponível no momento. Tente de novo em alguns segundos.",
        retry_after_s=UNAVAILABLE_RETRY_S,
    )

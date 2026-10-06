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
    RATE_LIMITED = "RATE_LIMITED"
    OVERLOADED = "OVERLOADED"
    ANALYZER_UNAVAILABLE = "ANALYZER_UNAVAILABLE"
    # Acesso restrito à equipe (Sprint 13, FR-22 e FR-25).
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    DOMAIN_NOT_ALLOWED = "DOMAIN_NOT_ALLOWED"
    ACCOUNT_PENDING_VERIFICATION = "ACCOUNT_PENDING_VERIFICATION"
    ACCOUNT_PENDING_APPROVAL = "ACCOUNT_PENDING_APPROVAL"
    ACCOUNT_REJECTED = "ACCOUNT_REJECTED"
    ACCOUNT_REMOVED = "ACCOUNT_REMOVED"
    ORIGIN_MISMATCH = "ORIGIN_MISMATCH"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    # Registro, verificação e perfil (Sprint 14, FR-23 e FR-26).
    NAME_TAKEN = "NAME_TAKEN"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    WEAK_PASSWORD = "WEAK_PASSWORD"  # noqa: S105 - código de erro, não um segredo
    INVALID_TOKEN = "INVALID_TOKEN"  # noqa: S105 - código de erro, não um segredo
    EMAIL_UNAVAILABLE = "EMAIL_UNAVAILABLE"
    # Sprint 15: gerenciamento da equipe (FR-27).
    FORBIDDEN = "FORBIDDEN"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    ACCOUNT_STATE_CHANGED = "ACCOUNT_STATE_CHANGED"
    # Sprint 25: uma falha inesperada da API vira um 500 em JSON, com o identificador (S25-04).
    INTERNAL_ERROR = "INTERNAL_ERROR"


#: Espera sugerida ao cliente quando o analyzer não responde.
UNAVAILABLE_RETRY_S = 30
#: Espera sugerida quando não há vaga para a análise (admissão).
OVERLOADED_RETRY_S = 10


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


def database_unavailable() -> ApiError:
    return ApiError(
        503,
        ErrorCode.DATABASE_UNAVAILABLE,
        "O serviço está indisponível no momento. Tente de novo em alguns segundos.",
        retry_after_s=UNAVAILABLE_RETRY_S,
    )


def unauthenticated() -> ApiError:
    return ApiError(
        401, ErrorCode.UNAUTHENTICATED, "Entre com a sua conta da equipe para usar o IP-Checker."
    )


def overloaded() -> ApiError:
    return ApiError(
        503,
        ErrorCode.OVERLOADED,
        "O serviço está sobrecarregado no momento. Tente de novo em alguns segundos.",
        retry_after_s=OVERLOADED_RETRY_S,
    )

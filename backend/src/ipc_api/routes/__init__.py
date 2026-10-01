"""Rotas públicas da API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ipc_api.schemas import ErrorResponse


def error_docs(descriptions: Mapping[int, str]) -> dict[int | str, dict[str, Any]]:
    """Documenta respostas de erro no OpenAPI, sempre com o envelope ``ErrorResponse``."""
    return {
        status: {"model": ErrorResponse, "description": text}
        for status, text in descriptions.items()
    }

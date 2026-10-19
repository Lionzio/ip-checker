"""As dependências do FastAPI para os gabaritos pelo painel (Sprint 51)."""

from __future__ import annotations

from fastapi import Request

from ipc_api.answer_keys.service import GabaritoService


def get_gabarito_service(request: Request) -> GabaritoService:
    service: GabaritoService = request.app.state.gabarito_service
    return service

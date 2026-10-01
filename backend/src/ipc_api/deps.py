"""Dependências das rotas: o estado criado em ``create_app`` e no lifespan."""

from __future__ import annotations

from fastapi import Request

from ipc_api.clients.analyzer import AnalyzerClient
from ipc_api.settings import ApiSettings


def get_analyzer(request: Request) -> AnalyzerClient:
    client: AnalyzerClient = request.app.state.analyzer
    return client


def get_settings(request: Request) -> ApiSettings:
    settings: ApiSettings = request.app.state.settings
    return settings


def get_request_id(request: Request) -> str:
    request_id: str = request.state.request_id
    return request_id

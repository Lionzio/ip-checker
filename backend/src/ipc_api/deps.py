"""Dependências das rotas: o estado criado em ``create_app`` e no lifespan."""

from __future__ import annotations

from fastapi import Request

from ipc_api.admission import Admission
from ipc_api.clients.analyzer import AnalyzerClient
from ipc_api.settings import ApiSettings
from ipc_api.slo import SloMonitor
from ipc_api.telemetry import Telemetry


def get_analyzer(request: Request) -> AnalyzerClient:
    client: AnalyzerClient = request.app.state.analyzer
    return client


def get_admission(request: Request) -> Admission:
    admission: Admission = request.app.state.admission
    return admission


def get_settings(request: Request) -> ApiSettings:
    settings: ApiSettings = request.app.state.settings
    return settings


def get_request_id(request: Request) -> str:
    request_id: str = request.state.request_id
    return request_id


def get_telemetry(request: Request) -> Telemetry:
    telemetry: Telemetry = request.app.state.telemetry
    return telemetry


def get_slo(request: Request) -> SloMonitor:
    monitor: SloMonitor = request.app.state.slo
    return monitor

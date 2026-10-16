"""Indícios de uso de IA na API (ADR-08, US-34; S29-01 e S29-03).

Desligados por padrão (``IPC_AI_INDICATORS``): no piloto, só depois de a coordenação aprovar a
política (S29-04). Ligados, vão só na resposta da verificação, para a equipe, com o aviso de que não
são prova; nunca no feedback ao aluno.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import httpx2
import pytest
import yaml
from fastapi.testclient import TestClient

from conftest import BASE_RULESET, REPO_ROOT
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.schemas import FeedbackResponse, ValidateResponse
from ipc_api.settings import ApiSettings
from ipc_api.telemetry import TelemetryEvent
from test_api import HEALTH, INVALID, MANIFEST, SETTINGS, FakeAnalyzer, make_client, reply, validate

INDICATORS = {
    "level": "alto",
    "items": [
        {
            "signal": "multiplas_violacoes",
            "kind": "variedade",
            "level": "alto",
            "confidence": "alta",
            "reason": "3 proibições gerais diferentes: 'break', 'continue' e 'pass'.",
            "lines": [5, 7, 9],
            "evidence": {"rule": "R-11, R-12", "excerpt": "break"},
        }
    ],
    "questions": ["O que o 'break' da linha 5 faz?", "Faça uma pequena mudança no programa."],
}


class Recording(FakeAnalyzer):
    """O analisador simulado, guardando o corpo de cada pedido de análise."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.bodies: list[dict[str, Any]] = []

        def analyze(request: httpx2.Request) -> httpx2.Response:
            self.bodies.append(json.loads(request.content))
            return httpx2.Response(200, json=answer)

        super().__init__(
            {
                "/internal/analyze": analyze,
                "/internal/health": reply(200, HEALTH),
                "/internal/ruleset/manifest": reply(200, MANIFEST),
            }
        )


def test_off_by_default_nothing_is_asked_or_shown() -> None:
    analyzer = Recording({**INVALID, "indicators": INDICATORS})

    with make_client(analyzer) as client:
        response = validate(client)
        options = client.get("/api/v1/auth/options").json()

    assert response.status_code == 200
    assert analyzer.bodies[0]["indicators"] is False
    # Mesmo que o analisador mandasse algo, a API não repassa com os indícios desligados.
    assert response.json()["indicators"] is None
    assert options["ai_indicators"] is False


def test_when_on_the_team_sees_the_indicators_with_the_notice() -> None:
    analyzer = Recording({**INVALID, "indicators": INDICATORS})

    with make_client(analyzer, replace(SETTINGS, ai_indicators=True)) as client:
        response = validate(client)
        options = client.get("/api/v1/auth/options").json()

    assert analyzer.bodies[0]["indicators"] is True
    found = response.json()["indicators"]
    assert found["level"] == "alto"
    assert found["items"] == INDICATORS["items"]
    assert found["questions"] == INDICATORS["questions"]
    assert "não são prova" in found["notice"]
    assert options["ai_indicators"] is True


def test_when_on_without_indicators_nothing_is_shown() -> None:
    analyzer = Recording({**INVALID, "indicators": None})

    with make_client(analyzer, replace(SETTINGS, ai_indicators=True)) as client:
        response = validate(client)

    assert response.json()["indicators"] is None


def test_an_untrustworthy_indicator_makes_the_analyzer_unavailable() -> None:
    broken = {**INDICATORS, "level": "certeza"}
    analyzer = Recording({**INVALID, "indicators": broken})

    with make_client(analyzer, replace(SETTINGS, ai_indicators=True)) as client:
        response = validate(client)

    assert response.status_code == 503


def test_the_feedback_never_carries_indicators() -> None:
    # O feedback vai para o aluno: o contrato dele não tem onde pôr um indício (ADR-08, item 4).
    assert "indicators" not in FeedbackResponse.model_fields
    assert "indicators" in ValidateResponse.model_fields


# --- Pelo analisador de verdade ------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_app(settings)) as client:
        yield client


def test_the_analyzer_service_computes_them_only_when_asked(real_analyzer: TestClient) -> None:
    code = (
        "for i in range(5):\n"
        "    if i == 1:\n"
        "        break\n"
        "    if i == 2:\n"
        "        continue\n"
        "    pass\n"
    )
    payload = {"code": code, "list_number": 2}

    without = real_analyzer.post("/internal/analyze", json=payload).json()
    with_them = real_analyzer.post("/internal/analyze", json={**payload, "indicators": True}).json()

    assert without["indicators"] is None
    assert with_them["indicators"]["level"] == "alto"
    assert [item["kind"] for item in with_them["indicators"]["items"]] == ["variedade"]
    assert with_them["indicators"]["items"][0]["lines"] == [3, 5, 6]
    # S42-03: a evidência (a regra e o trecho da primeira linha) e a confiança.
    assert with_them["indicators"]["items"][0]["evidence"] == {
        "rule": "R-11, R-12",
        "excerpt": "break",
    }
    assert with_them["indicators"]["items"][0]["confidence"] == "alta"
    assert 2 <= len(with_them["indicators"]["questions"]) <= 3


def test_the_pilot_keeps_them_off_until_the_policy_is_approved() -> None:
    # ADR-08 e S29-04: ligar no piloto é mudar o render.yaml por PR, depois da política aprovada.
    blueprint = yaml.safe_load((REPO_ROOT / "render.yaml").read_text(encoding="utf-8"))
    env = {item["key"]: item.get("value") for item in blueprint["services"][0]["envVars"]}

    assert env["IPC_AI_INDICATORS"] == "0"
    assert ApiSettings().ai_indicators is False


def test_the_evidence_never_reaches_the_logs_or_the_telemetry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # S42-03: o trecho da evidência é código do aluno; vai só na resposta para a equipe.
    canary = "CANARIO_EVIDENCIA_42"
    item = {**INDICATORS["items"][0], "evidence": {"rule": "R-11", "excerpt": f"# {canary}"}}
    analyzer = Recording({**INVALID, "indicators": {**INDICATORS, "items": [item]}})
    caplog.set_level("DEBUG")

    with make_client(analyzer, replace(SETTINGS, ai_indicators=True)) as client:
        response = validate(client)

    assert response.json()["indicators"]["items"][0]["evidence"]["excerpt"] == f"# {canary}"
    assert canary not in caplog.text
    fields = {field.name for field in dataclasses.fields(TelemetryEvent)}
    assert not fields & {"indicators", "evidence", "excerpt", "reason"}

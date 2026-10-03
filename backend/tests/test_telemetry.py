"""Telemetria anônima (S21-01; FR-16, NFR-12) e alertas de latência e erro (S21-02; NFR-15)."""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Sequence
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import authed_client, make_app
from ipc_api.settings import ApiSettings
from ipc_api.slo import SloConfig, SloMonitor
from ipc_api.telemetry import Telemetry, TelemetryConfig, TelemetryEvent, semester_of
from test_api import INVALID, MANIFEST, VALID, FakeAnalyzer, reply

CANARY = "CANARIO_TELEMETRIA_7f3a"


class FakeSink:
    def __init__(self, *, fail: bool = False) -> None:
        self.batches: list[list[TelemetryEvent]] = []
        self.purges = 0
        self.closed = False
        self.fail = fail

    async def write(self, events: Sequence[TelemetryEvent]) -> None:
        if self.fail:
            raise ConnectionError("banco fora")
        self.batches.append(list(events))

    async def purge_expired(self) -> int:
        self.purges += 1
        if self.fail:
            raise ConnectionError("banco fora")
        return 3

    async def close(self) -> None:
        self.closed = True

    @property
    def events(self) -> list[TelemetryEvent]:
        return [event for batch in self.batches for event in batch]


def event(outcome: str = "valid", rules: Sequence[str] = ()) -> TelemetryEvent:
    return TelemetryEvent.from_result(
        ruleset_version="2026.2.1",
        list_number=2,
        outcome=outcome,  # type: ignore[arg-type]
        rule_ids=rules,
        analysis_ms=12,
    )


# --- O evento ----------------------------------------------------------------------------------


def test_event_counts_rules_and_takes_the_period_from_the_ruleset() -> None:
    found = event("invalid", ["R-37", "R-02", "R-37"])

    assert found.semester == "2026.2"
    assert found.question_id is None
    assert found.violation_count == 3
    assert found.rules == (("R-02", 1), ("R-37", 2))
    assert semester_of("2027.1.4") == "2027.1"


def test_event_has_no_field_for_code_ip_or_account() -> None:
    fields = {field.name for field in dataclasses.fields(TelemetryEvent)}

    assert fields == {
        "semester",
        "list_number",
        "question_id",
        "ruleset_version",
        "outcome",
        "violation_count",
        "analysis_ms",
        "rules",
    }


# --- A fila e a gravação em lote ----------------------------------------------------------------


def run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


FAST = TelemetryConfig(batch_size=3, flush_interval_s=0.05, queue_size=5)


def test_events_are_written_in_batches_and_purge_runs_at_start() -> None:
    async def scenario() -> FakeSink:
        sink = FakeSink()
        telemetry = Telemetry(sink, FAST)
        telemetry.start()
        for _ in range(4):
            telemetry.record(event())
        await asyncio.sleep(0.2)
        await telemetry.stop()
        return sink

    sink = run(scenario())

    assert [len(batch) for batch in sink.batches] == [3, 1]
    assert sink.purges == 1
    assert sink.closed


def test_a_full_queue_drops_events_without_blocking() -> None:
    async def scenario() -> Telemetry:
        telemetry = Telemetry(FakeSink(), dataclasses.replace(FAST, flush_interval_s=10))
        telemetry.start()
        for _ in range(8):  # a fila guarda 5; o lote de 3 só sai depois da janela de 10 s
            telemetry.record(event())
        await asyncio.sleep(0)
        dropped = telemetry.stats.dropped
        await telemetry.stop()
        assert telemetry.stats.written + dropped == 8
        return telemetry

    telemetry = run(scenario())

    assert telemetry.stats.dropped >= 3


def test_a_failing_database_never_reaches_the_caller() -> None:
    async def scenario() -> Telemetry:
        telemetry = Telemetry(FakeSink(fail=True), FAST)
        telemetry.start()
        telemetry.record(event())
        telemetry.record(event())
        await asyncio.sleep(0.2)
        await telemetry.stop()
        return telemetry

    telemetry = run(scenario())

    assert telemetry.stats.failed_batches == 1
    assert telemetry.stats.dropped == 2
    assert telemetry.stats.written == 0


def test_stop_writes_what_is_still_queued() -> None:
    async def scenario() -> FakeSink:
        sink = FakeSink()
        telemetry = Telemetry(sink, dataclasses.replace(FAST, flush_interval_s=10, batch_size=50))
        telemetry.start()
        telemetry.record(event())
        await telemetry.stop()
        return sink

    assert len(run(scenario()).events) == 1


@pytest.mark.parametrize(
    "telemetry", [Telemetry(None), Telemetry(FakeSink(), TelemetryConfig(enabled=False))]
)
def test_without_database_or_disabled_nothing_is_queued(telemetry: Telemetry) -> None:
    async def scenario() -> None:
        telemetry.start()
        telemetry.record(event())
        assert telemetry.queued == 0
        await telemetry.stop()

    run(scenario())

    assert not telemetry.active
    assert telemetry.ruleset_version == "2026.2.1"


# --- O que a verificação registra --------------------------------------------------------------


def client_with(sink: FakeSink, analyzer: FakeAnalyzer, **settings: Any) -> TestClient:
    config = ApiSettings(
        analyzer_url="http://analyzer.test",
        telemetry=TelemetryConfig(flush_interval_s=0.01),
        **settings,
    )
    app, store = make_app(
        config, analyzer_transport=httpx2.MockTransport(analyzer), telemetry_sink=sink
    )
    return authed_client(app, store)


def analyzer_with(analyze: Any) -> FakeAnalyzer:
    return FakeAnalyzer(
        {"/internal/analyze": analyze, "/internal/ruleset/manifest": reply(200, MANIFEST)}
    )


def post(client: TestClient, code: str, list_number: int = 1) -> int:
    response = client.post(
        "/api/v1/validate", json={"code": code, "list_number": list_number, "question_id": None}
    )
    return response.status_code


def test_each_verification_becomes_an_anonymous_event() -> None:
    sink = FakeSink()
    analyzer = analyzer_with(reply(200, INVALID))

    with client_with(sink, analyzer) as client:
        assert post(client, f"# {CANARY}\nfor i in range(3):\n    print(i)\n") == 200

    (found,) = sink.events
    assert (found.semester, found.list_number, found.ruleset_version) == ("2026.2", 1, "2026.2.0")
    assert (found.outcome, found.violation_count, found.rules) == ("invalid", 1, (("R-34", 1),))
    assert found.analysis_ms >= 0
    assert CANARY not in repr(found)


def test_refusals_are_counted_with_the_known_ruleset_version() -> None:
    sink = FakeSink()
    limit = {"error": {"code": "ANALYSIS_LIMIT", "message": "complexo demais"}}
    analyzer = analyzer_with(reply(422, limit))

    with client_with(sink, analyzer) as client:
        assert post(client, "x = (1)\n") == 422  # o analisador recusa: limite de análise
        assert post(client, "\x00") == 422  # a API recusa antes de analisar
        assert post(client, "x = 1\n", list_number=5) == 422  # lista não habilitada: não conta

    assert [(e.outcome, e.ruleset_version, e.list_number) for e in sink.events] == [
        ("analysis_limit", "2026.2.0", 1),
        ("rejected", "2026.2.0", 1),
    ]


def test_valid_code_is_an_event_without_rules() -> None:
    sink = FakeSink()

    with client_with(sink, analyzer_with(reply(200, VALID))) as client:
        assert post(client, "x = 1\nif x:\n    print(x)\n") == 200

    assert [(e.outcome, e.violation_count, e.rules) for e in sink.events] == [("valid", 0, ())]


# --- Alertas: /health/slo ---------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_p95_and_error_rate_over_the_window() -> None:
    clock = Clock()
    monitor = SloMonitor(SloConfig(min_requests=20), clock=clock)
    for latency in [50.0] * 19 + [900.0]:
        monitor.observe("/api/v1/validate", 200, latency)

    healthy = monitor.report()
    assert (healthy.healthy, healthy.p95_ms, healthy.validations) == (True, 50.0, 20)

    for _ in range(2):
        monitor.observe("/api/v1/validate", 200, 900.0)
    slow = monitor.report()
    assert (slow.healthy, slow.reasons, slow.p95_ms) == (False, ("latencia",), 900.0)

    clock.now += 301  # a janela de 5 minutos passou
    assert monitor.report().requests == 0


def test_errors_above_one_percent_degrade_and_operation_routes_are_ignored() -> None:
    monitor = SloMonitor(SloConfig(min_requests=20), clock=Clock())
    for _ in range(50):
        monitor.observe("/health/slo", 503, 1.0)
        monitor.observe("/ready", 503, 1.0)
    for _ in range(98):
        monitor.observe("/api/v1/lists", 200, 5.0)
    monitor.observe("/api/v1/validate", 503, 5.0)
    monitor.observe("/api/v1/validate", 502, 5.0)

    report = monitor.report()

    assert (report.requests, report.error_rate_pct) == (100, 2.0)
    assert report.reasons == ("erros",)
    assert report.validations == 0  # 5xx não entra na latência


def test_little_traffic_never_alerts() -> None:
    monitor = SloMonitor(SloConfig(min_requests=20), clock=Clock())
    monitor.observe("/api/v1/validate", 500, 5000.0)

    assert monitor.report().healthy


def test_health_slo_answers_503_when_the_goal_is_missed() -> None:
    sink = FakeSink()
    strict = SloConfig(p95_ms=0.0, min_requests=1)

    with client_with(sink, analyzer_with(reply(200, VALID)), slo=strict) as client:
        before = client.get("/health/slo")
        assert post(client, "x = 1\nif x:\n    print(x)\n") == 200
        after = client.get("/health/slo")

    assert before.status_code == 200
    assert before.json()["status"] == "ok"
    assert before.headers["Cache-Control"] == "no-store"
    assert after.status_code == 503
    body = after.json()
    assert (body["status"], body["reasons"], body["validations"]) == ("degraded", ["latencia"], 1)
    assert set(body["telemetry"]) == {"written", "dropped", "failed_batches", "queued"}


def test_health_slo_needs_no_session() -> None:
    app, _ = make_app(ApiSettings(analyzer_url="http://analyzer.test"))

    with TestClient(app) as client:
        response = client.get("/health/slo")

    assert response.status_code == 200
    assert response.json()["p95_ms"] is None

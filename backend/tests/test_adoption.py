"""Adoção pela equipe e conta de verificação do deploy (S28-02; critério 2 da P-09, Q-15)."""

from __future__ import annotations

import asyncio
import dataclasses
import json
from typing import Any

import httpx2
from fastapi.testclient import TestClient

from api_support import authed_client, make_app, member
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.adoption import Adoption
from ipc_api.settings import ApiSettings
from ipc_api.telemetry import TelemetryConfig
from test_api import INVALID, MANIFEST, VALID, FakeAnalyzer, reply
from test_telemetry import FakeSink

LIMIT = {"error": {"code": "ANALYSIS_LIMIT", "message": "complexo demais"}}


def setup(analyze: Any, *, check: bool = False) -> tuple[TestClient, MemoryAccountStore, FakeSink]:
    sink = FakeSink()
    config = ApiSettings(
        analyzer_url="http://analyzer.test",
        telemetry=TelemetryConfig(flush_interval_s=0.01),
        enabled_lists=frozenset({1, 2, 3, 4, 5, 6}),
    )
    analyzer = FakeAnalyzer(
        {"/internal/analyze": analyze, "/internal/ruleset/manifest": reply(200, MANIFEST)}
    )
    app, store = make_app(
        config, analyzer_transport=httpx2.MockTransport(analyzer), telemetry_sink=sink
    )
    account = member(store)
    if check:
        account = dataclasses.replace(account, check_account=True)
        store.accounts[account.id] = account
    return authed_client(app, store, account), store, sink


def post(
    client: TestClient, code: str = "x = 1\nif x:\n    print(x)\n", list_number: int = 1
) -> int:
    response = client.post("/api/v1/validate", json={"code": code, "list_number": list_number})
    return response.status_code


def echo_list(request: httpx2.Request) -> httpx2.Response:
    """O analisador simulado responde sobre a lista pedida."""
    list_number = json.loads(request.content)["list_number"]
    return httpx2.Response(200, json={**INVALID, "list_number": list_number})


def test_the_first_verification_in_each_list_records_the_adoption() -> None:
    client, store, sink = setup(echo_list)

    with client:
        assert post(client) == 200
        assert post(client) == 200
        assert post(client, list_number=3) == 200
        member_id = next(iter(store.adoption))[0]

    assert store.adoption == {(member_id, "2026.2", 1), (member_id, "2026.2", 3)}
    assert len(sink.events) == 3


def test_a_refused_code_is_not_adoption() -> None:
    client, store, sink = setup(reply(422, LIMIT))

    with client:
        assert post(client) == 422
        assert post(client, "\x00") == 422

    assert store.adoption == set()
    assert [event.outcome for event in sink.events] == ["analysis_limit", "rejected"]


def test_the_check_account_counts_nowhere() -> None:
    client, store, sink = setup(reply(200, VALID), check=True)

    with client:
        assert post(client) == 200
        assert post(client, "\x00") == 422

    assert store.adoption == set()
    assert sink.events == []


def test_a_database_failure_is_retried_on_the_next_verification() -> None:
    async def scenario() -> set[tuple[Any, str, int]]:
        store = MemoryAccountStore()
        account = member(store)
        adoption = Adoption(store)
        store.available = False
        adoption.record(account.id, "2027.1", 1)
        await adoption.drain()
        store.available = True
        adoption.record(account.id, "2027.1", 1)
        await adoption.drain()
        return store.adoption

    assert len(asyncio.run(scenario())) == 1


def test_a_known_combination_is_not_written_again() -> None:
    class CountingStore(MemoryAccountStore):
        writes = 0

        async def record_adoption(self, account_id: Any, semester: str, list_number: int) -> None:
            CountingStore.writes += 1
            await super().record_adoption(account_id, semester, list_number)

    async def scenario() -> int:
        store = CountingStore()
        account = member(store)
        adoption = Adoption(store, max_keys=2)
        for list_number in (1, 1, 2, 1, 3, 3):
            adoption.record(account.id, "2027.1", list_number)
            await adoption.drain()
        return CountingStore.writes

    # 1, 2 e 3 uma vez cada; com o teto de 2 combinações, a memória é esvaziada antes do 3.
    assert asyncio.run(scenario()) == 3

"""Limpeza diária do banco (S25-03; Q-19 d): a tarefa da API, as contagens e o ``/health/slo``.

O que cada rodada apaga está no contrato do repositório (``test_account_store.py``).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api_support import make_app
from ipc_api.accounts.models import (
    Account,
    HousekeepingCounts,
    SignupMethod,
    Status,
    Treatment,
)
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.housekeeping import Housekeeping, HousekeepingConfig
from ipc_api.settings import ApiSettings

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def unconfirmed(store: MemoryAccountStore, created_at: datetime) -> Account:
    return store.add(
        Account(
            id=uuid.uuid4(),
            name=f"Nunca Confirmou {uuid.uuid4().hex[:6]}",
            course="Ciência da Computação",
            treatment=Treatment.NEUTRO,
            role=None,
            status=Status.AGUARDANDO_VERIFICACAO,
            ja_foi_monitor_chefe=False,
            password_hash="$argon2id$x",
            signup_method=SignupMethod.SENHA,
            emails=(f"{uuid.uuid4().hex[:8]}@cin.ufpe.br",),
            created_at=created_at,
        )
    )


def test_config_from_the_environment() -> None:
    assert HousekeepingConfig.from_env({}) == HousekeepingConfig(enabled=True, interval_s=86400)
    assert HousekeepingConfig.from_env(
        {"IPC_HOUSEKEEPING": "0", "IPC_HOUSEKEEPING_INTERVAL_S": "60"}
    ) == HousekeepingConfig(enabled=False, interval_s=60)


@pytest.mark.anyio
async def test_each_run_adds_to_the_counts() -> None:
    store = MemoryAccountStore()
    unconfirmed(store, NOW - timedelta(days=3))
    housekeeping = Housekeeping(store, HousekeepingConfig(), clock=lambda: NOW)

    first = await housekeeping.run_once()
    unconfirmed(store, NOW - timedelta(days=3))
    unconfirmed(store, NOW - timedelta(days=4))
    second = await housekeeping.run_once()

    assert (first, second) == (HousekeepingCounts(unverified=1), HousekeepingCounts(unverified=2))
    assert (housekeeping.stats.runs, housekeeping.stats.failures) == (2, 0)
    assert housekeeping.stats.removed == HousekeepingCounts(unverified=3)


@pytest.mark.anyio
async def test_a_database_outage_is_counted_and_retried(caplog: pytest.LogCaptureFixture) -> None:
    store = MemoryAccountStore()
    store.available = False
    housekeeping = Housekeeping(store, HousekeepingConfig(), clock=lambda: NOW)

    with caplog.at_level(logging.WARNING, logger="ipc_api.housekeeping"):
        assert await housekeeping.run_once() is None
    store.available = True
    assert await housekeeping.run_once() == HousekeepingCounts()

    assert (housekeeping.stats.runs, housekeeping.stats.failures) == (1, 1)
    assert "limpeza diária falhou (StoreUnavailable)" in caplog.text


@pytest.mark.anyio
async def test_the_task_runs_at_start_and_every_interval() -> None:
    store = MemoryAccountStore()
    housekeeping = Housekeeping(store, HousekeepingConfig(interval_s=0.01), clock=lambda: NOW)

    housekeeping.start()
    housekeeping.start()  # uma tarefa só
    for _ in range(200):
        if housekeeping.stats.runs >= 3:
            break
        await asyncio.sleep(0.01)
    await housekeeping.stop()
    runs = housekeeping.stats.runs
    await asyncio.sleep(0.05)

    assert runs >= 3
    assert housekeeping.stats.runs == runs  # parou de vez
    await housekeeping.stop()  # parar de novo não falha


@pytest.mark.anyio
async def test_a_disabled_task_never_runs() -> None:
    housekeeping = Housekeeping(
        MemoryAccountStore(), HousekeepingConfig(enabled=False), clock=lambda: NOW
    )

    housekeeping.start()
    await asyncio.sleep(0.02)
    await housekeeping.stop()

    assert housekeeping.stats.runs == 0


def test_the_api_cleans_up_when_it_starts_and_reports_on_health_slo() -> None:
    store = MemoryAccountStore()
    old = unconfirmed(store, datetime.now(UTC) - timedelta(days=3))
    app, _ = make_app(ApiSettings(analyzer_url="http://analyzer.test"), store=store)

    with TestClient(app) as client:
        deadline = time.monotonic() + 5
        while True:
            body = client.get("/health/slo").json()
            if body["housekeeping"]["runs"] or time.monotonic() > deadline:
                break
            time.sleep(0.01)

    assert body["housekeeping"] == {
        "runs": 1,
        "failures": 0,
        "sessions": 0,
        "tokens": 0,
        "unverified": 1,
        "inactive": 0,
        "log": 0,
    }
    assert old.id not in store.accounts


def test_the_api_can_run_without_the_cleanup() -> None:
    store = MemoryAccountStore()
    old = unconfirmed(store, datetime.now(UTC) - timedelta(days=3))
    settings = ApiSettings(
        analyzer_url="http://analyzer.test", housekeeping=HousekeepingConfig(enabled=False)
    )
    app, _ = make_app(settings, store=store)

    with TestClient(app) as client:
        body = client.get("/health/slo").json()

    assert body["housekeeping"]["runs"] == 0
    assert old.id in store.accounts

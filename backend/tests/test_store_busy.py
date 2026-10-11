"""O pool do banco cheio por sobrecarga responde ``OVERLOADED`` (S35-08), não banco fora do ar.

Achado da S34-03 (ADR-03, "Pico no plano gratuito"): a 1.500 verificações por minuto no plano
gratuito, 2.996 das 3.978 recusas diziam que o banco estava fora do ar, porque a consulta da sessão
esperava uma conexão do pool até estourar o prazo de 5 s.
"""

from __future__ import annotations

import asyncio

import pytest

from api_support import authed_client, make_app
from ipc_api.accounts.models import StoreBusy, StoreUnavailable
from ipc_api.accounts.postgres import MAX_PENDING, POOL_SIZE, PostgresAccountStore
from ipc_api.errors import OVERLOADED_RETRY_S, UNAVAILABLE_RETRY_S

CODE = "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\n"


# --- O contador de operações no PostgreSQL ---------------------------------------------------


def test_too_many_pending_operations_are_refused_at_once() -> None:
    store = PostgresAccountStore(pool=None)
    store._pending = MAX_PENDING

    async def enter() -> None:
        async with store._op():
            pytest.fail("a operação não podia começar")

    with pytest.raises(StoreBusy):
        asyncio.run(enter())
    assert store._pending == MAX_PENDING


def test_a_timeout_while_waiting_for_the_pool_is_overload() -> None:
    store = PostgresAccountStore(pool=None)
    store._pending = POOL_SIZE  # todas as conexões ocupadas: a próxima espera o pool

    async def slow() -> None:
        async with store._op(deadline_s=0.01):
            await asyncio.sleep(1)

    with pytest.raises(StoreBusy) as caught:
        asyncio.run(slow())
    assert caught.value.busy is True
    assert store._pending == POOL_SIZE


def test_a_timeout_with_free_connections_is_the_database() -> None:
    store = PostgresAccountStore(pool=None)

    async def slow() -> None:
        async with store._op(deadline_s=0.01):
            await asyncio.sleep(1)

    with pytest.raises(StoreUnavailable) as caught:
        asyncio.run(slow())
    assert not isinstance(caught.value, StoreBusy)
    assert store._pending == 0


def test_other_failures_pass_through_unchanged() -> None:
    store = PostgresAccountStore(pool=None)
    store._pending = POOL_SIZE

    async def broken() -> None:
        async with store._op():
            raise OSError("conexão recusada")

    with pytest.raises(StoreUnavailable) as caught:
        asyncio.run(broken())
    assert not isinstance(caught.value, StoreBusy)


# --- A resposta da API ------------------------------------------------------------------------


def test_the_validation_answers_overloaded_with_retry_after() -> None:
    app, store = make_app()
    with authed_client(app, store) as client:
        store.busy = True
        response = client.post("/api/v1/validate", json={"code": CODE, "list_number": 1})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OVERLOADED"
    assert response.headers["Retry-After"] == str(OVERLOADED_RETRY_S)


def test_login_also_says_overloaded() -> None:
    app, store = make_app()
    with authed_client(app, store) as client:
        store.busy = True
        login = client.post("/api/v1/auth/login", json={"login": "x@cin.ufpe.br", "password": "y"})

    assert (login.status_code, login.json()["error"]["code"]) == (503, "OVERLOADED")
    assert login.headers["Retry-After"] == str(OVERLOADED_RETRY_S)


def test_a_database_outage_still_says_database_unavailable() -> None:
    app, store = make_app()
    with authed_client(app, store) as client:
        store.available = False
        response = client.post("/api/v1/validate", json={"code": CODE, "list_number": 1})

    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert response.headers["Retry-After"] == str(UNAVAILABLE_RETRY_S)

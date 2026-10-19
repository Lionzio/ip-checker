"""Contrato do repositório de gabaritos (Sprint 51, S51-01): a versão em memória e a do PostgreSQL.

Cada teste roda nos dois, como em ``test_catalog_store.py``: um gabarito por questão e tipo,
salvar de novo reescreve, apagar devolve se havia, e a auditoria guarda só o SHA-256 do código.
O PostgreSQL só entra com ``IPC_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from db_support import DATABASE_URL, fresh_schema
from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.answer_keys.models import RuleHit, code_sha256
from ipc_api.answer_keys.postgres import PostgresGabaritoStore
from ipc_api.answer_keys.store import Actor, GabaritoStore, MemoryGabaritoStore

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
PERIOD = "2026.2"
#: Um texto que só existe no gabarito: nunca pode aparecer na auditoria.
CANARY = "CANARIO_GABARITO_51"
CODE = f"# {CANARY}\nn = int(input())\nprint(n * 2)\n"


@dataclass
class Store:
    store: GabaritoStore
    actor: Actor
    other: Actor
    pool: Any = None


async def _account(pool: Any, name: str) -> Actor:
    account_id = await pool.fetchval(
        "INSERT INTO app.account (name, course, treatment, role, status, signup_method) VALUES "
        "($1, 'Ciência da Computação', 'neutro', 'professor', 'ativo', 'senha') RETURNING id",
        name,
    )
    return Actor(account_id, name)


@pytest.fixture(
    params=[
        "memoria",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not DATABASE_URL, reason="sem IPC_TEST_DATABASE_URL"),
        ),
    ]
)
async def gabaritos(request: pytest.FixtureRequest) -> AsyncIterator[Store]:
    if request.param == "memoria":
        yield Store(
            MemoryGabaritoStore(),
            Actor(uuid.uuid4(), "Professora Ana"),
            Actor(uuid.uuid4(), "Monitor-chefe Bruno"),
        )
        return
    await fresh_schema()
    accounts = await PostgresAccountStore.connect(DATABASE_URL)
    try:
        actor = await _account(accounts.pool, "Professora Ana")
        other = await _account(accounts.pool, "Monitor-chefe Bruno")
        yield Store(PostgresGabaritoStore(accounts), actor, other, accounts.pool)
    finally:
        await accounts.close()


async def save(g: Store, question: str = "L2-Q4", kind: Any = "notion", **changes: Any) -> Any:
    values: dict[str, Any] = {
        "period": PERIOD,
        "question_id": question,
        "kind": kind,
        "source": "painel",
        "code": CODE,
        "violations": (),
        "actor": g.actor,
        "now": NOW,
    }
    values.update(changes)
    return await g.store.save(**values)


async def test_a_saved_gabarito_comes_back_with_who_and_when(gabaritos: Store) -> None:
    saved = await save(gabaritos, violations=(RuleHit("R-37", 3),))

    found = await gabaritos.store.get(PERIOD, "L2-Q4", "notion")

    assert found == saved
    assert found is not None
    assert (found.code, found.violations) == (CODE, (RuleHit("R-37", 3),))
    assert (found.created_at, found.updated_at) == (NOW, NOW)
    assert (found.created_by, found.updated_by_name) == (
        gabaritos.actor.account_id,
        "Professora Ana",
    )
    assert CANARY not in repr(found)
    assert await gabaritos.store.get(PERIOD, "L2-Q4", "ip_cc") is None


async def test_saving_again_rewrites_and_keeps_who_created(gabaritos: Store) -> None:
    await save(gabaritos)
    later = NOW + timedelta(hours=1)

    rewritten = await save(
        gabaritos, code="print(2)\n", actor=gabaritos.other, now=later, source="dikastis"
    )

    assert (rewritten.code, rewritten.source) == ("print(2)\n", "dikastis")
    assert (rewritten.created_at, rewritten.updated_at) == (NOW, later)
    assert rewritten.created_by == gabaritos.actor.account_id
    assert rewritten.updated_by_name == "Monitor-chefe Bruno"


async def test_two_kinds_per_question_and_the_period_in_order(gabaritos: Store) -> None:
    await save(gabaritos, "L2-Q10", "notion")
    await save(gabaritos, "L2-Q4", "ip_cc")
    await save(gabaritos, "L2-Q4", "notion")
    await save(gabaritos, "L1-Q1", "notion", period="2027.1")

    listed = await gabaritos.store.list_period(PERIOD)

    assert [(g.question_id, g.kind) for g in listed] == [
        ("L2-Q4", "notion"),
        ("L2-Q4", "ip_cc"),
        ("L2-Q10", "notion"),
    ]
    assert [(g.period, g.question_id) for g in await gabaritos.store.all()][-1] == (
        "2027.1",
        "L1-Q1",
    )


async def test_deleting_says_whether_there_was_one(gabaritos: Store) -> None:
    await save(gabaritos)

    assert await gabaritos.store.delete(PERIOD, "L2-Q4", "notion", gabaritos.other, NOW) is True
    assert await gabaritos.store.delete(PERIOD, "L2-Q4", "notion", gabaritos.other, NOW) is False
    assert await gabaritos.store.get(PERIOD, "L2-Q4", "notion") is None


async def test_the_audit_keeps_who_did_what_and_only_the_hash(gabaritos: Store) -> None:
    await save(gabaritos)
    await save(gabaritos, code="print(3)\n", actor=gabaritos.other, now=NOW + timedelta(minutes=1))
    await gabaritos.store.delete(
        PERIOD, "L2-Q4", "notion", gabaritos.actor, NOW + timedelta(minutes=2)
    )

    entries = await gabaritos.store.audit(PERIOD, "L2-Q4")

    assert [(e.action, e.account_id) for e in entries] == [
        ("apagar", gabaritos.actor.account_id),
        ("alterar", gabaritos.other.account_id),
        ("criar", gabaritos.actor.account_id),
    ]
    assert entries[-1].code_sha256 == code_sha256(CODE)
    assert CANARY not in repr(entries)
    if gabaritos.pool is not None:
        text = await gabaritos.pool.fetchval(
            "SELECT string_agg(row_to_json(a)::text, '') FROM app.gabarito_audit a"
        )
        assert CANARY not in text


async def test_an_import_has_no_author(gabaritos: Store) -> None:
    saved = await save(gabaritos, actor=Actor(None, None), source="importado")

    assert (saved.created_by, saved.updated_by_name, saved.source) == (None, None, "importado")

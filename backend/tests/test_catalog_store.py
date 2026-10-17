"""Contrato do catálogo das listas (S50-05): a versão em memória e a do PostgreSQL.

Cada teste roda nos dois repositórios, como em ``test_account_store.py``: o novo acrescenta, o
que mudou reescreve e guarda a versão anterior (as 5 mais recentes), o igual não muda nada e o
que sumiu fica marcado, sem nada apagado. O PostgreSQL só entra com ``IPC_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from db_support import DATABASE_URL, fresh_schema
from ipc_api.accounts.postgres import PostgresAccountStore
from ipc_api.importing.hashing import Sample, content_hash, normalize_text
from ipc_api.importing.models import ClassIn, ImportToken, ListIn, QuestionIn, QuestionRef
from ipc_api.importing.postgres import PostgresCatalogStore
from ipc_api.importing.store import (
    MAX_VERSIONS,
    CatalogStore,
    MemoryCatalogStore,
    UnknownListError,
    UnknownRunError,
    question_order,
)

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
PERIOD = "2026.2"
VECTORS = Path(__file__).resolve().parents[2] / "extensao" / "test" / "vetores-hash.json"
SI = ClassIn("01KZGJ6PKKN55TE1Z31G4DXGCN", "IP SI UFPE 2026.2", "SI")
EC = ClassIn("01KZGJ6PKKN55TE1Z31G4DXGEC", "IP EC UFPE 2026.2", "EC")


@dataclass
class Catalog:
    store: CatalogStore
    account_id: uuid.UUID
    pool: Any = None

    async def versions(self, question_id: str) -> list[int]:
        """As versões anteriores guardadas (só para conferir; a API não as expõe ainda)."""
        if isinstance(self.store, MemoryCatalogStore):
            return [q.version for q in self.store.versions.get((PERIOD, question_id), [])]
        rows = await self.pool.fetch(
            "SELECT v.version FROM app.catalog_question_version v "
            "JOIN app.catalog_question q ON q.id = v.question_id "
            "WHERE q.period = $1 AND q.question_id = $2 ORDER BY v.version",
            PERIOD,
            question_id,
        )
        return [row["version"] for row in rows]


@pytest.fixture(
    params=[
        "memoria",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not DATABASE_URL, reason="sem IPC_TEST_DATABASE_URL"),
        ),
    ]
)
async def catalog(request: pytest.FixtureRequest) -> AsyncIterator[Catalog]:
    if request.param == "memoria":
        yield Catalog(MemoryCatalogStore(), uuid.uuid4())
        return
    await fresh_schema()
    accounts = await PostgresAccountStore.connect(DATABASE_URL)
    try:
        account_id = await accounts.pool.fetchval(
            "INSERT INTO app.account (name, course, treatment, role, status, signup_method) "
            "VALUES ('Chefia de teste', 'Ciência da Computação', 'neutro', 'monitor_chefe', "
            "'ativo', 'senha') RETURNING id"
        )
        yield Catalog(PostgresCatalogStore(accounts), account_id, accounts.pool)
    finally:
        await accounts.close()


def question(
    question_id: str, *, description: str = "Leia N e imprima N.", problem: str | None = None
) -> QuestionIn:
    number = int(question_id[1:].split("-Q")[0])
    samples = (Sample("1", "1"), Sample("2", "2"))
    title = f"{PERIOD[2:]}{question_id.replace('-', '')} - Questão"
    return QuestionIn(
        question_id=question_id,
        dikastis_problem_id=problem or f"P{question_id.replace('-', '')}",
        list_kind="lista" if question_id.startswith("L") else "prova",
        list_number=number,
        title=title,
        description=description,
        input_description="Um inteiro N.",
        output_description="O mesmo N.",
        samples=samples,
        time_limit_ms=1000,
        content_hash=content_hash(
            title=title,
            description=description,
            input_description="Um inteiro N.",
            output_description="O mesmo N.",
            samples=samples,
        ),
    )


def lista(
    number: int, items: list[QuestionIn], *, school_class: ClassIn = SI, task: str | None = None
) -> ListIn:
    return ListIn(
        dikastis_task_id=task or f"T{number}{school_class.course}",
        class_org_id=school_class.dikastis_org_id,
        kind="lista",
        number=number,
        title=f"Lista {number}",
        starts_at=NOW,
        ends_at=NOW + timedelta(days=7),
        questions=tuple(
            QuestionRef(q.dikastis_problem_id, q.question_id, q.content_hash) for q in items
        ),
    )


async def sync(
    catalog: Catalog,
    lists: list[ListIn],
    questions: list[QuestionIn] | None = None,
    *,
    now: datetime = NOW,
    classes: tuple[ClassIn, ...] = (SI,),
) -> tuple[Any, Any]:
    """Uma rodada completa: o manifesto e, se faltar algo, as questões pedidas."""
    manifest = await catalog.store.apply_manifest(
        account_id=catalog.account_id,
        mode="manual",
        period=PERIOD,
        classes=classes,
        lists=lists,
        now=now,
    )
    sent = [q for q in (questions or []) if q.dikastis_problem_id in manifest.need]
    result = None
    if sent:
        result = await catalog.store.apply_questions(
            account_id=catalog.account_id,
            run_id=manifest.run_id,
            period=PERIOD,
            questions=sent,
            now=now,
        )
    return manifest, result


async def test_the_first_sync_adds_every_question(catalog: Catalog) -> None:
    items = [question("L1-Q1"), question("L1-Q2")]

    manifest, result = await sync(catalog, [lista(1, items)], items)

    assert sorted(manifest.need) == ["PL1Q1", "PL1Q2"]
    assert (manifest.unchanged, manifest.missing) == (0, ())
    assert (result.created, result.updated, result.unchanged) == (2, 0, 0)
    lists, stored = await catalog.store.catalog(PERIOD)
    assert [(item.kind, item.number, item.classes) for item in lists] == [
        ("lista", 1, ("IP SI UFPE 2026.2",))
    ]
    assert [(q.question_id, q.version, q.samples) for q in stored] == [
        ("L1-Q1", 1, (Sample("1", "1"), Sample("2", "2"))),
        ("L1-Q2", 1, (Sample("1", "1"), Sample("2", "2"))),
    ]
    assert await catalog.store.periods() == [PERIOD]


async def test_an_equal_sync_changes_nothing(catalog: Catalog) -> None:
    items = [question("L1-Q1"), question("L1-Q2")]
    await sync(catalog, [lista(1, items)], items)
    before = (await catalog.store.catalog(PERIOD))[1]

    manifest, result = await sync(catalog, [lista(1, items)], items, now=NOW + timedelta(hours=1))

    assert (manifest.need, manifest.unchanged, manifest.missing) == ((), 2, ())
    assert result is None
    assert (await catalog.store.catalog(PERIOD))[1] == before


async def test_a_changed_statement_is_rewritten_and_the_old_one_kept(catalog: Catalog) -> None:
    first = question("L1-Q1")
    await sync(catalog, [lista(1, [first])], [first])
    later = NOW + timedelta(days=1)
    changed = question("L1-Q1", description="Leia N e imprima o dobro de N.")

    manifest, result = await sync(catalog, [lista(1, [changed])], [changed], now=later)

    assert manifest.need == ("PL1Q1",)
    assert (result.created, result.updated, result.unchanged) == (0, 1, 0)
    (stored,) = (await catalog.store.catalog(PERIOD))[1]
    assert (stored.version, stored.description) == (2, "Leia N e imprima o dobro de N.")
    assert (stored.first_seen, stored.updated_at) == (NOW, later)
    assert await catalog.versions("L1-Q1") == [1]


async def test_only_the_last_five_versions_are_kept(catalog: Catalog) -> None:
    for step in range(MAX_VERSIONS + 3):
        item = question("L1-Q1", description=f"Versão {step}")
        await sync(catalog, [lista(1, [item])], [item], now=NOW + timedelta(minutes=step))

    (stored,) = (await catalog.store.catalog(PERIOD))[1]
    assert stored.version == MAX_VERSIONS + 3
    assert await catalog.versions("L1-Q1") == list(range(3, MAX_VERSIONS + 3))


async def test_a_new_question_is_added_without_touching_the_others(catalog: Catalog) -> None:
    first = question("L1-Q1")
    await sync(catalog, [lista(1, [first])], [first])
    second = question("L1-Q2")

    manifest, result = await sync(catalog, [lista(1, [first, second])], [first, second])

    assert (manifest.need, manifest.unchanged) == (("PL1Q2",), 1)
    assert (result.created, result.updated) == (1, 0)
    stored = (await catalog.store.catalog(PERIOD))[1]
    assert [(q.question_id, q.version) for q in stored] == [("L1-Q1", 1), ("L1-Q2", 1)]


async def test_what_disappeared_is_marked_and_cleared_when_it_returns(catalog: Catalog) -> None:
    q1, q2, q3 = question("L1-Q1"), question("L1-Q2"), question("L2-Q1")
    await sync(catalog, [lista(1, [q1, q2]), lista(2, [q3])], [q1, q2, q3])
    later = NOW + timedelta(days=2)

    manifest, _ = await sync(catalog, [lista(1, [q1])], [q1], now=later)

    assert manifest.missing == ("L1-Q2", "L2-Q1")
    lists, stored = await catalog.store.catalog(PERIOD)
    assert [(item.number, item.missing_since) for item in lists] == [(1, None), (2, later)]
    assert [(q.question_id, q.missing_since) for q in stored] == [
        ("L1-Q1", None),
        ("L1-Q2", later),
        ("L2-Q1", later),
    ]

    manifest, _ = await sync(catalog, [lista(1, [q1, q2]), lista(2, [q3])], [q1, q2, q3])

    assert (manifest.need, manifest.missing) == ((), ())
    lists, stored = await catalog.store.catalog(PERIOD)
    assert all(item.missing_since is None for item in lists)
    assert all(q.missing_since is None for q in stored)


async def test_the_last_sync_is_the_last_manifest(catalog: Catalog) -> None:
    assert await catalog.store.last_sync(PERIOD) is None
    await sync(catalog, [lista(1, [])])
    await sync(catalog, [lista(1, [])], now=NOW + timedelta(hours=2))

    assert await catalog.store.last_sync(PERIOD) == NOW + timedelta(hours=2)
    assert await catalog.store.last_sync("2027.1") is None


async def test_the_same_list_in_two_classes_is_one_list(catalog: Catalog) -> None:
    items = [question("L1-Q1")]
    lists = [lista(1, items), lista(1, items, school_class=EC)]

    manifest, result = await sync(catalog, lists, items, classes=(SI, EC))

    assert manifest.need == ("PL1Q1",)
    assert result.created == 1
    (stored_list,) = (await catalog.store.catalog(PERIOD))[0]
    assert stored_list.classes == ("IP EC UFPE 2026.2", "IP SI UFPE 2026.2")


async def test_a_training_task_has_no_number(catalog: Catalog) -> None:
    training = ListIn("T0", SI.dikastis_org_id, "treino", None, "Treino", None, None, ())

    await sync(catalog, [training])

    (stored,) = (await catalog.store.catalog(PERIOD))[0]
    assert (stored.kind, stored.number, stored.title) == ("treino", None, "Treino")


async def test_questions_need_a_run_of_the_same_account_and_period(catalog: Catalog) -> None:
    item = question("L1-Q1")
    manifest, _ = await sync(catalog, [lista(1, [item])])

    for run_id, account_id, period in (
        (uuid.uuid4(), catalog.account_id, PERIOD),
        (manifest.run_id, uuid.uuid4(), PERIOD),
        (manifest.run_id, catalog.account_id, "2026.1"),
    ):
        with pytest.raises(UnknownRunError):
            await catalog.store.apply_questions(
                account_id=account_id, run_id=run_id, period=period, questions=[item], now=NOW
            )


async def test_a_question_of_a_list_outside_the_manifest_is_refused(catalog: Catalog) -> None:
    manifest, _ = await sync(catalog, [lista(1, [question("L1-Q1")])])

    with pytest.raises(UnknownListError):
        await catalog.store.apply_questions(
            account_id=catalog.account_id,
            run_id=manifest.run_id,
            period=PERIOD,
            questions=[question("L3-Q1")],
            now=NOW,
        )


async def test_import_tokens_are_kept_only_as_a_hash(catalog: Catalog) -> None:
    token = ImportToken(
        uuid.uuid4(), catalog.account_id, "a" * 64, "Chrome", NOW, NOW + timedelta(days=90)
    )
    await catalog.store.add_import_token(token)

    assert await catalog.store.find_import_token("a" * 64) == token
    assert await catalog.store.find_import_token("b" * 64) is None
    await catalog.store.touch_import_token(token.id, NOW + timedelta(minutes=5))
    assert await catalog.store.revoke_import_token(uuid.uuid4(), token.id, NOW) is False
    assert await catalog.store.revoke_import_token(catalog.account_id, token.id, NOW) is True
    assert await catalog.store.revoke_import_token(catalog.account_id, token.id, NOW) is False
    (stored,) = await catalog.store.list_import_tokens(catalog.account_id)
    assert (stored.revoked_at, stored.last_used_at) == (NOW, NOW + timedelta(minutes=5))


# --- O hash do enunciado (o contrato com a extensão) -------------------------------------------


def test_the_hash_matches_the_vectors_shared_with_the_extension() -> None:
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))["vetores"]

    assert len(vectors) >= 6
    for vector in vectors:
        doc = vector["questao"]
        digest = content_hash(
            title=doc["title"],
            description=doc["description"],
            input_description=doc["input_description"],
            output_description=doc["output_description"],
            samples=[Sample(s["input"], s["output"]) for s in doc["samples"]],
        )
        assert digest == vector["hash"], vector["nome"]


def test_the_hash_rule_is_the_documented_one() -> None:
    # O JSON canônico escrito à mão: chaves em ordem, sem espaços, acentos sem escape.
    assert normalize_text(" a  \r\nb\t\r c \n") == "a\nb\n c"
    assert normalize_text("\N{NO-BREAK SPACE}x\N{NO-BREAK SPACE}") == (
        "\N{NO-BREAK SPACE}x\N{NO-BREAK SPACE}"
    )
    canonical = (
        '{"description":"Dê","input_description":"E","output_description":"S",'
        '"samples":[{"input":"1","output":"2"}],"title":"T"}'
    )
    digest = content_hash(
        title="T ",
        description="Dê",
        input_description="E",
        output_description="S",
        samples=[Sample("1\n", "2")],
    )
    assert digest == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_questions_are_ordered_by_list_then_number() -> None:
    ids = ["P1-Q1", "L2-Q10", "L10-Q1", "L2-Q9", "L1-Q2"]

    assert sorted(ids, key=question_order) == ["L1-Q2", "L2-Q9", "L2-Q10", "L10-Q1", "P1-Q1"]

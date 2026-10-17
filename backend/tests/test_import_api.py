"""A importação do Dikastis pela API (S50-04, S50-05; ADR-15 e ADR-19).

O token de importação nasce no Perfil (só a chefia e o desenvolvedor), aparece uma vez, fica só
como hash e vale 90 dias. As rotas ``/api/v1/import/*`` aceitam só esse token e são as únicas
que aceitam a origem da extensão. O valor do token nunca vai para os logs.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_support import BASE_URL, authed_client, make_app, member
from ipc_api.accounts.models import Account, Role
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.importing.hashing import Sample, content_hash
from ipc_api.importing.service import ImportService
from ipc_api.importing.store import MemoryCatalogStore
from ipc_api.settings import DEFAULT_EXTENSION_ID, ApiSettings

TOKENS = "/api/v1/profile/import-tokens"
MANIFEST = "/api/v1/import/catalog/manifest"
QUESTIONS = "/api/v1/import/catalog/questions"
EXTENSION = f"chrome-extension://{DEFAULT_EXTENSION_ID}"
OTHER_EXTENSION = "chrome-extension://" + "a" * 32
CLASS_ID = "01KZGJ6PKKN55TE1Z31G4DXGCN"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def api(clock: Clock) -> Iterator[tuple[FastAPI, MemoryAccountStore]]:
    app, store = make_app(clock=clock)
    with TestClient(app, base_url=BASE_URL):
        yield app, store


def error_of(response: Any) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def create(app: FastAPI, store: MemoryAccountStore, account: Account, label: str = "Chrome") -> Any:
    with authed_client(app, store, account) as client:
        return client.post(TOKENS, json={"label": label})


def new_token(app: FastAPI, store: MemoryAccountStore, role: Role = Role.MONITOR_CHEFE) -> str:
    response = create(app, store, member(store, role=role))
    assert response.status_code == 201, response.text
    token: str = response.json()["token"]
    return token


def question(question_id: str = "L1-Q1", description: str = "Leia N.") -> dict[str, Any]:
    texts = {
        "title": "26.2L1Q1 - Eco",
        "description": description,
        "input_description": "Um inteiro N.",
        "output_description": "O mesmo N.",
    }
    samples = [{"input": "1", "output": "1"}]
    return {
        "question_id": question_id,
        "dikastis_problem_id": "PROB1",
        "list_kind": "lista",
        "list_number": 1,
        **texts,
        "samples": samples,
        "time_limit_ms": 1000,
        "content_hash": content_hash(
            **texts, samples=[Sample(s["input"], s["output"]) for s in samples]
        ),
    }


def manifest(*questions: dict[str, Any], **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "period": "2026.2",
        "mode": "manual",
        "classes": [{"dikastis_org_id": CLASS_ID, "name": "IP SI UFPE 2026.2", "course": "SI"}],
        "lists": [
            {
                "dikastis_task_id": "TASK1",
                "class_org_id": CLASS_ID,
                "kind": "lista",
                "number": 1,
                "title": "Lista 1",
                "starts_at": "2026-10-01T12:00:00Z",
                "ends_at": "2026-10-08T12:00:00Z",
                "questions": [
                    {
                        "dikastis_problem_id": q["dikastis_problem_id"],
                        "question_id": q["question_id"],
                        "content_hash": q["content_hash"],
                    }
                    for q in questions
                ],
            }
        ],
    }
    body.update(changes)
    return body


def extension(app: FastAPI, token: str | None) -> TestClient:
    """Um cliente sem cookie, como a extensão: só o token e a origem dela."""
    client = TestClient(app, base_url=BASE_URL)
    client.headers["Origin"] = EXTENSION
    if token is not None:
        client.headers["Authorization"] = f"Bearer {token}"
    return client


# --- O token no Perfil -------------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.MONITOR_CHEFE, Role.PROFESSOR, Role.DESENVOLVEDOR])
def test_leadership_creates_a_token_shown_only_once(api: Any, role: Role) -> None:
    app, store = api
    account = member(store, role=role)

    response = create(app, store, account, "  Chrome do notebook ")

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["token"].startswith("ipc_imp_")
    assert len(body["token"]) > 40
    assert (body["label"], body["active"], body["revoked_at"]) == ("Chrome do notebook", True, None)
    assert body["expires_at"] == "2027-01-14T12:00:00Z"
    with authed_client(app, store, account) as client:
        listed = client.get(TOKENS)
    assert listed.headers["cache-control"] == "no-store"
    (info,) = listed.json()["tokens"]
    assert info["id"] == body["id"]
    assert "token" not in info
    assert body["token"] not in listed.text


def test_only_the_hash_of_the_token_is_kept(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)

    catalog: MemoryCatalogStore = app.state.importing.store
    (stored,) = catalog.tokens.values()
    assert stored.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in repr(catalog)


@pytest.mark.parametrize("role", [Role.MONITOR, None])
def test_monitors_and_accounts_without_a_role_cannot_create_tokens(api: Any, role: Role) -> None:
    app, store = api

    assert error_of(create(app, store, member(store, role=role))) == (403, "FORBIDDEN")


def test_at_most_three_active_tokens(api: Any) -> None:
    app, store = api
    account = member(store, role=Role.PROFESSOR)
    for label in ("A", "B", "C"):
        assert create(app, store, account, label).status_code == 201

    assert error_of(create(app, store, account, "D")) == (422, "INVALID_INPUT")

    with authed_client(app, store, account) as client:
        first = client.get(TOKENS).json()["tokens"][0]["id"]
        assert client.delete(f"{TOKENS}/{first}").status_code == 204
    assert create(app, store, account, "D").status_code == 201


def test_an_invalid_label_is_refused(api: Any) -> None:
    app, store = api
    account = member(store, role=Role.PROFESSOR)

    for label in ("", "   ", "x" * 61):
        assert error_of(create(app, store, account, label)) == (422, "INVALID_INPUT"), label


def test_a_revoked_token_stops_working_and_cannot_be_revoked_twice(api: Any) -> None:
    app, store = api
    account = member(store, role=Role.MONITOR_CHEFE)
    created = create(app, store, account).json()
    with extension(app, created["token"]) as client:
        assert client.post(MANIFEST, json=manifest()).status_code == 200

    with authed_client(app, store, account) as client:
        assert client.delete(f"{TOKENS}/{created['id']}").status_code == 204
        assert error_of(client.delete(f"{TOKENS}/{created['id']}")) == (404, "ACCOUNT_NOT_FOUND")
        (info,) = client.get(TOKENS).json()["tokens"]
        assert info["active"] is False
    with extension(app, created["token"]) as client:
        assert error_of(client.post(MANIFEST, json=manifest())) == (401, "UNAUTHENTICATED")


def test_nobody_revokes_a_token_of_another_account(api: Any) -> None:
    app, store = api
    created = create(app, store, member(store, role=Role.MONITOR_CHEFE)).json()

    with authed_client(app, store, member(store, role=Role.PROFESSOR)) as client:
        assert error_of(client.delete(f"{TOKENS}/{created['id']}")) == (404, "ACCOUNT_NOT_FOUND")
    with extension(app, created["token"]) as client:
        assert client.post(MANIFEST, json=manifest()).status_code == 200


def test_the_token_expires_after_90_days(api: Any, clock: Clock) -> None:
    app, store = api
    raw = new_token(app, store)
    clock.now += timedelta(days=89, hours=23)
    with extension(app, raw) as client:
        assert client.post(MANIFEST, json=manifest()).status_code == 200

    clock.now += timedelta(hours=1)

    with extension(app, raw) as client:
        assert error_of(client.post(MANIFEST, json=manifest())) == (401, "UNAUTHENTICATED")


def test_a_token_stops_working_when_the_account_leaves_leadership(api: Any) -> None:
    app, store = api
    account = member(store, role=Role.MONITOR_CHEFE)
    raw = create(app, store, account).json()["token"]

    store.accounts[account.id] = replace(account, role=Role.MONITOR)

    with extension(app, raw) as client:
        assert error_of(client.post(MANIFEST, json=manifest())) == (401, "UNAUTHENTICATED")


def test_the_last_use_is_recorded(api: Any, clock: Clock) -> None:
    app, store = api
    account = member(store, role=Role.MONITOR_CHEFE)
    raw = create(app, store, account).json()["token"]
    clock.now += timedelta(minutes=10)

    with extension(app, raw) as client:
        client.post(MANIFEST, json=manifest())

    with authed_client(app, store, account) as client:
        (info,) = client.get(TOKENS).json()["tokens"]
    assert info["last_used_at"] == "2026-10-16T12:10:00Z"


# --- As rotas da extensão ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer ipc_imp_inexistente", "Bearer qualquer-coisa", "Basic dXNlcjpzZW5oYQ=="],
)
def test_the_import_routes_need_a_valid_token(api: Any, authorization: str | None) -> None:
    app, _ = api
    with extension(app, None) as client:
        if authorization is not None:
            client.headers["Authorization"] = authorization

        assert error_of(client.post(MANIFEST, json=manifest())) == (401, "UNAUTHENTICATED")


def test_a_session_cookie_alone_does_not_open_the_import_routes(api: Any) -> None:
    app, store = api
    with authed_client(app, store, member(store, role=Role.DESENVOLVEDOR)) as client:
        assert error_of(client.post(MANIFEST, json=manifest())) == (401, "UNAUTHENTICATED")


def test_the_extension_origin_is_accepted_only_on_the_import_routes(api: Any) -> None:
    app, store = api
    account = member(store, role=Role.MONITOR_CHEFE)
    raw = create(app, store, account).json()["token"]

    with extension(app, raw) as client:
        assert client.post(MANIFEST, json=manifest()).status_code == 200
        client.headers["Origin"] = OTHER_EXTENSION
        assert error_of(client.post(MANIFEST, json=manifest())) == (403, "ORIGIN_MISMATCH")
    with authed_client(app, store, account) as client:
        response = client.post(TOKENS, json={"label": "X"}, headers={"Origin": EXTENSION})
        assert error_of(response) == (403, "ORIGIN_MISMATCH")


def test_other_extension_ids_come_from_the_environment() -> None:
    other = "b" * 32

    settings = ApiSettings.from_env({"IPC_IMPORT_EXTENSION_IDS": f" {other}, {'c' * 32} "})

    assert settings.import_extension_ids == (other, "c" * 32)
    assert ApiSettings.from_env({}).import_extension_ids == (DEFAULT_EXTENSION_ID,)
    assert ApiSettings.from_env({"IPC_IMPORT_EXTENSION_IDS": ""}).import_extension_ids == (
        DEFAULT_EXTENSION_ID,
    )
    with pytest.raises(ValueError, match="IPC_IMPORT_EXTENSION_IDS"):
        ApiSettings.from_env({"IPC_IMPORT_EXTENSION_IDS": "chrome-extension://abc"})


def test_a_full_sync_adds_then_keeps_then_rewrites(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)
    first = question()
    with extension(app, raw) as client:
        response = client.post(MANIFEST, json=manifest(first))
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        result = response.json()
        assert (result["need"], result["unchanged"], result["missing"]) == (["PROB1"], 0, [])
        saved = client.put(
            QUESTIONS, json={"run_id": result["run_id"], "period": "2026.2", "questions": [first]}
        )
        assert saved.json() == {"created": 1, "updated": 0, "unchanged": 0}

        again = client.post(MANIFEST, json=manifest(first)).json()
        assert (again["need"], again["unchanged"]) == ([], 1)

        changed = question(description="Leia N e imprima N.")
        run = client.post(MANIFEST, json=manifest(changed)).json()
        assert run["need"] == ["PROB1"]
        saved = client.put(
            QUESTIONS, json={"run_id": run["run_id"], "period": "2026.2", "questions": [changed]}
        )
        assert saved.json() == {"created": 0, "updated": 1, "unchanged": 0}

        gone = client.post(MANIFEST, json=manifest()).json()
        assert gone["missing"] == ["L1-Q1"]


def test_a_hash_that_does_not_match_the_statement_is_refused(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)
    item = question()
    with extension(app, raw) as client:
        run = client.post(MANIFEST, json=manifest(item)).json()
        tampered = {**item, "description": "Outro enunciado."}

        response = client.put(
            QUESTIONS, json={"run_id": run["run_id"], "period": "2026.2", "questions": [tampered]}
        )

    assert error_of(response) == (422, "INVALID_INPUT")
    assert "hash" in response.json()["error"]["message"]


def test_questions_of_an_unknown_run_or_list_are_refused(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)
    with extension(app, raw) as client:
        run = client.post(MANIFEST, json=manifest(question())).json()
        unknown_run = client.put(
            QUESTIONS,
            json={
                "run_id": "00000000-0000-4000-8000-000000000000",
                "period": "2026.2",
                "questions": [question()],
            },
        )
        other_list = {**question("L2-Q1"), "list_number": 2}
        unknown_list = client.put(
            QUESTIONS, json={"run_id": run["run_id"], "period": "2026.2", "questions": [other_list]}
        )

    assert error_of(unknown_run) == (422, "INVALID_INPUT")
    assert error_of(unknown_list) == (422, "INVALID_INPUT")


@pytest.mark.parametrize(
    "changes",
    [
        {"period": "2026.3"},
        {"classes": []},
        {"mode": "automatico"},
        {"extra": 1},
    ],
)
def test_a_manifest_out_of_shape_is_refused(api: Any, changes: dict[str, Any]) -> None:
    app, store = api
    raw = new_token(app, store)
    with extension(app, raw) as client:
        assert error_of(client.post(MANIFEST, json=manifest(**changes))) == (422, "INVALID_INPUT")


def test_a_manifest_with_wrong_lists_is_refused(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)
    body = manifest()
    training_with_number = [{**body["lists"][0], "kind": "treino"}]
    unknown_class = [{**body["lists"][0], "class_org_id": "OUTRA"}]
    bad_question = [
        {
            **body["lists"][0],
            "questions": [
                {"dikastis_problem_id": "P", "question_id": "L1Q1", "content_hash": "a" * 64}
            ],
        }
    ]
    with extension(app, raw) as client:
        for lists in (training_with_number, unknown_class, bad_question):
            response = client.post(MANIFEST, json={**body, "lists": lists})
            assert error_of(response) == (422, "INVALID_INPUT"), lists


def test_the_statement_limits_are_enforced(api: Any) -> None:
    app, store = api
    raw = new_token(app, store)
    with extension(app, raw) as client:
        run = client.post(MANIFEST, json=manifest(question())).json()
        for changes in (
            {"description": "x" * 20_001},
            {"samples": [{"input": "1", "output": "1"}] * 11},
            {"samples": [{"input": "x" * 4_001, "output": "1"}]},
        ):
            body = {
                "run_id": run["run_id"],
                "period": "2026.2",
                "questions": [question() | changes],
            }
            assert error_of(client.put(QUESTIONS, json=body)) == (422, "INVALID_INPUT"), changes
        too_many = {"run_id": run["run_id"], "period": "2026.2", "questions": [question()] * 61}
        assert error_of(client.put(QUESTIONS, json=too_many))[0] in (413, 422)


def test_each_token_has_its_own_rate_limit(api: Any, clock: Clock) -> None:
    app, store = api
    raw = new_token(app, store)
    with extension(app, raw) as client:
        # Cada cliente de teste sobe o app de novo; o limite menor vale só para este.
        app.state.importing = ImportService(app.state.importing.store, clock=clock, per_minute=2)
        assert client.post(MANIFEST, json=manifest()).status_code == 200
        assert client.post(MANIFEST, json=manifest()).status_code == 200

        response = client.post(MANIFEST, json=manifest())

    assert error_of(response) == (429, "RATE_LIMITED")
    assert int(response.headers["retry-after"]) >= 1


def test_the_token_never_reaches_the_logs(
    api: Any, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    app, store = api
    raw = new_token(app, store)
    with extension(app, raw) as client:
        client.post(MANIFEST, json=manifest(question()))
        client.headers["Authorization"] = f"Bearer {raw}x"
        client.post(MANIFEST, json=manifest())

    out, err = capfd.readouterr()
    assert raw not in out + err + caplog.text

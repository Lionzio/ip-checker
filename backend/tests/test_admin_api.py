"""Gerenciamento da equipe pela API (S15-02; US-27, US-28): cada regra provocada por chamada direta.

A matriz completa está em ``test_role_policy.py``; aqui ficam os caminhos de ponta a ponta: a fila,
as listas, cada ação com o efeito no banco e nas sessões, e as recusas (401, 403, 404, 409, 422).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api_support import (
    BASE_URL,
    DEV_EMAIL,
    FAST_PASSWORDS,
    PASSWORD,
    cookie_header,
    make_app,
    member,
    open_session,
)
from ipc_api.accounts.models import Account, Role, Status, StoreUnavailable
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.auth.management import Management
from ipc_api.auth.policy import Action
from ipc_api.errors import ApiError, ErrorCode

ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/api/v1/admin/requests", None),
    ("POST", "/api/v1/admin/requests/{id}/approve", {"role": "monitor"}),
    ("POST", "/api/v1/admin/requests/{id}/reject", None),
    ("GET", "/api/v1/admin/members", None),
    ("PATCH", "/api/v1/admin/members/{id}/role", {"role": "monitor_chefe"}),
    ("POST", "/api/v1/admin/members/{id}/remove", None),
    ("POST", "/api/v1/admin/members/{id}/reactivate", {"role": "monitor"}),
    ("GET", "/api/v1/admin/log", None),
]


@pytest.fixture
def store() -> MemoryAccountStore:
    return MemoryAccountStore()


@pytest.fixture
def api(store: MemoryAccountStore) -> Iterator[TestClient]:
    app, _ = make_app(store=store)
    with TestClient(app, base_url=BASE_URL) as client:
        yield client


@pytest.fixture
def developer(api: TestClient, store: MemoryAccountStore) -> Account:
    return next(a for a in store.accounts.values() if a.role is Role.DESENVOLVEDOR)


def as_(store: MemoryAccountStore, account: Account) -> dict[str, str]:
    return cookie_header(open_session(store, account))


def call(
    api: TestClient,
    store: MemoryAccountStore,
    actor: Account,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> httpx2.Response:
    return api.request(method, path, json=body, headers=as_(store, actor))


def act(
    api: TestClient,
    store: MemoryAccountStore,
    actor: Account,
    action: str,
    target: Account | uuid.UUID,
    role: str | None = None,
) -> httpx2.Response:
    target_id = target if isinstance(target, uuid.UUID) else target.id
    method, path = {
        "approve": ("POST", "/api/v1/admin/requests/{}/approve"),
        "reject": ("POST", "/api/v1/admin/requests/{}/reject"),
        "role": ("PATCH", "/api/v1/admin/members/{}/role"),
        "remove": ("POST", "/api/v1/admin/members/{}/remove"),
        "reactivate": ("POST", "/api/v1/admin/members/{}/reactivate"),
    }[action]
    body = {"role": role} if role is not None else None
    return call(api, store, actor, method, path.format(target_id), body)


def error_of(response: httpx2.Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def pending(store: MemoryAccountStore, name: str = "Pedido Novo") -> Account:
    return member(store, name=name, role=None, status=Status.AGUARDANDO_APROVACAO)


# --- Quem acessa ----------------------------------------------------------------------------------


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
def test_a_monitor_gets_403_on_every_management_route(
    api: TestClient,
    store: MemoryAccountStore,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    target = pending(store)
    response = call(api, store, member(store), method, path.format(id=target.id), body)

    assert error_of(response) == (403, "FORBIDDEN")
    assert store.accounts[target.id] == target


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
def test_without_a_session_every_management_route_is_401(
    api: TestClient, store: MemoryAccountStore, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = api.request(method, path.format(id=uuid.uuid4()), json=body)

    assert error_of(response) == (401, "UNAUTHENTICATED")


@pytest.mark.parametrize(
    ("role", "manages"),
    [(Role.PROFESSOR, True), (Role.MONITOR_CHEFE, True), (Role.MONITOR, False)],
)
def test_the_account_says_who_sees_the_management_screen(
    api: TestClient, store: MemoryAccountStore, role: Role, manages: bool
) -> None:
    me = api.get("/api/v1/auth/me", headers=as_(store, member(store, role=role)))

    assert me.json()["can_manage"] is manages


# --- Fila de pedidos (US-27) ----------------------------------------------------------------------


def test_the_queue_lists_only_verified_requests_without_the_treatment(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    waiting = pending(store, "Ana Pedido")
    member(store, role=None, status=Status.AGUARDANDO_VERIFICACAO)
    member(store, role=None, status=Status.RECUSADO)

    response = call(api, store, developer, "GET", "/api/v1/admin/requests")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "items": [
            {
                "id": str(waiting.id),
                "name": "Ana Pedido",
                "email": waiting.primary_email,
                "course": "Ciência da Computação",
                "signup_method": "senha",
                "requested_at": waiting.created_at.isoformat().replace("+00:00", "Z"),
                "role": None,
                "role_label": None,
                "status": "aguardando_aprovacao",
                "status_label": "Pendente",
                "actions": ["aprovar", "recusar"],
                "roles": ["professor", "monitor_chefe", "monitor"],
                "removal_status": None,
            }
        ]
    }


def test_registration_verification_and_approval_end_to_end(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    sender = api.app.state.accounts.sender  # type: ignore[attr-defined]
    api.post(
        "/api/v1/auth/register",
        json={
            "name": "Bia Nova",
            "email": "bia.nova@cin.ufpe.br",
            "password": "Senha-forte-1",
            "course": "Sistemas de Informação",
            "treatment": "feminino",
        },
    )
    body = sender.messages[-1].get_body(("plain",)).get_content()
    api.post("/api/v1/auth/verify", json={"token": body.split("token=", 1)[1].split()[0]})
    login = {"login": "bia.nova@cin.ufpe.br", "password": "Senha-forte-1"}
    assert error_of(api.post("/api/v1/auth/login", json=login)) == (
        403,
        "ACCOUNT_PENDING_APPROVAL",
    )
    [request] = call(api, store, developer, "GET", "/api/v1/admin/requests").json()["items"]

    approved = act(api, store, developer, "approve", uuid.UUID(request["id"]), "monitor_chefe")
    entered = api.post("/api/v1/auth/login", json=login)

    assert approved.status_code == 204
    assert entered.status_code == 200
    assert (entered.json()["role"], entered.json()["can_manage"]) == ("monitor_chefe", True)
    assert store.decisions[uuid.UUID(request["id"])][0] == developer.id


def test_a_head_monitor_approves_only_as_head_monitor_or_monitor(
    api: TestClient, store: MemoryAccountStore
) -> None:
    chefe = member(store, role=Role.MONITOR_CHEFE)
    waiting = pending(store)

    [item] = call(api, store, chefe, "GET", "/api/v1/admin/requests").json()["items"]
    as_professor = act(api, store, chefe, "approve", waiting, "professor")
    as_monitor = act(api, store, chefe, "approve", waiting, "monitor")

    assert item["roles"] == ["monitor_chefe", "monitor"]
    assert error_of(as_professor) == (403, "FORBIDDEN")
    assert as_monitor.status_code == 204
    assert (store.accounts[waiting.id].status, store.accounts[waiting.id].role) == (
        Status.ATIVO,
        Role.MONITOR,
    )


def test_nobody_approves_someone_as_developer(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    response = act(api, store, developer, "approve", pending(store), "desenvolvedor")

    assert error_of(response) == (403, "FORBIDDEN")


def test_a_rejected_request_sees_the_rejection_after_the_right_password(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    waiting = member(
        store,
        name="Caio Recusado",
        role=None,
        status=Status.AGUARDANDO_APROVACAO,
        password_hash=FAST_PASSWORDS.hash_sync(PASSWORD),
    )

    rejected = act(api, store, developer, "reject", waiting)
    login = api.post("/api/v1/auth/login", json={"login": "Caio Recusado", "password": PASSWORD})

    assert rejected.status_code == 204
    assert store.accounts[waiting.id].status is Status.RECUSADO
    assert store.decisions[waiting.id][0] == developer.id
    assert error_of(login) == (403, "ACCOUNT_REJECTED")


def test_a_decided_request_cannot_be_decided_again(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    waiting = pending(store)
    professor = member(store, role=Role.PROFESSOR)

    first = act(api, store, developer, "approve", waiting, "monitor")
    second = act(api, store, professor, "reject", waiting)

    assert first.status_code == 204
    assert error_of(second) == (409, "ACCOUNT_STATE_CHANGED")
    assert store.accounts[waiting.id].status is Status.ATIVO


# --- Membros (US-28) ------------------------------------------------------------------------------


def test_members_show_only_the_buttons_each_person_can_use(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    chefe = member(store, name="Chefe", role=Role.MONITOR_CHEFE)
    member(store, name="Professora", role=Role.PROFESSOR)
    member(store, name="Monitora", role=Role.MONITOR)
    member(store, name="Antiga", role=Role.MONITOR, status=Status.EX_MONITOR)

    lists = call(api, store, chefe, "GET", "/api/v1/admin/members").json()
    active = {item["name"]: item for item in lists["active"]}

    assert set(active) == {developer.name, "Chefe", "Professora", "Monitora"}
    assert active[developer.name]["role_label"] == "Monitor e desenvolvedor"
    assert active[developer.name]["actions"] == []
    assert active["Chefe"]["actions"] == []  # a própria conta
    assert active["Professora"]["actions"] == []
    assert active["Monitora"]["actions"] == ["alterar_cargo", "remover"]
    assert active["Monitora"]["roles"] == ["monitor_chefe"]
    assert active["Monitora"]["removal_status"] == "ex_monitor"
    [removed] = lists["removed"]
    assert (removed["name"], removed["status_label"], removed["actions"]) == (
        "Antiga",
        "Ex-monitor",
        ["reativar"],
    )
    assert removed["roles"] == ["monitor_chefe", "monitor"]
    assert all("treatment" not in item for item in [*lists["active"], *lists["removed"]])


def test_a_head_monitor_cannot_change_or_remove_a_professor(
    api: TestClient, store: MemoryAccountStore
) -> None:
    chefe = member(store, role=Role.MONITOR_CHEFE)
    professor = member(store, role=Role.PROFESSOR)

    assert error_of(act(api, store, chefe, "role", professor, "monitor")) == (403, "FORBIDDEN")
    assert error_of(act(api, store, chefe, "remove", professor)) == (403, "FORBIDDEN")
    assert store.accounts[professor.id] == professor


@pytest.mark.parametrize("role", [Role.PROFESSOR, Role.MONITOR_CHEFE])
def test_only_the_developer_alters_the_developer_account(
    api: TestClient, store: MemoryAccountStore, developer: Account, role: Role
) -> None:
    actor = member(store, role=role)

    assert error_of(act(api, store, actor, "remove", developer)) == (403, "FORBIDDEN")
    assert error_of(act(api, store, actor, "role", developer, "monitor")) == (403, "FORBIDDEN")
    # Nem o próprio desenvolvedor se remove ou se rebaixa por aqui.
    assert error_of(act(api, store, developer, "remove", developer)) == (403, "FORBIDDEN")
    assert store.accounts[developer.id] == developer


def test_nobody_changes_the_own_role(api: TestClient, store: MemoryAccountStore) -> None:
    professor = member(store, role=Role.PROFESSOR)

    assert error_of(act(api, store, professor, "role", professor, "monitor")) == (403, "FORBIDDEN")
    assert error_of(act(api, store, professor, "remove", professor)) == (403, "FORBIDDEN")


def test_changing_the_role_ends_the_sessions_and_marks_head_monitors_for_good(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    monitor = member(store, role=Role.MONITOR)
    session = as_(store, monitor)

    promoted = act(api, store, developer, "role", monitor, "monitor_chefe")
    demoted = act(api, store, developer, "role", monitor, "monitor")

    assert (promoted.status_code, demoted.status_code) == (204, 204)
    assert api.get("/api/v1/auth/me", headers=session).status_code == 401
    assert store.accounts[monitor.id].role is Role.MONITOR
    assert store.accounts[monitor.id].ja_foi_monitor_chefe


@pytest.mark.parametrize(
    ("role", "ja_foi_monitor_chefe", "result"),
    [
        (Role.MONITOR, False, Status.EX_MONITOR),
        (Role.MONITOR, True, Status.CONSELHEIRO),
        (Role.MONITOR_CHEFE, True, Status.CONSELHEIRO),
        (Role.PROFESSOR, False, Status.INATIVO),
    ],
)
def test_removal_keeps_the_account_with_the_right_status_and_ends_its_sessions(
    api: TestClient,
    store: MemoryAccountStore,
    developer: Account,
    role: Role,
    ja_foi_monitor_chefe: bool,
    result: Status,
) -> None:
    target = member(store, role=role, ja_foi_monitor_chefe=ja_foi_monitor_chefe)
    session = as_(store, target)

    response = act(api, store, developer, "remove", target)

    assert response.status_code == 204
    assert (store.accounts[target.id].status, store.accounts[target.id].role) == (result, role)
    assert api.get("/api/v1/auth/me", headers=session).status_code == 401


def test_removed_accounts_see_their_removal_after_the_right_password(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    target = member(store, name="Duda Saindo", password_hash=FAST_PASSWORDS.hash_sync(PASSWORD))

    act(api, store, developer, "remove", target)
    login = api.post("/api/v1/auth/login", json={"login": "Duda Saindo", "password": PASSWORD})

    assert error_of(login) == (403, "ACCOUNT_REMOVED")


def test_reactivation_depends_on_the_role_given(api: TestClient, store: MemoryAccountStore) -> None:
    chefe = member(store, role=Role.MONITOR_CHEFE)
    former_professor = member(store, role=Role.PROFESSOR, status=Status.INATIVO)

    as_professor = act(api, store, chefe, "reactivate", former_professor, "professor")
    as_monitor = act(api, store, chefe, "reactivate", former_professor, "monitor")

    assert error_of(as_professor) == (403, "FORBIDDEN")
    assert as_monitor.status_code == 204
    assert (
        store.accounts[former_professor.id].status,
        store.accounts[former_professor.id].role,
    ) == (
        Status.ATIVO,
        Role.MONITOR,
    )


def test_actions_from_the_wrong_list_are_conflicts(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    active = member(store)
    former = member(store, status=Status.EX_MONITOR)

    assert error_of(act(api, store, developer, "approve", active, "monitor")) == (
        409,
        "ACCOUNT_STATE_CHANGED",
    )
    assert error_of(act(api, store, developer, "remove", former)) == (409, "ACCOUNT_STATE_CHANGED")
    assert error_of(act(api, store, developer, "reactivate", active, "monitor")) == (
        409,
        "ACCOUNT_STATE_CHANGED",
    )


def test_unknown_account_is_404(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    response = act(api, store, developer, "remove", uuid.uuid4())

    assert error_of(response) == (404, "ACCOUNT_NOT_FOUND")


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/admin/members/nao-e-uuid/remove", None),
        ("/api/v1/admin/requests/{id}/approve", {"role": "rei"}),
        ("/api/v1/admin/requests/{id}/approve", {}),
        ("/api/v1/admin/requests/{id}/approve", {"role": "monitor", "extra": 1}),
    ],
)
def test_invalid_input_is_422(
    api: TestClient,
    store: MemoryAccountStore,
    developer: Account,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    response = call(api, store, developer, "POST", path.format(id=pending(store).id), body)

    assert error_of(response) == (422, "INVALID_INPUT")
    assert "role" in response.json()["error"]["message"]


def test_actions_from_another_site_are_refused(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    waiting = pending(store)
    response = api.post(
        f"/api/v1/admin/requests/{waiting.id}/approve",
        json={"role": "monitor"},
        headers={**as_(store, developer), "Origin": "https://evil.example"},
    )

    assert error_of(response) == (403, "ORIGIN_MISMATCH")
    assert store.accounts[waiting.id] == waiting


def test_the_developer_email_is_still_the_login_after_management(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    act(api, store, developer, "approve", pending(store), "professor")

    assert (
        api.post("/api/v1/auth/login", json={"login": DEV_EMAIL, "password": PASSWORD}).status_code
        == 200
    )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/admin/requests", None),
        ("GET", "/api/v1/admin/members", None),
        ("POST", "/api/v1/admin/members/{id}/remove", None),
    ],
)
def test_database_outage_is_503(
    api: TestClient,
    store: MemoryAccountStore,
    developer: Account,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    target = member(store)
    headers = as_(store, developer)

    async def down(*_args: Any, **_kwargs: Any) -> None:
        raise StoreUnavailable("fora do ar")

    store.list_accounts = down  # type: ignore[assignment,method-assign]
    store.transition = down  # type: ignore[method-assign]
    store.management_log = down  # type: ignore[assignment,method-assign]
    response = api.request(method, path.format(id=target.id), json=body, headers=headers)

    assert error_of(response) == (503, "DATABASE_UNAVAILABLE")


def test_someone_acting_first_between_the_check_and_the_write_is_409(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    target = member(store)
    headers = as_(store, developer)

    async def lost_the_race(*_args: Any, **_kwargs: Any) -> None:
        return None

    store.transition = lost_the_race  # type: ignore[method-assign]
    response = api.post(f"/api/v1/admin/members/{target.id}/remove", headers=headers)

    assert error_of(response) == (409, "ACCOUNT_STATE_CHANGED")


@pytest.mark.anyio
async def test_the_service_refuses_who_does_not_manage(store: MemoryAccountStore) -> None:
    management = Management(store)
    monitor = member(store)

    for call_service in (
        management.requests(monitor),
        management.members(monitor),
        management.act(monitor, Action.REMOVE, member(store).id),
    ):
        with pytest.raises(ApiError) as caught:
            await call_service
        assert caught.value.code is ErrorCode.FORBIDDEN


# --- Registro das ações (S23-03, REC-06) --------------------------------------------------------


def log_of(api: TestClient, store: MemoryAccountStore, actor: Account) -> list[dict[str, Any]]:
    response = call(api, store, actor, "GET", "/api/v1/admin/log")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    items: list[dict[str, Any]] = response.json()["items"]
    return items


@pytest.mark.parametrize(
    ("role", "sees"),
    [(Role.PROFESSOR, True), (Role.MONITOR_CHEFE, False), (Role.MONITOR, False)],
)
def test_only_the_developer_and_professors_see_the_log(
    api: TestClient, store: MemoryAccountStore, developer: Account, role: Role, sees: bool
) -> None:
    actor = member(store, role=role)

    me = api.get("/api/v1/auth/me", headers=as_(store, actor))
    response = call(api, store, actor, "GET", "/api/v1/admin/log")

    assert me.json()["can_view_log"] is sees
    assert response.status_code == (200 if sees else 403)
    assert api.get("/api/v1/auth/me", headers=as_(store, developer)).json()["can_view_log"]


def test_every_action_enters_the_log_with_who_did_it_and_when(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    professor = member(store, name="Professora Ana", role=Role.PROFESSOR)
    chefe = member(store, name="Chefe Caio", role=Role.MONITOR_CHEFE)
    bia = pending(store, "Bia Souza")
    davi = pending(store, "Davi Lima")

    assert act(api, store, chefe, "approve", bia, "monitor").status_code == 204
    assert act(api, store, chefe, "reject", davi).status_code == 204
    assert act(api, store, professor, "role", bia, "monitor_chefe").status_code == 204
    assert act(api, store, professor, "remove", bia).status_code == 204
    assert act(api, store, developer, "reactivate", bia, "monitor").status_code == 204

    log = log_of(api, store, professor)

    assert [(e["actor_name"], e["action_label"], e["target_name"]) for e in log] == [
        (developer.name, "Reativou", "Bia Souza"),
        ("Professora Ana", "Removeu", "Bia Souza"),
        ("Professora Ana", "Alterou o cargo de", "Bia Souza"),
        ("Chefe Caio", "Recusou", "Davi Lima"),
        ("Chefe Caio", "Aprovou", "Bia Souza"),
    ]
    assert log[0]["actor_role_label"] == "Monitor e desenvolvedor"
    assert (log[1]["from_status_label"], log[1]["to_status_label"]) == ("Ativo", "Conselheiro")
    assert (log[2]["from_role_label"], log[2]["to_role_label"]) == ("Monitor", "Monitor-chefe")
    assert (log[3]["to_status"], log[3]["to_role"]) == ("recusado", None)
    assert (log[4]["from_status"], log[4]["to_role"]) == ("aguardando_aprovacao", "monitor")
    # Nada do tratamento nem do e-mail de ninguém (FR-26): só nomes e cargos.
    assert all("treatment" not in entry and "email" not in entry for entry in log)


def test_refused_actions_do_not_enter_the_log(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    monitor = member(store, role=Role.MONITOR)
    bia = pending(store)

    assert act(api, store, monitor, "approve", bia, "monitor").status_code == 403
    assert act(api, store, developer, "approve", bia, "monitor").status_code == 204
    assert act(api, store, developer, "approve", bia, "monitor").status_code == 409

    assert [entry["action"] for entry in log_of(api, store, developer)] == ["aprovar"]


def test_the_log_keeps_the_names_of_the_moment(
    api: TestClient, store: MemoryAccountStore, developer: Account
) -> None:
    bia = pending(store, "Bia Souza")
    assert act(api, store, developer, "approve", bia, "monitor").status_code == 204

    # A pessoa troca o nome no perfil depois: o registro continua com o nome da época.
    store.accounts[bia.id] = replace(store.accounts[bia.id], name="Beatriz Souza")

    assert [entry["target_name"] for entry in log_of(api, store, developer)] == ["Bia Souza"]

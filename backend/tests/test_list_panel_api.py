"""``GET /api/v1/admin/list-panel`` (S40-03; US-16): só a chefia, só contagens anônimas."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_support import BASE_URL, cookie_header, make_app, member, open_session
from ipc_api.accounts.models import ListPanel, Role, RuleCount
from ipc_api.accounts.store import MemoryAccountStore

PANEL = ListPanel(
    semester="2026.2",
    list_number=2,
    top_rules=(RuleCount("R-46", 12, 30), RuleCount("R-11", 4, 5)),
    events=40,
    syntax_errors=6,
    adoption_pct=62.5,
)


def _get(role: Role, query: str = "list_number=2&semester=2026.2") -> tuple[int, dict]:  # type: ignore[type-arg]
    store = MemoryAccountStore()
    store.panels[("2026.2", 2)] = PANEL
    app, _ = make_app(store=store)
    with TestClient(app, base_url=BASE_URL) as client:
        response = client.get(
            f"/api/v1/admin/list-panel?{query}",
            headers=cookie_header(open_session(store, member(store, role=role))),
        )
    return response.status_code, response.json()


def test_the_chief_monitor_sees_only_anonymous_counts() -> None:
    status, body = _get(Role.MONITOR_CHEFE)

    assert status == 200
    assert body == {
        "semester": "2026.2",
        "list_number": 2,
        "top_rules": [
            {"rule_id": "R-46", "events": 12, "occurrences": 30},
            {"rule_id": "R-11", "events": 4, "occurrences": 5},
        ],
        "events": 40,
        "syntax_errors": 6,
        "adoption_pct": 62.5,
    }


def test_professors_and_the_developer_see_it_too() -> None:
    for role in (Role.PROFESSOR, Role.DESENVOLVEDOR):
        assert _get(role)[0] == 200


def test_a_monitor_does_not_see_the_panel() -> None:
    assert _get(Role.MONITOR)[0] == 403


def test_an_invalid_list_or_semester_is_refused() -> None:
    assert _get(Role.PROFESSOR, "list_number=7")[0] == 422
    assert _get(Role.PROFESSOR, "list_number=1&semester=2026")[0] == 422


def test_a_list_without_data_is_an_empty_panel() -> None:
    status, body = _get(Role.PROFESSOR, "list_number=5&semester=2026.2")

    assert status == 200
    assert body["top_rules"] == []
    assert body["adoption_pct"] is None

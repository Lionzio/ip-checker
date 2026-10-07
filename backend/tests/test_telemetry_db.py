"""Telemetria no PostgreSQL (S21-01; 5.2.4, US-16, NFR-12): papéis, views e expurgo de 12 meses."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from db_support import DATABASE_URL, fresh_schema, requires_database
from ipc_api.db.migrate import ensure_login_role
from ipc_api.telemetry import PostgresTelemetrySink, TelemetryEvent

pytestmark = [pytest.mark.anyio, requires_database]

#: Nenhuma coluna de view pode guardar código, IP, conta ou identificador de cliente (US-16).
FORBIDDEN = ("code", "codigo", "ip", "account", "conta", "client", "session", "email", "name")


def as_user(role: str, password: str) -> str:
    parts = urlsplit(DATABASE_URL)
    return urlunsplit(parts._replace(netloc=f"{role}:{password}@{parts.hostname}:{parts.port}"))


@pytest.fixture
async def admin() -> AsyncIterator[Any]:
    await fresh_schema()
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        await connection.close()


@pytest.fixture
async def api_url(admin: Any) -> str:
    """O usuário da API, criado como no deploy: membro de ipc_app (e, por ele, de ipc_writer)."""
    password = secrets.token_urlsafe(16)
    await ensure_login_role(admin, "ipc_api_teste", password)
    return as_user("ipc_api_teste", password)


@pytest.fixture
async def reader(admin: Any) -> AsyncIterator[Any]:
    """Uma pessoa da coordenação com o papel ipc_reader (como o deploy/compose.md ensina)."""
    password = secrets.token_urlsafe(16)
    await admin.execute("DROP ROLE IF EXISTS ipc_leitura_teste")
    statement = await admin.fetchval(
        "SELECT format('CREATE ROLE ipc_leitura_teste LOGIN PASSWORD %L IN ROLE ipc_reader', "
        "$1::text)",
        password,
    )
    await admin.execute(statement)
    connection = await asyncpg.connect(as_user("ipc_leitura_teste", password))
    try:
        yield connection
    finally:
        await connection.close()
        await admin.execute("DROP ROLE ipc_leitura_teste")


def sample(outcome: str, rules: list[str], list_number: int = 1) -> TelemetryEvent:
    return TelemetryEvent.from_result(
        ruleset_version="2026.2.1",
        list_number=list_number,
        outcome=outcome,  # type: ignore[arg-type]
        rule_ids=rules,
        analysis_ms=15,
    )


async def test_the_api_user_writes_and_purges_but_cannot_read(admin: Any, api_url: str) -> None:
    sink = await PostgresTelemetrySink.connect(api_url)
    try:
        await sink.write(
            [
                sample("invalid", ["R-34", "R-35", "R-34"]),
                sample("valid", []),
                sample("syntax_error", [], list_number=2),
            ]
        )
        assert await sink.purge_expired() == 0
    finally:
        await sink.close()

    assert await admin.fetchval("SELECT count(*) FROM telemetry.validation_event") == 3
    assert await admin.fetchval("SELECT sum(occurrences) FROM telemetry.validation_event_rule") == 3
    api = await asyncpg.connect(api_url)
    try:
        for statement in (
            "SELECT count(*) FROM telemetry.validation_event",
            "SELECT * FROM telemetry.v_top_rules_by_list",
            "DELETE FROM telemetry.validation_event",
            "UPDATE telemetry.validation_event SET list_number = 2",
        ):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await api.execute(statement)
    finally:
        await api.close()


async def test_views_answer_the_fr17_questions(admin: Any, api_url: str, reader: Any) -> None:
    sink = await PostgresTelemetrySink.connect(api_url)
    try:
        await sink.write(
            [
                sample("invalid", ["R-34", "R-35"]),
                sample("invalid", ["R-34"]),
                sample("syntax_error", []),
                sample("valid", []),
            ]
        )
    finally:
        await sink.close()

    top = await reader.fetch(
        "SELECT rule_id, events, occurrences FROM telemetry.v_top_rules_by_list "
        "WHERE semester = '2026.2' AND list_number = 1 ORDER BY occurrences DESC, rule_id"
    )
    assert [tuple(row) for row in top] == [("R-34", 2, 2), ("R-35", 1, 1)]
    rate = await reader.fetchrow("SELECT * FROM telemetry.v_syntax_error_rate")
    assert (rate["events"], rate["syntax_errors"], float(rate["syntax_error_pct"])) == (4, 1, 25.0)
    week = await reader.fetchrow("SELECT * FROM telemetry.v_weekly_volume")
    assert (week["events"], week["valid"], week["invalid"], week["syntax_error"]) == (4, 1, 2, 1)
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.fetch("SELECT * FROM telemetry.validation_event")
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.fetch("SELECT * FROM app.account")


async def test_no_view_or_table_has_a_column_that_identifies_someone(admin: Any) -> None:
    columns = await admin.fetch(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'telemetry'"
    )

    assert columns
    for row in columns:
        assert not any(word in row["column_name"] for word in FORBIDDEN), tuple(row)


async def test_purge_removes_only_what_is_older_than_twelve_months(
    admin: Any, api_url: str
) -> None:
    for age in ("13 months", "11 months", "1 day"):
        event_id = await admin.fetchval(
            "INSERT INTO telemetry.validation_event (created_at, semester, list_number, "
            "ruleset_version, outcome, analysis_ms) "
            "VALUES (now() - $1::text::interval, '2026.2', 1, '2026.2.1', 'invalid', 3) "
            "RETURNING id",
            age,
        )
        await admin.execute(
            "INSERT INTO telemetry.validation_event_rule VALUES ($1, 'R-34', 1)", event_id
        )
    sink = await PostgresTelemetrySink.connect(api_url)
    try:
        assert await sink.purge_expired() == 1
    finally:
        await sink.close()

    assert await admin.fetchval("SELECT count(*) FROM telemetry.validation_event") == 2
    assert await admin.fetchval("SELECT count(*) FROM telemetry.validation_event_rule") == 2


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("semester", "2026.3"),
        ("list_number", 7),
        ("question_id", "Q1"),
        ("ruleset_version", "versao"),
        ("violation_count", 201),
        ("analysis_ms", -1),
    ],
    ids=["periodo", "lista", "questao", "versao", "violacoes", "tempo"],
)
async def test_the_schema_refuses_out_of_range_values(admin: Any, column: str, value: Any) -> None:
    row: dict[str, Any] = {
        "semester": "2026.2",
        "list_number": 1,
        "question_id": None,
        "ruleset_version": "2026.2.1",
        "violation_count": 0,
        "analysis_ms": 1,
        column: value,
    }

    with pytest.raises(asyncpg.CheckViolationError):
        await admin.execute(
            "INSERT INTO telemetry.validation_event (semester, list_number, question_id, "
            "ruleset_version, outcome, violation_count, analysis_ms) "
            "VALUES ($1, $2, $3, $4, 'valid', $5, $6)",
            *row.values(),
        )

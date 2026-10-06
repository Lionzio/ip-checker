"""Contrato da API (S8-01, DoD: testes de contrato gerados do OpenAPI).

1. O ``docs/openapi.json`` versionado é exatamente o que a aplicação gera.
2. A API conversa com o analyzer de verdade (em memória, com o pool real): os fluxos principais
   do 5.2.2 funcionam ponta a ponta.
3. O schemathesis gera requisições a partir do ``docs/openapi.json`` e confere que cada resposta
   está documentada, segue o esquema publicado e nunca é um 5xx.

Desde a Sprint 13, as rotas da equipe exigem sessão: as chamadas levam o cookie de um membro, e
cada status das rotas de autenticação é provocado de propósito no fim do arquivo.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
import schemathesis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.config import SchemathesisConfig
from schemathesis.specs.openapi.checks import ignored_auth, positive_data_acceptance

from api_support import (
    COOKIE,
    DEV_EMAIL,
    PASSWORD,
    authed_client,
    make_app,
    member,
    open_session,
)
from conftest import BASE_RULESET, REPO_ROOT
from ipc_analyzer.runtime.pool import PoolConfig
from ipc_analyzer.service.app import create_app as create_analyzer
from ipc_analyzer.service.settings import AnalyzerSettings
from ipc_api.accounts.models import Role, Status
from ipc_api.accounts.store import MemoryAccountStore
from ipc_api.admission import AdmissionConfig
from ipc_api.auth.google import GoogleConfig
from ipc_api.openapi import build, render
from ipc_api.ratelimit import RateLimitConfig
from ipc_api.settings import ApiSettings

OPENAPI_FILE = REPO_ROOT / "docs" / "openapi.json"
#: Os testes daqui mandam centenas de requisições de um mesmo cliente; o limite de taxa tem
#: os próprios testes (test_api_rate_limit.py).
#: Desde a Sprint 23 todas as listas vêm habilitadas; aqui a Lista 6 fica de fora para cobrir o
#: LIST_NOT_ENABLED.
UNLIMITED = ApiSettings(
    rate_limit=RateLimitConfig(
        client_per_min=1_000_000, ip_per_min=1_000_000, api_ip_per_min=1_000_000
    ),
    enabled_lists=frozenset({1, 2, 3, 4, 5}),
)


def test_openapi_contract_is_up_to_date() -> None:
    committed = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))

    assert committed == build(), (
        "docs/openapi.json está desatualizado. Regenere a partir de backend/ com: "
        "uv run python -m ipc_api.openapi ../docs/openapi.json"
    )
    assert OPENAPI_FILE.read_text(encoding="utf-8") == render()


#: O 503 de /health/slo não é um erro da requisição: é o próprio relatório, fora da meta (S21-02).
REPORT_ON_503 = {("get", "/health/slo", "503"): "#/components/schemas/SloResponse"}


def test_every_documented_error_uses_the_error_envelope() -> None:
    contract = build()
    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            for status, response in operation["responses"].items():
                if status.startswith(("4", "5")):
                    schema = response["content"]["application/json"]["schema"]
                    expected = REPORT_ON_503.get(
                        (method, path, status), "#/components/schemas/ErrorResponse"
                    )
                    assert schema == {"$ref": expected}, (method, path)


# ---------------------------------------------------------------------------------------------
# API + analyzer de verdade, em memória
# ---------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def analyzer() -> Iterator[TestClient]:
    settings = AnalyzerSettings(ruleset_path=BASE_RULESET, pool=PoolConfig(workers=1))
    with TestClient(create_analyzer(settings)) as client:
        yield client


@pytest.fixture(scope="module")
def api_bundle(analyzer: TestClient) -> tuple[FastAPI, MemoryAccountStore]:
    """A API com a rede trocada por uma ponte direta para o analyzer em memória."""

    def bridge(request: httpx2.Request) -> httpx2.Response:
        answer = analyzer.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={"Content-Type": "application/json"},
        )
        return httpx2.Response(
            answer.status_code,
            content=answer.content,
            headers={"Content-Type": answer.headers["content-type"]},
        )

    return make_app(UNLIMITED, analyzer_transport=httpx2.MockTransport(bridge))


@pytest.fixture(scope="module")
def api_app(api_bundle: tuple[FastAPI, MemoryAccountStore]) -> FastAPI:
    return api_bundle[0]


@pytest.fixture(scope="module")
def session(api_bundle: tuple[FastAPI, MemoryAccountStore]) -> dict[str, str]:
    """O cookie da sessão de um membro. Como cookie (e não cabeçalho), o schemathesis consegue
    tirá-lo e conferir que a rota recusa a chamada sem sessão (checagem ignored_auth)."""
    store = api_bundle[1]
    return {COOKIE: open_session(store, member(store))}


@pytest.fixture(scope="module")
def api(api_bundle: tuple[FastAPI, MemoryAccountStore]) -> Iterator[TestClient]:
    with authed_client(*api_bundle) as client:
        yield client


def post(api: TestClient, code: str, list_number: int = 1) -> httpx2.Response:
    return api.post("/api/v1/validate", json={"code": code, "list_number": list_number})


def test_valid_code_end_to_end(api: TestClient) -> None:
    response = post(api, "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\n")

    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_violation_end_to_end(api: TestClient) -> None:
    body = post(api, "x = 1\nfor i in range(3):\n    print(i)\n").json()

    assert body["status"] == "invalid"
    # Sem if, a Lista 1 também cobra o assunto da lista (R-02), sempre primeiro.
    assert [(v["rule_id"], v["line"]) for v in body["violations"]] == [
        ("R-02", 1),
        ("R-34", 2),
        ("R-35", 2),
    ]
    assert body["violations"][0]["category"] == "EXIGENCIA"
    assert body["violations"][1]["construct"] == "node:For"


def test_syntax_error_end_to_end(api: TestClient) -> None:
    body = post(api, "if x > 0\n    print(x)\n").json()

    assert body["status"] == "syntax_error"
    assert body["syntax_error"] == {"line": 1, "col": 9, "message": "faltou ':'"}


def test_analysis_limit_end_to_end(api: TestClient) -> None:
    response = post(api, "(" * 1_000 + ")" * 1_000)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANALYSIS_LIMIT"


def test_analyzer_only_checks_reach_the_student(api: TestClient) -> None:
    # A API não conhece caracteres de controle; o analyzer recusa, e o aluno recebe o motivo.
    response = post(api, "x = 1\x1b\n")

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "INVALID_INPUT",
        "message": "O código contém um caractere de controle inválido (U+001B) na linha 1.",
        "retry_after_s": None,
    }


def test_lists_and_ready_end_to_end(api: TestClient) -> None:
    assert api.get("/api/v1/lists").json() == [
        # O ruleset do repositório ainda não tem questões cadastradas (R-01).
        {"number": 1, "title": "Comandos condicionais", "questions": []},
        {"number": 2, "title": "Laços de repetição", "questions": []},
        {"number": 3, "title": "Listas e tuplas", "questions": []},
        {"number": 4, "title": "Funções e escopo de variável", "questions": []},
        {"number": 5, "title": "Dicionários", "questions": []},
    ]
    assert api.get("/ready").json() == {
        "status": "ready",
        "ruleset_version": "2026.2.3",
        "release": None,
    }


# ---------------------------------------------------------------------------------------------
# Testes gerados do OpenAPI (schemathesis)
# ---------------------------------------------------------------------------------------------

#: Um corpo válido pelo esquema ainda pode ser recusado pelas regras do contrato (código vazio
#: ou grande demais, lista não habilitada, questão não cadastrada, análise acima dos limites).
CONTRACT_CONFIG = SchemathesisConfig.from_dict(
    {"checks": {"positive_data_acceptance": {"expected-statuses": ["2xx", "413", "422"]}}}
)


def _schema() -> Any:
    return schemathesis.openapi.from_dict(
        json.loads(OPENAPI_FILE.read_text(encoding="utf-8")), config=CONTRACT_CONFIG
    )


@pytest.fixture(scope="module")
def contract(api_app: FastAPI) -> Any:
    schema = _schema()
    schema.app = api_app
    return schema


# Login, logout, registro e troca de senha gerados ao acaso recusariam credenciais, encerrariam a
# sessão dos demais casos ou esbarrariam em nomes já usados; o gerenciamento recusa a sessão de
# monitora dos casos gerados (403) e contas sorteadas (404); o Google redireciona para a página.
# Os status de todos eles são provocados um a um nos testes de acesso restrito abaixo.
schema = (
    schemathesis.pytest.from_fixture("contract")
    .exclude(
        path=[
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/register",
            "/api/v1/profile/password",
            # O feedback gasta a cota diária da conta: os casos gerados a esgotariam (429).
            "/api/v1/feedback",
        ]
    )
    .exclude(path_regex=r"^/api/v1/(admin|auth/google)/")
)


@schema.parametrize()
@settings(max_examples=60, deadline=None, suppress_health_check=list(HealthCheck))
def test_responses_follow_the_published_contract(case: Any, session: dict[str, str]) -> None:
    # Os casos gerados trazem o cookie da sessão com um valor qualquer, que vira o de um membro.
    # Os casos negativos que o omitem conferem que a rota recusa a chamada sem sessão.
    if COOKIE in (case.cookies or {}):
        case.call_and_validate(cookies=session)
    else:
        case.call_and_validate()


# Cada status documentado do 5.2.2, provocado de propósito e validado contra o OpenAPI publicado.
DOCUMENTED_CASES = {
    "200-valid": ({"code": "x = 1\n", "list_number": 1}, 200, None),
    "200-invalid": ({"code": "for i in range(3):\n    print(i)\n", "list_number": 1}, 200, None),
    "200-syntax-error": ({"code": "if x\n    y = 1\n", "list_number": 1}, 200, None),
    "413": ({"code": "#" + "a" * 51_200, "list_number": 1}, 413, "PAYLOAD_TOO_LARGE"),
    "422-invalid-input": ({"code": "", "list_number": 1}, 422, "INVALID_INPUT"),
    "422-list-not-enabled": ({"code": "x = 1\n", "list_number": 6}, 422, "LIST_NOT_ENABLED"),
    "422-unknown-question": (
        {"code": "x = 1\n", "list_number": 1, "question_id": "L1-Q1"},
        422,
        "UNKNOWN_QUESTION",
    ),
    "422-analysis-limit": (
        {"code": "(" * 1_000 + ")" * 1_000, "list_number": 1},
        422,
        "ANALYSIS_LIMIT",
    ),
}


@pytest.mark.parametrize("name", DOCUMENTED_CASES, ids=list(DOCUMENTED_CASES))
def test_every_documented_status_follows_the_contract(
    contract: Any, session: dict[str, str], name: str
) -> None:
    body, status, error_code = DOCUMENTED_CASES[name]
    case = contract["/api/v1/validate"]["POST"].Case(body=body, media_type="application/json")

    response = case.call_and_validate(cookies=session)

    assert response.status_code == status
    if error_code is not None:
        assert response.json()["error"]["code"] == error_code


def _contract_with_session(
    settings: ApiSettings, transport: httpx2.MockTransport
) -> tuple[Any, dict[str, str]]:
    app, store = make_app(settings, analyzer_transport=transport)
    schema = _schema()
    schema.app = app
    return schema, {COOKIE: open_session(store, member(store))}


@pytest.fixture(scope="module")
def contract_without_analyzer() -> tuple[Any, dict[str, str]]:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("analyzer parado", request=request)

    return _contract_with_session(ApiSettings(), httpx2.MockTransport(refuse))


@pytest.mark.parametrize(
    ("path", "method", "body"),
    [
        ("/api/v1/validate", "POST", {"code": "x = 1\n", "list_number": 1}),
        ("/api/v1/lists", "GET", None),
        ("/ready", "GET", None),
    ],
)
def test_unavailable_analyzer_follows_the_contract(
    contract_without_analyzer: tuple[Any, dict[str, str]],
    path: str,
    method: str,
    body: dict[str, Any] | None,
) -> None:
    contract, session = contract_without_analyzer
    operation = contract[path][method]
    case = operation.Case(body=body, media_type="application/json") if body else operation.Case()

    # O 503 ANALYZER_UNAVAILABLE é documentado; as demais checagens (status documentado, esquema
    # do corpo, cabeçalhos) continuam valendo. 5xx genérico segue proibido no teste gerado acima.
    response = case.call_and_validate(cookies=session, excluded_checks=[not_a_server_error])

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ANALYZER_UNAVAILABLE"


def _contract_for(settings: ApiSettings) -> tuple[Any, dict[str, str]]:
    def valid(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "ruleset_version": "2026.2.0",
                "status": "valid",
                "list_number": 1,
                "syntax_error": None,
                "violations": [],
                "truncated": False,
            },
        )

    return _contract_with_session(settings, httpx2.MockTransport(valid))


def test_rate_limited_follows_the_contract() -> None:
    contract, session = _contract_for(ApiSettings(rate_limit=RateLimitConfig(client_per_min=1)))
    operation = contract["/api/v1/validate"]["POST"]
    body = {"code": "x = 1\n", "list_number": 1}

    first = operation.Case(body=body, media_type="application/json")
    second = operation.Case(body=body, media_type="application/json")

    # Sem a checagem ignored_auth: as chamadas extras dela gastariam o limite de 1 por minuto.
    assert (
        first.call_and_validate(cookies=session, excluded_checks=[ignored_auth]).status_code == 200
    )
    response = second.call_and_validate(cookies=session, excluded_checks=[ignored_auth])
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["retry-after"] == [str(response.json()["error"]["retry_after_s"])]


def test_overloaded_follows_the_contract() -> None:
    # Sem nenhuma vaga de admissão, toda análise é recusada com 503 OVERLOADED.
    contract, session = _contract_for(
        ApiSettings(admission=AdmissionConfig(capacity=0, max_waiting=0))
    )
    case = contract["/api/v1/validate"]["POST"].Case(
        body={"code": "x = 1\n", "list_number": 1}, media_type="application/json"
    )

    response = case.call_and_validate(cookies=session, excluded_checks=[not_a_server_error])

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OVERLOADED"
    assert response.headers["retry-after"] == ["10"]


# ---------------------------------------------------------------------------------------------
# Acesso restrito (Sprint 13): cada status das rotas de autenticação e das rotas protegidas
# ---------------------------------------------------------------------------------------------


def test_auth_statuses_follow_the_contract() -> None:
    app, store = make_app(ApiSettings())
    contract = _schema()
    contract.app = app
    login = contract["/api/v1/auth/login"]["POST"]
    waiting = member(store, status=Status.AGUARDANDO_APROVACAO, password_hash=None)

    # Os status de recusa são conferidos um a um; a checagem de "dado válido aceito" não se aplica.
    refusals = [positive_data_acceptance, not_a_server_error]

    def attempt(body: dict[str, Any], **kwargs: Any) -> Any:
        case = login.Case(body=body, media_type="application/json")
        return case.call_and_validate(excluded_checks=refusals, **kwargs)

    with TestClient(app):  # o lifespan cria a conta do desenvolvedor
        ok = attempt({"login": DEV_EMAIL, "password": PASSWORD})
        name, token = ok.headers["set-cookie"][0].split(";")[0].split("=", 1)
        session = {name: token}
        assert ok.status_code == 200
        assert attempt({"login": DEV_EMAIL, "password": "errada"}).status_code == 401
        assert attempt({"login": "x@xcin.ufpe.br", "password": "x"}).status_code == 422
        # Sem senha, a conta que aguarda aprovação nunca chega ao 403: mensagem única de 401.
        assert attempt({"login": waiting.name, "password": PASSWORD}).status_code == 401
        evil = attempt(
            {"login": DEV_EMAIL, "password": PASSWORD}, headers={"Origin": "https://evil.example"}
        )
        assert evil.status_code == 403
        for _ in range(4):
            attempt({"login": DEV_EMAIL, "password": "errada"})
        assert attempt({"login": DEV_EMAIL, "password": PASSWORD}).status_code == 429

        me = contract["/api/v1/auth/me"]["GET"]
        assert me.Case().call_and_validate(cookies=session).status_code == 200
        assert me.Case().call_and_validate(excluded_checks=refusals).status_code == 401
        logout = contract["/api/v1/auth/logout"]["POST"].Case().call_and_validate(cookies=session)
        assert logout.status_code == 204
        after = me.Case().call_and_validate(cookies=session, excluded_checks=refusals)
        assert after.status_code == 401


@pytest.mark.parametrize(
    ("path", "method", "body"),
    [
        ("/api/v1/validate", "POST", {"code": "x = 1\n", "list_number": 1}),
        ("/api/v1/lists", "GET", None),
    ],
)
def test_routes_without_session_follow_the_contract(
    contract: Any, path: str, method: str, body: dict[str, Any] | None
) -> None:
    operation = contract[path][method]
    case = operation.Case(body=body, media_type="application/json") if body else operation.Case()

    response = case.call_and_validate(excluded_checks=[positive_data_acceptance])

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_management_statuses_follow_the_contract() -> None:
    app, store = make_app(ApiSettings())
    contract = _schema()
    contract.app = app
    refusals = [positive_data_acceptance, not_a_server_error]
    monitor = {COOKIE: open_session(store, member(store))}
    chefe = {COOKIE: open_session(store, member(store, role=Role.MONITOR_CHEFE))}
    waiting = member(store, role=None, status=Status.AGUARDANDO_APROVACAO)
    target = member(store)

    def run(path: str, method: str, cookies: dict[str, str] | None, **case: Any) -> int:
        operation = contract[path][method]
        response = operation.Case(**case).call_and_validate(
            cookies=cookies, excluded_checks=refusals
        )
        return int(response.status_code)

    approve = "/api/v1/admin/requests/{account_id}/approve"
    role = {"media_type": "application/json"}
    with TestClient(app):
        assert run("/api/v1/admin/requests", "GET", chefe) == 200
        assert run("/api/v1/admin/members", "GET", chefe) == 200
        assert run("/api/v1/admin/members", "GET", monitor) == 403
        assert run("/api/v1/admin/members", "GET", None) == 401
        ids = {"account_id": str(waiting.id)}
        assert (
            run(approve, "POST", chefe, path_parameters=ids, body={"role": "professor"}, **role)
            == 403
        )
        assert (
            run(approve, "POST", chefe, path_parameters=ids, body={"role": "monitor"}, **role)
            == 204
        )
        assert (
            run(approve, "POST", chefe, path_parameters=ids, body={"role": "monitor"}, **role)
            == 409
        )
        unknown = {"account_id": str(uuid.uuid4())}
        assert (
            run(approve, "POST", chefe, path_parameters=unknown, body={"role": "monitor"}, **role)
            == 404
        )
        assert run(approve, "POST", chefe, path_parameters=ids, body={"role": "rei"}, **role) == 422
        member_ids = {"account_id": str(target.id)}
        assert (
            run(
                "/api/v1/admin/members/{account_id}/role",
                "PATCH",
                chefe,
                path_parameters=member_ids,
                body={"role": "monitor_chefe"},
                **role,
            )
            == 204
        )
        assert (
            run(
                "/api/v1/admin/members/{account_id}/remove",
                "POST",
                chefe,
                path_parameters=member_ids,
            )
            == 204
        )
        assert (
            run(
                "/api/v1/admin/members/{account_id}/reactivate",
                "POST",
                chefe,
                path_parameters=member_ids,
                body={"role": "monitor"},
                **role,
            )
            == 204
        )
        assert (
            run(
                "/api/v1/admin/requests/{account_id}/reject",
                "POST",
                chefe,
                path_parameters=member_ids,
            )
            == 409
        )


def test_google_statuses_follow_the_contract() -> None:
    app, _ = make_app(ApiSettings(google=GoogleConfig(client_id="c", client_secret="s")))
    contract = _schema()
    contract.app = app
    refusals = [positive_data_acceptance, not_a_server_error]

    def run(path: str, method: str, **case: Any) -> int:
        operation = contract[path][method]
        response = operation.Case(**case).call_and_validate(
            excluded_checks=refusals, allow_redirects=False
        )
        return int(response.status_code)

    with TestClient(app):
        assert run("/api/v1/auth/options", "GET") == 200
        assert run("/api/v1/auth/google/start", "GET") == 303
        assert run("/api/v1/auth/google/callback", "GET", query={"error": "access_denied"}) == 303
        assert run("/api/v1/auth/google/callback", "GET", query={"state": "x" * 300}) == 422
        assert run("/api/v1/auth/google/pending", "GET") == 422
        body = {"name": "Gabi", "course": "CC", "treatment": "neutro"}
        assert (
            run("/api/v1/auth/google/complete", "POST", body=body, media_type="application/json")
            == 422
        )


def test_feedback_statuses_follow_the_contract(
    api_bundle: tuple[FastAPI, MemoryAccountStore],
) -> None:
    app, store = api_bundle
    contract = _schema()
    contract.app = app
    refusals = [positive_data_acceptance, not_a_server_error]
    session = {COOKIE: open_session(store, member(store))}
    operation = contract["/api/v1/feedback"]["POST"]

    def run(body: dict[str, Any], cookies: dict[str, str] | None = session) -> Any:
        case = operation.Case(body=body, media_type="application/json")
        return case.call_and_validate(cookies=cookies, excluded_checks=refusals)

    base = {"code": "x = 1\nif x:\n    print(x)\n", "list_number": 1, "student_name": "Ana"}
    # Sem IA configurada, o texto é montado por modelos: 200 mesmo assim.
    ok = run(base)
    assert (ok.status_code, ok.json()["source"], ok.json()["provider"]) == (200, "template", None)
    assert run({**base, "code": "if x\n    y = 1\n"}).status_code == 422
    assert run({**base, "code": "#" + "a" * 51_200}).status_code == 413
    assert run({**base, "list_number": 6}).status_code == 422
    assert run(base, cookies=None).status_code == 401

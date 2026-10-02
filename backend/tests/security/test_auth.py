"""Suíte de segurança da autenticação (S16-03; DoD, seção 8, itens 16 a 20; ameaças 15 e 16).

Cada ataque passa pela borda (Caddy) do ``deploy/compose.yaml`` real, a partir de um contêiner
cliente na ``edge_net``, como um navegador ou um script de fora: sessões sem cookie, matriz de
permissões por chamada direta, domínios parecidos, atributos e rotação do cookie, ``Origin`` de
outro site, links de verificação usados e vencidos, senhas fracas, força bruta e, no fim, o
canário: nenhuma senha, token ou cookie usado aqui aparece nos logs dos serviços.

O Google não está configurado no compose (não há provedor de verdade na CI): aqui só se confere
que ele fica desligado. As recusas dele (domínio fora com ``hd`` adulterado, ``email_verified``
falso, ``state``, ``nonce``, assinatura e o pré-sequestro de conta) estão em
``tests/test_google.py``, com um provedor OIDC falso que assina tokens de verdade.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any

from argon2 import PasswordHasher

from security.harness import (
    DEV_PASSWORD,
    MAIL_UI_PORT,
    REPO_ROOT,
    SESSION_COOKIE,
    Answer,
    Client,
    docker,
    requires_docker,
    service_logs,
)

pytestmark = requires_docker

DEV_EMAIL = "vlacg@cin.ufpe.br"
EVIL = "https://evil.example"
#: Argon2id barato: as contas daqui só existem nesta suíte.
HASHER = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
#: Tudo o que foi mandado como senha, token ou cookie; o último teste procura nos logs.
SECRETS: set[str] = {DEV_PASSWORD}


def _remember(*values: str) -> None:
    SECRETS.update(value for value in values if value)


# --- Banco e contas ------------------------------------------------------------------------------


def _psql(db: str, sql: str) -> str:
    return docker(
        "exec", "-i", db, "psql", "-U", "postgres", "-d", "ipchecker",
        "-v", "ON_ERROR_STOP=1", "-q", "-At",
        input=sql,
    )  # fmt: skip


def _account(
    db: str,
    *,
    role: str | None = "monitor",
    status: str = "ativo",
    password: str | None = None,
) -> tuple[str, str, str]:
    """Cria uma conta direto no banco e devolve (id, nome, e-mail)."""
    run = uuid.uuid4().hex[:10]
    name, email = f"Seguranca {run}", f"seg.{run}@cin.ufpe.br"
    # Só valores gerados aqui (hex, hash do Argon2, nomes fixos) entram no SQL.
    hashed = f"'{HASHER.hash(password)}'" if password is not None else "NULL"
    role_sql = f"'{role}'" if role is not None else "NULL"
    sql = (
        "WITH a AS (INSERT INTO app.account (name, course, treatment, role, status, "  # noqa: S608
        f"signup_method, password_hash) VALUES ('{name}', 'Teste', 'neutro', {role_sql}, "
        f"'{status}', 'senha', {hashed}) RETURNING id) "
        "INSERT INTO app.account_email (email, account_id, verified_at) "
        f"SELECT '{email}', id, now() FROM a RETURNING account_id;"
    )
    return _psql(db, sql).strip(), name, email


def _developer_id(db: str) -> str:
    return _psql(
        db,
        f"SELECT account_id FROM app.account_email WHERE email = '{DEV_EMAIL}';",  # noqa: S608
    ).strip()


# --- HTTP pela borda -----------------------------------------------------------------------------


def _request(
    method: str,
    path: str,
    body: Any = None,
    *,
    session: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    extra = dict(headers or {})
    if session is not None:
        extra["Cookie"] = f"{SESSION_COOKIE}={session}"
    request: dict[str, Any] = {"method": method, "path": path, "headers": extra}
    if body is not None:
        request["json"] = body
    elif method in ("POST", "PATCH"):
        request["raw"] = ""  # corpo vazio, mas presente: a borda recusa POST sem Content-Length
    return request


def _one(client: Client, *args: Any, **kwargs: Any) -> Answer:
    return client.send([_request(*args, **kwargs)])[0]


def _session_of(answer: Answer) -> str:
    cookie = answer.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}="), cookie
    token = cookie.split(";", 1)[0].split("=", 1)[1]
    _remember(token)
    return token


def _login(client: Client, login: str, password: str, session: str | None = None) -> Answer:
    _remember(password)
    return _one(
        client,
        "POST",
        "/api/v1/auth/login",
        {"login": login, "password": password},
        session=session,
    )


def _signed_in(client: Client, login: str, password: str) -> str:
    answer = _login(client, login, password)
    assert answer.status == 200, answer
    return _session_of(answer)


def _error(answer: Answer) -> tuple[int, str | None]:
    return answer.status, answer.error_code


def _new_password() -> str:
    return f"Seg-{secrets.token_urlsafe(9)}!"


# --- Item 16: sem sessão, nada ------------------------------------------------------------------

OPEN = {("GET", "/health"), ("GET", "/ready"), ("GET", "/health/slo")}


def test_without_a_session_every_route_answers_401_and_no_data(fresh_client: Client) -> None:
    contract = json.loads((REPO_ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    requests = []
    for path, operations in contract["paths"].items():
        for method in operations:
            route = (method.upper(), path)
            if route in OPEN or path.startswith("/api/v1/auth/"):
                continue
            concrete = path.replace("{account_id}", str(uuid.uuid4()))
            body: dict[str, Any] | None = {} if route[0] in ("POST", "PATCH") else None
            requests.append(_request(route[0], concrete, body))

    answers = fresh_client.send(requests)

    assert len(answers) >= 10
    for request, answer in zip(requests, answers, strict=True):
        assert _error(answer) == (401, "UNAUTHENTICATED"), (request["path"], answer)
        assert set(answer.body) == {"error"}


# --- Item 17: matriz de permissões por chamada direta -------------------------------------------


def test_the_permission_matrix_holds_by_direct_calls(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    db = stack["db"]
    password = _new_password()
    _, _, monitor_email = _account(db, role="monitor", password=password)
    _, _, chefe_email = _account(db, role="monitor_chefe", password=password)
    professor_id, _, professor_email = _account(db, role="professor", password=password)
    other_id, _, _ = _account(db, role="monitor")
    pending_id, _, _ = _account(db, role=None, status="aguardando_aprovacao")
    developer_id = _developer_id(db)
    monitor = _signed_in(fresh_client, monitor_email, password)
    chefe = _signed_in(fresh_client, chefe_email, password)
    professor = _signed_in(fresh_client, professor_email, password)
    developer = _signed_in(fresh_client, DEV_EMAIL, DEV_PASSWORD)
    chefe_id = _psql(
        db,
        f"SELECT account_id FROM app.account_email WHERE email = '{chefe_email}';",  # noqa: S608
    ).strip()

    admin = "/api/v1/admin"
    monitor_calls = [
        ("GET", f"{admin}/requests", None),
        ("GET", f"{admin}/members", None),
        ("POST", f"{admin}/requests/{pending_id}/approve", {"role": "monitor"}),
        ("POST", f"{admin}/requests/{pending_id}/reject", None),
        ("PATCH", f"{admin}/members/{other_id}/role", {"role": "monitor_chefe"}),
        ("POST", f"{admin}/members/{other_id}/remove", None),
        ("POST", f"{admin}/members/{other_id}/reactivate", {"role": "monitor"}),
    ]
    refused = [
        # Monitor não aprova, não muda cargos nem remove contas.
        *[(monitor, method, path, body) for method, path, body in monitor_calls],
        # Monitor-chefe não age sobre professor nem aprova como professor.
        (chefe, "PATCH", f"{admin}/members/{professor_id}/role", {"role": "monitor"}),
        (chefe, "POST", f"{admin}/members/{professor_id}/remove", None),
        (chefe, "POST", f"{admin}/requests/{pending_id}/approve", {"role": "professor"}),
        # Só o desenvolvedor altera a conta do desenvolvedor, e nem ele por aqui.
        (professor, "PATCH", f"{admin}/members/{developer_id}/role", {"role": "monitor"}),
        (professor, "POST", f"{admin}/members/{developer_id}/remove", None),
        (developer, "POST", f"{admin}/members/{developer_id}/remove", None),
        # Ninguém altera o próprio cargo.
        (chefe, "PATCH", f"{admin}/members/{chefe_id}/role", {"role": "professor"}),
        (developer, "PATCH", f"{admin}/members/{developer_id}/role", {"role": "professor"}),
        # Ninguém atribui o cargo de desenvolvedor.
        (developer, "POST", f"{admin}/requests/{pending_id}/approve", {"role": "desenvolvedor"}),
    ]
    answers = fresh_client.send(
        [_request(method, path, body, session=who) for who, method, path, body in refused]
    )
    for (_, method, path, _), answer in zip(refused, answers, strict=True):
        assert _error(answer) == (403, "FORBIDDEN"), (method, path, answer)

    # Controle: dentro da alçada, a mesma chamada passa.
    approved = _one(
        fresh_client,
        "POST",
        f"{admin}/requests/{pending_id}/approve",
        {"role": "monitor"},
        session=chefe,
    )
    assert approved.status == 204


# --- Item 18: domínios e Google ------------------------------------------------------------------

LOOKALIKES = ["x@xcin.ufpe.br", "x@ee.ufpe.br", "x@cin.ufpe.br.exemplo.com"]


def test_lookalike_domains_are_refused_and_uppercase_is_accepted(fresh_client: Client) -> None:
    password = _new_password()
    _remember(password)
    register = [
        _request(
            "POST",
            "/api/v1/auth/register",
            {
                "name": f"Parecido {index} {uuid.uuid4().hex[:6]}",
                "email": email,
                "password": password,
                "course": "Teste",
                "treatment": "neutro",
            },
        )
        for index, email in enumerate(LOOKALIKES)
    ]
    login = [
        _request("POST", "/api/v1/auth/login", {"login": email, "password": password})
        for email in LOOKALIKES
    ]
    upper = f"Seg.Maiuscula.{uuid.uuid4().hex[:6]}@CIN.UFPE.BR"
    accepted = _request(
        "POST",
        "/api/v1/auth/register",
        {
            "name": f"Maiuscula {uuid.uuid4().hex[:6]}",
            "email": upper,
            "password": password,
            "course": "Teste",
            "treatment": "neutro",
        },
    )

    answers = fresh_client.send([*register, *login, accepted])

    for answer in answers[:-1]:
        assert _error(answer) == (422, "DOMAIN_NOT_ALLOWED"), answer
    assert answers[-1].status == 201
    assert answers[-1].body == {"status": "aguardando_verificacao", "email": upper.lower()}


def test_google_stays_off_without_configuration(fresh_client: Client) -> None:
    options, start = fresh_client.send(
        [_request("GET", "/api/v1/auth/options"), _request("GET", "/api/v1/auth/google/start")]
    )

    assert options.body == {"google": False, "feedback_ai": False}
    assert start.status == 303
    assert start.headers["location"] == "/entrar?google=indisponivel"


# --- Item 19: sessão ---------------------------------------------------------------------------


def test_the_cookie_is_safe_and_every_login_gets_a_new_identifier(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    password = _new_password()
    _, _, email = _account(stack["db"], password=password)

    first = _login(fresh_client, email, password)
    second = _login(fresh_client, email, password, session=_session_of(first))
    old, new = _session_of(first), _session_of(second)
    me_old, me_new = fresh_client.send(
        [
            _request("GET", "/api/v1/auth/me", session=old),
            _request("GET", "/api/v1/auth/me", session=new),
        ]
    )

    cookie = first.headers["set-cookie"].lower()
    assert all(flag in cookie for flag in ("httponly", "secure", "samesite=lax", "path=/"))
    assert "domain=" not in cookie
    assert first.headers["cache-control"] == "no-store"
    assert old != new
    # O identificador apresentado no login morreu (fixação de sessão).
    assert (me_old.status, me_new.status) == (401, 200)


def test_sessions_end_on_password_change_role_change_and_removal(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    password, changed = _new_password(), _new_password()
    _remember(changed)
    account_id, _, email = _account(stack["db"], password=password)
    developer = _signed_in(fresh_client, DEV_EMAIL, DEV_PASSWORD)

    def me(session: str) -> int:
        return _one(fresh_client, "GET", "/api/v1/auth/me", session=session).status

    # Troca de senha: a sessão que trocou continua; as outras caem.
    keep, other = (
        _signed_in(fresh_client, email, password),
        _signed_in(fresh_client, email, password),
    )
    change = _one(
        fresh_client,
        "POST",
        "/api/v1/profile/password",
        {"current_password": password, "new_password": changed},
        session=keep,
    )
    assert change.status == 204
    assert (me(keep), me(other)) == (200, 401)

    # Mudança de cargo: as sessões da conta caem.
    role = _one(
        fresh_client,
        "PATCH",
        f"/api/v1/admin/members/{account_id}/role",
        {"role": "monitor_chefe"},
        session=developer,
    )
    assert role.status == 204
    assert me(keep) == 401

    # Remoção: as sessões caem, e o login mostra a conta removida só com a senha certa.
    session = _signed_in(fresh_client, email, changed)
    removed = _one(
        fresh_client, "POST", f"/api/v1/admin/members/{account_id}/remove", session=developer
    )
    assert removed.status == 204
    assert me(session) == 401
    assert _error(_login(fresh_client, email, changed)) == (403, "ACCOUNT_REMOVED")
    assert _error(_login(fresh_client, email, _new_password())) == (401, "INVALID_CREDENTIALS")


def test_state_changes_from_another_site_are_refused(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    developer = _signed_in(fresh_client, DEV_EMAIL, DEV_PASSWORD)
    pending_id, _, _ = _account(stack["db"], role=None, status="aguardando_aprovacao")
    evil = {"Origin": EVIL}
    attempts = [
        _request(
            "POST",
            "/api/v1/auth/login",
            {"login": DEV_EMAIL, "password": DEV_PASSWORD},
            headers=evil,
        ),
        _request("POST", "/api/v1/auth/logout", session=developer, headers=evil),
        _request(
            "POST",
            "/api/v1/validate",
            {"code": "x = 1\n", "list_number": 1},
            session=developer,
            headers=evil,
        ),
        _request(
            "PATCH", "/api/v1/profile", {"course": "Invadido"}, session=developer, headers=evil
        ),
        _request(
            "POST",
            f"/api/v1/admin/requests/{pending_id}/approve",
            {"role": "professor"},
            session=developer,
            headers=evil,
        ),
        _request(
            "POST",
            "/api/v1/auth/google/complete",
            {"name": "Invasor", "course": "X", "treatment": "neutro"},
            headers=evil,
        ),
    ]

    answers = fresh_client.send(attempts)

    for request, answer in zip(attempts, answers, strict=True):
        assert _error(answer) == (403, "ORIGIN_MISMATCH"), (request["path"], answer)
    # Nada mudou: o pedido segue na fila e a sessão do desenvolvedor segue válida.
    status = _psql(stack["db"], f"SELECT status FROM app.account WHERE id = '{pending_id}';")  # noqa: S608
    assert status.strip() == "aguardando_aprovacao"
    assert _one(fresh_client, "GET", "/api/v1/auth/me", session=developer).status == 200


# --- Item 20: tokens e senhas --------------------------------------------------------------------


def _mailpit_token(to: str) -> str:
    base = f"http://127.0.0.1:{MAIL_UI_PORT}/api/v1"
    deadline = time.monotonic() + 15
    while True:
        query = urllib.parse.urlencode({"query": f'to:"{to}"'})
        with urllib.request.urlopen(f"{base}/search?{query}", timeout=10) as response:  # noqa: S310
            messages = json.load(response)["messages"]
        if messages:
            break
        assert time.monotonic() < deadline, f"o e-mail para {to} não chegou ao Mailpit"
        time.sleep(0.5)
    with urllib.request.urlopen(f"{base}/message/{messages[0]['ID']}", timeout=10) as response:  # noqa: S310
        text = json.load(response)["Text"]
    token = str(text).split("token=", 1)[1].split()[0]
    _remember(token)
    return token


def test_used_and_expired_verification_links_do_not_work(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    password = _new_password()
    _remember(password)
    email = f"seg.link.{uuid.uuid4().hex[:8]}@cin.ufpe.br"
    registered = _one(
        fresh_client,
        "POST",
        "/api/v1/auth/register",
        {
            "name": f"Link {uuid.uuid4().hex[:6]}",
            "email": email,
            "password": password,
            "course": "Teste",
            "treatment": "neutro",
        },
    )
    assert registered.status == 201
    token = _mailpit_token(email)

    first, again = fresh_client.send(
        [_request("POST", "/api/v1/auth/verify", {"token": token}) for _ in range(2)]
    )
    assert first.status == 200
    assert _error(again) == (422, "INVALID_TOKEN")

    # Um link vencido (24 h) não funciona, mesmo nunca usado.
    expired = secrets.token_urlsafe(32)
    _remember(expired)
    waiting_id, _, _ = _account(stack["db"], role=None, status="aguardando_verificacao")
    digest = hashlib.sha256(expired.encode()).hexdigest()
    _psql(
        stack["db"],
        "INSERT INTO app.email_token (token_hash, account_id, purpose, expires_at) "  # noqa: S608
        f"VALUES (decode('{digest}', 'hex'), '{waiting_id}', 'verificacao', "
        "now() - interval '1 minute');",
    )
    answer = _one(fresh_client, "POST", "/api/v1/auth/verify", {"token": expired})
    assert _error(answer) == (422, "INVALID_TOKEN")


WEAK = ["Curta-1!", "sem-maiuscula-1", "SemEspecial1", "A!" + "a" * 128]


def test_weak_passwords_are_refused_by_the_backend(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    password = _new_password()
    _, _, email = _account(stack["db"], password=password)
    session = _signed_in(fresh_client, email, password)
    _remember(*WEAK)
    requests = [
        _request(
            "POST",
            "/api/v1/auth/register",
            {
                "name": f"Fraca {uuid.uuid4().hex[:6]}",
                "email": f"fraca.{uuid.uuid4().hex[:6]}@ufpe.br",
                "password": weak,
                "course": "Teste",
                "treatment": "neutro",
            },
        )
        for weak in WEAK
    ] + [
        _request(
            "POST",
            "/api/v1/profile/password",
            {"current_password": password, "new_password": weak},
            session=session,
        )
        for weak in WEAK
    ]

    answers = fresh_client.send(requests)

    for answer in answers:
        assert _error(answer) in {(422, "WEAK_PASSWORD"), (422, "INVALID_INPUT")}, answer
    # A senha longa demais esbarra no limite do esquema; as outras, na política.
    assert [a.error_code for a in answers].count("WEAK_PASSWORD") >= 6


def test_after_five_failures_the_next_login_waits(
    fresh_client: Client, stack: dict[str, str]
) -> None:
    password = _new_password()
    _, _, email = _account(stack["db"], password=password)
    wrong = [_new_password() for _ in range(5)]

    failures = [_login(fresh_client, email, attempt) for attempt in wrong]
    blocked = _login(fresh_client, email, password)  # nem a senha certa passa enquanto espera

    assert [_error(answer) for answer in failures] == [(401, "INVALID_CREDENTIALS")] * 5
    assert _error(blocked) == (429, "RATE_LIMITED")
    assert blocked.headers["retry-after"] == str(blocked.body["error"]["retry_after_s"])
    assert 1 <= blocked.body["error"]["retry_after_s"] <= 15 * 60


# --- Canário: por último -------------------------------------------------------------------------


def test_no_password_token_or_cookie_reaches_the_logs(stack: dict[str, str]) -> None:
    logs = service_logs("web", "api", "analyzer", "db")

    assert len(SECRETS) >= 20, "os testes acima não rodaram"
    assert "request" in logs  # os serviços escreveram, e mesmo assim nada vazou
    leaked = sorted(value for value in SECRETS if value in logs)
    assert leaked == [], f"{len(leaked)} segredo(s) nos logs"
    for token in [value for value in SECRETS if len(value) >= 40]:
        assert hashlib.sha256(token.encode()).hexdigest() not in logs

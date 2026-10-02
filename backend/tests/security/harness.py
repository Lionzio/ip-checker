"""Infraestrutura da suíte de segurança: Docker, cliente HTTP na rede interna e sondas.

A suíte testa o que vai para produção: o ``deploy/compose.yaml`` real (web, api e analyzer). As
requisições partem de contêineres clientes: um só na ``analyzer_net``, no papel da ``api``, para
atacar o analyzer; outro só na ``edge_net``, no papel do navegador, para atacar a borda pública.
Os pedidos seguem pela entrada padrão, sem limite de tamanho de linha de comando, e as respostas
voltam em JSON com o tempo medido dentro da rede.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "deploy" / "compose.yaml"
PROJECT = "ipc-security-test"
NETWORK = f"{PROJECT}_analyzer_net"
EDGE_NETWORK = f"{PROJECT}_edge_net"
CLIENT = f"{PROJECT}-client"
PUBLIC_CLIENT = f"{PROJECT}-public-client"
#: Clientes da borda criados por teste, cada um com outro IP (S16-03, S17-02): assim não
#: dividem o limite por IP que ``test_api_rate_limit_edge`` esgota de propósito.
FRESH_CLIENT = f"{PROJECT}-fresh-client"
IMAGE = "ip-checker-backend:local"
ANALYZER_URL = "http://analyzer:8001"
WEB_URL = "http://web:8080"
#: Porta da borda nesta suíte, diferente da 8180 do compose de desenvolvimento.
HTTP_PORT = "18180"
#: Página do Mailpit nesta suíte, diferente da 8125 do compose de desenvolvimento.
MAIL_UI_PORT = "18125"
#: UID e GID do usuário do serviço na imagem.
UID_GID = 10001
#: Workers do pool no compose (PoolConfig padrão).
WORKERS = 2
#: Mesma imagem do banco do compose (S13-01), fixada por digest.
POSTGRES_IMAGE = (
    "postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
)
#: Senhas desta execução da suíte (o compose as lê do ambiente; nunca vão para o disco).
DB_ADMIN_PASSWORD = secrets.token_urlsafe(24)
DB_API_PASSWORD = secrets.token_urlsafe(24)
DEV_PASSWORD = "Dev-" + secrets.token_urlsafe(12) + "!"
#: Desde a S13-02, toda rota da equipe exige a sessão de uma conta ativa (FR-22).
SESSION_COOKIE = "__Host-ipc_session"

requires_docker = pytest.mark.skipif(
    os.environ.get("IPC_SECURITY_TESTS") != "1",
    reason="precisa de Docker; defina IPC_SECURITY_TESTS=1 para rodar",
)

# ---------------------------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------------------------


def docker(*args: str, timeout: float = 60, input: str | None = None, check: bool = True) -> str:
    executable = shutil.which("docker")
    if executable is None:
        pytest.fail("IPC_SECURITY_TESTS=1, mas o Docker não foi encontrado no PATH")
    result = subprocess.run(  # noqa: S603 - argumentos fixos do próprio teste, sem shell
        [executable, *args],
        capture_output=True,
        encoding="utf-8",
        input=input,
        timeout=timeout,
        check=False,
        env={
            **os.environ,
            "IPC_HTTP_PORT": HTTP_PORT,
            "IPC_MAIL_UI_PORT": MAIL_UI_PORT,
            "IPC_DB_ADMIN_PASSWORD": DB_ADMIN_PASSWORD,
            "IPC_DB_API_PASSWORD": DB_API_PASSWORD,
            "IPC_DEV_INITIAL_PASSWORD": DEV_PASSWORD,
        },
    )
    if check and result.returncode != 0:
        pytest.fail(f"docker {' '.join(args[:3])} falhou ({result.returncode}):\n{result.stderr}")
    return result.stdout


def compose(*args: str, timeout: float = 60) -> str:
    return docker("compose", "-f", str(COMPOSE_FILE), "-p", PROJECT, *args, timeout=timeout)


def probe(container: str, code: str, *args: str) -> Any:
    """Roda ``code`` com o Python de dentro do contêiner e devolve o JSON que ele imprimir."""
    return json.loads(docker("exec", container, "python", "-c", code, *args))


def service_logs(*services: str) -> str:
    return compose("logs", "--no-color", *services)


def analyzer_logs() -> str:
    return service_logs("analyzer")


# ---------------------------------------------------------------------------------------------
# Cliente HTTP (roda no contêiner cliente)
# ---------------------------------------------------------------------------------------------

HTTP_PROBE = r"""
import base64, json, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

job = json.load(sys.stdin)

KEPT_HEADERS = (
    "x-request-id",
    "retry-after",
    "content-type",
    "access-control-allow-origin",
    "access-control-expose-headers",
    "strict-transport-security",
    "x-content-type-options",
    "set-cookie",
    "location",
    "cache-control",
)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Os redirecionamentos (Google) são conferidos como respostas, não seguidos.
    def redirect_request(self, *args, **kwargs):
        return None

OPENER = urllib.request.build_opener(NoRedirect)

def call(request):
    if request.get("raw") is not None:
        data = base64.b64decode(request["raw"])
    elif request.get("json") is not None:
        data = json.dumps(request["json"]).encode()
    else:
        data = None
    if data is not None and request.get("chunked"):
        data = iter([data])  # sem Content-Length: o urllib envia em partes (chunked)
    http = urllib.request.Request(
        job["base"] + request["path"],
        data=data,
        method=request["method"],
        headers={"Content-Type": "application/json", **request.get("headers", {})},
    )
    start = time.perf_counter()
    try:
        with OPENER.open(http, timeout=30) as response:
            status, raw, headers = response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        status, raw, headers = error.code, error.read(), error.headers
    elapsed_ms = (time.perf_counter() - start) * 1000
    try:
        body = json.loads(raw)
    except ValueError:
        body = raw.decode("utf-8", "replace")
    kept = {name: headers[name] for name in KEPT_HEADERS if headers.get(name) is not None}
    return {"status": status, "body": body, "elapsed_ms": elapsed_ms, "headers": kept}

with ThreadPoolExecutor(max_workers=job["concurrency"]) as executor:
    print(json.dumps(list(executor.map(call, job["requests"]))))
"""


@dataclass(frozen=True, slots=True)
class Answer:
    status: int
    body: Any
    elapsed_ms: float
    #: Só os cabeçalhos de KEPT_HEADERS (no HTTP_PROBE), com nomes em minúsculas.
    headers: dict[str, str]

    @property
    def error_code(self) -> str | None:
        if isinstance(self.body, dict) and isinstance(self.body.get("error"), dict):
            code: str = self.body["error"]["code"]
            return code
        return None

    @property
    def flagged(self) -> set[tuple[int, str]]:
        """Pares (linha, construção) das violações da resposta."""
        return {(v["line"], v["construct"]) for v in self.body.get("violations", [])}


def analyze_request(code: str, list_number: int = 1) -> dict[str, Any]:
    return {
        "method": "POST",
        "path": "/internal/analyze",
        "json": {"code": code, "list_number": list_number},
    }


def create_sessions(db_container: str, count: int, database: str = "ipchecker") -> list[str]:
    """Contas ativas da equipe, cada uma com uma sessão aberta, criadas direto no banco.

    Só esta suíte faz isso: assim, cada ataque pode vir de um membro diferente, como antes vinha
    de um ``X-Client-Id`` diferente. Devolve os identificadores dos cookies.
    """
    run = uuid.uuid4().hex[:8]
    tokens = [secrets.token_urlsafe(32) for _ in range(count)]
    # Só valores gerados aqui (hex, números) entram no SQL; nada vem de fora da suíte.
    statements = [
        "WITH a AS (INSERT INTO app.account (name, course, treatment, role, status, signup_method) "  # noqa: S608
        f"VALUES ('Membro {run} {index}', 'Teste', 'neutro', 'monitor', 'ativo', 'senha') "
        "RETURNING id) INSERT INTO app.session (token_hash, account_id, expires_at) "
        f"SELECT decode('{hashlib.sha256(token.encode()).hexdigest()}', 'hex'), id, "
        "now() + interval '1 day' FROM a;"
        for index, token in enumerate(tokens)
    ]
    sql = "BEGIN;\n" + "\n".join(statements) + "\nCOMMIT;\n"
    docker(
        "exec", "-i", db_container, "psql", "-U", "postgres", "-d", database,
        "-v", "ON_ERROR_STOP=1", "-q",
        input=sql,
    )  # fmt: skip
    return tokens


class SessionPool:
    """Sessões prontas para os ataques pela borda, criadas em lotes no banco do compose."""

    def __init__(self, db_container: str, batch: int = 100) -> None:
        self.db_container = db_container
        self.batch = batch
        self._free: list[str] = []

    def take(self) -> str:
        if not self._free:
            self._free = create_sessions(self.db_container, self.batch)
        return self._free.pop()


_POOL: SessionPool | None = None


def use_sessions(pool: SessionPool) -> None:
    # A suíte inteira usa um único compose e, portanto, um único conjunto de sessões.
    global _POOL
    _POOL = pool


def new_session() -> str:
    """A sessão de um membro que ainda não fez nenhuma requisição."""
    if _POOL is None:
        pytest.fail("o compose da suíte não subiu: use a fixture stack")
    return _POOL.take()


def session_header(token: str | None = None) -> dict[str, str]:
    return {"Cookie": f"{SESSION_COOKIE}={token or new_session()}"}


def validate_request(
    code: str,
    list_number: int = 1,
    headers: dict[str, str] | None = None,
    *,
    session: str | None = None,
) -> dict[str, Any]:
    """Requisição à API pública, pela borda (5.2.2).

    Cada requisição vem de um membro diferente (sessão nova), a não ser que ``session`` seja
    passada: o limite de 30 por minuto por conta tem os próprios testes
    (``test_api_rate_limit_edge``). Um ``Cookie`` em ``headers`` substitui o da sessão.
    """
    return {
        "method": "POST",
        "path": "/api/v1/validate",
        "json": {"code": code, "list_number": list_number},
        "headers": {**session_header(session), **(headers or {})},
    }


def raw_request(
    body: bytes, path: str = "/internal/analyze", *, chunked: bool = False
) -> dict[str, Any]:
    # Na API pública, a sessão faz a requisição chegar à validação; o analyzer a ignora.
    headers = session_header() if path.startswith("/api/") else {}
    return {
        "method": "POST",
        "path": path,
        "raw": base64.b64encode(body).decode(),
        "chunked": chunked,
        "headers": headers,
    }


HEALTH_REQUEST: dict[str, Any] = {"method": "GET", "path": "/internal/health"}


@dataclass(frozen=True, slots=True)
class Client:
    container: str
    base: str = ANALYZER_URL

    def send(self, requests: list[dict[str, Any]], concurrency: int = 1) -> list[Answer]:
        job = {"base": self.base, "requests": requests, "concurrency": concurrency}
        output = docker(
            "exec",
            "-i",
            self.container,
            "python",
            "-c",
            HTTP_PROBE,
            input=json.dumps(job),
            timeout=120,
        )
        answers = [Answer(**answer) for answer in json.loads(output)]
        for request, answer in zip(requests, answers, strict=True):
            # DoD, seção 8: nenhuma entrada, por pior que seja, produz um 5xx genérico.
            assert answer.status < 500, (request.get("json") or request, answer)
        return answers

    def analyze(self, code: str, list_number: int = 1) -> Answer:
        return self.send([analyze_request(code, list_number)])[0]

    def health(self) -> Answer:
        return self.send([HEALTH_REQUEST])[0]


# ---------------------------------------------------------------------------------------------
# Sondas que rodam no contêiner do analyzer
# ---------------------------------------------------------------------------------------------

PROCESSES_PROBE = r"""
import json, pathlib
processes = []
for entry in pathlib.Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        lines = (entry / "status").read_text().splitlines()
        cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode().strip()
        environ = (entry / "environ").read_bytes().split(b"\0")
        limits = (entry / "limits").read_text().splitlines()
    except OSError:
        continue  # o processo terminou durante a varredura
    status = dict(line.split(":\t", 1) for line in lines if ":\t" in line)
    processes.append({
        "pid": int(entry.name),
        "ppid": int(status["PPid"]),
        "state": status["State"].split()[0],
        "uids": [int(uid) for uid in status["Uid"].split()],
        "gids": [int(gid) for gid in status["Gid"].split()],
        "caps": {name: status[name] for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
        "no_new_privs": int(status["NoNewPrivs"]),
        "seccomp": int(status["Seccomp"]),
        "cmdline": cmdline,
        "env": sorted({item.split(b"=", 1)[0].decode() for item in environ if item}),
        "limits": limits,
    })
print(json.dumps(processes))
"""


def processes(container: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = probe(container, PROCESSES_PROBE)
    return found


def workers(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Os workers são os filhos do forkserver (que também tem 'forkserver' na linha de comando)."""
    by_pid = {process["pid"]: process for process in found}
    return [
        process
        for process in found
        if "forkserver" in process["cmdline"]
        and "forkserver" in by_pid.get(process["ppid"], {}).get("cmdline", "")
    ]

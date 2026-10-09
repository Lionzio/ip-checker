"""Isolamento por processo na imagem do piloto (S11-01; NFR-07 e DoD item 11 na Fase 1).

O Render roda um único contêiner, sem rede interna nem flags de contêiner. Este módulo sobe a
imagem ``deploy/render/Dockerfile`` como o Render a roda (sem endurecimento do Docker, sem a
capacidade ``CAP_KILL``, que o Render não dá (P-17), e com uma variável que faz o papel de segredo)
e confere, de dentro dela, o que o blueprint exige:

- a API roda como UID 10001 e o analisador como UID 10002, com o ambiente vazio;
- o analisador não lê o ambiente da API nem o do supervisord;
- os workers têm o filtro seccomp e os limites de recursos, e lá dentro abrir socket, executar
  programa e gravar em disco falham;
- só a API escuta fora do loopback;
- o pior caso de 50 KB cabe nos 160 MiB por worker;
- CORS, HSTS e a versão implantada se comportam como no piloto;
- sem ``CAP_KILL``, o contêiner para em menos de 15 s, sem ``CRIT`` do supervisord (S30-10).

Desde a Sprint 13, a API do piloto não sobe sem o banco de contas: um PostgreSQL de teste roda
numa rede só dele, as migrações são aplicadas antes (como no deploy) e a credencial do banco é
mais um segredo que só a API pode ver.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Iterator
from typing import Any

import pytest

from security.harness import (
    DB_ADMIN_PASSWORD,
    DB_API_PASSWORD,
    DEV_PASSWORD,
    POSTGRES_IMAGE,
    REPO_ROOT,
    Client,
    create_sessions,
    docker,
    requires_docker,
    session_header,
)

pytestmark = requires_docker

PILOT_IMAGE = "ip-checker-pilot:local"
CONTAINER = "ipc-security-test-pilot"
#: Banco de contas do piloto nos testes: uma rede só para ele e a API.
PILOT_NETWORK = "ipc-security-test-pilot-net"
PILOT_DB = "ipc-security-test-pilot-db"
#: Um segundo contêiner, só para conferir o desligamento (S30-10).
STOP_CONTAINER = "ipc-security-test-pilot-stop"
#: O ``stopwaitsecs`` do supervisord.
STOP_WAIT_S = 15
DATABASE_URL = f"postgresql://ipc_api:{DB_API_PASSWORD}@{PILOT_DB}:5432/ipchecker"
#: Faz o papel de uma credencial no ambiente do Render: só a API pode recebê-la.
CANARY_SECRET = "segredo-canario-7d1f"
SPA = "https://ip-checker.vercel.app"
RELEASE = "0123456789abcdef"
API_UID, ANALYZER_UID = 10001, 10002
MIB = 1024 * 1024
#: O que o analisador pode ter no ambiente (o supervisord o inicia com ``env -i``). LC_CTYPE é
#: acrescentado pelo próprio Python (coerção de locale).
ANALYZER_ENV = frozenset(
    {
        "PATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONUNBUFFERED",
        "IPC_RULESET_PATH",
        "IPC_SANDBOX",
        "IPC_MEMORY_MB",
        "IPC_WORKERS",
        "LC_CTYPE",
    }
)

#: Lista os processos; o ambiente só aparece quando quem roda a sonda pode lê-lo.
PROCESSES_PROBE = r"""
import json, pathlib
found = []
for entry in pathlib.Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        lines = (entry / "status").read_text().splitlines()
        cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode().strip()
        limits = (entry / "limits").read_text().splitlines()
    except OSError:
        continue
    try:
        raw = (entry / "environ").read_bytes().split(b"\0")
        env = sorted({item.split(b"=", 1)[0].decode() for item in raw if item})
    except OSError:
        env = None
    status = dict(line.split(":\t", 1) for line in lines if ":\t" in line)
    found.append({
        "pid": int(entry.name),
        "ppid": int(status["PPid"]),
        "uid": int(status["Uid"].split()[0]),
        "filters": int(status.get("Seccomp_filters", "0")),
        "cmdline": cmdline,
        "env": env,
        "limits": limits,
    })
print(json.dumps(found))
"""

#: Roda como o usuário do analisador e se fecha como um worker; depois tenta escapar.
ESCAPE_PROBE = r"""
import errno, json, os, socket, subprocess, sys
from ipc_analyzer.runtime.limits import ResourceLimits, apply_limits, forbid_new_processes
from ipc_analyzer.runtime.sandbox import SandboxMode, enforce
api_pid = int(sys.argv[1])
results = {}
for name, path in {"api": f"/proc/{api_pid}/environ", "supervisord": "/proc/1/environ"}.items():
    try:
        open(path, "rb").read()
        results["environ_" + name] = "leu"
    except OSError as exc:
        results["environ_" + name] = errno.errorcode[exc.errno]
target = "/tmp/ipc-canario-%d" % os.getpid()
apply_limits(ResourceLimits(memory_bytes=160 * 1024 * 1024))
enforce(SandboxMode.REQUIRED)
forbid_new_processes()

def write_file():
    # RLIMIT_FSIZE = 0: criar um arquivo vazio ainda é possível, gravar um byte não.
    with open(target, "w") as handle:
        handle.write("x" * 4096)
        handle.flush()

attempts = {
    "socket": lambda: socket.create_connection(("1.1.1.1", 443), timeout=2),
    "loopback": lambda: socket.create_connection(("127.0.0.1", 10000), timeout=2),
    "exec": lambda: subprocess.run(["/bin/sh", "-c", "true"], check=True),
    "write": write_file,
}
for name, attempt in attempts.items():
    try:
        attempt()
        results[name] = "conseguiu"
    except OSError as exc:
        results[name] = errno.errorcode.get(exc.errno or 0, str(exc.errno))
print(json.dumps(results))
"""

LISTEN_PROBE = r"""
import json
listening = []
for line in open("/proc/net/tcp").read().splitlines()[1:]:
    fields = line.split()
    if fields[3] == "0A":
        address, port = fields[1].split(":")
        ip = ".".join(str(int(address[i:i + 2], 16)) for i in (6, 4, 2, 0))
        listening.append(f"{ip}:{int(port, 16)}")
print(json.dumps(sorted(listening)))
"""


def probe_as(user: int | str, code: str, *args: str) -> Any:
    return json.loads(docker("exec", "-u", str(user), CONTAINER, "python", "-c", code, *args))


@pytest.fixture(scope="module")
def pilot() -> Iterator[str]:
    docker(
        "build",
        "-f",
        str(REPO_ROOT / "deploy/render/Dockerfile"),
        "-t",
        PILOT_IMAGE,
        str(REPO_ROOT),
        timeout=900,
    )
    _cleanup()
    docker("network", "create", PILOT_NETWORK)
    docker(
        "run", "--detach", "--name", PILOT_DB, "--network", PILOT_NETWORK,
        "-e", "POSTGRES_DB=ipchecker",
        "-e", f"POSTGRES_PASSWORD={DB_ADMIN_PASSWORD}",
        POSTGRES_IMAGE,
    )  # fmt: skip
    _wait_for_database()
    # Como no deploy: as migrações rodam antes, com a credencial de admin, fora do serviço.
    docker(
        "run", "--rm", "--network", PILOT_NETWORK,
        "-e", f"IPC_DATABASE_ADMIN_URL=postgresql://postgres:{DB_ADMIN_PASSWORD}@{PILOT_DB}:5432/ipchecker",
        "-e", f"IPC_DB_LOGIN_PASSWORD={DB_API_PASSWORD}",
        PILOT_IMAGE,
        "python", "-m", "ipc_api.db.migrate", "up", "--login-role", "ipc_api",
        timeout=120,
    )  # fmt: skip
    _run_pilot(CONTAINER)
    try:
        client = Client(CONTAINER, base="http://127.0.0.1:10000")
        _wait_until_ready(CONTAINER)
        yield client.container
    finally:
        _cleanup()


def _run_pilot(name: str) -> None:
    docker(
        "run", "--detach", "--name", name, "--network", PILOT_NETWORK,
        # Como no Render (P-17): sem CAP_KILL, o root não sinaliza processos de outro usuário.
        "--cap-drop", "KILL",
        "-e", f"IPC_FAKE_SECRET={CANARY_SECRET}",
        "-e", f"IPC_CORS_ORIGINS={SPA}",
        "-e", "IPC_HSTS=1",
        "-e", f"RENDER_GIT_COMMIT={RELEASE}",
        "-e", f"IPC_DATABASE_URL={DATABASE_URL}",
        "-e", f"IPC_DEV_INITIAL_PASSWORD={DEV_PASSWORD}",
        PILOT_IMAGE,
    )  # fmt: skip


def _wait_until_ready(name: str) -> None:
    deadline = time.monotonic() + 90
    while True:
        state = docker("inspect", "--format", "{{.State.Status}}", name).strip()
        if state != "running":
            pytest.fail(f"o contêiner do piloto parou:\n{docker('logs', name)}")
        if docker("exec", name, "python", "-c", READY_PROBE, check=False).strip() == "200":
            return
        if time.monotonic() > deadline:
            pytest.fail(f"o piloto não ficou pronto em 90 s:\n{docker('logs', name)}")
        time.sleep(1)


def _cleanup() -> None:
    docker("rm", "--force", CONTAINER, STOP_CONTAINER, PILOT_DB, check=False)
    docker("network", "rm", PILOT_NETWORK, check=False)


def _wait_for_database() -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ready = docker(
            "exec", PILOT_DB, "pg_isready", "-U", "postgres", "-d", "ipchecker", check=False
        )
        if "accepting connections" in ready:
            # O pg_isready responde antes de o initdb terminar e reiniciar o servidor.
            time.sleep(2)
            return
        time.sleep(1)
    pytest.fail(f"o banco do piloto não ficou pronto:\n{docker('logs', PILOT_DB, check=False)}")


READY_PROBE = r"""
import urllib.request
try:
    print(urllib.request.urlopen("http://127.0.0.1:10000/ready", timeout=2).status)
except Exception:
    print(0)
"""


@pytest.fixture(scope="module")
def processes(pilot: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = probe_as("root", PROCESSES_PROBE)
    return [p for p in found if "python -c" not in p["cmdline"]]  # sem a própria sonda


def _by_role(found: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    roles: dict[str, list[dict[str, Any]]] = {
        "supervisord": [],
        "launcher": [],
        "api": [],
        "analyzer": [],
    }
    for process in found:
        if "supervisord" in process["cmdline"]:
            roles["supervisord"].append(process)
        elif "/etc/ipc/run_as.py" in process["cmdline"]:
            roles["launcher"].append(process)  # lançador (root) e guardião de cada serviço
        elif "ipc_api.app" in process["cmdline"]:
            roles["api"].append(process)
        else:
            roles["analyzer"].append(process)  # serviço, forkserver, resource tracker e workers
    return roles


def _soft_limit(lines: list[str], name: str) -> str:
    return next(line[26:].split()[0] for line in lines if line.startswith(name))


# ---------------------------------------------------------------------------------------------


def test_each_process_runs_as_its_own_user(processes: list[dict[str, Any]]) -> None:
    roles = _by_role(processes)

    assert [p["pid"] for p in roles["supervisord"]] == [1]
    assert roles["supervisord"][0]["uid"] == 0
    # S30-10: um lançador root por serviço, filho do supervisord, e um guardião com o usuário do
    # serviço, filho do lançador. Só o supervisord e os lançadores são root.
    launchers = [p for p in roles["launcher"] if p["ppid"] == 1]
    guardians = [p for p in roles["launcher"] if p["ppid"] != 1]
    assert sorted(p["uid"] for p in launchers) == [0, 0]
    assert sorted(p["uid"] for p in guardians) == [API_UID, ANALYZER_UID]
    assert {p["ppid"] for p in guardians} == {p["pid"] for p in launchers}
    assert {p["uid"] for p in roles["api"]} == {API_UID}
    assert len(roles["analyzer"]) >= 4  # serviço, resource tracker, forkserver e o worker
    assert {p["uid"] for p in roles["analyzer"]} == {ANALYZER_UID}


def test_analyzer_environment_has_no_secret(pilot: str, processes: list[dict[str, Any]]) -> None:
    # Lido pelo próprio UID 10002: sem CAP_SYS_PTRACE, nem o root lê o ambiente de outro usuário.
    mine = [p for p in probe_as(ANALYZER_UID, PROCESSES_PROBE) if p["uid"] == ANALYZER_UID]
    analyzer = [p for p in mine if "python -c" not in p["cmdline"]]
    readable = [p for p in analyzer if p["env"] is not None]

    assert len(readable) >= 4  # serviço, resource tracker, forkserver e o worker
    for process in readable:
        assert set(process["env"]) <= ANALYZER_ENV, process["cmdline"]

    # S30-10: o guardião troca de usuário sem executar outro programa, e o kernel o deixa ilegível
    # para os outros processos do mesmo usuário. O ambiente dele é o do lançador (lido pelo root,
    # dono do lançador), que o env -i do supervisord.conf já limpou.
    hidden = [p for p in analyzer if p["env"] is None]
    assert [p["cmdline"].split()[3:5] for p in hidden] == [["/etc/ipc/run_as.py", "ipc-analyzer"]]
    (launcher,) = [p for p in processes if p["pid"] == hidden[0]["ppid"]]
    assert launcher["uid"] == 0
    assert set(launcher["env"]) <= ANALYZER_ENV

    # Prova de que os segredos existem no contêiner e chegam a quem deve: a API.
    (api,) = [
        p
        for p in probe_as(API_UID, PROCESSES_PROBE)
        if "ipc_api.app" in p["cmdline"] and "run_as.py" not in p["cmdline"]
    ]
    assert "IPC_FAKE_SECRET" in api["env"]
    assert "IPC_DATABASE_URL" in api["env"]


def test_workers_are_sandboxed_and_limited(processes: list[dict[str, Any]]) -> None:
    analyzer = _by_role(processes)["analyzer"]
    service = next(p for p in analyzer if "uvicorn" in p["cmdline"])
    forkserver = next(
        p for p in analyzer if p["ppid"] == service["pid"] and "forkserver" in p["cmdline"]
    )
    workers = [p for p in analyzer if p["ppid"] == forkserver["pid"]]

    assert len(workers) == 1  # um worker no plano gratuito (S25-04)
    for worker in workers:
        # Um filtro a mais que o processo que o criou: o seccomp do IP-Checker.
        assert worker["filters"] == service["filters"] + 1
        assert _soft_limit(worker["limits"], "Max address space") == str(160 * MIB)
        assert _soft_limit(worker["limits"], "Max file size") == "0"
        assert _soft_limit(worker["limits"], "Max open files") == "32"
        assert _soft_limit(worker["limits"], "Max processes") == "0"
        assert _soft_limit(worker["limits"], "Max core file size") == "0"
    assert service["filters"] == forkserver["filters"]  # o serviço não é filtrado


def test_analyzer_user_cannot_read_other_environments_or_escape(
    processes: list[dict[str, Any]],
) -> None:
    (api,) = _by_role(processes)["api"]

    results = probe_as(ANALYZER_UID, ESCAPE_PROBE, str(api["pid"]))

    assert results == {
        "environ_api": "EACCES",
        "environ_supervisord": "EACCES",
        "socket": "EPERM",
        "loopback": "EPERM",
        # RLIMIT_NPROC = 0 (S25-04): o fork falha antes mesmo do execve.
        "exec": "EAGAIN",
        "write": "EFBIG",
    }


def test_the_image_has_no_package_installer(pilot: str) -> None:
    # S31-03: sem o pip da imagem base (e as bibliotecas que ele embute, que o Trivy apontava).
    found = probe_as(
        "root",
        "import importlib.util, json, shutil; print(json.dumps([importlib.util.find_spec('pip') "
        "is not None, importlib.util.find_spec('ensurepip._bundled') is not None, "
        "shutil.which('pip'), shutil.which('pip3')]))",
    )

    assert found == [False, False, None, None]


def test_only_the_api_listens_outside_loopback(pilot: str) -> None:
    # Numa rede própria do Docker (a do banco de teste), o resolvedor DNS do Docker escuta em
    # 127.0.0.11 dentro do contêiner; ele é do Docker, não do piloto, e não existe no Render.
    listening: list[str] = probe_as("root", LISTEN_PROBE)
    ours = [address for address in listening if not address.startswith("127.0.0.11:")]

    assert ours == ["0.0.0.0:10000", "127.0.0.1:8001"]


def test_worst_case_inputs_fit_in_160_mib(pilot: str) -> None:
    client = Client(pilot, base="http://127.0.0.1:10000")
    widest = ("a = " + ",".join("bcdefghijklmnopqrstuvwxy") + "\n") * 980
    dense = "a = (b, c, d, e, f, g, h, i, j, k, l, m, n, o, p)\n" * 1_000
    literal = 'x = "' + "a" * 51_180 + '"\n'
    sessions = create_sessions(PILOT_DB, 3)
    requests = [
        {
            "method": "POST",
            "path": "/api/v1/validate",
            "json": {"code": code, "list_number": 1},
            "headers": session_header(sessions[index]),
        }
        for index, code in enumerate([widest, dense, literal])
    ]

    answers = client.send(requests)

    # Nenhuma vira ANALYSIS_LIMIT por falta de memória: todas são analisadas.
    assert [answer.status for answer in answers] == [200, 200, 200]
    # Todas sem if: a Lista 1 também cobra a R-02. O que importa é que foram analisadas.
    assert [answer.body["status"] for answer in answers] == ["invalid"] * 3


def test_pilot_api_cors_headers_and_release(pilot: str) -> None:
    client = Client(pilot, base="http://127.0.0.1:10000")
    (session,) = create_sessions(PILOT_DB, 1)
    preflight, validate, ready, evil = client.send(
        [
            {
                "method": "OPTIONS",
                "path": "/api/v1/validate",
                "headers": {
                    "Origin": SPA,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            },
            {
                "method": "POST",
                "path": "/api/v1/validate",
                "json": {"code": "x = 1\n", "list_number": 1},
                "headers": {"Origin": SPA, **session_header(session)},
            },
            {"method": "GET", "path": "/ready"},
            {
                "method": "POST",
                "path": "/api/v1/validate",
                "json": {"code": "x = 1\n", "list_number": 1},
                "headers": {"Origin": "https://evil.example", **session_header(session)},
            },
        ]
    )

    assert preflight.status == 200
    assert preflight.headers["access-control-allow-origin"] == SPA
    assert validate.headers["access-control-allow-origin"] == SPA
    assert "retry-after" in validate.headers["access-control-expose-headers"].lower()
    assert validate.headers["strict-transport-security"].startswith("max-age=31536000")
    assert validate.headers["x-content-type-options"] == "nosniff"
    assert validate.status == 200
    assert ready.body == {"status": "ready", "ruleset_version": "2026.2.4", "release": RELEASE}
    assert "access-control-allow-origin" not in evil.headers
    assert (evil.status, evil.error_code) == (403, "ORIGIN_MISMATCH")


def test_logs_have_no_secret(pilot: str) -> None:
    logs = docker("logs", pilot) + docker("logs", pilot, check=False)

    assert CANARY_SECRET not in logs
    assert DB_API_PASSWORD not in logs
    assert DEV_PASSWORD not in logs
    assert '"service": "api"' in logs
    assert '"service": "analyzer"' in logs


def _stderr_logs(name: str) -> str:
    executable = shutil.which("docker")
    assert executable is not None
    result = subprocess.run(  # noqa: S603 - argumentos fixos do próprio teste, sem shell
        [executable, "logs", name],
        capture_output=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    )
    return result.stderr


def test_stopping_without_cap_kill_is_clean(pilot: str) -> None:
    # S30-10 (P-17): sem CAP_KILL, o supervisord registrava "CRIT unknown problem killing" com
    # PermissionError e esperava o stopwaitsecs. Agora os dois serviços saem pelo SIGTERM.
    _run_pilot(STOP_CONTAINER)
    try:
        _wait_until_ready(STOP_CONTAINER)
        started = time.monotonic()
        docker("stop", "--time", str(STOP_WAIT_S + 10), STOP_CONTAINER, timeout=60)
        elapsed = time.monotonic() - started
        # O supervisord escreve os próprios avisos (o CRIT) na saída de erro do contêiner.
        logs = docker("logs", STOP_CONTAINER) + _stderr_logs(STOP_CONTAINER)
    finally:
        docker("rm", "--force", STOP_CONTAINER, check=False)

    assert "run_as ipc-api: CAP_KILL ausente" in logs
    assert "CRIT" not in logs
    assert "PermissionError" not in logs
    assert logs.count("Finished server process") == 2, logs  # API e analisador, sem SIGKILL
    assert elapsed < STOP_WAIT_S

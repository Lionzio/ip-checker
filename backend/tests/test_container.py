"""Contêiner endurecido do analyzer (S6-01, NFR-07, US-15).

Sobe ``deploy/compose.yaml`` num projeto próprio, confere a configuração real com ``docker inspect``
e sonda, de dentro do contêiner, o que um processo comprometido conseguiria fazer: cada item do
NFR-07 tem um teste. Precisa de Docker, por isso só roda quando pedido (job ``container`` da CI):

    IPC_CONTAINER_TESTS=1 uv run pytest tests/test_container.py --no-cov

A suíte de ataques contra o endpoint do analyzer (itens 2 a 12 da DoD) entra na Sprint 7.
"""

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from conftest import REPO_ROOT

pytestmark = pytest.mark.skipif(
    os.environ.get("IPC_CONTAINER_TESTS") != "1",
    reason="precisa de Docker; defina IPC_CONTAINER_TESTS=1 para rodar",
)

COMPOSE_FILE = REPO_ROOT / "deploy" / "compose.yaml"
PROJECT = "ipc-isolation-test"
NETWORK = f"{PROJECT}_analyzer_net"
IMAGE = "ip-checker-analyzer:local"
UID = 10001
MIB = 1024 * 1024
#: O único diretório gravável do contêiner (tmpfs em memória), não o /tmp desta máquina.
CONTAINER_TMP = "/tmp"

#: Tudo o que pode existir no ambiente do analyzer. Nenhum nome aqui é segredo: GPG_KEY é a
#: impressão digital pública da chave que assina o Python, PYTHON_SHA256 é o hash do download, e
#: HOSTNAME e HOME são definidas pelo Docker. Qualquer variável nova exige revisão deste teste.
ALLOWED_ENV = frozenset(
    {
        "PATH",
        "GPG_KEY",
        "PYTHON_VERSION",
        "PYTHON_SHA256",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONUNBUFFERED",
        "IPC_RULESET_PATH",
    }
)
DOCKER_RUNTIME_ENV = frozenset({"HOSTNAME", "HOME"})

# ---------------------------------------------------------------------------------------------
# Sondas: programas que rodam dentro do contêiner e respondem em JSON.
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

WRITE_PROBE = r"""
import errno, json, sys
results = {}
for path in sys.argv[1:]:
    try:
        with open(path, "a") as handle:
            handle.write("invadido")
        results[path] = "gravou"
    except OSError as exc:
        results[path] = errno.errorcode.get(exc.errno, str(exc.errno))
print(json.dumps(results))
"""

MOUNTS_PROBE = r"""
import json
mounts = {}
for line in open("/proc/mounts"):
    _, point, _, options, *_ = line.split()
    mounts[point] = options.split(",")
print(json.dumps(mounts))
"""

TMP_EXEC_PROBE = r"""
import errno, json, os, subprocess
script = "/tmp/ipc-sonda.sh"
with open(script, "w") as handle:
    handle.write("#!/bin/sh\necho executou\n")
os.chmod(script, 0o755)
try:
    subprocess.run([script], check=True, capture_output=True)
    result = "executou"
except OSError as exc:
    result = errno.errorcode.get(exc.errno, str(exc.errno))
finally:
    os.remove(script)
print(json.dumps(result))
"""

EGRESS_PROBE = r"""
import json, socket
routes = open("/proc/net/route").read().splitlines()[1:]
result = {"default_route": any(line.split()[1] == "00000000" for line in routes)}
for name, address in {"ip": ("1.1.1.1", 443), "dns": ("example.com", 443)}.items():
    try:
        socket.create_connection(address, timeout=3).close()
        result[name] = "conectou"
    except OSError as exc:
        result[name] = type(exc).__name__
print(json.dumps(result))
"""

#: Cliente HTTP mínimo: ``python -c HTTP_PROBE <url base> <json com [método, caminho, corpo]>``.
HTTP_PROBE = r"""
import json, sys, urllib.error, urllib.request
base, calls = sys.argv[1], json.loads(sys.argv[2])
answers = []
for method, path, body in calls:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        base + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            answers.append([response.status, json.load(response)])
    except urllib.error.HTTPError as error:
        answers.append([error.code, json.load(error)])
print(json.dumps(answers))
"""

IMAGE_FILES_PROBE = r"""
import json, pathlib, shutil
root = pathlib.Path("/opt/ip-checker")
print(json.dumps({
    "app_files": sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()),
    "uv": shutil.which("uv"),
}))
"""


# ---------------------------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------------------------


def docker(*args: str, timeout: float = 60) -> str:
    executable = shutil.which("docker")
    if executable is None:
        pytest.fail("IPC_CONTAINER_TESTS=1, mas o Docker não foi encontrado no PATH")
    result = subprocess.run(  # noqa: S603 - argumentos fixos do próprio teste, sem shell
        [executable, *args],
        capture_output=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"docker {' '.join(args[:3])} falhou ({result.returncode}):\n{result.stderr}")
    return result.stdout


def compose(*args: str, timeout: float = 60) -> str:
    return docker("compose", "-f", str(COMPOSE_FILE), "-p", PROJECT, *args, timeout=timeout)


def probe(container: str, code: str, *args: str) -> Any:
    return json.loads(docker("exec", container, "python", "-c", code, *args))


@pytest.fixture(scope="module")
def container() -> Iterator[str]:
    try:
        compose("up", "--build", "--detach", "--wait", "--wait-timeout", "120", timeout=600)
        yield compose("ps", "--quiet", "analyzer").strip()
    finally:
        compose("down", "--volumes", "--remove-orphans", timeout=120)


@pytest.fixture(scope="module")
def inspected(container: str) -> dict[str, Any]:
    details: dict[str, Any] = json.loads(docker("inspect", container))[0]
    return details


@pytest.fixture(scope="module")
def processes(container: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = probe(container, PROCESSES_PROBE)
    return found


def _soft_limits(lines: list[str]) -> dict[str, str]:
    limits = {}
    for line in lines[1:]:
        match = re.match(r"(Max [a-z ]+?)\s{2,}(\S+)", line)
        if match:
            limits[match.group(1)] = match.group(2)
    return limits


# ---------------------------------------------------------------------------------------------
# NFR-07, item a item
# ---------------------------------------------------------------------------------------------


def test_runs_as_unprivileged_user(
    inspected: dict[str, Any], processes: list[dict[str, Any]]
) -> None:
    assert inspected["Config"]["User"] == f"{UID}:{UID}"
    assert not inspected["HostConfig"]["Privileged"]
    # Real, efetivo, salvo e de sistema de arquivos: nenhum processo tem UID ou GID 0.
    assert processes
    for process in processes:
        assert process["uids"] == [UID] * 4, process["cmdline"]
        assert process["gids"] == [UID] * 4, process["cmdline"]


def test_root_filesystem_is_read_only(inspected: dict[str, Any], container: str) -> None:
    assert inspected["HostConfig"]["ReadonlyRootfs"] is True

    # /var/tmp é gravável por qualquer usuário na imagem: ali, só o read_only impede a escrita.
    new_files = ["/ipc-canario.txt", "/var/tmp/ipc-canario.txt", "/opt/venv/lib/ipc-canario.py"]
    # Arquivos existentes são do root: o UID 10001 já é barrado antes (EACCES).
    existing = ["/opt/ip-checker/rulesets/2026.2/base.yaml", "/etc/passwd"]

    results = probe(container, WRITE_PROBE, *new_files, *existing)

    assert {path: results[path] for path in new_files} == dict.fromkeys(new_files, "EROFS")
    assert {results[path] for path in existing} <= {"EACCES", "EROFS"}


def test_only_memory_areas_are_writable_and_nothing_is_mounted(
    inspected: dict[str, Any], container: str
) -> None:
    host = inspected["HostConfig"]
    assert set(host["Tmpfs"]) == {CONTAINER_TMP}
    assert {"size=16m", "noexec", "nosuid", "nodev"} <= set(host["Tmpfs"][CONTAINER_TMP].split(","))
    assert host["ShmSize"] == 16 * MIB
    # Nenhum volume, bind mount nem segredo do Docker (/run/secrets) chega ao analyzer.
    assert inspected["Mounts"] == []
    assert not host["Binds"]

    mounts = probe(container, MOUNTS_PROBE)
    for writable in (CONTAINER_TMP, "/dev/shm"):
        assert {"rw", "noexec", "nosuid", "nodev"} <= set(mounts[writable]), writable
    assert probe(container, TMP_EXEC_PROBE) == errno.errorcode[errno.EACCES]


def test_all_capabilities_are_dropped(
    inspected: dict[str, Any], processes: list[dict[str, Any]]
) -> None:
    assert inspected["HostConfig"]["CapDrop"] == ["ALL"]
    assert not inspected["HostConfig"]["CapAdd"]
    for process in processes:
        assert set(process["caps"].values()) == {"0" * 16}, process["cmdline"]


def test_privileges_cannot_be_raised(
    inspected: dict[str, Any], processes: list[dict[str, Any]]
) -> None:
    security = inspected["HostConfig"]["SecurityOpt"]
    assert "no-new-privileges:true" in security
    # O perfil seccomp padrão do Docker continua ativo (ameaça 2): nada de seccomp=unconfined.
    assert not any(option.startswith("seccomp") for option in security)
    for process in processes:
        assert process["no_new_privs"] == 1, process["cmdline"]
        assert process["seccomp"] == 2, process["cmdline"]  # 2 = modo filtro


def test_processes_and_memory_are_limited(inspected: dict[str, Any]) -> None:
    host = inspected["HostConfig"]

    assert 0 < host["PidsLimit"] <= 64
    assert 0 < host["Memory"] <= 512 * MIB
    # Swap igual à memória significa nenhum swap: o teto total continua 512 MB.
    assert host["MemorySwap"] == host["Memory"]


def test_only_network_is_internal_and_no_port_is_published(inspected: dict[str, Any]) -> None:
    assert set(inspected["NetworkSettings"]["Networks"]) == {NETWORK}
    assert json.loads(docker("network", "inspect", NETWORK))[0]["Internal"] is True
    assert not inspected["HostConfig"]["PortBindings"]
    assert not any(inspected["NetworkSettings"]["Ports"].values())


def test_there_is_no_route_out(container: str) -> None:
    assert probe(container, EGRESS_PROBE) == {
        "default_route": False,
        "ip": "OSError",  # Network is unreachable: não há gateway
        "dns": "gaierror",  # o DNS da rede interna não resolve nomes externos
    }


def test_environment_has_no_secrets(
    inspected: dict[str, Any], processes: list[dict[str, Any]], container: str
) -> None:
    configured = {item.split("=", 1)[0] for item in inspected["Config"]["Env"]}
    assert configured <= ALLOWED_ENV

    service = next(p for p in processes if "uvicorn" in p["cmdline"] and p["pid"] != 1)
    assert set(service["env"]) <= ALLOWED_ENV | DOCKER_RUNTIME_ENV

    secrets = probe(container, "import json, os; print(json.dumps(os.path.exists('/run/secrets')))")
    assert secrets is False


# ---------------------------------------------------------------------------------------------
# O serviço continua funcionando com todo o endurecimento
# ---------------------------------------------------------------------------------------------


def test_healthcheck_reports_healthy(inspected: dict[str, Any]) -> None:
    assert inspected["Config"]["Healthcheck"]["Test"][0] == "CMD"
    assert inspected["State"]["Health"]["Status"] == "healthy"


def test_workers_run_with_resource_limits(processes: list[dict[str, Any]]) -> None:
    by_pid = {process["pid"]: process for process in processes}
    workers = [
        process
        for process in processes
        if "forkserver" in process["cmdline"]
        and "forkserver" in by_pid.get(process["ppid"], {}).get("cmdline", "")
    ]

    assert len(workers) == 2
    for worker in workers:
        limits = _soft_limits(worker["limits"])
        assert limits["Max address space"] == str(256 * MIB)
        assert limits["Max file size"] == "0"
        assert limits["Max open files"] == "32"


def test_pathological_input_is_contained(container: str) -> None:
    calls = [
        ["POST", "/internal/analyze", {"code": "(" * 1_000 + ")" * 1_000, "list_number": 1}],
        ["GET", "/internal/health", None],
    ]

    (limit_status, limit_body), (health_status, _) = probe(
        container, HTTP_PROBE, "http://127.0.0.1:8001", json.dumps(calls)
    )

    assert (limit_status, limit_body["error"]["code"]) == (422, "ANALYSIS_LIMIT")
    assert health_status == 200


def test_peer_on_internal_network_reaches_the_analyzer(container: str) -> None:
    # Simula a api da Sprint 8: outro contêiner, só na analyzer_net, chama o analyzer pelo nome.
    calls = [
        [
            "POST",
            "/internal/analyze",
            {"code": "for i in range(3):\n    print(i)\n", "list_number": 1},
        ]
    ]
    output = docker(
        "run",
        "--rm",
        "--network",
        NETWORK,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--entrypoint",
        "python",
        IMAGE,
        "-c",
        HTTP_PROBE,
        "http://analyzer:8001",
        json.dumps(calls),
    )

    [[status, body]] = json.loads(output)
    assert status == 200
    assert [v["rule_id"] for v in body["violations"]] == ["R-34", "R-35"]


def test_image_contains_only_runtime_files(container: str) -> None:
    contents = probe(container, IMAGE_FILES_PROBE)

    assert contents["uv"] is None
    assert contents["app_files"]
    assert all(Path(name).parts[0] == "rulesets" for name in contents["app_files"])

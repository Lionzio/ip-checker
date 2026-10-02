"""Isolamento do analyzer em contêiner (S6-01, NFR-07, DoD item 11, US-15).

Confere a configuração real com ``docker inspect`` e sonda, de dentro do contêiner, o que um
processo comprometido conseguiria fazer: cada item do NFR-07 tem um teste. Roda no job
``security`` da CI e localmente com:

    IPC_SECURITY_TESTS=1 uv run pytest tests/security --no-cov
"""

from __future__ import annotations

import errno
import json
import re
from pathlib import Path
from typing import Any

import pytest

from security.harness import NETWORK, UID_GID, Client, docker, probe, processes, requires_docker
from security.harness import workers as find_workers

pytestmark = requires_docker

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

IMAGE_FILES_PROBE = r"""
import json, pathlib, shutil
root = pathlib.Path("/opt/ip-checker")
print(json.dumps({
    "app_files": sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()),
    "uv": shutil.which("uv"),
}))
"""


@pytest.fixture(scope="module")
def inspected(analyzer: str) -> dict[str, Any]:
    details: dict[str, Any] = json.loads(docker("inspect", analyzer))[0]
    return details


@pytest.fixture(scope="module")
def running(analyzer: str) -> list[dict[str, Any]]:
    return processes(analyzer)


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
    inspected: dict[str, Any], running: list[dict[str, Any]]
) -> None:
    assert inspected["Config"]["User"] == f"{UID_GID}:{UID_GID}"
    assert not inspected["HostConfig"]["Privileged"]
    # Real, efetivo, salvo e de sistema de arquivos: nenhum processo tem UID ou GID 0.
    assert running
    for process in running:
        assert process["uids"] == [UID_GID] * 4, process["cmdline"]
        assert process["gids"] == [UID_GID] * 4, process["cmdline"]


def test_root_filesystem_is_read_only(inspected: dict[str, Any], analyzer: str) -> None:
    assert inspected["HostConfig"]["ReadonlyRootfs"] is True

    # /var/tmp é gravável por qualquer usuário na imagem: ali, só o read_only impede a escrita.
    new_files = ["/ipc-canario.txt", "/var/tmp/ipc-canario.txt", "/opt/venv/lib/ipc-canario.py"]
    # Arquivos existentes são do root: o UID 10001 já é barrado antes (EACCES).
    existing = ["/opt/ip-checker/rulesets/2026.2/base.yaml", "/etc/passwd"]

    results = probe(analyzer, WRITE_PROBE, *new_files, *existing)

    assert {path: results[path] for path in new_files} == dict.fromkeys(new_files, "EROFS")
    assert {results[path] for path in existing} <= {"EACCES", "EROFS"}


def test_only_memory_areas_are_writable_and_nothing_is_mounted(
    inspected: dict[str, Any], analyzer: str
) -> None:
    host = inspected["HostConfig"]
    assert set(host["Tmpfs"]) == {CONTAINER_TMP}
    assert {"size=16m", "noexec", "nosuid", "nodev"} <= set(host["Tmpfs"][CONTAINER_TMP].split(","))
    assert host["ShmSize"] == 16 * MIB
    # Nenhum volume, bind mount nem segredo do Docker (/run/secrets) chega ao analyzer.
    assert inspected["Mounts"] == []
    assert not host["Binds"]

    mounts = probe(analyzer, MOUNTS_PROBE)
    for writable in (CONTAINER_TMP, "/dev/shm"):
        assert {"rw", "noexec", "nosuid", "nodev"} <= set(mounts[writable]), writable
    assert probe(analyzer, TMP_EXEC_PROBE) == errno.errorcode[errno.EACCES]


def test_all_capabilities_are_dropped(
    inspected: dict[str, Any], running: list[dict[str, Any]]
) -> None:
    assert inspected["HostConfig"]["CapDrop"] == ["ALL"]
    assert not inspected["HostConfig"]["CapAdd"]
    for process in running:
        assert set(process["caps"].values()) == {"0" * 16}, process["cmdline"]


def test_privileges_cannot_be_raised(
    inspected: dict[str, Any], running: list[dict[str, Any]]
) -> None:
    security = inspected["HostConfig"]["SecurityOpt"]
    assert "no-new-privileges:true" in security
    # O perfil seccomp padrão do Docker continua ativo (ameaça 2): nada de seccomp=unconfined.
    assert not any(option.startswith("seccomp") for option in security)
    for process in running:
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


def test_there_is_no_route_out(analyzer: str) -> None:
    assert probe(analyzer, EGRESS_PROBE) == {
        "default_route": False,
        "ip": "OSError",  # Network is unreachable: não há gateway
        "dns": "gaierror",  # o DNS da rede interna não resolve nomes externos
    }


def test_environment_has_no_secrets(
    inspected: dict[str, Any], running: list[dict[str, Any]], analyzer: str
) -> None:
    configured = {item.split("=", 1)[0] for item in inspected["Config"]["Env"]}
    assert configured <= ALLOWED_ENV

    service = next(p for p in running if "uvicorn" in p["cmdline"] and p["pid"] != 1)
    assert set(service["env"]) <= ALLOWED_ENV | DOCKER_RUNTIME_ENV

    secrets = probe(analyzer, "import json, os; print(json.dumps(os.path.exists('/run/secrets')))")
    assert secrets is False


# ---------------------------------------------------------------------------------------------
# O serviço continua funcionando com todo o endurecimento
# ---------------------------------------------------------------------------------------------


def test_healthcheck_reports_healthy(inspected: dict[str, Any]) -> None:
    assert inspected["Config"]["Healthcheck"]["Test"][0] == "CMD"
    assert inspected["State"]["Health"]["Status"] == "healthy"


def test_workers_run_with_resource_limits(running: list[dict[str, Any]]) -> None:
    workers = find_workers(running)

    assert len(workers) == 2
    for worker in workers:
        limits = _soft_limits(worker["limits"])
        assert limits["Max address space"] == str(256 * MIB)
        assert limits["Max file size"] == "0"
        assert limits["Max open files"] == "32"


def test_peer_on_internal_network_reaches_the_analyzer(client: Client) -> None:
    # O cliente está só na analyzer_net, como a api da Sprint 8, e chama o analyzer pelo nome.
    answer = client.analyze("for i in range(3):\n    print(i)\n", 1)

    assert answer.status == 200
    # Sem if, a Lista 1 também cobra o assunto da lista (R-02).
    assert [v["rule_id"] for v in answer.body["violations"]] == ["R-02", "R-34", "R-35"]


def test_image_contains_only_runtime_files(analyzer: str) -> None:
    contents = probe(analyzer, IMAGE_FILES_PROBE)

    assert contents["uv"] is None
    assert contents["app_files"]
    # Só os dados de que os serviços precisam: o ruleset e, desde a S13-01, as migrações em SQL
    # (usadas apenas pelo serviço migrate). Nenhum teste, gabarito ou código-fonte solto.
    for name in contents["app_files"]:
        parts = Path(name).parts
        assert parts[0] == "rulesets" or (parts[:2] == ("database", "migrations")), name
        if parts[0] == "database":
            assert name.endswith((".up.sql", ".down.sql")), name

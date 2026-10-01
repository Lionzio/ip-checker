"""Infraestrutura da suíte de segurança: Docker, cliente HTTP na rede interna e sondas.

A suíte testa o que vai para produção: o ``deploy/compose.yaml`` real, sem nenhuma porta aberta.
Por isso as requisições partem de um contêiner cliente ligado só à ``analyzer_net``, como a
``api`` fará a partir da Sprint 8. Os pedidos seguem pela entrada padrão, sem limite de tamanho
de linha de comando, e as respostas voltam em JSON com o tempo medido dentro da rede.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "deploy" / "compose.yaml"
PROJECT = "ipc-security-test"
NETWORK = f"{PROJECT}_analyzer_net"
CLIENT = f"{PROJECT}-client"
IMAGE = "ip-checker-backend:local"
ANALYZER_URL = "http://analyzer:8001"
#: UID e GID do usuário do serviço na imagem.
UID_GID = 10001
#: Workers do pool no compose (PoolConfig padrão).
WORKERS = 2

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
    )
    if check and result.returncode != 0:
        pytest.fail(f"docker {' '.join(args[:3])} falhou ({result.returncode}):\n{result.stderr}")
    return result.stdout


def compose(*args: str, timeout: float = 60) -> str:
    return docker("compose", "-f", str(COMPOSE_FILE), "-p", PROJECT, *args, timeout=timeout)


def probe(container: str, code: str, *args: str) -> Any:
    """Roda ``code`` com o Python de dentro do contêiner e devolve o JSON que ele imprimir."""
    return json.loads(docker("exec", container, "python", "-c", code, *args))


def analyzer_logs() -> str:
    return compose("logs", "--no-color", "analyzer")


# ---------------------------------------------------------------------------------------------
# Cliente HTTP (roda no contêiner cliente)
# ---------------------------------------------------------------------------------------------

HTTP_PROBE = r"""
import base64, json, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

job = json.load(sys.stdin)

def call(request):
    if request.get("raw") is not None:
        data = base64.b64decode(request["raw"])
    elif request.get("json") is not None:
        data = json.dumps(request["json"]).encode()
    else:
        data = None
    http = urllib.request.Request(
        job["base"] + request["path"],
        data=data,
        method=request["method"],
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(http, timeout=30) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    elapsed_ms = (time.perf_counter() - start) * 1000
    try:
        body = json.loads(raw)
    except ValueError:
        body = raw.decode("utf-8", "replace")
    return {"status": status, "body": body, "elapsed_ms": elapsed_ms}

with ThreadPoolExecutor(max_workers=job["concurrency"]) as executor:
    print(json.dumps(list(executor.map(call, job["requests"]))))
"""


@dataclass(frozen=True, slots=True)
class Answer:
    status: int
    body: Any
    elapsed_ms: float

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


def raw_request(body: bytes) -> dict[str, Any]:
    return {"method": "POST", "path": "/internal/analyze", "raw": base64.b64encode(body).decode()}


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

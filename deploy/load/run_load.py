"""Teste de carga do piloto com os recursos dos planos do Render (S12-02, com login desde a S28-01).

Sobe um PostgreSQL, aplica as migrações, sobe a imagem do piloto (``deploy/render/Dockerfile``) com
a CPU e a memória de um plano do Render e roda o ``pilot-load.js`` (k6, em contêiner) contra ela,
na mesma rede Docker, entrando com a conta do desenvolvedor. Serve para decidir se o plano
gratuito atende o NFR-01 no pico ou se o backend precisa do Starter (ADR-03). Na raiz do
repositório:

    python deploy/load/run_load.py --plan free
    python deploy/load/run_load.py --plan starter --rate 500 --duration 3m

Os limites por conta e por IP são aumentados só neste contêiner de teste: todo o tráfego sai de
uma conta e de um único IP (o do k6), e o objetivo aqui é medir capacidade, não os limites, que
têm os próprios testes. O banco fica na mesma máquina, então a distância até o banco do piloto
(Q-20) não entra aqui: ela é medida no Render pelo workflow "Carga no piloto".
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ip-checker-pilot:local"
K6_IMAGE = "grafana/k6@sha256:e66db15b860113878fa74670e31f5e274830b7b6e42c8bff28b2f2d86a257603"
#: Mesma imagem do banco do compose (S13-01), fixada por digest.
POSTGRES_IMAGE = (
    "postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
)
NETWORK = "ipc-load"
CONTAINER = "ipc-load-pilot"
DATABASE = "ipc-load-db"
#: A conta do desenvolvedor, criada pela API ao subir (P-14); só existe neste banco de teste.
LOGIN = "carga@cin.ufpe.br"
#: Limites por conta e por IP só deste contêiner: o k6 é uma conta e um IP.
UNLIMITED = "1000000"

#: Recursos dos planos do Render (ADR-03).
PLANS = {"free": ("0.1", "512m"), "starter": ("0.5", "512m")}


def docker(*args: str, check: bool = True, timeout: float = 900) -> str:
    executable = shutil.which("docker")
    if executable is None:
        sys.exit("Docker não encontrado no PATH.")
    result = subprocess.run(  # noqa: S603 - argumentos fixos do próprio script, sem shell
        [executable, *args], capture_output=True, encoding="utf-8", timeout=timeout, check=False
    )
    if check and result.returncode != 0:
        sys.exit(f"docker {' '.join(args[:2])} falhou:\n{result.stderr}")
    return result.stdout


def wait_for(probe: list[str], expected: str, what: str, logs: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if expected in docker(*probe, check=False):
            return
        time.sleep(1)
    sys.exit(f"{what} não ficou pronto:\n{docker('logs', logs, check=False)}")


def start(cpus: str, memory: str, password: str) -> None:
    admin, api = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
    docker(
        "run", "--detach", "--name", DATABASE, "--network", NETWORK,
        "-e", "POSTGRES_DB=ipchecker", "-e", f"POSTGRES_PASSWORD={admin}",
        POSTGRES_IMAGE,
    )  # fmt: skip
    ready = ["exec", DATABASE, "pg_isready", "-U", "postgres", "-d", "ipchecker"]
    wait_for(ready, "accepting connections", "O banco", DATABASE)
    time.sleep(2)  # o pg_isready responde antes de o initdb reiniciar o servidor
    docker(
        "run", "--rm", "--network", NETWORK,
        "-e", f"IPC_DATABASE_ADMIN_URL=postgresql://postgres:{admin}@{DATABASE}:5432/ipchecker",
        "-e", f"IPC_DB_LOGIN_PASSWORD={api}",
        IMAGE, "python", "-m", "ipc_api.db.migrate", "up", "--login-role", "ipc_api",
        timeout=120,
    )  # fmt: skip
    docker(
        "run", "--detach", "--name", CONTAINER, "--network", NETWORK,
        "--cpus", cpus, "--memory", memory, "--memory-swap", memory,
        "-e", f"IPC_DATABASE_URL=postgresql://ipc_api:{api}@{DATABASE}:5432/ipchecker",
        "-e", f"IPC_DEV_EMAILS={LOGIN}",
        "-e", f"IPC_DEV_INITIAL_PASSWORD={password}",
        "-e", f"IPC_RATE_LIMIT_CLIENT_PER_MIN={UNLIMITED}",
        "-e", f"IPC_RATE_LIMIT_IP_PER_MIN={UNLIMITED}",
        "-e", f"IPC_RATE_LIMIT_API_IP_PER_MIN={UNLIMITED}",
        IMAGE,
    )  # fmt: skip
    probe = (
        "import urllib.request;"
        "print(urllib.request.urlopen('http://127.0.0.1:10000/ready', timeout=2).status)"
    )
    wait_for(["exec", CONTAINER, "python", "-c", probe], "200", "O piloto", CONTAINER)


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--plan", choices=sorted(PLANS), default="free")
    parser.add_argument("--rate", type=int, default=500, help="verificações por minuto")
    parser.add_argument("--duration", default="3m")
    parser.add_argument("--no-build", action="store_true", help="usa a imagem já construída")
    args = parser.parse_args()
    cpus, memory = PLANS[args.plan]
    # Uma senha por execução, com maiúscula e caractere especial (FR-23); nunca vai para o disco.
    password = "Carga-" + secrets.token_urlsafe(12) + "!"

    if not args.no_build:
        print("Construindo a imagem do piloto...", flush=True)
        docker("build", "-f", str(ROOT / "deploy/render/Dockerfile"), "-t", IMAGE, str(ROOT))
    cleanup()
    docker("network", "create", NETWORK)
    try:
        start(cpus, memory, password)
        print(f"Plano {args.plan}: {cpus} CPU, {memory}. {args.rate}/min por {args.duration}.")
        k6 = [
            shutil.which("docker") or "docker",
            "run", "--rm", "--network", NETWORK,
            "-v", f"{ROOT / 'deploy/load'}:/scripts:ro",
            "-e", f"BASE_URL=http://{CONTAINER}:10000",
            "-e", f"RATE={args.rate}",
            "-e", f"DURATION={args.duration}",
            "-e", f"LOGIN={LOGIN}",
            "-e", "PASSWORD",
            K6_IMAGE,
            "run", "--quiet", "/scripts/pilot-load.js",
        ]  # fmt: skip
        # A senha vai pelo ambiente do processo, não pela linha de comando. O k6 escreve o resumo
        # no terminal; o código de saída diz se os limites do NFR-01 passaram.
        result = subprocess.run(  # noqa: S603
            k6, encoding="utf-8", check=False, env={**os.environ, "PASSWORD": password}
        )
        outcomes(docker("logs", CONTAINER, check=False))
        return result.returncode
    finally:
        cleanup()


def cleanup() -> None:
    docker("rm", "--force", CONTAINER, DATABASE, check=False)
    docker("network", "rm", NETWORK, check=False)


def outcomes(logs: str) -> None:
    """Resultado de cada verificação, pela linha de log da API (S9-01)."""
    counts: dict[str, int] = {}
    for line in logs.splitlines():
        if not line.startswith("{"):
            continue
        event = json.loads(line)
        if event.get("service") == "api" and event.get("path") == "/api/v1/validate":
            counts[event["outcome"]] = counts.get(event["outcome"], 0) + 1
    print("resultados na API:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    sys.exit(main())

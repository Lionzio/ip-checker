"""Teste de carga do piloto com os recursos dos planos do Render (S12-02).

Sobe a imagem do piloto (``deploy/render/Dockerfile``) com a CPU e a memória de um plano do Render
e roda o ``pilot-load.js`` (k6, em contêiner) contra ela, na mesma rede Docker. Serve para decidir,
antes do primeiro prazo, se o plano gratuito atende o NFR-01 no pico ou se o backend precisa do
Starter (ADR-03). Na raiz do repositório:

    python deploy/load/run_load.py --plan free
    python deploy/load/run_load.py --plan starter --rate 500 --duration 3m

O limite por IP é aumentado só neste contêiner de teste: todo o tráfego sai de um único IP (o do
k6), e o objetivo aqui é medir capacidade, não o limite de taxa, que tem os próprios testes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ip-checker-pilot:local"
K6_IMAGE = "grafana/k6@sha256:e66db15b860113878fa74670e31f5e274830b7b6e42c8bff28b2f2d86a257603"
NETWORK = "ipc-load"
CONTAINER = "ipc-load-pilot"

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


def wait_ready() -> None:
    probe = (
        "import urllib.request;"
        "print(urllib.request.urlopen('http://127.0.0.1:10000/ready', timeout=2).status)"
    )
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if docker("exec", CONTAINER, "python", "-c", probe, check=False).strip() == "200":
            return
        time.sleep(1)
    sys.exit(f"O piloto não ficou pronto:\n{docker('logs', CONTAINER, check=False)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--plan", choices=sorted(PLANS), default="free")
    parser.add_argument("--rate", type=int, default=500, help="verificações por minuto")
    parser.add_argument("--duration", default="3m")
    parser.add_argument("--no-build", action="store_true", help="usa a imagem já construída")
    args = parser.parse_args()
    cpus, memory = PLANS[args.plan]

    if not args.no_build:
        print("Construindo a imagem do piloto...", flush=True)
        docker("build", "-f", str(ROOT / "deploy/render/Dockerfile"), "-t", IMAGE, str(ROOT))
    docker("rm", "--force", CONTAINER, check=False)
    docker("network", "rm", NETWORK, check=False)
    docker("network", "create", NETWORK)
    try:
        docker(
            "run", "--detach", "--name", CONTAINER, "--network", NETWORK,
            "--cpus", cpus, "--memory", memory, "--memory-swap", memory,
            "-e", "IPC_RATE_LIMIT_IP_PER_MIN=1000000",
            IMAGE,
        )  # fmt: skip
        wait_ready()
        print(f"Plano {args.plan}: {cpus} CPU, {memory}. {args.rate}/min por {args.duration}.")
        with tempfile.TemporaryDirectory() as out:
            k6 = [
                shutil.which("docker") or "docker",
                "run", "--rm", "--network", NETWORK,
                "-v", f"{ROOT / 'deploy/load'}:/scripts:ro",
                "-v", f"{out}:/out",
                "-e", f"BASE_URL=http://{CONTAINER}:10000",
                "-e", f"RATE={args.rate}",
                "-e", f"DURATION={args.duration}",
                K6_IMAGE,
                "run", "--quiet", "--summary-export", "/out/summary.json",
                "/scripts/pilot-load.js",
            ]  # fmt: skip
            # O k6 escreve o resumo no terminal; o código de saída diz se os limites passaram.
            result = subprocess.run(k6, encoding="utf-8", check=False)  # noqa: S603
            summary = json.loads((Path(out) / "summary.json").read_text(encoding="utf-8"))
        report(args.plan, summary)
        outcomes(docker("logs", CONTAINER, check=False))
        return result.returncode
    finally:
        docker("rm", "--force", CONTAINER, check=False)
        docker("network", "rm", NETWORK, check=False)


def report(plan: str, summary: dict[str, Any]) -> None:
    metrics: dict[str, Any] = summary["metrics"]
    ok = metrics.get("http_req_duration{expected_response:true}", {})
    failed = metrics.get("http_req_failed", {})
    reqs = metrics.get("http_reqs", {})
    print(f"\n=== Plano {plan} ===")
    print(f"requisições: {reqs.get('count')} ({reqs.get('rate', 0) * 60:.0f}/min)")
    print(f"falhas (não 200): {failed.get('value', 0) * 100:.2f}%")
    for name in ("med", "p(95)", "p(99)", "max"):
        print(f"latência {name}: {ok.get(name, float('nan')):.0f} ms")


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

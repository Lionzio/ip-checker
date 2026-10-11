"""Teste de carga do piloto com os recursos dos planos do Render (S12-02, com login desde a S28-01).

Sobe um PostgreSQL, aplica as migrações, sobe a imagem do piloto (``deploy/render/Dockerfile``) com
a CPU e a memória de um plano do Render e roda o ``pilot-load.js`` (k6, em contêiner) contra ela,
na mesma rede Docker, entrando com a conta do desenvolvedor. Serve para decidir se o plano
gratuito atende o NFR-01 no pico ou se o backend precisa do Starter (ADR-03). Na raiz do
repositório:

    python deploy/load/run_load.py --plan free
    python deploy/load/run_load.py --plan starter --rate 500 --duration 3m
    python deploy/load/run_load.py --plan free --scenario degraus   # S34-01
    python deploy/load/run_load.py --plan free --scenario nfr04     # 500/min por 15 min
    python deploy/load/run_load.py --plan free --scenario nfr05     # 1.500/min

Cenários (S34-03):

- ``vespera`` (padrão): taxa fixa, de um IP; os limites do k6 são os do NFR-01.
- ``degraus`` (S34-01): a mesma carga em degraus (``--rates``), no mesmo contêiner, para achar a
  maior taxa sem nenhuma recusa ``OVERLOADED``.
- ``nfr04``: 500 por minuto por 15 min, com 80% das verificações vindas de 4 IPs do campus (o NAT
  do CIn, P-04) e o resto de IPs externos. Critério: nenhum 5xx e menos de 0,1% sem resposta.
- ``nfr05``: 1.500 por minuto com a mesma mistura e, depois, 90 s a 20 por minuto. Critério: nenhum
  500, 502 ou 504; todo 503 com ``Retry-After`` e em até 1,1 s (quem esperou uma vaga recebe o 503
  em até 1 s, P-11); recuperação em até 60 s.

Todo o tráfego sai de uma conta (a do desenvolvedor), então o limite por conta é aumentado só neste
contêiner de teste. Em ``vespera`` e ``degraus``, o limite por IP também, porque o k6 é um IP só; em
``nfr04`` e ``nfr05``, os limites por IP são os do piloto, e cada verificação traz o IP de origem no
``X-Forwarded-For``, em que o contêiner confia (``IPC_TRUSTED_PROXY_HOPS=1``, só aqui). O banco fica
na mesma máquina, então a distância até o banco do piloto (Q-20) não entra aqui: ela é medida no
Render pelo workflow "Carga no piloto" (ou ``scripts/carga-piloto.sh``).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
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
#: Taxa (por minuto) e duração padrão de cada cenário (S34-03).
SCENARIOS = {
    "vespera": (500, "3m"),
    "degraus": (0, "3m"),
    "nfr04": (500, "15m"),
    "nfr05": (1500, "3m"),
}
#: Os degraus da S34-01, em verificações por minuto.
STEPS = "100,150,200,300,500"
#: Pausa entre degraus, para a fila de admissão esvaziar.
STEP_PAUSE_S = 30
#: Teto do 503 (s): quem esperou uma vaga recebe o 503 em até 1 s (P-11), mais a rede do Docker.
MAX_REFUSAL_MS = 1100
MAX_RECOVERY_S = 60


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


def start(cpus: str, memory: str, password: str, *, real_ip_limits: bool = False) -> None:
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
        *ip_limits(real_ip_limits),
        IMAGE,
    )  # fmt: skip
    probe = (
        "import urllib.request;"
        "print(urllib.request.urlopen('http://127.0.0.1:10000/ready', timeout=2).status)"
    )
    wait_for(["exec", CONTAINER, "python", "-c", probe], "200", "O piloto", CONTAINER)


def ip_limits(real: bool) -> list[str]:
    """Com o NAT simulado, os limites por IP do piloto e 1 proxy confiável; sem ele, sem limite."""
    if real:
        return ["-e", "IPC_TRUSTED_PROXY_HOPS=1"]
    return [
        "-e", f"IPC_RATE_LIMIT_IP_PER_MIN={UNLIMITED}",
        "-e", f"IPC_RATE_LIMIT_API_IP_PER_MIN={UNLIMITED}",
    ]  # fmt: skip


def run_k6(scenario: str, rate: int, duration: str, password: str, out: Path) -> tuple[int, Any]:
    """Roda o pilot-load.js e devolve o código de saída do k6 e o resumo em JSON."""
    name = f"{scenario}-{rate}.json"
    k6 = [
        shutil.which("docker") or "docker",
        "run", "--rm", "--network", NETWORK,
        "-v", f"{ROOT / 'deploy/load'}:/scripts:ro",
        "-v", f"{out}:/out",
        "-e", f"BASE_URL=http://{CONTAINER}:10000",
        "-e", f"SCENARIO={'vespera' if scenario == 'degraus' else scenario}",
        "-e", f"RATE={rate}",
        "-e", f"DURATION={duration}",
        "-e", f"LOGIN={LOGIN}",
        "-e", "PASSWORD",
        "-e", f"SUMMARY=/out/{name}",
        K6_IMAGE,
        "run", "--quiet", "/scripts/pilot-load.js",
    ]  # fmt: skip
    # A senha vai pelo ambiente do processo, não pela linha de comando. O k6 escreve o resumo
    # no terminal; o código de saída diz se os limites do NFR-01 passaram.
    result = subprocess.run(  # noqa: S603
        k6, encoding="utf-8", check=False, env={**os.environ, "PASSWORD": password}
    )
    summary_file = out / name
    summary = json.loads(summary_file.read_text(encoding="utf-8")) if summary_file.exists() else {}
    return result.returncode, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--plan", choices=sorted(PLANS), default="free")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="vespera")
    parser.add_argument("--rate", type=int, help="verificações por minuto (padrão do cenário)")
    parser.add_argument("--duration", help="duração, como 3m (padrão do cenário)")
    parser.add_argument("--rates", default=STEPS, help="degraus por minuto, separados por vírgula")
    parser.add_argument("--no-build", action="store_true", help="usa a imagem já construída")
    args = parser.parse_args()
    cpus, memory = PLANS[args.plan]
    default_rate, default_duration = SCENARIOS[args.scenario]
    duration = args.duration or default_duration
    rates = (
        [int(rate) for rate in args.rates.split(",")]
        if args.scenario == "degraus"
        else [args.rate or default_rate]
    )
    # Uma senha por execução, com maiúscula e caractere especial (FR-23); nunca vai para o disco.
    password = "Carga-" + secrets.token_urlsafe(12) + "!"

    if not args.no_build:
        print("Construindo a imagem do piloto...", flush=True)
        docker("build", "-f", str(ROOT / "deploy/render/Dockerfile"), "-t", IMAGE, str(ROOT))
    cleanup()
    docker("network", "create", NETWORK)
    try:
        start(cpus, memory, password, real_ip_limits=args.scenario in {"nfr04", "nfr05"})
        print(f"Plano {args.plan}: {cpus} CPU, {memory}. Cenário {args.scenario}.", flush=True)
        with tempfile.TemporaryDirectory(prefix="ipc-load-") as folder:
            out = Path(folder)
            results = []
            for index, rate in enumerate(rates):
                if index:
                    time.sleep(STEP_PAUSE_S)
                print(f"\n{rate}/min por {duration}...", flush=True)
                results.append((rate, *run_k6(args.scenario, rate, duration, password, out)))
        outcomes(docker("logs", CONTAINER, check=False))
    finally:
        cleanup()

    if args.scenario == "vespera":
        return results[0][1]
    print()
    plan = f"Plano {args.plan} ({cpus} CPU, {memory})"
    print(f"{plan}, cenário {args.scenario}, {duration} por taxa:")
    if args.scenario == "degraus":
        return report_steps([(rate, summary) for rate, _, summary in results])
    _, _, summary = results[0]
    verdict = check_nfr04(summary) if args.scenario == "nfr04" else check_nfr05(summary)
    for line in verdict:
        print(line)
    return exit_code(verdict)


def exit_code(verdict: list[str]) -> int:
    """1 se algum critério reprovou; 2 se a carga não provou nada; 0 se tudo passou."""
    if any(line.startswith("REPROVADO") for line in verdict):
        return 1
    return 2 if any(line.startswith("INCONCLUSIVO") for line in verdict) else 0


def values(summary: Any, metric: str) -> dict[str, float]:
    return dict(summary.get("metrics", {}).get(metric, {}).get("values", {}))


def count(summary: Any, metric: str) -> int:
    return int(values(summary, metric).get("count", 0))


def statuses(summary: Any) -> dict[str, int]:
    names = ["0", "200", "401", "422", "429", "500", "502", "503", "504", "outro"]
    return {name: count(summary, f"status_{name}") for name in names}


def latency(summary: Any) -> dict[str, float]:
    return values(summary, "http_req_duration{nome:verificar,expected_response:true}")


def _ms(value: float | None) -> str:
    return "?" if value is None else f"{value:.0f} ms"


def report_steps(results: list[tuple[int, Any]]) -> int:
    """Tabela da S34-01: por degrau, o P95 das aceitas e as recusas 503 (``OVERLOADED`` e, sem
    CPU, também ``ANALYZER_UNAVAILABLE`` e ``DATABASE_UNAVAILABLE``)."""
    columns = [
        "Taxa (/min)", "Verificações", "P95 (aceitas)", "P99 (aceitas)",
        "503 (recusas)", "500/502/504", "Sem resposta",
    ]  # fmt: skip
    print("| " + " | ".join(columns) + " |")
    print("|" + "---|" * len(columns))
    best = 0
    clean = True
    failed = False
    for rate, summary in results:
        by_status = statuses(summary)
        total = sum(by_status.values())
        refused = by_status["503"]
        generic = by_status["500"] + by_status["502"] + by_status["504"]
        failed = failed or generic > 0
        share = f"{refused} ({100 * refused / total:.1f}%)" if total else "?"
        times = latency(summary)
        print(
            f"| {rate} | {total} | {_ms(times.get('p(95)'))} | {_ms(times.get('p(99)'))} "
            f"| {share} | {generic} | {by_status['0']} |"
        )
        # A maior taxa sem recusa, desde que nenhum degrau abaixo dela tenha recusado.
        clean = clean and total > 0 and refused == 0
        if clean:
            best = rate
    print()
    print(f"Maior taxa sem nenhuma recusa 503: {best or 'nenhuma'} por minuto.")
    if failed:
        print("REPROVADO: houve 500, 502 ou 504 (o NFR-05 pede degradação só com 503).")
    return 1 if failed else 0


def check_nfr04(summary: Any) -> list[str]:
    by_status = statuses(summary)
    total = sum(by_status.values())
    five = sum(by_status[code] for code in ("500", "502", "503", "504"))
    lost = by_status["0"] + by_status["outro"]
    times = latency(summary)
    lines = [
        f"Verificações: {total}; por status: "
        + ", ".join(f"{k}={v}" for k, v in by_status.items() if v),
        f"Aceitas: P50 {_ms(times.get('med'))} · P95 {_ms(times.get('p(95)'))} · "
        f"P99 {_ms(times.get('p(99)'))}",
    ]
    if total == 0:
        return [*lines, "REPROVADO: nenhuma verificação foi feita."]
    lines.append(
        ("OK" if five == 0 else "REPROVADO")
        + f": 5xx = {five} ({100 * five / total:.2f}%; meta 0%, das quais 503 = {by_status['503']})"
    )
    lines.append(
        ("OK" if lost / total < 0.001 else "REPROVADO")
        + f": sem resposta = {lost} ({100 * lost / total:.3f}%; meta < 0,1%)"
    )
    lines.append(
        ("OK" if by_status["429"] == 0 else "REPROVADO")
        + f": 429 = {by_status['429']} (o NAT do campus não pode esbarrar no limite por IP)"
    )
    return lines


def check_nfr05(summary: Any) -> list[str]:
    by_status = statuses(summary)
    total = sum(by_status.values())
    generic = by_status["500"] + by_status["502"] + by_status["504"]
    refused = values(summary, "recusa_ms")
    missing = count(summary, "recusa_sem_retry_after")
    recovery = values(summary, "recuperacao_erro_s")
    recovered_in = recovery.get("max", 0.0)
    lines = [
        f"Verificações na sobrecarga: {total}; por status: "
        + ", ".join(f"{k}={v}" for k, v in by_status.items() if v),
        f"503: {int(refused.get('count', 0)) or by_status['503']}; P50 {_ms(refused.get('med'))} · "
        f"P95 {_ms(refused.get('p(95)'))} · máx. {_ms(refused.get('max'))} "
        "(≤ 100 ms com a fila cheia; ≤ 1 s para quem esperou uma vaga)",
        ("OK" if generic == 0 else "REPROVADO") + f": 500/502/504 = {generic} (meta 0)",
        ("OK" if by_status["503"] > 0 else "INCONCLUSIVO")
        + f": a carga gerou {by_status['503']} recusas 503 (sem recusa, não houve sobrecarga; "
        "aumente o --rate)",
        ("OK" if missing == 0 else "REPROVADO") + f": 503 sem Retry-After = {missing}",
        ("OK" if refused.get("max", 0) <= MAX_REFUSAL_MS else "REPROVADO")
        + f": o 503 mais lento levou {_ms(refused.get('max'))} (teto {MAX_REFUSAL_MS} ms)",
        ("OK" if recovered_in <= MAX_RECOVERY_S else "REPROVADO")
        + f": recuperação em {recovered_in:.1f} s depois da sobrecarga "
        f"({count(summary, 'recuperacao_verificacoes')} verificações; meta ≤ {MAX_RECOVERY_S} s)",
    ]
    return lines


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

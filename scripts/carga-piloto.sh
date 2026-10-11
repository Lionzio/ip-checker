#!/usr/bin/env bash
# Carga no piloto a partir desta máquina (S34-04, P-19): o mesmo do workflow "Carga no piloto"
# (.github/workflows/load.yml), para quando o GitHub Actions estiver sem cota. Serve para medir a
# latência com o banco a distância e para o exercício de alerta de cada release (runbook,
# "Registro dos exercícios de alerta").
#
# Uso, no Git Bash, na raiz do repositório (Docker Desktop aberto):
#
#   scripts/carga-piloto.sh            # 20 verificações por minuto por 5 minutos
#   scripts/carga-piloto.sh 20 10m     # taxa (1 a 25 por minuto) e duração (até 10m)
#
# Pede o login e a senha da conta de verificação do deploy, a senha sem mostrá-la, ou os lê de
# PILOT_LOGIN e PILOT_PASSWORD; nada é salvo. A taxa fica abaixo do limite de 30 verificações por
# minuto da conta (P-11 h), e todo o tráfego sai do IP desta máquina.
set -euo pipefail

K6_IMAGE="grafana/k6@sha256:e66db15b860113878fa74670e31f5e274830b7b6e42c8bff28b2f2d86a257603"
rate=${1:-20}
duration=${2:-5m}

if ! [[ "$rate" =~ ^[0-9]+$ ]] || [ "$rate" -lt 1 ] || [ "$rate" -gt 25 ]; then
  echo "carga-piloto: a taxa precisa ser de 1 a 25 por minuto (recebido: $rate)" >&2
  exit 2
fi
if ! [[ "$duration" =~ ^([0-9]+)([sm])$ ]]; then
  echo "carga-piloto: use a duração como 90s ou 5m (recebido: $duration)" >&2
  exit 2
fi
seconds=${BASH_REMATCH[1]}
[ "${BASH_REMATCH[2]}" = "m" ] && seconds=$((seconds * 60))
[ "$seconds" -le 600 ] || { echo "carga-piloto: a duração máxima é 10 minutos" >&2; exit 2; }

command -v docker > /dev/null || { echo "carga-piloto: o Docker Desktop precisa estar aberto" >&2; exit 2; }
root=$(git rev-parse --show-toplevel)
repo=Lionzio/ip-checker
api=${PILOT_API_URL:-$(gh variable get PILOT_API_URL --repo "$repo" 2>/dev/null || true)}
web=${PILOT_WEB_URL:-$(gh variable get PILOT_WEB_URL --repo "$repo" 2>/dev/null || true)}
[[ "$api" =~ ^https:// && "$web" =~ ^https:// ]] || {
  echo "carga-piloto: defina PILOT_API_URL e PILOT_WEB_URL (https://...)" >&2
  exit 2
}

if [ -z "${PILOT_LOGIN:-}" ]; then
  read -rp "Login da conta de verificação: " PILOT_LOGIN
fi
if [ -z "${PILOT_PASSWORD:-}" ]; then
  read -rsp "Senha da conta de verificação (não aparece na tela): " PILOT_PASSWORD
  echo
fi
export LOGIN=$PILOT_LOGIN PASSWORD=$PILOT_PASSWORD BASE_URL=$web RATE=$rate DURATION=$duration

echo "Acordando a API..."
for _ in $(seq 1 30); do
  curl -fsS --max-time 20 "$api/ready" -o /dev/null && break
  sleep 10
done

echo "Carga de $rate por minuto por $duration, pela página ($web), desde $(date -u +%H:%M:%S) UTC..."
scripts=$(cd "$root/deploy/load" && pwd -W 2>/dev/null || pwd)
MSYS_NO_PATHCONV=1 docker run --rm -v "$scripts:/scripts:ro" \
  -e BASE_URL -e RATE -e DURATION -e LOGIN -e PASSWORD \
  "$K6_IMAGE" run --quiet --no-thresholds /scripts/pilot-load.js
unset LOGIN PASSWORD PILOT_PASSWORD

echo "Fim às $(date -u +%H:%M:%S) UTC. Medido no servidor (/health/slo, últimos 5 minutos; NFR-01: P95 <= 200 ms):"
curl -fsS --max-time 20 "$api/health/slo" || echo "(o /health/slo não respondeu)"
echo

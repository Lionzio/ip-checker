#!/usr/bin/env bash
# Cronômetro do rollback do piloto (S30-08; docs/runbook.md, "Voltar para a versão anterior").
#
# Rode ANTES de clicar em Rollback no Render: o script marca o início, consulta o /ready da API e o
# /version.json da página a cada 5 s e para quando os dois mostram o commit esperado, com o tempo
# total. Depois, anote o resultado no registro dos ensaios do runbook.
#
# Uso, no Git Bash, na raiz do repositório:
#
#   scripts/rollback-check.sh <commit>          # o commit para o qual os dois devem voltar
#   scripts/rollback-check.sh 715cd16           # um prefixo do commit basta
#
# Os endereços vêm das variáveis do GitHub (PILOT_API_URL e PILOT_WEB_URL), lidas com o gh, ou do
# ambiente, se já estiverem definidos. Nenhum segredo é usado.
set -euo pipefail

[ $# -eq 1 ] || { echo "uso: scripts/rollback-check.sh <commit>" >&2; exit 2; }
expected=$1
[[ "$expected" =~ ^[0-9a-f]{7,40}$ ]] || { echo "rollback-check: commit inválido: $expected" >&2; exit 2; }

repo=${GITHUB_REPOSITORY:-Lionzio/ip-checker}
api=${PILOT_API_URL:-$(gh variable get PILOT_API_URL --repo "$repo")}
web=${PILOT_WEB_URL:-$(gh variable get PILOT_WEB_URL --repo "$repo")}

release_of() {
  curl -fsS --max-time 10 "$1" 2>/dev/null \
    | python -c "import json, sys; print(json.load(sys.stdin).get('release') or '')" 2>/dev/null \
    || true
}

start=$SECONDS
echo "Início: $(date -u +%H:%M:%S) UTC. Faça agora o Rollback no Render e o Instant Rollback na Vercel."
api_at="" web_at=""
while [ $((SECONDS - start)) -lt 1800 ]; do
  now=$((SECONDS - start))
  api_release=$(release_of "$api/ready")
  web_release=$(release_of "$web/version.json")
  if [ -z "$api_at" ] && [[ "$api_release" == "$expected"* ]]; then
    api_at=$now
    echo "API (Render) no commit esperado em ${api_at} s."
  fi
  if [ -z "$web_at" ] && [[ "$web_release" == "$expected"* ]]; then
    web_at=$now
    echo "Página (Vercel) no commit esperado em ${web_at} s."
  fi
  if [ -n "$api_at" ] && [ -n "$web_at" ]; then
    total=$(( api_at > web_at ? api_at : web_at ))
    printf 'Total até o passo 3: %d min %02d s (meta da DoD: até 5 min).\n' $((total / 60)) $((total % 60))
    exit 0
  fi
  printf '%4d s  API: %.7s  página: %.7s\n' "$now" "${api_release:-?}" "${web_release:-?}"
  sleep 5
done
echo "rollback-check: os dois não chegaram ao commit $expected em 30 minutos." >&2
exit 1

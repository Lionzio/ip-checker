#!/usr/bin/env bash
# A CI nesta máquina (P-19): os mesmos passos do ci.yml, para quando o GitHub Actions estiver sem
# cota (2.000 minutos por mês em repositório privado) ou para conferir antes de abrir o PR.
#
# Uso, no Git Bash, na raiz do repositório (Docker Desktop aberto):
#
#   scripts/ci-local.sh            # backend, gabaritos, segurança e frontend
#   scripts/ci-local.sh --e2e      # também o smoke e2e (compose separado + Playwright)
#   scripts/ci-local.sh --rapido   # sem a segurança e sem o e2e (só para iterar)
#
# No fim, imprime um resumo em Markdown para colar no PR. O banco de teste, o compose do e2e e as
# senhas sorteadas são descartados ao sair; o ambiente de desenvolvimento (deploy/.env, porta 8180)
# não é tocado.
set -uo pipefail

e2e=false
security=true
for arg in "$@"; do
  case "$arg" in
    --e2e) e2e=true ;;
    --rapido) security=false; e2e=false ;;
    *) echo "uso: scripts/ci-local.sh [--e2e | --rapido]" >&2; exit 2 ;;
  esac
done

root=$(git rev-parse --show-toplevel)
cd "$root"
sha=$(git rev-parse --short HEAD)
dirty=$([ -n "$(git status --porcelain)" ] && echo " (com mudanças não commitadas)" || echo "")

uv=$(command -v uv || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe 2>/dev/null | head -1)
[ -n "$uv" ] || { echo "ci-local: instale o uv (winget install astral-sh.uv)" >&2; exit 2; }
command -v docker > /dev/null || { echo "ci-local: o Docker Desktop precisa estar aberto" >&2; exit 2; }

results=()
failed=0
step() {
  local name=$1
  shift
  local start=$SECONDS
  echo
  echo "=== $name"
  if "$@"; then
    results+=("| $name | ok | $((SECONDS - start)) s |")
  else
    results+=("| $name | **falhou** | $((SECONDS - start)) s |")
    failed=1
  fi
}

pg=ipc-ci-local-pg
compose_project=ipc-ci-local
cleanup() {
  docker rm -f "$pg" > /dev/null 2>&1 || true
  if [ -n "${e2e_env:-}" ]; then
    docker compose -p "$compose_project" -f deploy/compose.yaml --env-file "$e2e_env" down -v \
      > /dev/null 2>&1 || true
    rm -f "$e2e_env"
  fi
}
trap cleanup EXIT

# --- Backend --------------------------------------------------------------------------------
pg_password=$(python -c "import secrets; print(secrets.token_urlsafe(18))")
docker rm -f "$pg" > /dev/null 2>&1 || true
docker run -d --name "$pg" -e POSTGRES_DB=ipc_test -e POSTGRES_PASSWORD="$pg_password" \
  -p 127.0.0.1::5432 postgres:17-alpine > /dev/null
pg_port=$(docker port "$pg" 5432/tcp | head -1 | sed 's/.*://')
for _ in $(seq 1 60); do
  docker exec "$pg" pg_isready -U postgres -d ipc_test > /dev/null 2>&1 && break
  sleep 1
done
sleep 2

backend() { (cd backend && "$uv" "$@"); }
step "Backend: dependências" backend sync --locked
step "Backend: ruff" backend run ruff check .
step "Backend: formatação" backend run ruff format --check .
step "Backend: mypy" backend run mypy
step "Backend: fronteiras" backend run lint-imports
step "Ruleset e golden" backend run ipc-rules validate ../rulesets/2026.2 --golden tests/golden
step "Backend: pytest (cobertura >= 90%)" env \
  IPC_TEST_DATABASE_URL="postgresql://postgres:$pg_password@127.0.0.1:$pg_port/ipc_test" \
  bash -c "cd backend && '$uv' run pytest -q -p no:cacheprovider"

if [ -d ../ip-checker-gabaritos ]; then
  step "Gabaritos (zero violação)" env IPC_GABARITOS_DIR=../../ip-checker-gabaritos \
    bash -c "cd backend && '$uv' run pytest tests/official_answers --no-cov -q -p no:cacheprovider"
else
  results+=("| Gabaritos (zero violação) | pulado: clone o ip-checker-gabaritos ao lado | — |")
fi

if $security; then
  step "Segurança (isolamento e imagem do piloto)" env IPC_SECURITY_TESTS=1 \
    bash -c "cd backend && '$uv' run pytest tests/security --no-cov -q -p no:cacheprovider"
else
  results+=("| Segurança | pulada (--rapido) | — |")
fi

# --- Frontend -------------------------------------------------------------------------------
frontend() { (cd frontend && "$@"); }
step "Frontend: dependências" frontend npm ci --no-audit --no-fund
step "Frontend: tipos do OpenAPI em dia" bash -c \
  "cd frontend && npm run -s gen:api && git diff --exit-code -- src/types/openapi.ts"
step "Frontend: ESLint" frontend npm run -s lint
step "Frontend: TypeScript" frontend npm run -s typecheck
step "Frontend: Vitest" frontend npm test --silent
step "Frontend: build" frontend npm run -s build
step "Frontend: build do piloto" env IPC_API_ORIGIN=https://ip-checker-api.onrender.com \
  bash -c "cd frontend && npm run -s build:vercel && rm -rf .vercel"

# --- e2e (opcional) -------------------------------------------------------------------------
if $e2e; then
  e2e_env=$(mktemp)
  dev_password="Dev-$(python -c 'import secrets; print(secrets.token_urlsafe(12))')!"
  {
    echo "IPC_DB_ADMIN_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
    echo "IPC_DB_API_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
    echo "IPC_DEV_INITIAL_PASSWORD=$dev_password"
    echo "IPC_LLM_PROVIDER=fake"
    echo "IPC_HTTP_PORT=28280"
    echo "IPC_MAIL_UI_PORT=28225"
  } > "$e2e_env"
  step "e2e: subir o compose (porta 28280)" docker compose -p "$compose_project" \
    -f deploy/compose.yaml --env-file "$e2e_env" up --build -d --wait --wait-timeout 300
  step "e2e: Playwright" env E2E_BASE_URL=http://127.0.0.1:28280 \
    E2E_MAILPIT_URL=http://127.0.0.1:28225 E2E_PASSWORD="$dev_password" \
    bash -c "cd frontend && npx playwright install chromium > /dev/null && npm run -s e2e"
else
  results+=("| Smoke e2e | pulado (use --e2e) | — |")
fi

echo
echo "----- resumo para o PR -----"
echo "**CI local** (\`scripts/ci-local.sh\`, P-19) em \`$sha\`$dirty, $(date '+%d/%m/%Y %H:%M'):"
echo
echo "| Passo | Resultado | Tempo |"
echo "|---|---|---|"
printf '%s\n' "${results[@]}"
exit "$failed"

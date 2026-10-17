#!/usr/bin/env bash
# A CI nesta máquina (P-19): os mesmos passos do ci.yml, para quando o GitHub Actions estiver sem
# cota (2.000 minutos por mês em repositório privado) ou para conferir antes de abrir o PR.
#
# Uso, no Git Bash, na raiz do repositório (Docker Desktop aberto):
#
#   scripts/ci-local.sh            # backend, gabaritos, segurança, auditoria e frontend
#   scripts/ci-local.sh --e2e      # também o smoke e2e (compose separado + Playwright)
#   scripts/ci-local.sh --rapido   # sem a segurança, a auditoria e o e2e (só para iterar)
#   scripts/ci-local.sh --completo # roda todos os passos, mesmo os sem mudança (com --e2e)
#
# Desde a S49 (ADR-20), a rodada é incremental e em faixas:
#
# - Cada passo declara as entradas de que depende. O scripts/ci-passos.py calcula a impressão
#   digital delas (o blob de cada arquivo rastreado ou não ignorado) e guarda os verdes em
#   .git/ci-local-passos.json. Um passo cujas entradas não mudaram desde um verde é pulado, e o
#   resumo diz "pulado: igual ao verde de <sha>". --completo força tudo.
# - Três faixas rodam em paralelo: A (lint, tipos e pytest do backend), B (as auditorias) e C (o
#   frontend). Depois, a faixa silenciosa, sozinha na máquina: benchmark, testes de tempo,
#   Lighthouse e segurança, que medem tempo ou memória. Por fim, o e2e.
# - O Semgrep varre só os arquivos alterados desde o último verde (as regras são de arquivo único),
#   sobre uma cópia dentro do contêiner, e não sobre a pasta montada (lenta no Docker do Windows);
#   pip-audit e npm audit só rodam com lock novo ou verde com mais de 7 dias; o gitleaks varre do
#   último commit auditado em diante. Com --completo, tudo é varrido.
#
# No fim, imprime um resumo em Markdown para colar no PR. Uma rodada com --e2e, sem nenhuma falha e
# sem mudanças não commitadas, fica registrada pela árvore do commit em .git/ci-local-verde: é a
# evidência que o scripts/release.sh --ci-local aceita (P-19); ele também aceita a cobertura por
# passos (todos com verde para as entradas atuais). O banco de teste, o compose do e2e e as senhas
# sorteadas são descartados ao sair; o ambiente de desenvolvimento (deploy/.env, porta 8180) não
# é tocado.
set -uo pipefail

e2e=false
security=true
completo=false
for arg in "$@"; do
  case "$arg" in
    --e2e) e2e=true ;;
    --rapido) security=false; e2e=false ;;
    --completo) completo=true ;;
    *) echo "uso: scripts/ci-local.sh [--e2e | --rapido] [--completo]" >&2; exit 2 ;;
  esac
done

root=$(git rev-parse --show-toplevel)
cd "$root"
sha=$(git rev-parse --short HEAD)
dirty=$([ -n "$(git status --porcelain)" ] && echo " (com mudanças não commitadas)" || echo "")

uv=$(command -v uv || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe 2>/dev/null | head -1)
[ -n "$uv" ] || { echo "ci-local: instale o uv (winget install astral-sh.uv)" >&2; exit 2; }
command -v docker > /dev/null || { echo "ci-local: o Docker Desktop precisa estar aberto" >&2; exit 2; }
passos="python scripts/ci-passos.py"
# As entradas dos passos usam pathspecs do Git ("*.md", ":!docs"): o bash não deve expandi-las.
set -f

# --- Passos com impressão digital (S49-01) ----------------------------------------------------
# Todo passo depende também do próprio script da CI e do ci-passos.py.
common="scripts/ci-local.sh scripts/ci-passos.py"
# Os vetores do hash do enunciado (S50-05) são lidos pelo pytest e pelo Vitest.
in_backend="backend rulesets extensao/test/vetores-hash.json"
in_frontend="frontend docs/openapi.json"
# A extensão do Dikastis (S50-01); o teste do manifesto confere o ID no settings.py da API.
in_extensao="extensao backend/src/ipc_api/settings.py"
in_engine="backend/src/ipc_analyzer/engine backend/tests/benchmark backend/pyproject.toml backend/uv.lock rulesets"
in_security="backend deploy rulesets"
in_docs="docs *.md backend/tests/test_docs_links.py"
in_semgrep=". :!.semgrep :!frontend/src/types/openapi.ts :!docs :!*.md"
in_e2e=". :!docs :!*.md :!extensao"
if [ -d ../ip-checker-gabaritos ]; then in_gabaritos="$in_backend ../ip-checker-gabaritos"; else in_gabaritos=""; fi

results=()
failed=0
skipped=0
step() {
  local name=$1
  shift
  local start=$SECONDS
  echo
  echo "=== $name"
  if "$@"; then
    results+=("| $name | ok | $((SECONDS - start)) s |")
    return 0
  fi
  results+=("| $name | **falhou** | $((SECONDS - start)) s |")
  failed=1
  return 1
}
# step_fp NOME "ENTRADAS" [--max-age-days N] COMANDO...: pula o passo quando as entradas não mudaram
# desde um verde registrado; grava o verde quando o passo passa.
step_fp() {
  local name=$1 inputs=$2
  shift 2
  local age=()
  if [ "${1:-}" = "--max-age-days" ]; then age=(--max-age-days "$2"); shift 2; fi
  local digest green
  # shellcheck disable=SC2086
  digest=$($passos hash -- $inputs $common) || { echo "ci-local: ci-passos.py falhou em $name" >&2; failed=1; return 1; }
  if ! $completo && green=$($passos check "$name" "$digest" "${age[@]}"); then
    echo
    echo "=== $name: pulado, igual ao verde de $green"
    results+=("| $name | pulado: igual ao verde de \`${green%% *}\` | — |")
    skipped=$((skipped + 1))
    return 0
  fi
  if step "$name" "$@"; then
    # shellcheck disable=SC2086
    $passos record "$name" "$digest" "$sha$dirty" -- $inputs $common
    return 0
  fi
  return 1
}

pg=ipc-ci-local-pg
compose_project=ipc-ci-local
lane_dir=$(mktemp -d)
cleanup() {
  docker rm -f "$pg" > /dev/null 2>&1 || true
  if [ -n "${e2e_env:-}" ]; then
    docker compose -p "$compose_project" -f deploy/compose.yaml --env-file "$e2e_env" down -v \
      > /dev/null 2>&1 || true
    rm -f "$e2e_env"
  fi
  rm -rf "$lane_dir"
}
trap cleanup EXIT

backend() { (cd backend && "$uv" "$@"); }
frontend() { (cd frontend && "$@"); }
extensao() { (cd extensao && "$@"); }

# --- Faixas em paralelo (S49-02) --------------------------------------------------------------
# Cada faixa roda num subshell com o próprio log e os próprios resultados; o texto é mostrado em
# ordem quando as três terminam. O banco do pytest sobe antes, só para a faixa A.
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

lane_a() {
  step "Backend: dependências" backend sync --locked
  step_fp "Backend: ruff" "$in_backend" backend run ruff check .
  step_fp "Backend: formatação" "$in_backend" backend run ruff format --check .
  step_fp "Backend: mypy" "$in_backend" backend run mypy
  step_fp "Backend: fronteiras" "$in_backend" backend run lint-imports
  step_fp "Ruleset e golden" "$in_backend" backend run ipc-rules validate ../rulesets --golden tests/golden
  # S39-03 e S49-02: o pytest em três etapas. Em paralelo (4 processos), tudo que não usa o banco
  # nem mede o relógio; em série, os testes do PostgreSQL (que recriam o esquema no mesmo banco);
  # os de tempo (marcador timing) ficam para a faixa silenciosa, com a soma da cobertura.
  step_fp "Backend: pytest em paralelo (sem banco e sem tempo)" "$in_backend" \
    bash -c "cd backend && '$uv' run pytest -q -p no:cacheprovider -n 4 -m 'not db and not timing' --cov-fail-under=0"
  step_fp "Backend: pytest em série (banco)" "$in_backend" env \
    IPC_TEST_DATABASE_URL="postgresql://postgres:$pg_password@127.0.0.1:$pg_port/ipc_test" \
    bash -c "cd backend && '$uv' run pytest -q -p no:cacheprovider -m db --cov-append --cov-fail-under=0"
  step_fp "Documentação: links" "$in_docs" \
    bash -c "cd backend && '$uv' run pytest -q -p no:cacheprovider --no-cov tests/test_docs_links.py"
  if [ -n "$in_gabaritos" ]; then
    step_fp "Gabaritos (zero violação)" "$in_gabaritos" env IPC_GABARITOS_DIR=../../ip-checker-gabaritos \
      bash -c "cd backend && '$uv' run pytest tests/official_answers --no-cov -q -p no:cacheprovider"
  else
    results+=("| Gabaritos (zero violação) | pulado: clone o ip-checker-gabaritos ao lado | — |")
  fi
}

lane_b() {
  if ! $security; then
    results+=("| Auditoria | pulada (--rapido) | — |")
    return
  fi
  local repo_mount history_mount history_clone="" log_opts=() last
  repo_mount=$(pwd -W 2>/dev/null || pwd)
  history_mount=$repo_mount
  if [ -f .git ]; then
    # Numa worktree, o .git aponta para fora da pasta montada: o gitleaks lê um clone local.
    history_clone=$(mktemp -d)
    git clone -q --no-local --branch "$(git branch --show-current)" . "$history_clone"
    history_mount=$(cd "$history_clone" && (pwd -W 2>/dev/null || pwd))
  fi
  # S49-03: do último commit auditado em diante, quando ele é ancestral do HEAD; já auditado até o
  # HEAD, nada a fazer; senão (histórico reescrito ou sem registro), tudo.
  last=$($passos check "Auditoria: gitleaks (último commit)" sempre 2>/dev/null | cut -d' ' -f1)
  if ! $completo && [ -n "$last" ] && [ "$(git rev-parse "$last" 2>/dev/null)" = "$(git rev-parse HEAD)" ]; then
    echo
    echo "=== Auditoria: segredos no histórico (gitleaks): pulado, já auditado até $last"
    results+=("| Auditoria: segredos no histórico (gitleaks) | pulado: já auditado até \`$last\` | — |")
    skipped=$((skipped + 1))
  else
    if ! $completo && [ -n "$last" ] && git merge-base --is-ancestor "$last" HEAD 2>/dev/null; then
      log_opts=(--log-opts="$last..HEAD")
      echo "gitleaks: do commit $last em diante"
    fi
    if step "Auditoria: segredos no histórico (gitleaks)" env MSYS_NO_PATHCONV=1 docker run --rm \
        -v "$history_mount:/repo:ro" \
        zricethezav/gitleaks@sha256:cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854 \
        git /repo --redact --no-banner --log-level warn --exit-code 1 \
        --gitleaks-ignore-path /repo/.gitleaksignore "${log_opts[@]}"; then
      $passos record "Auditoria: gitleaks (último commit)" sempre "$(git rev-parse HEAD)" -- .gitleaksignore
    fi
  fi
  step_fp "Auditoria: Semgrep (testes das regras)" ".semgrep" env MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$repo_mount:/src:ro" -w /src \
    semgrep/semgrep@sha256:32e459968daabe7ab86968184a29109b9564aa00392401156f9788452b42786b \
    semgrep --test --metrics=off --disable-version-check .semgrep/
  # S49-03: só os arquivos alterados desde o último verde (regras de arquivo único); com
  # --completo, sem registro ou com mais de 200 arquivos, a varredura inteira.
  local targets=(.) changed_files
  # shellcheck disable=SC2086
  changed_files=$($passos changed "Auditoria: Semgrep (varredura)" -- $in_semgrep $common .semgrep/ip-checker.yml)
  if ! $completo && [ "$changed_files" = "." ]; then
    echo
    echo "=== Auditoria: Semgrep (varredura): pulado, nenhum arquivo mudou desde o último verde"
    results+=("| Auditoria: Semgrep (varredura) | pulado: nenhum arquivo mudou desde o último verde | — |")
    skipped=$((skipped + 1))
  else
    if ! $completo && [ "$(printf '%s\n' "$changed_files" | wc -l)" -le 200 ] \
       && ! printf '%s\n' "$changed_files" | grep -q '^\.semgrep/ip-checker\.yml$'; then
      mapfile -t targets <<< "$changed_files"
      echo "semgrep: ${#targets[@]} arquivo(s) alterado(s) desde o último verde"
    fi
    # A varredura roda sobre uma cópia dos arquivos dentro do contêiner (um tar pelo git), e não
    # sobre a pasta montada: no Docker do Windows, ler centenas de arquivos pelo bind mount leva
    # minutos (225 s na medida de 16/10/2026); pelo tar, 4 s.
    semgrep_scan() {
      local list status
      list=$(mktemp)
      if [ "${targets[0]}" = "." ]; then
        # shellcheck disable=SC2086
        git ls-files -z --cached --others --exclude-standard -- $in_semgrep > "$list"
      else
        printf '%s\0' "${targets[@]}" > "$list"
      fi
      printf '%s\0' .semgrepignore .semgrep/ip-checker.yml >> "$list"
      tar --null -T "$list" -cf - | env MSYS_NO_PATHCONV=1 docker run --rm -i -w /src \
        semgrep/semgrep@sha256:32e459968daabe7ab86968184a29109b9564aa00392401156f9788452b42786b \
        sh -c 'tar -xf - && semgrep scan --config .semgrep/ip-checker.yml --error --metrics=off --disable-version-check --quiet .'
      status=$?
      rm -f "$list"
      return $status
    }
    if step "Auditoria: Semgrep (varredura)" semgrep_scan; then
      # shellcheck disable=SC2086
      $passos record "Auditoria: Semgrep (varredura)" "$($passos hash -- $in_semgrep $common .semgrep/ip-checker.yml)" \
        "$sha$dirty" --manifest -- $in_semgrep $common .semgrep/ip-checker.yml
    fi
  fi
  local audit_requirements
  audit_requirements=$(mktemp)
  step_fp "Auditoria: dependências Python (pip-audit)" "backend/uv.lock backend/pyproject.toml" --max-age-days 7 bash -c \
    "cd backend && '$uv' export --locked --no-hashes --no-emit-project --format requirements-txt \
     > '$audit_requirements' && '$uv' tool run --from pip-audit==2.9.0 pip-audit --strict \
     -r '$audit_requirements'"
  rm -f "$audit_requirements"
  if [ -n "$history_clone" ]; then rm -rf "$history_clone"; fi
  step_fp "Auditoria: dependências npm (npm audit)" "frontend/package-lock.json frontend/package.json" --max-age-days 7 \
    bash -c "cd frontend && npm audit --audit-level=high"
  step_fp "Auditoria: dependências npm da extensão" "extensao/package-lock.json extensao/package.json" --max-age-days 7 \
    bash -c "cd extensao && npm audit --audit-level=high"
}

lane_c() {
  # S49-04: npm ci só com lock novo (ou sem node_modules).
  if [ -d frontend/node_modules ]; then
    step_fp "Frontend: dependências" "frontend/package-lock.json frontend/package.json" frontend npm ci --no-audit --no-fund
  else
    step "Frontend: dependências" frontend npm ci --no-audit --no-fund
  fi
  step_fp "Frontend: tipos do OpenAPI em dia" "docs/openapi.json frontend/package.json frontend/src/types frontend/scripts" bash -c \
    "cd frontend && npm run -s gen:api && git diff --exit-code -- src/types/openapi.ts"
  step_fp "Frontend: ESLint" "$in_frontend" frontend npm run -s lint
  step_fp "Frontend: TypeScript" "$in_frontend" frontend npm run -s typecheck
  step_fp "Frontend: Vitest (cobertura das páginas >= 80%)" "$in_frontend" frontend npm run test:coverage --silent
  step_fp "Frontend: build" "$in_frontend" frontend npm run -s build
  if [ -d frontend/dist ]; then
    local budget_out budget_note
    budget_out=$(mktemp)
    step_fp "Frontend: JS inicial com gzip (NFR-03)" "$in_frontend" bash -c \
      "set -o pipefail; cd frontend && node scripts/js-budget.mjs | tee '$budget_out'"
    # A folga até o próximo degrau do FCP vai para o resumo, com o aviso abaixo de 2 KB (S39-01).
    budget_note=$(grep -m1 '^Folga até o próximo degrau do FCP' "$budget_out")
    if [ -n "$budget_note" ]; then
      grep -q '^AVISO:' "$budget_out" && budget_note=", **com aviso**; ${budget_note,}" \
        || budget_note="; ${budget_note,}"
      results[-1]=${results[-1]/| ok |/| ok$budget_note |}
    fi
    rm -f "$budget_out"
  fi
  step_fp "Frontend: build do piloto" "$in_frontend" env IPC_API_ORIGIN=https://ip-checker-api.onrender.com \
    bash -c "cd frontend && npm run -s build:vercel && rm -rf .vercel"
  # S50-01: a extensão do Dikastis, com os mesmos passos da página.
  if [ -d extensao/node_modules ]; then
    step_fp "Extensão: dependências" "extensao/package-lock.json extensao/package.json" extensao npm ci --no-audit --no-fund
  else
    step "Extensão: dependências" extensao npm ci --no-audit --no-fund
  fi
  step_fp "Extensão: ESLint" "$in_extensao" extensao npm run -s lint
  step_fp "Extensão: TypeScript" "$in_extensao" extensao npm run -s typecheck
  step_fp "Extensão: Vitest (cobertura >= 80%)" "$in_extensao" extensao npm run -s test:coverage
  step_fp "Extensão: build" "$in_extensao" extensao npm run -s build
}

run_lane() {  # run_lane NOME FUNÇÃO: subshell com log e resultados próprios
  local name=$1 fn=$2
  (
    results=(); failed=0; skipped=0; start=$SECONDS
    "$fn"
    printf '%s\n' "${results[@]}" > "$lane_dir/$name.results"
    printf '%s %s %s\n' "$failed" "$skipped" "$((SECONDS - start))" > "$lane_dir/$name.status"
  ) > "$lane_dir/$name.log" 2>&1 &
}

echo "=== Faixas A (backend), B (auditoria) e C (frontend) em paralelo"
lanes_start=$SECONDS
run_lane A lane_a
run_lane B lane_b
run_lane C lane_c
wait
for name in A B C; do
  echo
  echo "##### Faixa $name"
  cat "$lane_dir/$name.log"
  [ -s "$lane_dir/$name.results" ] && mapfile -t -O "${#results[@]}" results < "$lane_dir/$name.results"
  read -r lane_failed lane_skipped lane_time < "$lane_dir/$name.status"
  [ "$lane_failed" = "1" ] && failed=1
  skipped=$((skipped + lane_skipped))
  results+=("| Faixa $name (tempo da faixa) | — | $lane_time s |")
done
results+=("| Faixas A, B e C em paralelo (caminho crítico) | — | $((SECONDS - lanes_start)) s |")

# --- Faixa silenciosa (S49-02): sozinha na máquina, porque mede tempo ou memória --------------
echo
echo "=== Faixa silenciosa: tempo, cobertura, benchmark, Lighthouse e segurança"
# Os processos das faixas (node, uv, contêineres das auditorias) ainda estão terminando: alguns
# segundos de folga antes de medir tempo.
sleep 5
step_fp "Backend: pytest de tempo (timing; cobertura >= 90%)" "$in_backend" \
  bash -c "cd backend && '$uv' run pytest -q -p no:cacheprovider -m timing --cov-append"
step_fp "Backend: cobertura por pasta (motor >= 90%, resto >= 80%)" "$in_backend" bash -c \
  "cd backend && '$uv' run coverage json -q -o coverage.json \
   && '$uv' run python scripts/coverage_by_folder.py coverage.json"
step_fp "Backend: benchmark do motor (NFR-02)" "$in_engine" env IPC_BENCHMARK=1 \
  bash -c "cd backend && '$uv' run pytest tests/benchmark --no-cov -q -s -p no:cacheprovider"
if [ -d frontend/dist ]; then
  step_fp "Frontend: Lighthouse, perfil móvel (NFR-03)" "$in_frontend" frontend \
    npx --yes @lhci/cli@0.15.1 autorun --config=lighthouserc.json
fi
if $security; then
  step_fp "Segurança (isolamento e imagem do piloto)" "$in_security" env IPC_SECURITY_TESTS=1 \
    bash -c "cd backend && '$uv' run pytest tests/security --no-cov -q -p no:cacheprovider"
else
  results+=("| Segurança | pulada (--rapido) | — |")
fi

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
  e2e_run() {
    docker compose -p "$compose_project" -f deploy/compose.yaml --env-file "$e2e_env" \
      up --build -d --wait --wait-timeout 300 \
    && env E2E_BASE_URL=http://127.0.0.1:28280 E2E_MAILPIT_URL=http://127.0.0.1:28225 \
      E2E_PASSWORD="$dev_password" \
      bash -c "cd frontend && npx playwright install chromium > /dev/null && npm run -s e2e"
  }
  step_fp "e2e: compose (porta 28280) e Playwright" "$in_e2e" e2e_run
else
  results+=("| Smoke e2e | pulado (use --e2e) | — |")
fi

echo
echo "----- resumo para o PR -----"
mode=$($completo && echo ", --completo" || echo "")
echo "**CI local** (\`scripts/ci-local.sh\`, P-19, incremental desde a S49$mode) em \`$sha\`$dirty, $(date '+%d/%m/%Y %H:%M'), $skipped passo(s) pulado(s) por entradas iguais a um verde:"
echo
echo "| Passo | Resultado | Tempo |"
echo "|---|---|---|"
printf '%s\n' "${results[@]}"
echo
echo "tempo total: $SECONDS s"
if [ "$failed" = "1" ]; then
  echo "Houve falhas: veja os passos acima."
  exit 1
fi
if $e2e && [ -z "$dirty" ]; then
  # A evidência da release (P-19): a árvore do commit, não o commit, para valer também depois de
  # um merge squash com o mesmo conteúdo. Passos pulados contam: tiveram verde para o mesmo conteúdo.
  tree=$(git rev-parse "HEAD^{tree}")
  record="$(git rev-parse --git-common-dir)/ci-local-verde"
  echo "$tree $(date '+%Y-%m-%dT%H:%M') $sha" >> "$record"
  echo "Registrado em .git/ci-local-verde (árvore ${tree:0:12}): vale para o release.sh --ci-local."
fi

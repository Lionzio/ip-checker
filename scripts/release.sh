#!/usr/bin/env bash
# Release de uma sprint (S28-04): leva a develop para a main por fast-forward, cria a tag
# sprint-NN e o GitHub Release com as notas do CHANGELOG.md. O deploy do piloto sai sozinho da main,
# depois da CI (.github/workflows/deploy.yml).
#
# Uso, na raiz do repositório, com o gh autenticado:
#
#   scripts/release.sh 28              # faz a release da Sprint 28
#   scripts/release.sh 28 --dry-run    # só mostra o que faria
#   scripts/release.sh 31 --ci-local   # sem a cota do Actions (P-19): vale a CI desta máquina
#   scripts/release.sh 31.1 --ci-local # release extra entre duas sprints (seção "## Sprint 31.1")
#
# Recusa se: a árvore tem mudanças; a main não é ancestral da develop (ela só avança por
# fast-forward); a CI da ponta da develop não está verde; a tag já existe; o CHANGELOG.md não tem a
# seção "## Sprint NN". Com --ci-local (decisão do autor de 09/10/2026, P-19), a CI verde é uma
# rodada completa do scripts/ci-local.sh --e2e, sem falha, na mesma árvore da ponta da develop
# (registrada em .git/ci-local-verde); o deploy, então, é à mão (runbook, "Sem GitHub Actions").
set -euo pipefail

usage() {
  echo "uso: scripts/release.sh NÚMERO_DA_SPRINT [--dry-run] [--ci-local]" >&2
  exit 2
}

[ $# -ge 1 ] || usage
sprint=$1
dry_run=false
ci_local=false
for option in "${@:2}"; do
  case "$option" in
    --dry-run) dry_run=true ;;
    --ci-local) ci_local=true ;;
    *) usage ;;
  esac
done
[[ "$sprint" =~ ^[0-9]+(\.[0-9]+)?$ ]] || usage
tag="sprint-$sprint"

fail() {
  echo "release: $*" >&2
  exit 1
}

cd "$(git rev-parse --show-toplevel)"
command -v gh > /dev/null || fail "o gh (GitHub CLI) não está instalado."
[ -z "$(git status --porcelain)" ] || fail "a árvore de trabalho tem mudanças; faça commit ou stash antes."

git fetch --quiet --tags origin develop main
develop=$(git rev-parse origin/develop)
git merge-base --is-ancestor origin/main "$develop" \
  || fail "a main tem commits que não estão na develop; releases são só fast-forward."
if git rev-parse -q --verify "refs/tags/$tag" > /dev/null; then
  fail "a tag $tag já existe."
fi

repository=$(gh repo view --json nameWithOwner -q .nameWithOwner)
if $ci_local; then
  tree=$(git rev-parse "$develop^{tree}")
  record="$(git rev-parse --git-common-dir)/ci-local-verde"
  if grep -q "^$tree " "$record" 2>/dev/null; then
    echo "CI local verde na árvore ${tree:0:12}: $(grep "^$tree " "$record" | tail -1 | cut -d' ' -f2-)"
  else
    # S49-05 (ADR-20): sem a rodada inteira nesta árvore, vale a cobertura por passos: cada passo
    # da CI local com um verde registrado para as entradas atuais, calculadas nesta árvore de
    # trabalho, que precisa ser a da ponta da develop; e o gitleaks auditado até esse commit.
    [ "$(git rev-parse 'HEAD^{tree}')" = "$tree" ] \
      || fail "nenhuma rodada verde do scripts/ci-local.sh --e2e na árvore da develop em ${develop:0:7}, e esta árvore de trabalho não é a dela (faça checkout da develop atualizada)."
    passos=(
      "Backend: ruff" "Backend: formatação" "Backend: mypy" "Backend: fronteiras" "Ruleset e golden"
      "Backend: pytest em paralelo (sem banco e sem tempo)" "Backend: pytest em série (banco)"
      "Documentação: links" "Gabaritos (zero violação)"
      "Auditoria: Semgrep (testes das regras)" "Auditoria: Semgrep (varredura)"
      "Auditoria: dependências Python (pip-audit)" "Auditoria: dependências npm (npm audit)"
      "Frontend: tipos do OpenAPI em dia" "Frontend: ESLint" "Frontend: TypeScript"
      "Frontend: Vitest (cobertura das páginas >= 80%)" "Frontend: build"
      "Frontend: JS inicial com gzip (NFR-03)" "Frontend: build do piloto"
      "Auditoria: dependências npm da extensão" "Extensão: ESLint" "Extensão: TypeScript"
      "Extensão: Vitest (cobertura >= 80%)" "Extensão: build"
      "Backend: pytest de tempo (timing; cobertura >= 90%)"
      "Backend: cobertura por pasta (motor >= 90%, resto >= 80%)" "Backend: benchmark do motor (NFR-02)"
      "Frontend: Lighthouse, perfil móvel (NFR-03)" "Segurança (isolamento e imagem do piloto)"
      "e2e: compose (porta 28280) e Playwright"
    )
    python scripts/ci-passos.py verify "${passos[@]}" \
      || fail "a CI local não cobre a develop em ${develop:0:7}: rode scripts/ci-local.sh --e2e (passos acima sem verde)."
    audited=$(python scripts/ci-passos.py check "Auditoria: gitleaks (último commit)" sempre | cut -d' ' -f1)
    [ -n "$audited" ] && [ "$(git rev-parse "$audited")" = "$develop" ] \
      || fail "o gitleaks não auditou a develop em ${develop:0:7}: rode scripts/ci-local.sh --e2e."
    echo "CI local verde por passos na árvore ${tree:0:12} (ADR-20): todos os passos com verde para as entradas atuais."
  fi
else
  green=$(gh api "repos/$repository/actions/runs?head_sha=$develop&branch=develop&event=push&status=success" \
    -q '[.workflow_runs[] | select(.name == "CI")] | length')
  [ "$green" != "0" ] || fail "a CI da develop em ${develop:0:7} não está verde (ou ainda não terminou)."
fi

# As notas são a seção da sprint no CHANGELOG.md, até a próxima seção "## ".
notes=$(awk -v head="## Sprint $sprint" '
  index($0, head) == 1 && (length($0) == length(head) || substr($0, length(head) + 1, 1) ~ /[ :—-]/) { on = 1; print; next }
  on && /^## / { exit }
  on { print }
' CHANGELOG.md)
[ -n "$notes" ] || fail "o CHANGELOG.md não tem a seção \"## Sprint $sprint\"."
title=$(printf '%s\n' "$notes" | head -n 1 | sed 's/^## //')

echo "Release $tag: develop ${develop:0:7} -> main, com o título \"$title\"."
if $dry_run; then
  printf '%s\n' "$notes"
  echo "(--dry-run: nada foi feito)"
  exit 0
fi

# O push recusa sozinho o que não for fast-forward.
git push origin "$develop:refs/heads/main"
git tag -a "$tag" "$develop" -m "$title"
git push origin "refs/tags/$tag"
printf '%s\n' "$notes" | tail -n +2 | gh release create "$tag" --verify-tag --title "$title" --notes-file -
if $ci_local; then
  echo "Pronto: $tag publicada. Sem a cota do Actions, o deploy é à mão (runbook, P-19)."
else
  echo "Pronto: $tag publicada. O deploy do piloto começa quando a CI da main terminar."
fi
# S34-04 (NFR-15): o alerta é exercitado a cada release, depois do deploy.
echo "Depois do deploy: o exercício de alerta desta release e uma linha na tabela do runbook"
echo "(\"Registro dos exercícios de alerta\"), e o scripts/sintetico-local.sh (ou o workflow \"Sintético diário\")."

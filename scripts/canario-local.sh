#!/usr/bin/env bash
# Canário mensal nesta máquina (S35-04, NFR-11, P-19): o mesmo do workflow "Canário mensal", para
# quando o GitHub Actions estiver sem cota.
#
# Uso, no Git Bash, na raiz do repositório:
#
#   scripts/canario-local.sh
#
# Planta uma marca única num código verificado, comparado e usado no feedback pela página, com a
# conta de verificação, e procura a marca em todas as tabelas dos esquemas app e telemetry do
# banco do piloto. Pede o login e a senha da conta de verificação e a connection string do Supabase
# (usuário postgres, a mesma do backup), as senhas sem mostrá-las, ou os lê de PILOT_LOGIN,
# PILOT_PASSWORD e PILOT_DATABASE_ADMIN_URL. Nada é salvo. Os logs do Render são conferidos pelo
# painel, com a marca que o script mostra (decisão do autor de 11/10/2026: sem chave de API).
set -euo pipefail

root=$(git rev-parse --show-toplevel)
uv=$(command -v uv || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe 2>/dev/null | head -1)
[ -n "$uv" ] || { echo "canario-local: instale o uv (winget install astral-sh.uv)" >&2; exit 2; }

web=${PILOT_WEB_URL:-$(gh variable get PILOT_WEB_URL --repo Lionzio/ip-checker 2>/dev/null || true)}
[[ "$web" =~ ^https:// ]] || { echo "canario-local: defina PILOT_WEB_URL (https://...)" >&2; exit 2; }

if [ -z "${PILOT_LOGIN:-}" ]; then
  read -rp "Login da conta de verificação: " PILOT_LOGIN
fi
if [ -z "${PILOT_PASSWORD:-}" ]; then
  read -rsp "Senha da conta de verificação (não aparece na tela): " PILOT_PASSWORD
  echo
fi
if [ -z "${PILOT_DATABASE_ADMIN_URL:-}" ]; then
  read -rsp "Connection string do Supabase (usuário postgres; não aparece na tela): " PILOT_DATABASE_ADMIN_URL
  echo
fi
[[ "$PILOT_DATABASE_ADMIN_URL" =~ ^postgres(ql)?:// ]] || {
  echo "canario-local: isso não parece uma connection string postgresql://..." >&2
  exit 2
}

cd "$root/backend"
PILOT_WEB_URL=$web PILOT_LOGIN=$PILOT_LOGIN PILOT_PASSWORD=$PILOT_PASSWORD \
  PILOT_DATABASE_ADMIN_URL=$PILOT_DATABASE_ADMIN_URL "$uv" run python scripts/canary.py

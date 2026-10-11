#!/usr/bin/env bash
# Teste sintético da primeira verificação nesta máquina (S34-02, P-19): o mesmo do workflow
# "Sintético diário", para quando o GitHub Actions estiver sem cota ou para conferir na hora.
#
# Uso, no Git Bash, na raiz do repositório:
#
#   scripts/sintetico-local.sh
#
# Pede o login e a senha da conta de verificação do deploy (os secrets PILOT_CHECK_LOGIN e
# PILOT_CHECK_PASSWORD), a senha sem mostrá-la, ou os lê de PILOT_LOGIN e PILOT_PASSWORD. Nada é
# salvo. O endereço da página vem da variável PILOT_WEB_URL do repositório (ou do ambiente).
set -euo pipefail

root=$(git rev-parse --show-toplevel)
uv=$(command -v uv || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe 2>/dev/null | head -1)
[ -n "$uv" ] || { echo "sintetico-local: instale o uv (winget install astral-sh.uv)" >&2; exit 2; }

web=${PILOT_WEB_URL:-$(gh variable get PILOT_WEB_URL --repo Lionzio/ip-checker 2>/dev/null || true)}
[[ "$web" =~ ^https:// ]] || { echo "sintetico-local: defina PILOT_WEB_URL (https://...)" >&2; exit 2; }

if [ -z "${PILOT_LOGIN:-}" ]; then
  read -rp "Login da conta de verificação: " PILOT_LOGIN
fi
if [ -z "${PILOT_PASSWORD:-}" ]; then
  read -rsp "Senha da conta de verificação (não aparece na tela): " PILOT_PASSWORD
  echo
fi
if [ -z "$PILOT_LOGIN" ] || [ -z "$PILOT_PASSWORD" ]; then
  echo "sintetico-local: login e senha são obrigatórios" >&2
  exit 2
fi

echo "Verificando pela página ($web)..."
cd "$root/backend"
PILOT_SYNTHETIC=1 PILOT_WEB_URL=$web PILOT_LOGIN=$PILOT_LOGIN PILOT_PASSWORD=$PILOT_PASSWORD \
  "$uv" run pytest tests/pilot/test_synthetic.py --no-cov -q -s -p no:cacheprovider \
  -k test_the_first_validation_of_the_day

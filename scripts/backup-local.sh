#!/usr/bin/env bash
# Backup do banco do piloto nesta máquina (P-19): o mesmo do workflow "Backup do banco do piloto"
# (pg_dump de app e telemetry, conferência, contagens e criptografia com age), para quando o GitHub
# Actions estiver sem cota.
#
# Uso, no Git Bash, na raiz do repositório (Docker Desktop aberto):
#
#   scripts/backup-local.sh                 # salva em ~/Desktop/IP-Checker/backups/piloto
#   scripts/backup-local.sh <pasta>         # ou em outra pasta, fora do repositório
#
# O script pede a connection string do Supabase (usuário postgres; Project Settings > Database >
# Connection string > URI) sem mostrá-la, ou a lê de PILOT_DATABASE_ADMIN_URL. Ela não é salva em
# lugar nenhum. O dump em claro só existe numa pasta temporária, apagada no fim; fica só o arquivo
# criptografado com a chave pública (BACKUP_AGE_RECIPIENT), o .sha256 e as contagens. Para abrir,
# use a chave privada (docs/runbook.md, "Restaurar um backup").
set -euo pipefail

POSTGRES_IMAGE="postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
root=$(cd "$(git rev-parse --show-toplevel)" && pwd -P)
out=${1:-"$HOME/Desktop/IP-Checker/backups/piloto"}
mkdir -p "$out"
case "$(cd "$out" && pwd -P)/" in
  "$root"/*) echo "backup-local: a pasta de saída não pode ficar dentro do repositório" >&2; exit 2 ;;
esac

command -v docker > /dev/null || { echo "backup-local: o Docker Desktop precisa estar aberto" >&2; exit 2; }
age=$(command -v age || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/FiloSottile.age_*/age/age.exe 2>/dev/null | head -1)
[ -n "$age" ] || { echo "backup-local: instale o age (winget install FiloSottile.age)" >&2; exit 2; }

recipient=${BACKUP_AGE_RECIPIENT:-$(gh variable get BACKUP_AGE_RECIPIENT --repo Lionzio/ip-checker 2>/dev/null || true)}
if ! [[ "$recipient" =~ ^age1[a-z0-9]{58}$ ]]; then
  echo "backup-local: BACKUP_AGE_RECIPIENT não parece uma chave pública age (age1...)" >&2
  exit 2
fi

if [ -z "${PILOT_DATABASE_ADMIN_URL:-}" ]; then
  read -rsp "Connection string do Supabase (usuário postgres; não aparece na tela): " PILOT_DATABASE_ADMIN_URL
  echo
fi
[[ "$PILOT_DATABASE_ADMIN_URL" =~ ^postgres(ql)?:// ]] || {
  echo "backup-local: isso não parece uma connection string postgresql://..." >&2
  exit 2
}
export DATABASE_URL=$PILOT_DATABASE_ADMIN_URL

mkdir -p "$out"
work=$(mktemp -d "$out/.tmp.XXXXXX")
trap 'rm -rf "$work"' EXIT
chmod 700 "$work"
name="ipc-piloto-$(date -u +%Y-%m-%d)"
mount=$(cd "$work" && pwd -W 2>/dev/null || pwd)
queries=$(cd "$root/deploy/backup" && pwd -W 2>/dev/null || pwd)

echo "Fazendo o pg_dump (app e telemetry)..."
MSYS_NO_PATHCONV=1 docker run --rm -e DATABASE_URL -v "$mount:/out" -v "$queries:/q:ro" \
  "$POSTGRES_IMAGE" sh -c \
  'pg_dump --format=custom --schema=app --schema=telemetry --no-owner --no-privileges \
     --file=/out/dump "$DATABASE_URL" && pg_restore --list /out/dump > /out/conteudo.txt \
   && psql "$DATABASE_URL" -X -A -F " | " -t -v ON_ERROR_STOP=1 -f /q/contagens.sql > /out/contagens.txt'
unset DATABASE_URL PILOT_DATABASE_ADMIN_URL

tables=$(grep -c " TABLE DATA " "$work/conteudo.txt" || true)
if [ "$tables" -lt 5 ]; then
  echo "backup-local: o dump tem só $tables tabelas com dados; algo está errado" >&2
  exit 1
fi
"$age" --encrypt --recipient "$recipient" --output "$out/$name.dump.age" "$work/dump"
(cd "$out" && sha256sum "$name.dump.age" > "$name.dump.age.sha256")
cp "$work/contagens.txt" "$out/$name.contagens.txt"

echo
echo "Backup pronto em $out:"
ls -l "$out/$name".*
echo
echo "Linhas por tabela no momento do backup:"
cat "$out/$name.contagens.txt"
echo
echo "Guarde uma cópia fora deste computador (o arquivo .age só abre com a chave privada)."

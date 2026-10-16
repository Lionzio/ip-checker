#!/usr/bin/env bash
# Ensaio de restauração do backup do piloto (S39-04, NFR-20): o passo 3 de "Restaurar um backup"
# do runbook, inteiro e cronometrado. Nunca toca no piloto: sobe um PostgreSQL descartável, aplica
# as migrações, restaura só os dados e compara as linhas por tabela com as do momento do backup.
#
# Uso, no Git Bash, na raiz do repositório (Docker Desktop aberto):
#
#   scripts/restaurar-ensaio.sh                       # o backup mais novo da pasta de sempre
#   scripts/restaurar-ensaio.sh <arquivo.dump.age>    # outro backup
#
# A chave privada vem de BACKUP_AGE_IDENTITY ou de ~/Desktop/IP-Checker/chave-backup/ipc-backup.key;
# se não houver, o caminho é pedido. O dump em claro só existe numa pasta temporária, apagada no
# fim com o contêiner. Só números e nomes de tabela aparecem na tela.
set -euo pipefail

POSTGRES_IMAGE="postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
root=$(cd "$(git rev-parse --show-toplevel)" && pwd -P)
backups="$HOME/Desktop/IP-Checker/backups/piloto"
file=${1:-$(ls -1t "$backups"/ipc-piloto-*.dump.age 2>/dev/null | head -1 || true)}
[ -n "$file" ] && [ -f "$file" ] || { echo "restaurar-ensaio: nenhum backup .dump.age em $backups" >&2; exit 2; }
base=${file%.dump.age}
name=$(basename "$base")

age=$(command -v age || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/FiloSottile.age_*/age/age.exe 2>/dev/null | head -1)
[ -n "$age" ] || { echo "restaurar-ensaio: instale o age (winget install FiloSottile.age)" >&2; exit 2; }
command -v docker > /dev/null && docker info > /dev/null 2>&1 || { echo "restaurar-ensaio: abra o Docker Desktop" >&2; exit 2; }
uv=$(command -v uv || ls "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe 2>/dev/null | head -1)

identity=${BACKUP_AGE_IDENTITY:-"$HOME/Desktop/IP-Checker/chave-backup/ipc-backup.key"}
if [ ! -f "$identity" ]; then
  read -rp "Caminho da chave privada do backup (ipc-backup.key): " identity
fi
[ -f "$identity" ] || { echo "restaurar-ensaio: chave privada não encontrada" >&2; exit 2; }

container="ipc-restore-ensaio"
work=$(mktemp -d)
cleanup() {
  docker rm -f "$container" > /dev/null 2>&1 || true
  rm -rf "$work"
}
trap cleanup EXIT
chmod 700 "$work"

started=$(date +%s)
echo "Backup: $name"
(cd "$(dirname "$file")" && sha256sum -c "$name.dump.age.sha256" --quiet) || { echo "restaurar-ensaio: o hash não confere" >&2; exit 1; }
echo "Hash conferido."
"$age" --decrypt -i "$identity" -o "$work/dump" "$file"
echo "Decifrado (o dump em claro fica só em $work, apagado no fim)."

docker rm -f "$container" > /dev/null 2>&1 || true
password=$(head -c 18 /dev/urandom | od -An -tx1 | tr -d ' \n')
docker run -d --name "$container" -e POSTGRES_PASSWORD="$password" -e POSTGRES_DB=ipchecker \
  -p 127.0.0.1::5432 "$POSTGRES_IMAGE" > /dev/null
port=$(docker port "$container" 5432/tcp | head -1 | sed 's/.*://')
for _ in $(seq 1 30); do
  docker exec "$container" pg_isready -U postgres -d ipchecker > /dev/null 2>&1 && break
  sleep 1
done

(cd "$root/backend" && IPC_DATABASE_ADMIN_URL="postgresql://postgres:$password@127.0.0.1:$port/ipchecker" \
  IPC_DB_LOGIN_PASSWORD="$password" "$uv" run python -m ipc_api.db.migrate up --login-role ipc_api) > /dev/null
echo "Migrações aplicadas no PostgreSQL descartável."
docker exec -i "$container" pg_restore --data-only --disable-triggers -U postgres -d ipchecker < "$work/dump"
echo "Dados restaurados."

docker exec -i "$container" psql -U postgres -d ipchecker -X -A -F " | " -t -v ON_ERROR_STOP=1 \
  < "$root/deploy/backup/contagens.sql" > "$work/contagens.txt"
elapsed=$(( $(date +%s) - started ))
tables=$(wc -l < "$work/contagens.txt" | tr -d ' ')
if diff -u "$base.contagens.txt" "$work/contagens.txt"; then
  echo
  echo "Restauração certa: linhas iguais nas $tables tabelas, em $elapsed s (RTO técnico; NFR-20: até 30 min)."
  echo "Linha para o runbook: | $(date +%d/%m/%Y) | <quem> | \`$name\` | Hash conferido, migrações e dados restaurados, linhas iguais nas $tables tabelas; RTO técnico de $elapsed s, sem contar o acesso à chave privada (scripts/restaurar-ensaio.sh) |"
else
  echo "restaurar-ensaio: as linhas por tabela não batem com as do backup" >&2
  exit 1
fi

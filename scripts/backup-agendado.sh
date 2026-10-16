#!/usr/bin/env bash
# O backup do piloto pela tarefa agendada do Windows (S39-04): abre o Docker Desktop se precisar,
# lê a connection string guardada com o DPAPI (scripts/guardar-segredo-backup.ps1) e roda o
# scripts/backup-local.sh sem perguntar nada. O resultado vai para agendado.log, na pasta dos
# backups, sem nenhum segredo. A tarefa é criada por scripts/agendar-backup.ps1.
#
# Para rodar à mão, no Git Bash, na raiz do repositório: scripts/backup-agendado.sh
set -uo pipefail

root=$(cd "$(dirname "$0")/.." && pwd -P)
out=${1:-"$HOME/Desktop/IP-Checker/backups/piloto"}
mkdir -p "$out"
log="$out/agendado.log"
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$log"; }

secret_file="$LOCALAPPDATA/ip-checker/backup.dpapi"
if [ ! -s "$secret_file" ]; then
  say "falhou: falta a connection string guardada (rode scripts/guardar-segredo-backup.ps1)"
  exit 2
fi

if ! docker info > /dev/null 2>&1; then
  say "abrindo o Docker Desktop"
  "/c/Program Files/Docker/Docker/Docker Desktop.exe" > /dev/null 2>&1 &
  for _ in $(seq 1 36); do
    docker info > /dev/null 2>&1 && break
    sleep 5
  done
  docker info > /dev/null 2>&1 || { say "falhou: o Docker não respondeu em 3 minutos"; exit 1; }
fi

# O DPAPI só abre para este usuário, nesta máquina; o valor vai direto para a variável, sem eco.
PILOT_DATABASE_ADMIN_URL=$(powershell -NoProfile -Command \
  "\$s = (Get-Content -Raw '$(cygpath -w "$secret_file")').Trim() | ConvertTo-SecureString; [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR(\$s))" \
  | tr -d '\r\n')
if [[ ! "$PILOT_DATABASE_ADMIN_URL" =~ ^postgres(ql)?:// ]]; then
  say "falhou: a connection string guardada não abriu (outro usuário ou arquivo trocado?)"
  exit 2
fi
export PILOT_DATABASE_ADMIN_URL

say "backup começou"
if "$root/scripts/backup-local.sh" "$out" > "$out/.agendado-ultima-saida.txt" 2>&1; then
  say "backup pronto: $(ls -1t "$out"/ipc-piloto-*.dump.age | head -1 | xargs -n1 basename)"
else
  say "falhou: veja $out/.agendado-ultima-saida.txt (sem segredos)"
  exit 1
fi

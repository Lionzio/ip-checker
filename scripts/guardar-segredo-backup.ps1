# Guarda a connection string do Supabase para o backup agendado (S39-04), cifrada com o DPAPI do
# Windows: só este usuário, nesta máquina, consegue abri-la. Rode uma vez, no PowerShell, na raiz do
# repositório:
#
#   powershell -ExecutionPolicy Bypass -File scripts\guardar-segredo-backup.ps1
#
# A connection string (usuário postgres; Supabase, Project Settings > Database > Connection string >
# URI) é pedida sem aparecer na tela e nunca é mostrada nem gravada em texto puro. Para trocar,
# rode de novo; para apagar, remova o arquivo indicado no fim.
$ErrorActionPreference = "Stop"

$folder = Join-Path $env:LOCALAPPDATA "ip-checker"
$file = Join-Path $folder "backup.dpapi"
New-Item -ItemType Directory -Force -Path $folder | Out-Null

$secret = Read-Host -AsSecureString "Connection string do Supabase (usuário postgres; não aparece na tela)"
$plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret))
if ($plain -notmatch "^postgres(ql)?://") {
  Write-Error "Isso não parece uma connection string postgresql://... Nada foi gravado."
}
$plain = $null

# ConvertFrom-SecureString sem -Key usa o DPAPI do usuário atual.
$secret | ConvertFrom-SecureString | Set-Content -Path $file -Encoding ascii
# Só o próprio usuário lê o arquivo (o conteúdo já é cifrado; isto é uma camada a mais).
icacls $file /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
Write-Output "Guardado em $file (cifrado para o usuário $env:USERNAME). O backup agendado vai usá-lo."

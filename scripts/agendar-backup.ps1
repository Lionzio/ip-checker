# Cria a tarefa "IP-Checker backup" no Agendador de Tarefas do Windows (S39-04): todo domingo ao
# meio-dia, ou no primeiro momento depois disso em que o computador estiver ligado e você logado,
# roda scripts/backup-agendado.sh pelo Git Bash. Antes, guarde a connection string com
# scripts/guardar-segredo-backup.ps1. Rode uma vez, no PowerShell, na raiz do repositório:
#
#   powershell -ExecutionPolicy Bypass -File scripts\agendar-backup.ps1
#
# Para rodar agora:     Start-ScheduledTask -TaskName "IP-Checker backup"
# Para ver a situação:  Get-ScheduledTaskInfo -TaskName "IP-Checker backup"
# Para remover:         Unregister-ScheduledTask -TaskName "IP-Checker backup" -Confirm:$false
$ErrorActionPreference = "Stop"

$name = "IP-Checker backup"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $bash)) { Write-Error "Git Bash não encontrado em $bash" }
if (-not (Test-Path (Join-Path $env:LOCALAPPDATA "ip-checker\backup.dpapi"))) {
  Write-Error "Falta a connection string guardada: rode antes scripts\guardar-segredo-backup.ps1"
}

$action = New-ScheduledTaskAction -Execute $bash -Argument "-lc 'scripts/backup-agendado.sh'" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 12:00
# Só com você logado: o DPAPI e o Docker Desktop são do seu usuário. Se o computador estiver
# desligado no horário, roda assim que der; no máximo 1 hora, e nunca duas ao mesmo tempo.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
  -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
  -Description "Backup semanal do banco do piloto do IP-Checker (scripts/backup-agendado.sh, S39-04)." -Force | Out-Null
Get-ScheduledTask -TaskName $name | Select-Object TaskName, State | Format-Table -AutoSize
Write-Output "Próxima execução: $((Get-ScheduledTaskInfo -TaskName $name).NextRunTime)"

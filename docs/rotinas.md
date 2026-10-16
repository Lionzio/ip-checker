# Agenda das rotinas

O que roda sozinho, o que alguém precisa fazer e quando (S39-05). Sem a cota do GitHub Actions
(P-19), cada rotina do Actions tem um script equivalente nesta máquina.

| Rotina | Quando | Com o Actions | Sem o Actions | Registro |
|---|---|---|---|---|
| Backup do banco do piloto | Diário no Actions; semanal na máquina | `backup.yml`, 06:00 UTC | Tarefa "IP-Checker backup" (domingo ao meio-dia) ou `scripts/backup-local.sh` | Artefato do workflow ou `backups/piloto/` e `agendado.log` |
| Ensaio de restauração | Uma vez por semestre (NFR-20) | — | `scripts/restaurar-ensaio.sh` | Tabela em "Restaurar um backup" no [`runbook.md`](runbook.md) |
| Sintético | Dias úteis e depois de cada deploy | `synthetic.yml` | `scripts/sintetico-local.sh` (o autor digita a senha da conta de verificação) | CHANGELOG da release |
| Exercício de alerta | A cada release que vai ao piloto (S34-04) | `load.yml` | Dois PRs do `render.yaml` e `scripts/carga-piloto.sh 20 10m` | Tabela em "Registro dos exercícios de alerta" no runbook |
| Canário | Mensal | `canary.yml` | `scripts/canario-local.sh` | Resumo do run |
| Auditoria de segurança | A cada PR e semanal | `audit.yml` e o job "Auditoria" da CI | As etapas de auditoria do `scripts/ci-local.sh` | Resumo da CI |
| Rollback | Quando um deploy der errado | — | Render: o deploy anterior; Vercel: **Instant Rollback** e depois **Promote** | Runbook, "Rollback" |
| Troca do token dos gabaritos | Por evento, nunca por data (P-23): suspeita de vazamento, mudança de quem administra a conta, 401 nos logs | — | Passo a passo do runbook | Runbook, "Credencial dos gabaritos" |
| Calibração dos indícios | A cada período, quando os indícios estiverem ligados (Sprint 42) | — | `ipc-rules calibrate` | ADR-08 |

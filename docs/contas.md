# Quem cuida de cada conta

Os serviços de que o piloto depende, quem administra cada um e onde ficam as credenciais (S39-05).
Nenhum valor de segredo entra aqui nem em outro arquivo do repositório; a troca de cada um está em
"Segredos", no [`runbook.md`](runbook.md).

| Serviço | Para quê | Quem administra | Onde a credencial é usada |
|---|---|---|---|
| GitHub (`Lionzio/ip-checker` e `Lionzio/ip-checker-gabaritos`) | Código, PRs, releases, Actions e os gabaritos | Autor | Secrets e variáveis do repositório (`PILOT_*`, `BACKUP_AGE_RECIPIENT`) |
| Render (serviço `ip-checker-api`, plano gratuito) | A API e o analisador do piloto | Autor | Variáveis do serviço: `IPC_DATABASE_URL`, `IPC_EDGE_SECRET`, `IPC_GABARITOS_TOKEN`, as chaves das IAs e o e-mail |
| Vercel (projeto `ip-checker`) | A página e o repasse de `/api/*` | Autor | O segredo da borda (`IPC_EDGE_SECRET`), igual ao do Render |
| Supabase | O banco do piloto (contas, sessões, telemetria) | Autor | A connection string de admin (`postgres`), digitada só no terminal, e a do `ipc_api` no Render |
| Brevo | Os e-mails de verificação e de senha (Q-17) | Autor | A chave da API no Render |
| UptimeRobot | Os três monitores do piloto e os e-mails de alerta (P-16) | Autor | Só na conta do UptimeRobot |
| Google AI Studio (Gemini) e Groq | O "Aprimorar com IA" (Q-16) | Autor | As chaves no Render |
| GitHub, token dos gabaritos | A API baixar os gabaritos ao subir (ADR-11) | Autor | `IPC_GABARITOS_TOKEN` no Render; sem vencimento, troca por evento (P-23) |
| Chave privada do backup (`age`) | Abrir os backups do banco | Autor | Fora do GitHub e do computador do dia a dia ([`runbook.md`](runbook.md), "Backup") |

Quando outra pessoa assumir uma conta, registre aqui e troque as credenciais que ela não deve
herdar; a mudança de quem administra a conta Lionzio é um dos eventos da troca do token (P-23).

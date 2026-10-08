# Runbook do piloto

O que fazer quando algo dá errado no piloto (Render, Vercel e Supabase; S25-02, completado na
S28-03). Cada seção começa pelo sintoma. A configuração das contas está em
[`deploy/piloto.md`](../deploy/piloto.md); quem chega ao projeto começa pelo
[`onboarding.md`](onboarding.md).

| Sintoma | Seção |
|---|---|
| Uma release quebrou o piloto | Voltar para a versão anterior (rollback) |
| O workflow "Deploy do piloto" ficou vermelho | O deploy parou no meio |
| `/ready` com 503 e `DATABASE_UNAVAILABLE` | Banco fora do ar |
| `/health/service` com 503 | Analisador indisponível |
| O UptimeRobot acusa o `/health/slo` | Latência ou erros acima da meta |
| Dados perdidos ou corrompidos no banco | Backup, "Restaurar um backup" |
| Um segredo vazou ou alguém acessou o que não devia | Segredos e Incidentes de segurança |

## Voltar para a versão anterior (rollback)

A meta da DoD é voltar em até 5 minutos, contados do início do passo 1 até o passo 3 conferido.
Os dois serviços guardam os deploys anteriores, então o caminho mais rápido é pelos painéis; o Git
vem depois, para a `main` não publicar o erro de novo. Cronometre e anote no registro dos ensaios
(abaixo), inclusive quando for de verdade.

1. **API (Render):** no serviço `ip-checker-api`, abra **Events**, escolha o último deploy que
   funcionava e clique em **Rollback**. O Render sobe a imagem anterior e só troca quando ela
   responde `/health/service`.
2. **Página (Vercel):** em **Deployments**, abra o deploy anterior de Production e use **Instant
   Rollback** (ou **Promote to Production**).
3. **Confira:** `curl -s <endereço do Render>/ready` e `<endereço da Vercel>/version.json` mostram o
   mesmo `release`, o do commit anterior. Para cronometrar, rode antes do passo 1, no Git Bash,
   `scripts/rollback-check.sh <commit anterior>`: ele consulta os dois a cada 5 s e mostra o tempo
   até o passo 3.
4. **Git:** na `develop`, reverta o commit com problema por um PR (`git revert`), espere a CI verde e
   faça a release (fast-forward da `main`). O deploy seguinte publica a correção e alinha os painéis
   com a `main`.

**Migrações:** elas só acrescentam (tabelas, colunas, finalidades), então a versão anterior funciona
com o banco migrado e não precisa de `migrate down`. Só reverta uma migração se ela quebrou a
versão anterior:

```bash
cd backend
IPC_DATABASE_ADMIN_URL='<connection string do Supabase, usuário postgres>' \
uv run python -m ipc_api.db.migrate down --to <versão anterior, ex.: 0003>
```

### Registro dos ensaios de rollback

Um ensaio por período, num momento sem uso da equipe: escolha no Render e na Vercel o deploy
anterior, faça os passos 1 a 3 cronometrando e depois volte para o atual pelo mesmo caminho (ou rode
o "Deploy do piloto" de novo). O Render guarda o deploy anterior mesmo quando ele é do mesmo commit
(uma troca de variável gera um deploy novo), então o ensaio funciona antes da segunda release.

| Data | Quem | De → para | Render | Vercel | Total até o passo 3 | Observações |
|---|---|---|---|---|---|---|
| (pendente) | | | | | | O primeiro ensaio (S30-08) fica com o autor: o agente da Sprint 30 não tem permissão para publicar pelos painéis. Releases disponíveis em 08/10/2026: `2a55908` (atual) e `715cd16` (anterior) |

## O deploy parou no meio

| Onde parou | O que significa | O que fazer |
|---|---|---|
| "Instalar a página e o Chromium do Playwright" (só com a conta de verificação) | Um espelho do Ubuntu não respondeu à instalação das bibliotecas do Chromium; o passo desiste em 10 minutos | Nada foi publicado: rode o "Deploy do piloto" de novo mais tarde |
| "Conferir que o commit ainda é a ponta da main" (aviso) | Outra release chegou à `main` durante o deploy | Nada: o deploy da release nova está na fila e publica a ponta |
| "Migrar o banco do piloto" | O Supabase recusou a conexão ou a migração falhou | Veja "Banco fora do ar"; a versão no ar não mudou |
| "Publicar a API no Render" | A API nova não respondeu `/ready` em 25 minutos | Veja o log do build no Render (**Events**); a página não foi publicada, e o Render manteve a versão anterior no ar |
| "Publicar a página na Vercel" | A página nova não publicou o `/version.json` em 10 minutos | Veja o build na Vercel; se a API nova já está no ar e é incompatível com a página antiga, faça o rollback da API |
| Verificações ou smoke e2e | O piloto está no ar, mas algo não funciona por fora | Leia o relatório do Playwright (artefato do workflow); se for grave, rollback |

Depois de corrigir a configuração, rode de novo em **Actions > Deploy do piloto > Run workflow**
(branch `main`).

**Release que muda o `render.yaml` (P-18):** o Render sincroniza o Blueprint no push da `main` e
publica o commit novo na hora, antes do passo de migração do pipeline. Por isso, uma release com
migração não muda o `render.yaml`; quando precisar dos dois, faça duas releases, a migração primeiro.

**Limite por IP (S30-03):** o último passo do deploy confere que o limite pega o cliente certo pela
página e direto no Render. Se ele ficar vermelho, a Vercel ou o Render mudaram os proxies: rode
`curl -4 -s -X POST -H "Origin: <endereço da Vercel>" <endereço da Vercel>/api/v1/proxy-check`, que
devolve os cabeçalhos de proxy da sua própria requisição e o IP que o limite usaria, e ajuste
`IPC_TRUSTED_PROXY_HOPS`, `IPC_TRUST_FORWARDED_HEADER` ou `IPC_RATE_LIMIT_EDGE_HEADER` no
`render.yaml`.

## Latência ou erros acima da meta (/health/slo)

O `/health/slo` responde 503 quando, nos últimos 5 minutos e com pelo menos 20 requisições, o P95
do `POST /api/v1/validate` passou de 200 ms ou mais de 1% das respostas foram 5xx. O corpo diz o
motivo (`reasons`: `latencia` ou `erros`).

- **Latência no plano gratuito:** a 20 por minuto, o P95 do servidor fica abaixo de 200 ms (S30-09);
  acima disso, a cota de 0,1 CPU segura as rajadas. O piloto fica no gratuito por decisão do autor
  (S30-11, ADR-03): veja se o alerta coincide com um prazo de lista e se as respostas `OVERLOADED`
  subiram; elas são a degradação esperada (NFR-05), não uma falha.
- **Latência no Starter:** veja se o Supabase está lento (**Reports** no painel) e rode o workflow
  "Carga no piloto" com uma taxa baixa, que separa a sessão no banco do analisador.
- **Erros:** os logs do Render mostram o `outcome` de cada requisição (sem código nem IP). Muitos
  `ANALYZER_UNAVAILABLE` ou `DATABASE_UNAVAILABLE` levam às seções abaixo.

### Registro dos exercícios de alerta

Um exercício por período confere que o alerta chega (NFR-15: até 5 min). Como fazer sem tráfego
real: baixe `IPC_SLO_P95_MS` no `render.yaml` por um PR (por exemplo, para 50), rode o workflow
"Carga no piloto" por 10 minutos, acompanhe **Incidents** no UptimeRobot e o e-mail, e volte o valor
para 200 no PR seguinte. Pelo `render.yaml`, e não pelo painel, para o arquivo e o serviço não
divergirem.

| Data | Quem | Como | Linha do tempo (UTC) | Do 503 ao e-mail |
|---|---|---|---|---|
| 08/10/2026 | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` em `2a55908` e `715cd16`; carga de 20 por minuto por 10 min | carga às 09:55:57; 503 entre 09:57:30 e 09:58:01; UptimeRobot detectou (HEAD) às 09:58:18, confirmou de 3 regiões às 09:59:01 e enviou o e-mail às 09:59:02 | 61 a 92 s |

## Banco fora do ar (DATABASE_UNAVAILABLE)

O `/ready` responde 503, a página não entra nem verifica, e o `/health/service` continua 200 (a
instância não reinicia por causa do banco).

1. No Supabase, veja se o projeto foi **pausado** (o plano gratuito pausa depois de 7 dias sem
   atividade). Se foi, clique em **Restore**; o monitor do `/ready` no UptimeRobot evita isso.
2. Veja **Database > Connection pooling**: a `IPC_DATABASE_URL` do Render usa o *Session pooler*,
   com o usuário `ipc_api`.
3. Se a senha do `ipc_api` mudou, atualize `IPC_DATABASE_URL` no Render e `PILOT_DB_API_PASSWORD` no
   GitHub.

## Analisador indisponível (ANALYZER_UNAVAILABLE)

O `/health/service` e o `/ready` respondem 503. No Render, o log mostra o motivo:

- **Filtro seccomp recusado** (`IPC_SANDBOX=required`, fail-closed): o Render não aceitou o filtro
  dos workers (P-12 b). A alternativa é `IPC_SANDBOX=optional`, com o risco das ameaças 2 e 6 em
  Médio (blueprint, 5.4); registre a decisão.
- **Ruleset inválido:** o analisador não sobe com um ruleset ou uma questão inválida (FR-15). Isso
  não deveria passar da CI (`ipc-rules validate`); faça o rollback e corrija por PR.

## Segredos

Trocar um segredo (vazou, ou alguém saiu da equipe técnica):

| Segredo | Onde trocar | Depois |
|---|---|---|
| Senha do `ipc_api` | Supabase (SQL: `ALTER ROLE ipc_api PASSWORD ...`, ou a migração com `--login-role`) | `IPC_DATABASE_URL` no Render e `PILOT_DB_API_PASSWORD` no GitHub |
| Senha do `postgres` | Supabase, **Project Settings > Database** | `PILOT_DATABASE_ADMIN_URL` no GitHub |
| Chave do Brevo | Brevo, **SMTP & API > API Keys** (crie a nova e apague a velha) | `IPC_EMAIL_API_KEY` no Render |
| Cliente OAuth do Google | Google Cloud, **Credentials** | `IPC_GOOGLE_CLIENT_SECRET` no Render |
| Chaves das IAs | Painel de cada provedor | `IPC_LLM_API_KEY` e `IPC_LLM_FALLBACK_API_KEY` no Render |
| Deploy hooks | Render (**Settings > Deploy Hook**, regenerar) e Vercel (apagar e criar) | `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL` no GitHub |
| Segredo da página (`IPC_EDGE_SECRET`) | Gere um novo (abaixo) | Vercel e Render, na ordem abaixo |

Trocar uma variável no Render reinicia o serviço; as sessões abertas continuam válidas, porque
ficam no banco.

### Segredo da página (`IPC_EDGE_SECRET`, S30-03)

Com ele, a API só atende `/api/*` pela página: o middleware da Vercel o manda junto, e o Render
responde 403 ao que chega sem ele. O mesmo valor fica nos dois painéis e em nenhum outro lugar.
Para ligar ou trocar, sem derrubar a página:

1. No Git Bash, gere o valor e copie para a área de transferência, sem mostrá-lo:
   `openssl rand -hex 32 | tr -d '\n' | clip`.
2. **Vercel primeiro:** no projeto, **Settings > Environment Variables**, crie (ou edite)
   `IPC_EDGE_SECRET` em **Production**, cole o valor e marque como **Sensitive**. Depois rode o
   "Deploy do piloto" (**Actions > Deploy do piloto > Run workflow**, branch `main`): só um deploy
   novo da página lê o valor. Enquanto o Render não o tem, ele ignora o cabeçalho.
3. **Render depois:** no serviço, **Environment**, preencha `IPC_EDGE_SECRET` com o mesmo valor e
   salve. O serviço reinicia em cerca de 1 minuto e passa a recusar o acesso direto.
4. Limpe a área de transferência (`echo limpo | clip`) e confira: rode o "Deploy do piloto" de
   novo. O último passo verifica que `/api/*` direto no Render recebe 403 e que a página continua
   funcionando.

Para desligar, apague a variável no Render primeiro e depois na Vercel. Um valor com menos de 32
caracteres faz a API não subir (o deploy fica vermelho, e a versão anterior continua no ar).

## Conta de verificação do deploy

Uma conta ativa (monitor), usada só pelas verificações e pelo smoke e2e do pipeline e pelo workflow
"Carga no piloto". O login e a senha ficam nos secrets `PILOT_CHECK_LOGIN`, `PILOT_CHECK_PASSWORD` e
`PILOT_CHECK_NAME`. A cada deploy, o passo das migrações a marca no banco (`check_account`, S28-02):
as verificações dela não entram na telemetria, e ela não conta como membro no relatório de eficácia.

- **Trocar a conta:** crie a nova pela página (registro, e-mail, aprovação como monitor), troque os
  três secrets e rode o "Deploy do piloto". A marca passa para a nova, e a antiga perde a marca;
  remova a antiga em **Gerenciar**.
- **Trocar a senha:** pelo perfil da conta e, depois, no secret `PILOT_CHECK_PASSWORD`.

## Backup

O workflow "Backup do banco do piloto" (`.github/workflows/backup.yml`, S28-03) roda todo dia às
06:00 UTC (diário desde a S30-12, para o RPO de 24 h da NFR-20) e à mão. Ele faz o `pg_dump` dos esquemas `app` (contas, sessões, registro de gerenciamento, cota de
feedback e adoção) e `telemetry`, confere o dump com o `pg_restore --list`, criptografa com o
[age](https://github.com/FiloSottile/age) e guarda o arquivo como artefato do workflow por 90 dias.
O dump tem dados pessoais da equipe (nomes, e-mails e resumos de senha), por isso só sai
criptografado. Sem a variável `BACKUP_AGE_RECIPIENT`, o workflow só avisa e não faz nada.

Configuração, uma vez, no Git Bash:

```bash
age-keygen -o ipc-backup.key
```

O comando mostra a chave pública (`age1...`). Grave-a no GitHub; ela não é segredo:

```bash
gh variable set BACKUP_AGE_RECIPIENT --repo Lionzio/ip-checker --body "age1..."
```

A chave privada (`ipc-backup.key`) fica **fora do GitHub e do computador do dia a dia**, num
gerenciador de senhas ou num pendrive guardado. Sem ela, nenhum backup abre; com ela, todos.

### Restaurar um backup

1. Em **Actions > Backup do banco do piloto**, abra a execução da data desejada e baixe o artefato
   (`ipc-piloto-AAAA-MM-DD`). Confira o arquivo: `sha256sum -c ipc-piloto-*.sha256`.
2. Decifre: `age --decrypt -i ipc-backup.key -o dump ipc-piloto-AAAA-MM-DD.dump.age`.
3. **Ensaio, sem tocar no piloto:** suba um PostgreSQL descartável, aplique as migrações e restaure
   só os dados:

   ```bash
   docker run -d --name ipc-restore -e POSTGRES_PASSWORD=ensaio -e POSTGRES_DB=ipchecker -p 127.0.0.1:55433:5432 postgres:17-alpine
   cd backend
   IPC_DATABASE_ADMIN_URL=postgresql://postgres:ensaio@127.0.0.1:55433/ipchecker IPC_DB_LOGIN_PASSWORD=ensaio uv run python -m ipc_api.db.migrate up --login-role ipc_api
   docker exec -i ipc-restore pg_restore --data-only --disable-triggers -U postgres -d ipchecker < ../dump
   ```

   Compare as linhas por tabela com as do momento do backup, que vêm no artefato
   (`ipc-piloto-AAAA-MM-DD.contagens.txt`) e no resumo do run (S30-07):

   ```bash
   docker exec -i ipc-restore psql -U postgres -d ipchecker -X -A -F " | " -t < ../deploy/backup/contagens.sql | diff - ipc-piloto-AAAA-MM-DD.contagens.txt
   ```

   Sem diferença, a restauração está certa. Apague o contêiner e o `dump`.
4. **No piloto, de verdade:** só depois do ensaio. Avise a equipe, rode o backup à mão (para guardar
   o estado atual), apague os dados das tabelas afetadas e restaure com o mesmo
   `pg_restore --data-only`, usando a `PILOT_DATABASE_ADMIN_URL`. Depois, `/ready` e um login.

O ensaio de restauração é feito uma vez por semestre (NFR-20) e anotado aqui:

| Data | Quem | Backup de | Resultado |
|---|---|---|---|
| 08/10/2026 | Claude (agente), pelo autor | `ipc-piloto-2026-10-08` (run 37753358195) | Hash conferido, migrações e dados restaurados, linhas iguais nas 9 tabelas; RTO técnico de 9 s, sem contar o acesso à chave privada (NFR-20: até 30 min) |

## Incidentes de segurança

Um vazamento de segredo, um acesso indevido a uma conta, um código de aluno que apareceu fora do
lugar (log, banco, disco) ou uma falha no isolamento do analisador. Como relatar está no
[`SECURITY.md`](../SECURITY.md).

1. **Conter:** troque o segredo (seção "Segredos"); remova a conta afetada em **Gerenciar** (as
   sessões dela acabam na hora); se for o isolamento, faça o rollback.
2. **Registrar:** uma linha na tabela abaixo, sem dados pessoais nem código de aluno.
3. **Corrigir:** por PR, com um teste que reproduz o problema.
4. **Avisar:** a coordenação da disciplina, quando dados pessoais da equipe foram expostos.

O critério 5 da P-09 conta os incidentes desta tabela ([`eficacia.md`](eficacia.md)).

| Data | O que aconteceu | Contenção | Correção (PR) |
|---|---|---|---|
| — | Nenhum incidente registrado | | |

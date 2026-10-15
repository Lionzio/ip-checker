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
| Os jobs do GitHub Actions não começam ("spending limit") | Sem GitHub Actions (cota esgotada) |

## Voltar para a versão anterior (rollback)

A meta da DoD é voltar em até 5 minutos, contados do início do passo 1 até o passo 3 conferido.
Os dois serviços guardam os deploys anteriores, então o caminho mais rápido é pelos painéis; o Git
vem depois, para a `main` não publicar o erro de novo. Cronometre e anote no registro dos ensaios
(abaixo), inclusive quando for de verdade.

1. **API (Render):** no serviço `ip-checker-api`, abra **Events**, escolha o último deploy que
   funcionava e clique em **Rollback**. O Render sobe a imagem anterior e só troca quando ela
   responde `/health/service`.
2. **Página (Vercel):** em **Deployments**, abra o deploy anterior de Production, use
   **Deployment Actions > Instant Rollback** e confirme duas vezes (**Continue** e **Confirm
   Rollback**). No plano Hobby, só dá para voltar ao deploy imediatamente anterior. Depois de um
   Instant Rollback, os deploys novos não entram em Production sozinhos: para voltar à versão
   atual, abra o deploy dela e use **Deployment Actions > Promote**, que desfaz o rollback.
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
| 08/10/2026 | Claude (agente), com o autor cronometrando | `8104253` → `64649b3` e volta | Rollback pedido às 08:29 e no ar às 08:30 (cerca de 1 min) | Instant Rollback no ar às 08:33:30, segundos depois da confirmação | Cerca de 4 min, com o tempo de achar o menu da Vercel (meta: até 5 min) | Horário de Brasília. A volta: Vercel por **Promote** às 08:34:52 e Render às 08:40:30 (o primeiro clique de confirmação no Render não pegou, com a página ainda carregando). Releases depois da volta: `8104253` nos dois |

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

Desde a Sprint 34 (S34-04), um exercício **a cada release**, depois do deploy, confere que o
alerta chega (NFR-15: até 5 min); o `scripts/release.sh` lembra no fim. Como fazer sem tráfego
real: baixe `IPC_SLO_P95_MS` no `render.yaml` por um PR (por exemplo, para 50), rode a carga por
10 minutos (o workflow "Carga no piloto" ou, sem a cota do Actions, `scripts/carga-piloto.sh 20
10m`, que pede a senha da conta de verificação sem mostrá-la), acompanhe **Incidents** no
UptimeRobot e o e-mail, e volte o valor para 200 no PR seguinte. Pelo `render.yaml`, e não pelo
painel, para o arquivo e o serviço não divergirem. Os dois PRs só mudam o `render.yaml`, então o
Render publica sozinho (P-18), sem migração. Acrescente uma linha à tabela.

| Data | Quem | Como | Linha do tempo (UTC) | Do 503 ao e-mail |
|---|---|---|---|---|
| 08/10/2026 | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` em `2a55908` e `715cd16`; carga de 20 por minuto por 10 min | carga às 09:55:57; 503 entre 09:57:30 e 09:58:01; UptimeRobot detectou (HEAD) às 09:58:18, confirmou de 3 regiões às 09:59:01 e enviou o e-mail às 09:59:02 | 61 a 92 s |
| 11/10/2026 (release `sprint-34`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #76 (`bf74834`) e de volta a 200 no PR seguinte; carga de 20 por minuto por 10 min pelo `scripts/carga-piloto.sh` | carga das 13:26:46 às 13:36:49 (200 verificações, todas 200); 503 desde 13:26:53, primeiro pelo motivo `erros` (1 erro 5xx em 41 requisições, da troca de instância do deploy) e só por `latencia` desde 13:28:17 (P95 de 140 a 192 ms); e-mail recebido às 13:31 | cerca de 4 min do primeiro 503 e 3 min do 503 por latência |
| 11/10/2026 (release `sprint-35`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #86 (`581c159`) e de volta a 200 no PR seguinte; carga de 20 por minuto por 10 min pelo `scripts/carga-piloto.sh` | carga das 17:13:34 às 17:23:38 (200 verificações, todas 200); 503 desde 17:13:43, primeiro por `erros` (o deploy logo antes) e só por `latencia` desde 17:15:47 (P95 de 145 a 225 ms); e-mail de queda recebido às 17:16; com o limite de volta a 200 (deploy às 17:25:50), e-mail de volta às 17:26 | cerca de 2 min do primeiro 503 e 1 min e meio do 503 por latência |
| 12/10/2026 (release `sprint-36.1`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #103 (`0217ee4`) e de volta a 200 pelo #104 (`c875d7d`); carga de 20 por minuto por 10 min pelo ajudante do terminal da Sprint 36 (`scripts/carga-piloto.sh`) | deploy pelo Blueprint às 19:10:16; carga das 19:10:25 às 19:20:28 (201 verificações, todas 200); 503 só por `latencia` desde 19:11:37 (P95 de 53 a 196 ms); e-mail de queda recebido às 19:16; com o limite de volta a 200 (deploy às 19:22:02), e-mail de volta às 19:26 | cerca de 4 min e meio do primeiro 503 |
| 14/10/2026 (release `sprint-37`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #113 (`1b2f925`) e de volta a 200 pelo #114 (`9ed739e`); carga de 20 por minuto por 10 min com `scripts/carga-piloto.sh`, rodado pelo autor no Git Bash | deploy pelo Blueprint às 18:32:54; carga desde 18:35:33; 503 por `latencia` desde 18:37:54 (P95 de 163 ms); e-mail de queda recebido às 18:41; depois da carga, o motivo virou `erros` (18:49:37 a 18:52:51: algumas respostas 5xx da carga ficaram na janela de 5 min e, com o tráfego caindo, passaram de 1%); `/health/slo` em 200 às 18:53:02; limite de volta a 200 (deploy às 18:54:58); e-mail de volta às 18:56 | cerca de 3 min do primeiro 503 |
| 15/10/2026 (release `sprint-38`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #118 (`3359c3d`) e de volta a 200 pelo #120 (`812fce5`); carga de 20 por minuto por 10 min com `scripts/carga-piloto.sh`, rodado pelo autor | deploy pelo Blueprint às 12:11 (horário de Brasília); carga desde 12:13:17; 503 por `latencia` desde 12:14:11 (P95 de 187 a 210 ms); e-mail de queda recebido às 12:15; carga até cerca de 12:23; limite de volta a 200 (deploy às 12:25:43), com o `/health/slo` em 200 desde 12:25:31 (a instância nova zerou a janela); e-mail de volta às 12:30 | cerca de 1 min do primeiro 503 |
| 15/10/2026 (release `sprint-38.1`) | Claude (agente), pelo autor | `IPC_SLO_P95_MS=50` pelo #123 (`82150de`) e de volta a 200 pelo #124 (`b6a83ed`); carga de 20 por minuto por 10 min com `scripts/carga-piloto.sh`, rodado pelo autor | deploy pelo Blueprint às 13:14:39 (horário de Brasília); carga desde 13:15:29; 503 só por `latencia` desde 13:16:33 (P95 de 171 a 205 ms), sem nenhum `erros` (a correção da conexão com o analisador); e-mail de queda recebido às 13:17; limite de volta a 200 (deploy às 13:27:39), com o `/health/slo` em 200 desde 13:27:36; e-mail de volta às 13:28 | cerca de 1 min do primeiro 503 |

## Sintético diário (S34-02)

O workflow "Sintético diário" (`synthetic.yml`) roda nos dias úteis às 07:00 (horário de
Brasília): entra pela página com a conta de verificação, verifica uma solução da Lista 1 e sai.
Ele falha com qualquer erro ou com a verificação acima de 300 ms **no servidor**, medida pelo
cabeçalho `Server-Timing` da `/api/v1/validate` (o tempo dentro da API, como o NFR-01 e o
`/health/slo`). A falha chega pelo e-mail do GitHub Actions. Sem a cota, rode
`scripts/sintetico-local.sh` (pede a senha sem mostrá-la).

- **Erro no login ou 5xx:** siga as seções de banco e de analisador abaixo; o `request_id` está na
  mensagem da falha, para achar a linha nos logs do Render.
- **Acima de 300 ms:** rode de novo. Se repetir, veja o `/health/slo` e a seção de latência acima;
  um caso isolado logo depois de um deploy é o analisador aquecendo.
- **504 da Vercel:** o Render dormiu ou reiniciou; confira o monitor do `/ready` no UptimeRobot.

## Canário mensal (S35-04)

Confere que o código verificado não fica guardado (NFR-11). No dia 1 de cada mês, o workflow
"Canário mensal" (`canary.yml`) planta uma marca única (`canario_<data>_<aleatório>`) num código
verificado, comparado e usado no feedback pela página, com a conta de verificação, e procura a
marca em todas as tabelas dos esquemas `app` e `telemetry` do banco do piloto. Sem a cota do
Actions, rode `scripts/canario-local.sh`, que pede a senha da conta de verificação e a connection
string do Supabase sem mostrá-las.

1. **Banco:** o script diz quantas colunas conferiu e falha se achar a marca em alguma. O esperado
   é "nenhuma ocorrência". A conta de verificação não gera telemetria (S28-02); o canário confere
   as tabelas que ela toca (sessão, cota de feedback e registro) e o esquema inteiro.
2. **Logs, pelo painel (decisão do autor, 11/10/2026: sem chave de API do Render):** em **Render >
   ip-checker-api > Logs**, busque a marca que o script mostrou, na última hora. O esperado é
   nenhuma linha. A mesma busca vale para o analisador, que escreve no mesmo log.
3. **Achou a marca?** É vazamento do código dos alunos: siga "Incidentes de segurança" abaixo, com
   a coluna (ou a linha do log) que o script ou o painel mostraram.

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
| Chaves das IAs | Painel de cada provedor | `IPC_LLM_<NOME>_API_KEY` de cada IA da cadeia (ou `IPC_LLM_API_KEY` e `IPC_LLM_FALLBACK_API_KEY`) no Render |
| Deploy hooks | Render (**Settings > Deploy Hook**, regenerar) e Vercel (apagar e criar) | `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL` no GitHub |
| Segredo da página (`IPC_EDGE_SECRET`) | Gere um novo (abaixo) | Vercel e Render, na ordem abaixo |
| Credencial dos gabaritos (`IPC_GABARITOS_TOKEN`) | GitHub, **Settings > Developer settings > Fine-grained tokens** (regenerar ou criar outra) | `IPC_GABARITOS_TOKEN` no Render (abaixo) |

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

Depois do passo 2, antes de mexer no Render, confira que a página já manda o segredo: o
diagnóstico pela página mostra o cabeçalho `x-ipc-client-ip`, que o middleware só acrescenta
quando tem o segredo (`curl -4 -s -X POST -H "Origin: <endereço da Vercel>"
<endereço da Vercel>/api/v1/proxy-check`). O "Deploy do piloto" de um commit que já está no ar não
espera a página nova, porque o `/version.json` não muda. Com o segredo também no Render, o mesmo
diagnóstico mostra `"edge_verified": true`.

Para desligar, apague a variável no Render primeiro e depois na Vercel. Um valor com menos de 32
caracteres faz a API não subir (o deploy fica vermelho, e a versão anterior continua no ar).

### Credencial dos gabaritos (`IPC_GABARITOS_TOKEN`, S32-01)

A comparação com o gabarito (ADR-11) usa os gabaritos do repositório privado
`Lionzio/ip-checker-gabaritos`, que a API baixa ao subir e guarda só na memória. A credencial é
um *fine-grained token* do GitHub, só de leitura e só desse repositório. Quem cria e cola é o autor;
o valor nunca vai para o Git, para uma conversa nem para o log.

1. No GitHub: **Settings > Developer settings > Personal access tokens > Fine-grained tokens >
   Generate new token**. Nome: `ip-checker-render-gabaritos`. Expiração: **No expiration** (sem
   vencimento), como o token em uso, criado em 10/10/2026 (S32-01; decisão do autor de 12/10/2026, P-23). **Resource
   owner**: Lionzio. **Repository access**: *Only select repositories*,
   `Lionzio/ip-checker-gabaritos`. **Permissions > Repository permissions > Contents**: *Read-only*
   (o *Metadata: Read-only* vem junto). Nada mais.
2. Clique em **Generate token** e use **Copy** (o valor só aparece uma vez).
3. No Render, no serviço, **Environment**: preencha `IPC_GABARITOS_TOKEN` com o valor e salve. O
   serviço reinicia em cerca de 1 minuto. `IPC_GABARITOS_REPO` já vem do `render.yaml`.
4. Confira, na página: escolha uma lista com gabarito e veja as questões dele no seletor (por
   exemplo, "L1-Q1: sem regra cadastrada (comparação com o gabarito)"). Nos logs do Render, a linha
   `gabaritos carregados: N` diz quantos entraram, sem nenhum caminho nem conteúdo.

**Gabaritos indisponíveis** (a página avisa "Os gabaritos não estão disponíveis neste servidor
agora"): nos logs do Render, a linha `gabaritos indisponíveis: ...` diz o tipo da falha. "o GitHub
respondeu 401" é credencial revogada ou apagada (o token não vence): troque-a (passos acima). "respondeu 404" é o nome do
repositório ou a branch errados, ou o token sem acesso a ele. A verificação e o plágio continuam
funcionando sem a comparação.

**Quando trocar o token (P-23):** como ele não vence, a troca é por evento, nunca por data:
- suspeita de que o valor vazou (apareceu num log, num print, num chat ou num repositório);
- mudança de quem administra a conta Lionzio ou o serviço no Render;
- "o GitHub respondeu 401" nos logs do Render.

Para trocar, gere um token novo (passos 1 a 3) e, depois de conferir a página (passo 4), apague o
antigo em **Fine-grained tokens > Delete**. O token é só de leitura e só do repositório dos
gabaritos, o que limita o estrago de um vazamento, mas um token sem vencimento continua valendo
até ser apagado.

**Gabarito novo:** a API só lê os gabaritos ao subir. Depois de um push no repositório dos
gabaritos, reinicie o serviço no Render (**Manual Deploy > Restart service**) para que os novos
entrem na comparação.

### IAs do Aprimorar com IA (S32-11)

O **Aprimorar com IA** (Q-16) usa uma cadeia de provedores gratuitos. Quem cria as contas e as
chaves é o autor; os valores ficam só no Render.

1. **Gemini:** no Google AI Studio, crie uma chave de API do plano gratuito e escolha um modelo
   disponível nele [A CONFIRMAR no painel: os modelos gratuitos mudam].
2. **Groq:** no console da Groq, crie uma chave de API e escolha um modelo do plano gratuito
   [A CONFIRMAR no painel].
3. No Render, **Environment**, preencha (as chaves por último, copiadas do painel de cada um):
   `IPC_LLM_CHAIN` = `gemini,groq`; `IPC_LLM_GEMINI_PROVIDER` = `gemini`; `IPC_LLM_GEMINI_MODEL`;
   `IPC_LLM_GEMINI_API_KEY`; `IPC_LLM_GROQ_PROVIDER` = `openai_compat`; `IPC_LLM_GROQ_BASE_URL` =
   `https://api.groq.com/openai/v1`; `IPC_LLM_GROQ_MODEL`; `IPC_LLM_GROQ_API_KEY`. Salve: o serviço
   reinicia. Uma configuração incompleta (um nome da cadeia sem provedor, sem modelo ou sem chave)
   impede a API de subir, com a mensagem do que falta: a versão anterior continua no ar.
4. Confira na página: depois de **Gerar feedback**, aparece **Aprimorar com IA**; o texto
   aprimorado diz qual IA escreveu.

**Mais uma IA:** acrescente o nome em `IPC_LLM_CHAIN` (na posição em que ela deve ser tentada) e as
variáveis `IPC_LLM_<NOME>_*`. **Cota esgotada:** a IA que responde 429 fica fora da cadeia por 60 s
(`IPC_LLM_COOLDOWN_S`) e a seguinte responde; se todas estiverem sem cota, a página fica com o
texto sem IA e um aviso. **Trocar de provedor:** mude a ordem ou os nomes em `IPC_LLM_CHAIN`.

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

## Sem GitHub Actions (cota esgotada)

Em repositório privado, o GitHub Free dá 2.000 minutos de Actions por mês, somados entre **todos**
os repositórios privados da conta (P-19). Quando acabam, e com o limite de gastos em US$ 0, nenhum
job começa: o run aparece como falha, sem passos, e a anotação diz "recent account payments have
failed or your spending limit needs to be increased". A cota volta no dia 1º do mês seguinte (veja
o uso em **Settings > Billing and plans > Usage**, produto Actions).

Até lá, nada roda sozinho: CI, "Deploy do piloto", backup diário, auditoria e carga. O piloto
continua no ar, e o UptimeRobot continua avisando. O que fazer:

- **Antes de cada merge,** rode a CI nesta máquina e cole o resumo no PR:
  `scripts/ci-local.sh` (com `--e2e` para o smoke também; `--rapido` só para iterar). O merge
  segue a regra de sempre, com o resumo local no lugar da CI verde.
- **Canário:** `scripts/canario-local.sh` faz o "Canário mensal" desta máquina (S35-04).
- **Sintético e carga:** `scripts/sintetico-local.sh` faz o "Sintético diário" e
  `scripts/carga-piloto.sh` faz a "Carga no piloto" (exercício de alerta), desta máquina.
- **Backup:** rode `scripts/backup-local.sh` pelo menos uma vez por semana (o RPO do dia a dia fica
  em até 7 dias enquanto a cota não volta). Ele pede a connection string do Supabase sem mostrá-la
  e salva só o arquivo criptografado em `~/Desktop/IP-Checker/backups/piloto`. Guarde uma cópia
  fora do computador.
- **Release:** `scripts/release.sh NN --ci-local` (decisão do autor de 09/10/2026) aceita, no lugar
  da CI do Actions, uma rodada completa e sem falha do `scripts/ci-local.sh --e2e` na mesma árvore
  da ponta da `develop`; rode a CI local de novo na `develop` atualizada se o último PR não foi o
  último commit testado. A `main` e a tag avançam, e o deploy é à mão, como abaixo.
- **Deploy:** evite até a cota voltar. Se precisar (correção urgente ou release com `--ci-local`),
  siga a ordem do pipeline à mão: as migrações com `uv run python -m ipc_api.db.migrate up --login-role ipc_api` (a connection
  string de admin em `IPC_DATABASE_ADMIN_URL`, digitada só no terminal), depois o Render
  (**Manual Deploy > Deploy latest commit**) e, com o `/ready` no commit novo, a Vercel (o deploy
  hook do projeto, em **Settings > Git > Deploy Hooks**, chamado com `curl -X POST`). Confira com
  `curl -s <endereço do Render>/ready` e `<endereço da Vercel>/version.json`.
- **Quando a cota voltar (01/11/2026, S33-10),** nesta ordem:
  1. **Actions > CI > Run workflow** na `develop`: o job "Gabaritos" precisa rodar (não *skipped*)
     e passar, e o job "Auditoria" também.
  2. **Actions > Deploy do piloto > Run workflow** na `main`: as verificações do piloto, com a conta
     de verificação, o smoke e2e e o limite por IP, conferem tudo o que foi publicado à mão desde
     08/10/2026.
  3. **Actions > Backup do banco do piloto > Run workflow**: confira o artefato cifrado.
  4. **Actions > Auditoria de segurança > Run workflow**: a primeira rodada bloqueante no Actions
     (S31-03), com o Trivy.
  5. **Actions > Sintético diário > Run workflow**: depois, ele roda sozinho nos dias úteis (S34-02).
  6. Volte a usar a CI do Actions nos PRs e o `scripts/release.sh NN` sem `--ci-local`. O
     `ci-local.sh` continua para conferir antes do PR.

Para gastar menos minutos (08/10/2026): a CI da `main` e a da `develop` depois do merge só
conferem que o mesmo conteúdo já passou no PR; um PR que só muda `.md` não roda os testes; e
vários pushes seguidos no mesmo PR cancelam a rodada anterior. Juntar mudanças pequenas num PR só
também ajuda.

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

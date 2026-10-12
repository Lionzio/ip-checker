# Piloto (Render + Vercel, Fase 1)

Separado do `deploy/README.md` na S28-03. O que fazer quando algo dá errado no piloto está no
[runbook](../docs/runbook.md).


No piloto de 2027.1 (ADR-03), a página fica na Vercel e o backend num único serviço Docker no
Render, no plano gratuito. O Render não tem rede interna nem flags de contêiner, então o isolamento
entre a API e o analisador é feito por processo (`deploy/render/`):

| Processo | Usuário | O que recebe | Isolamento |
|---|---|---|---|
| `supervisord` | root | O ambiente do Render | Só inicia os outros dois; não abre socket de controle |
| `api` | 10001 | O ambiente do Render (banco, e-mail, Google, limites) | Porta pública do Render |
| `analyzer` | 10002 | Ambiente vazio (`env -i`), só 6 variáveis próprias | Escuta só em `127.0.0.1:8001`; workers com seccomp (sem `socket`, `socketpair`, `execve` nem `execveat`), `RLIMIT_AS` de 160 MiB, `RLIMIT_FSIZE` 0 e `RLIMIT_NOFILE` 32 |

Desde a Sprint 16, a página e a API ficam na **mesma origem** (ADR-04): a Vercel repassa
`/api/*` ao Render por *rewrite* (`frontend/scripts/vercel-config.mjs`). O navegador só fala com o
endereço da Vercel, o cookie da sessão fica nele e o CORS deixa de existir. A API aceita, nas
requisições que mudam estado, o `Origin` de `IPC_PUBLIC_BASE_URL` (o endereço da página), porque
atrás do *rewrite* ela vê o `Host` do Render. O *rewrite* com o cookie `__Host-` e o feedback em
até 30 s foram confirmados no piloto em 08/10/2026 (P-15 a, S30-02).

**IP do cliente (P-12 e P-15 b, S30-03).** A suposição antiga, o cliente como penúltimo endereço do
`X-Forwarded-For` (`IPC_TRUSTED_PROXY_HOPS=2`), não valia: a borda do Render acrescenta duas
entradas e não limpa o valor do cliente. Com a configuração atual do `render.yaml`, a API acha o
cliente nesta ordem (`ipc_api.ratelimit.client_ip`):

1. o IP que o middleware da página manda junto com o segredo `IPC_EDGE_SECRET`, quando o segredo
   confere;
2. o `for=` do cabeçalho `Forwarded`, que a Vercel sempre reescreve com o IP real
   (`IPC_TRUST_FORWARDED_HEADER=1`);
3. a 4ª entrada do `X-Forwarded-For` a partir do fim, ou a primeira quando há menos de 4
   (`IPC_TRUSTED_PROXY_HOPS=4`): pela página, as entradas são o cliente, a saída da Vercel, o
   Cloudflare e um proxy interno do Render.

Sem sessão, um segundo limite, de 60 por minuto, usa o `cf-connecting-ip`, que o Cloudflare do
Render escreve e o cliente não forja (`IPC_RATE_LIMIT_EDGE_HEADER`). Com `IPC_EDGE_SECRET` no
Render, `/api/*` só atende pela página: o que chega direto no Render sem o segredo recebe 403.

O UID 10002 não lê o ambiente da API nem o do supervisord: o kernel só permite isso ao dono. Com
`IPC_SANDBOX=required`, se o Render não permitir o filtro seccomp, nenhum worker nasce e o `/ready`
nunca fica verde, ou seja, o deploy falha em vez de subir sem o isolamento.

`backend/tests/security/test_pilot_isolation.py` sobe a imagem do piloto como o Render a roda e
confere tudo isso na CI, inclusive o pior caso de 50 KB dentro dos 160 MiB por worker.

## Como o deploy acontece

```
develop ──(release: fast-forward)──> main ──> CI ──(verde)──> deploy.yml
    instala as ferramentas (sem segredos) ──> confere que o commit é a ponta da main
    ──> migrações no banco do piloto ──> hook do Render ──> espera /ready com a versão nova
    ──> hook da Vercel ──> espera /version.json com a versão nova
    ──> confere mesma origem, cabeçalhos, TLS e login (backend/tests/pilot) ──> smoke e2e com login
```

A página só é publicada depois que a API nova está no ar (S25-02): se o Render falhar, a página
antiga continua conversando com a API antiga. Se outra release chegar à `main` durante o deploy,
o deploy anterior para antes de publicar, e o novo segue na fila. O deploy também pode ser
disparado à mão em **Actions > Deploy do piloto > Run workflow** (só na `main` e só com a CI daquele
commit verde): é assim que se faz o primeiro deploy depois de configurar as contas. O rollback está
em [`docs/runbook.md`](../docs/runbook.md).

O Render e a Vercel estão com o deploy automático desligado (`render.yaml` e `frontend/vercel.json`):
nada vai ao ar sem a CI verde na `main`. Enquanto o piloto não estiver configurado no GitHub, o
pipeline só avisa e não faz nada. As migrações rodam antes da versão nova subir, então cada uma
precisa servir também à versão que ainda está no ar (só acrescentar tabelas e colunas; remover
fica para uma migração de uma release seguinte).

## Passo a passo da configuração (uma vez)

Estes passos são feitos por você nos painéis, com as suas contas. Nenhum segredo entra no
repositório.

1. **Release na `main`.** O Render e a Vercel leem a `main`, que precisa ter o código da última
   sprint concluída (no mínimo a Sprint 16, que trouxe o login e a mesma origem):

   ```bash
   git switch main && git merge --ff-only develop && git push origin main
   ```

   Sem as variáveis do passo 8, a CI roda e o deploy só avisa que o piloto não está configurado.

2. **Banco (Supabase).** Em <https://supabase.com>, crie um projeto na região East US (North
   Virginia), a mesma da API no Render (Q-20). Use na senha do banco só letras, números, `-` e `_`
   (ela vai dentro de uma URL; o botão de gerar senha do Supabase serve). No botão **Connect** do
   projeto, copie a *connection string* do **Session pooler** (porta 5432; os executores do GitHub
   não alcançam o endereço direto, que é só IPv6, e o *Transaction pooler*, porta 6543, não serve à
   API). Ela tem o formato
   `postgresql://postgres.<id do projeto>:<senha>@aws-0-us-east-1.pooler.supabase.com:5432/postgres`
   e é a `PILOT_DATABASE_ADMIN_URL` do passo 8. Escolha também uma senha para o usuário da API,
   `ipc_api` (`PILOT_DB_API_PASSWORD`, também só com letras, números, `-` e `_`); a migração cria
   esse usuário. A `IPC_DATABASE_URL` do Render é a mesma *connection string*, trocando
   `postgres.<id do projeto>` por `ipc_api.<id do projeto>` e a senha pela do `ipc_api`.

   Para gerar uma senha assim, no terminal: `python -c "import secrets; print(secrets.token_urlsafe(24))"`.

   Ainda no Supabase, em **Project Settings > API**, desligue a **Data API**: o IP-Checker fala
   com o banco só pela *connection string*, e a Data API exporia o esquema `public` às chaves
   anônimas. O controle das migrações já fica num esquema próprio, `ipc_meta`, sem acesso público.
   O plano gratuito pausa um projeto sem atividade por 7 dias; o monitor do `/ready` do passo 9
   consulta o banco a cada 5 minutos e evita a pausa.

2b. **Migrar o banco antes de criar o serviço no Render.** O `/ready` do Render consulta o banco, e o
   primeiro build do Render acontece logo que o serviço é criado. Rode a migração da sua máquina
   (Git Bash, na pasta do repositório), com os valores do passo 2:

   ```bash
   cd backend
   read -rs -p "Connection string do Session pooler (usuário postgres): " IPC_DATABASE_ADMIN_URL; echo
   read -rs -p "Senha escolhida para o ipc_api: " IPC_DB_LOGIN_PASSWORD; echo
   export IPC_DATABASE_ADMIN_URL IPC_DB_LOGIN_PASSWORD
   .venv/Scripts/python.exe -m ipc_api.db.migrate up --login-role ipc_api
   unset IPC_DATABASE_ADMIN_URL IPC_DB_LOGIN_PASSWORD
   ```

   O `read -s` pede os valores sem mostrá-los na tela nem guardá-los no histórico do terminal. No
   Linux ou no macOS, o Python do ambiente é `.venv/bin/python` (ou `uv run python`). A saída lista
   as migrações aplicadas e não mostra nenhuma senha. Depois disso, o pipeline aplica só as
   migrações novas a cada release.

3. **E-mail (Brevo).** Em <https://www.brevo.com>, verifique o remetente (o endereço que vai em
   `IPC_EMAIL_FROM`) e crie uma chave de API em **SMTP & API > API Keys**. Antes de usar um
   remetente `@cin.ufpe.br`, confira com o NTI se o SPF, o DKIM e o DMARC do domínio aceitam o envio
   por terceiros (Q-17); senão, os e-mails caem no spam ou são recusados.

4. **Render.** Em <https://dashboard.render.com>, **New > Blueprint**, conecte o repositório
   `Lionzio/ip-checker` e confirme o `render.yaml`. Ele cria o serviço `ip-checker-api` (Docker,
   plano Free, região Virginia). O assistente pede as variáveis marcadas com `sync: false`:
   preencha-as já ali, com os valores do passo 7, para o primeiro build subir completo. O endereço
   da Vercel (`IPC_PUBLIC_BASE_URL`) só existe depois do passo 5: se ainda não o tiver, use
   `https://ip-checker.vercel.app` e corrija depois (cada mudança de variável reinicia o serviço).
   Anote o endereço do serviço, por exemplo `https://ip-checker-api.onrender.com` (se o nome estiver
   ocupado, o Render acrescenta um sufixo: use o endereço que ele mostrar). Se o primeiro build não
   começar sozinho, use **Manual Deploy > Deploy latest commit**. Em **Settings > Deploy Hook**,
   copie a URL do hook.

5. **Vercel.** Em <https://vercel.com/new>, importe o mesmo repositório com **Root Directory**
   `frontend` e **Framework Preset** "Other" (o `vercel.json` define instalação e build). Em
   **Environment Variables**, crie `IPC_API_ORIGIN` com o endereço do Render, para Production: o
   build monta com ela o *rewrite* de `/api/*`, e ela nunca entra no código da página. O deploy
   por push está desligado (`"git": {"deploymentEnabled": false}` no `vercel.json`), então a
   importação cria o projeto sem publicar nada (um primeiro build pela branch padrão pode aparecer
   com erro; ignore-o). Confira em **Settings > Environments > Production** que o **Branch
   Tracking** é `main`. Em **Settings > Git > Deploy Hooks**, crie um hook para a branch `main`
   (digite `main` no campo) e copie a URL, que é o `VERCEL_DEPLOY_HOOK_URL` do passo 8. Para o
   primeiro deploy, use **Deployments > ⋯ > Create Deployment**, escolha `main` e clique em
   **Deploy to Production**; ou dispare o hook no terminal:
   `read -rs -p "Hook da Vercel: " HOOK; echo; curl -s -X POST "$HOOK"; unset HOOK`. Quando ele
   terminar, anote o endereço da página em **Settings > Domains**. Se `ip-checker.vercel.app` já
   tiver dono, a Vercel acrescenta um sufixo (no piloto de 2026, `ip-checker-red-phi.vercel.app`):
   use o endereço que ela mostrar. Volte ao Render e troque `IPC_PUBLIC_BASE_URL` por ele, com
   **Save and deploy**: os links dos e-mails usam esse endereço, e a API recusa ações que mudam
   estado vindas de outra origem.

6. **Google (opcional).** Em <https://console.cloud.google.com>, **APIs & Services > Credentials >
   Create credentials > OAuth client ID**, tipo **Web application**. Em **Authorized redirect
   URIs**, coloque `<endereço da Vercel>/api/v1/auth/google/callback` (o retorno fica na origem da
   página). A tela de consentimento pede só `openid`, `email` e `profile`. Copie o *client ID* e o
   *client secret*. Sem eles, a entrada por senha funciona e o botão do Google não aparece.

7. **Variáveis no Render.** No serviço, em **Environment**, preencha as que o `render.yaml` deixou
   em aberto:

   | Variável | Valor |
   |---|---|
   | `IPC_PUBLIC_BASE_URL` | Endereço da página na Vercel, sem barra no fim |
   | `IPC_DATABASE_URL` | *Connection string* do Supabase com o usuário `ipc_api` (passo 2) |
   | `IPC_DEV_INITIAL_PASSWORD` | Senha inicial da conta do desenvolvedor (9+ caracteres, 1 maiúscula, 1 especial); só vale na criação |
   | `IPC_EMAIL_API_KEY` e `IPC_EMAIL_FROM` | Chave do Brevo e remetente verificado (passo 3) |
   | `IPC_GOOGLE_CLIENT_ID` e `IPC_GOOGLE_CLIENT_SECRET` | Do passo 6, ou vazias |
   | `IPC_EDGE_SECRET` | Segredo que só a página e a API conhecem (S30-03), com pelo menos 32 caracteres; o mesmo valor fica na Vercel. Ordem para ligar: primeiro na Vercel, depois aqui ([runbook](../docs/runbook.md), "Segredo da página") |
   | `IPC_GABARITOS_TOKEN` | *Fine-grained token* do GitHub, só de leitura e só do repositório dos gabaritos, sem data de vencimento (S32-01, P-23); a troca é por evento ([runbook](../docs/runbook.md), "Credencial dos gabaritos"). Vazia, a comparação com o gabarito fica desligada, com um aviso |
   | `IPC_LLM_CHAIN` e `IPC_LLM_<NOME>_*` | A cadeia de IAs do **Aprimorar com IA** (Q-16, S32-12), na ordem, como `gemini,groq`, e o provedor, o modelo, a URL e a chave de cada nome (`IPC_LLM_GEMINI_PROVIDER`, `IPC_LLM_GEMINI_MODEL`, `IPC_LLM_GEMINI_API_KEY`...; [runbook](../docs/runbook.md), "IAs do Aprimorar com IA"). Um nome da cadeia sem provedor, modelo ou chave impede a API de subir |
   | `IPC_LLM_*` e `IPC_LLM_FALLBACK_*` | As duas vagas antigas, principal e de reserva ([`compose.md`](compose.md), "Feedback por IA"); só valem com `IPC_LLM_CHAIN` vazia. Sem nenhuma IA, o botão **Aprimorar com IA** não aparece, e o feedback continua montado sem IA, que é o padrão |

8. **GitHub.** Em **Settings > Secrets and variables > Actions** do repositório:
   - secrets: `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL` (URLs dos hooks);
     `PILOT_DATABASE_ADMIN_URL` e `PILOT_DB_API_PASSWORD` (passo 2), para as migrações;
     `PILOT_CHECK_LOGIN`, `PILOT_CHECK_PASSWORD` e `PILOT_CHECK_NAME`, de uma conta ativa usada só
     nas verificações e no smoke e2e do piloto;
   - variables: `PILOT_API_URL` (Render) e `PILOT_WEB_URL` (Vercel); para o backup diário (às
     06:00 UTC desde a S30-12, para o RPO de 24 h da NFR-20), `BACKUP_AGE_RECIPIENT` (chave pública
     age; [`docs/runbook.md`](../docs/runbook.md), "Backup"). `PILOT_AI_INDICATORS` fica vazia
     (ou `0`) enquanto os indícios de IA estiverem desligados no `render.yaml`
     ([`docs/indicios-de-ia.md`](../docs/indicios-de-ia.md), "Como ligar no piloto").

   A conta de verificação só pode ser criada com a página no ar: entre como desenvolvedor na página
   da Vercel, registre a conta com um e-mail institucional seu que não seja da conta do
   desenvolvedor, confirme o e-mail, aprove-a como monitor em **Gerenciar** e não a use para mais
   nada. Os e-mails da conta do desenvolvedor são reservados a ela; um subendereço da mesma caixa
   (como `usuario+verificacao@cin.ufpe.br`) é outro e-mail para o IP-Checker e chega na mesma caixa
   (S30-01, 08/10/2026). A senha pode ser gerada e gravada no secret sem aparecer na tela:
   `senha="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)Aa!"; printf '%s' "$senha" | clip;
   gh secret set PILOT_CHECK_PASSWORD --body "$senha"; unset senha`, colando-a (Ctrl+V) no cadastro
   e limpando a área de transferência depois. Sem ela, o pipeline publica a versão nova, confere tudo o que não precisa de login e
   avisa que o login pela página e o smoke e2e ficaram de fora. A cada deploy, o passo
   das migrações marca essa conta no banco (`IPC_CHECK_ACCOUNT_LOGIN`, S28-02): as verificações
   dela não entram na telemetria, e ela não conta como membro no relatório de eficácia.

   Os secrets podem ser gravados pelo terminal, sem passar pelo navegador: `gh secret set NOME`
   pede o valor sem mostrá-lo (por exemplo, `gh secret set RENDER_DEPLOY_HOOK_URL`). As variables
   não são segredos: `gh variable set PILOT_API_URL --body https://...`.

   A partir daí, toda release na `main` migra o banco, faz o deploy e as verificações sozinha. Para
   o primeiro deploy, sem esperar outra release, use **Actions > Deploy do piloto > Run workflow**,
   escolhendo a branch `main`.

9. **UptimeRobot.** Em <https://uptimerobot.com>, crie três monitores HTTP(S) com intervalo de 5 min
   e alerta por e-mail: `<endereço do Render>/ready`, `<endereço do Render>/health/slo` e
   `<endereço da Vercel>/`. O primeiro também mantém o plano gratuito do Render acordado (ADR-03);
   o segundo é o alerta de latência e de erro ([`compose.md`](compose.md), "Telemetria e alertas").
   O plano gratuito só consulta com HEAD e só aceita 2xx e 3xx; as rotas de operação respondem HEAD
   desde a S30-04.

## Lista de conferência do primeiro deploy

- [ ] Supabase em us-east-1, Data API desligada e migração do passo 2b aplicada.
- [ ] Serviço do Render com todas as variáveis do passo 7; o build terminou e `/health/service`
      responde 200.
- [ ] `/ready` responde 200 com o `release` do commit da `main`.
- [ ] A página da Vercel abre, e `/version.json` traz o mesmo `release`.
- [ ] Entrar com a conta do desenvolvedor pela página da Vercel funciona: o cookie da sessão é da
      origem da página e o *rewrite* de `/api/*` chega ao Render (P-15 a).
- [ ] O limite por IP vê o IP real: o passo "Limite por IP no piloto" do "Deploy do piloto" ficou
      verde (P-15 b; `IPC_TRUSTED_PROXY_HOPS=4`, `IPC_TRUST_FORWARDED_HEADER=1` e
      `IPC_RATE_LIMIT_EDGE_HEADER=cf-connecting-ip`, S30-03).
- [ ] O e-mail de verificação de um cadastro de teste chega à caixa de entrada, e o link abre a
      página da Vercel.
- [ ] O workflow "Deploy do piloto" ficou verde, com as verificações e o smoke e2e.
- [ ] Os três monitores do UptimeRobot estão verdes.

Se algo falhar, o [`docs/runbook.md`](../docs/runbook.md) diz como voltar para a versão anterior.

## Para conferir à mão depois do deploy

```bash
curl -s https://ip-checker-api.onrender.com/ready
```

A resposta traz o commit implantado em `release`. A página publica o dela em `/version.json`.

O *rewrite* mantém o prefixo: `<página>/api/v1/...` chega a `<Render>/api/v1/...`. Por isso
`<página>/api/health/service` responde 404 (`{"detail":"Not Found"}`, do FastAPI), e isso já prova
que o *rewrite* chegou ao Render; a saúde é conferida direto no Render. Sem sessão,
`<página>/api/v1/auth/me` responde 401, como no Render.

## Teste de carga: plano gratuito ou Starter (S12-02 e S28-01)

Dois testes, com o mesmo `deploy/load/pilot-load.js` (k6). Os dois entram com uma conta antes de
verificar, como a página: cada verificação passa pela sessão no banco.

**Capacidade por plano (local).** `deploy/load/run_load.py` sobe um PostgreSQL, aplica as migrações
e sobe a imagem do piloto com a CPU e a memória de um plano do Render; o k6 entra com a conta do
desenvolvedor desse banco descartável e verifica soluções reais da Lista 1 a uma taxa fixa. Os
limites por conta e por IP são aumentados só nesse contêiner, porque todo o tráfego sai de uma
conta e de um IP.

```bash
python deploy/load/run_load.py --plan free --rate 500 --duration 3m
python deploy/load/run_load.py --plan starter --rate 500 --duration 3m --no-build
```

Resultado de 07/10/2026 (S28-01), com login: o gratuito tem P95 entre 383 ms (30/min) e 1,9 s
(500/min, com 14,8% de recusas `OVERLOADED`); o Starter tem P95 de 28 ms a 500/min, sem falhas. A
tabela completa está no [ADR-03](../docs/adr/ADR-03-topologia-de-implantacao-por-fase.md), com a
recomendação da S28-01 (o Starter antes do primeiro prazo) e a decisão que a substituiu: o piloto
fica no plano gratuito (S30-11). A medição sem login, da S12-02, ficou no histórico do ADR.

**O piloto de verdade.** Com a conta de verificação criada e os secrets `PILOT_CHECK_*` gravados,
rode **Actions > Carga no piloto > Run workflow** (taxa de 1 a 25 por minuto, abaixo do limite de 30
da conta, e até 10 minutos). O resumo do workflow traz o que o k6 viu pela página da Vercel (a
verificação, só a sessão no banco e uma rota sem banco, cuja diferença é a distância até o Supabase,
Q-20) e o P95 medido no servidor pelo `/health/slo`, que é o do NFR-01. As verificações da conta de
verificação não entram na telemetria nem no relatório de eficácia (S28-02).

## Riscos do piloto

- **Seccomp no Render.** Testado aqui com o perfil padrão do Docker. Se o Render não permitir o
  filtro, o deploy fica vermelho (fail-closed). A saída, a decidir, é `IPC_SANDBOX=optional`, com o
  risco das ameaças 2 e 6 subindo para Médio durante o piloto (blueprint, 5.4).
- **IP do cliente.** Resolvido na S30-03 (08/10/2026, P-12 e P-15 b): o cliente vem do segredo da
  página, do `Forwarded` ou da 4ª entrada do `X-Forwarded-For` (seção do início). O passo "Limite por
  IP no piloto" do "Deploy do piloto" (`backend/tests/pilot/test_rate_limit.py`) confere isso a cada
  deploy.
- **Plano gratuito.** 0,1 CPU e 512 MB. O autor decidiu ficar no gratuito (S30-11, 08/10/2026,
  ADR-03): não há orçamento para o Starter. No Render de verdade, a 20 por minuto, o P95 do servidor
  ficou abaixo dos 200 ms do NFR-01 (S30-09); no pico de referência, o piloto recusa parte das
  verificações com `OVERLOADED`, em vez de cair (NFR-05; S34-01 e S34-03 no ADR-03).
- **Supabase gratuito.** O plano pausa projetos sem atividade por uma semana. O `/ready` consulta o
  banco, então o monitor do UptimeRobot a cada 5 min também mantém o projeto ativo.

# deploy

Configuração de implantação do IP-Checker. Nas Fases 0 (local) e 2 (servidor do CIn), o compose
sobe a borda `web` (Caddy com a SPA, S9-02), a `api` pública (S8-01), o `analyzer` endurecido
(S6-01), desde a Sprint 13, o banco de contas e sessões (`db`) com o serviço `migrate` e, desde a
Sprint 14, o `mailpit`, que captura os e-mails de verificação no desenvolvimento. No piloto
(Fase 1, 2027.1), a página vai para a Vercel e o backend para o Render, com o isolamento por
processo (seção "Piloto").

| Serviço | Redes | Porta na máquina | Endurecimento |
|---|---|---|---|
| `analyzer` | `analyzer_net` (interna, sem saída) | nenhuma | NFR-07 completo, testado (abaixo) |
| `api` | `analyzer_net`, `edge_net` e `db_net` | nenhuma | UID 10001, só leitura, sem capabilities, `no-new-privileges`, 64 processos, 256 MB |
| `web` | `edge_net` | `127.0.0.1:8180` | UID 10001, só leitura, sem capabilities (nem a de portas baixas), `no-new-privileges`, 64 processos, 128 MB |
| `db` | `db_net` (interna, sem saída) | nenhuma | PostgreSQL 17 por digest, usuário `postgres` (70) sem passar pelo root, só leitura (dados num volume), sem capabilities, `no-new-privileges`, 100 processos, 256 MB |
| `migrate` | `db_net` | nenhuma | Roda uma vez a cada subida e sai; é o único com a senha de administrador do banco |
| `mailpit` | `edge_net` | `127.0.0.1:8125` (página de leitura) | Só no desenvolvimento; UID 10001, só leitura, mensagens só em memória, sem capabilities, `no-new-privileges`, 64 processos, 128 MB. Não envia nada para fora |

A `api` entra no banco com o usuário `ipc_api`, membro de `ipc_app`: lê e escreve contas e sessões,
mas não altera o esquema nem apaga contas (`backend/tests/test_migrations.py`).

## Piloto (Render + Vercel, Fase 1)

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
atrás do *rewrite* ela vê o `Host` do Render. Três suposições ficam para conferir no primeiro
deploy com login (P-15): o *rewrite* externo no plano Hobby com cookies e tempo-limite suficiente;
o IP do cliente como penúltimo endereço do `X-Forwarded-For` (`IPC_TRUSTED_PROXY_HOPS=2`); e o
cookie `__Host-` atravessando o *rewrite*.

O UID 10002 não lê o ambiente da API nem o do supervisord: o kernel só permite isso ao dono. Com
`IPC_SANDBOX=required`, se o Render não permitir o filtro seccomp, nenhum worker nasce e o `/ready`
nunca fica verde, ou seja, o deploy falha em vez de subir sem o isolamento.

`backend/tests/security/test_pilot_isolation.py` sobe a imagem do piloto como o Render a roda e
confere tudo isso na CI, inclusive o pior caso de 50 KB dentro dos 160 MiB por worker.

### Como o deploy acontece

```
develop ──(release: fast-forward)──> main ──> CI ──(verde)──> deploy.yml
    migrações no banco do piloto ──> deploy hooks do Render e da Vercel
    ──> espera a versão nova em /ready e /version.json
    ──> confere mesma origem, cabeçalhos, TLS e login (backend/tests/pilot) ──> smoke e2e com login
```

O Render e a Vercel estão com o deploy automático desligado (`render.yaml` e `frontend/vercel.json`):
nada vai ao ar sem a CI verde na `main`. Enquanto o piloto não estiver configurado no GitHub, o
pipeline só avisa e não faz nada. As migrações rodam antes da versão nova subir, então cada uma
precisa servir também à versão que ainda está no ar (só acrescentar tabelas e colunas; remover
fica para uma migração de uma release seguinte).

### Passo a passo da configuração (uma vez)

Estes passos são feitos por você nos painéis, com as suas contas. Nenhum segredo entra no
repositório.

1. **Release na `main`.** O Render e a Vercel leem a `main`, que precisa ter o código da Sprint 16:

   ```bash
   git switch main && git merge --ff-only develop && git push origin main
   ```

   Sem as variáveis do passo 8, a CI roda e o deploy só avisa que o piloto não está configurado.

2. **Banco (Supabase).** Em <https://supabase.com>, crie um projeto na região mais próxima (São
   Paulo). Em **Project Settings > Database**, copie a *connection string* do **Session pooler**
   (os executores do GitHub não alcançam o endereço direto, que é só IPv6) com o usuário
   `postgres`: ela é a `PILOT_DATABASE_ADMIN_URL` do passo 8. Escolha também uma senha para o
   usuário da API, `ipc_api` (`PILOT_DB_API_PASSWORD`); a migração do pipeline cria esse usuário.
   A `IPC_DATABASE_URL` do Render é a mesma *connection string*, trocando `postgres` por `ipc_api`
   e a senha pela do `ipc_api`.

3. **E-mail (Brevo).** Em <https://www.brevo.com>, verifique o remetente (o endereço que vai em
   `IPC_EMAIL_FROM`) e crie uma chave de API em **SMTP & API > API Keys**. Antes de usar um
   remetente `@cin.ufpe.br`, confira com o NTI se o SPF, o DKIM e o DMARC do domínio aceitam o envio
   por terceiros (Q-17); senão, os e-mails caem no spam ou são recusados.

4. **Render.** Em <https://dashboard.render.com>, **New > Blueprint**, conecte o repositório
   `Lionzio/ip-checker` e confirme o `render.yaml`. Ele cria o serviço `ip-checker-api` (Docker,
   plano Free, região Virginia). Anote o endereço, por exemplo `https://ip-checker-api.onrender.com`.
   Em **Settings > Deploy Hook**, copie a URL do hook.

5. **Vercel.** Em <https://vercel.com/new>, importe o mesmo repositório com **Root Directory**
   `frontend` e **Framework Preset** "Other" (o `vercel.json` define instalação e build). Em
   **Environment Variables**, crie `IPC_API_ORIGIN` com o endereço do Render, para Production: o
   build monta com ela o *rewrite* de `/api/*`, e ela nunca entra no código da página. Depois do
   primeiro deploy, anote o endereço da página, por exemplo `https://ip-checker.vercel.app`. Em
   **Settings > Git > Deploy Hooks**, crie um hook para a branch `main` e copie a URL.

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
   | `IPC_LLM_*` e `IPC_LLM_FALLBACK_*` | As IAs do feedback (seção "Feedback por IA"), ou vazias: sem elas, o feedback é montado sem IA |

8. **GitHub.** Em **Settings > Secrets and variables > Actions** do repositório:
   - secrets: `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL` (URLs dos hooks);
     `PILOT_DATABASE_ADMIN_URL` e `PILOT_DB_API_PASSWORD` (passo 2), para as migrações;
     `PILOT_CHECK_LOGIN`, `PILOT_CHECK_PASSWORD` e `PILOT_CHECK_NAME`, de uma conta ativa usada só
     nas verificações e no smoke e2e do piloto (registre-a, aprove-a como monitor e não a use para
     mais nada);
   - variables: `PILOT_API_URL` (Render) e `PILOT_WEB_URL` (Vercel).

   A partir daí, toda release na `main` migra o banco, faz o deploy e as verificações sozinha.

9. **UptimeRobot.** Em <https://uptimerobot.com>, crie dois monitores HTTP(S) com intervalo de 5 min
   e alerta por e-mail: `<endereço do Render>/ready` e `<endereço da Vercel>/`. O primeiro também
   mantém o plano gratuito do Render acordado (ADR-03).

### Para conferir à mão depois do deploy

```bash
curl -s https://ip-checker-api.onrender.com/ready
```

A resposta traz o commit implantado em `release`. A página publica o dela em `/version.json`.

### Teste de carga: plano gratuito ou Starter (S12-02)

`deploy/load/run_load.py` sobe a imagem do piloto com a CPU e a memória de um plano do Render e roda
o `deploy/load/pilot-load.js` (k6) contra ela: soluções reais da Lista 1, cada verificação de um
aluno diferente, a uma taxa fixa. O limite por IP é aumentado só nesse contêiner, porque todo o
tráfego sai do k6; o objetivo é medir capacidade.

```bash
python deploy/load/run_load.py --plan free --rate 500 --duration 3m
```

Medido em 01/10/2026, nesta máquina, emulando o Render com `--cpus` e `--memory` do Docker:

| Plano | Taxa | Falhas (não 200) | P95 | P99 | O que falhou |
|---|---|---|---|---|---|
| Gratuito (0,1 CPU, 512 MB) | 500/min, 3 min | 12,8% a 41,6% (duas rodadas) | 3,0 s a 5,3 s | 3,9 s a 6,4 s | 503 `OVERLOADED` e `ANALYZER_UNAVAILABLE`; nenhum 500, 502 ou 504 |
| Gratuito (0,1 CPU, 512 MB) | 150/min, 2 min | 0% | 213 ms | 408 ms | nada |
| Starter (0,5 CPU, 512 MB) | 500/min, 3 min | 0% | 40 ms | 63 ms | nada |

**Conclusão:** o plano gratuito atende um dia comum (até cerca de 150 verificações por minuto), mas não
o pico de referência de uma véspera de prazo (500/min, P-01). Mesmo saturado, ele se degrada como o
NFR-05 pede: recusa rápida com `Retry-After`, sem erro genérico. Pelo critério do ADR-03, o backend
precisa do **Starter** (cerca de US$ 7 por mês) antes do primeiro prazo da Lista 1. A decisão de custo
é do autor do projeto.

Para confirmar no Render de verdade, com o piloto no ar, aumente por alguns minutos
`IPC_RATE_LIMIT_IP_PER_MIN` no painel (o k6 sai de um único IP) e rode:

```bash
docker run --rm -v "$PWD/deploy/load:/scripts:ro" -e BASE_URL=https://ip-checker-api.onrender.com -e RATE=500 -e DURATION=3m grafana/k6 run /scripts/pilot-load.js
```

Depois, volte o `IPC_RATE_LIMIT_IP_PER_MIN` ao padrão (120).

### Riscos do piloto

- **Seccomp no Render.** Testado aqui com o perfil padrão do Docker. Se o Render não permitir o
  filtro, o deploy fica vermelho (fail-closed). A saída, a decidir, é `IPC_SANDBOX=optional`, com o
  risco das ameaças 2 e 6 subindo para Médio durante o piloto (blueprint, 5.4).
- **IP do cliente.** O limite por IP supõe que a borda do Render acrescenta o IP do cliente ao fim do
  `X-Forwarded-For` (`IPC_TRUSTED_PROXY_HOPS=1`, P-12). Conferir nos primeiros dias pelos campos
  `rate_limit` do log.
- **Plano gratuito.** 0,1 CPU e 512 MB: não aguenta o pico de 500 verificações por minuto
  (teste de carga acima). A recomendação é o Starter antes do primeiro prazo (ADR-03).

## Uso (compose, Fases 0 e 2)

Todos os comandos rodam na raiz do repositório.

Antes da primeira subida, crie o `deploy/.env` (fora do Git) a partir do modelo e troque as três
senhas: a do administrador do banco, a do usuário da API e a senha inicial da conta do
desenvolvedor (P-14), que precisa de 9 caracteres, 1 maiúscula e 1 caractere especial:

```bash
cp deploy/.env.example deploy/.env
```

Subir tudo e esperar os healthchecks (cada serviço só sobe depois que o anterior está saudável; o
`migrate` aplica as migrações e sai):

```bash
docker compose -f deploy/compose.yaml up --build -d --wait
```

A página fica em http://127.0.0.1:8180, e a API, na mesma origem. Sem login, a página só mostra
Registrar e Entrar, e as rotas da equipe respondem 401:

```bash
curl -s http://127.0.0.1:8180/ready
```

Entrar pela página com `vlacg@cin.ufpe.br` (ou `vinicius.leoncio@ufpe.br`, ou o nome) e a senha do
`IPC_DEV_INITIAL_PASSWORD`. Ela só vale na criação da conta: trocar o `deploy/.env` depois não muda a
senha de uma conta que já existe. Para trocá-la, use **Perfil > Alterar a senha**; a troca encerra
as outras sessões da conta e mantém a atual.

### Registro e e-mails (S14)

Quem é da equipe se registra em **Registrar** com o e-mail `@cin.ufpe.br` ou `@ufpe.br`. No
compose, o e-mail de verificação não sai da máquina: o Mailpit o captura e mostra em
<http://127.0.0.1:8125>. O link abre a página **Confirmar o e-mail**, e só o botão dela gasta o
token (um antivírus que abre o link não confirma nada). Depois, o cadastro aguarda a aprovação
em **Gerenciar** (S15), que aparece para o desenvolvedor, os professores e os monitores-chefe: lá
ficam a fila de pedidos (aprovar com um cargo ou recusar), os membros ativos (alterar o cargo ou
remover) e as contas removidas (reativar). Cada linha só mostra o que o cargo de quem está logado
permite (FR-27), e a API confere de novo a cada ação.

Para enviar e-mails de verdade (Fase 2 ou piloto), configure um dos transportes na `api`:

| Variável | Uso |
|---|---|
| `IPC_EMAIL_TRANSPORT` | `smtp` (padrão) ou `brevo` (API HTTPS do Brevo) |
| `IPC_SMTP_HOST`, `IPC_SMTP_PORT`, `IPC_SMTP_SECURITY` (`starttls`, `ssl` ou `none`), `IPC_SMTP_USERNAME`, `IPC_SMTP_PASSWORD` | Transporte `smtp`. Sem `IPC_SMTP_HOST`, o envio fica desligado e o registro responde 503 `EMAIL_UNAVAILABLE` |
| `IPC_EMAIL_API_KEY` | Transporte `brevo`; obrigatória com ele (sem ela, a API não sobe) |
| `IPC_EMAIL_FROM` | Remetente, por exemplo `IP-Checker <endereco@cin.ufpe.br>` |
| `IPC_PUBLIC_BASE_URL` | Endereço público da página. O link é montado só a partir dele, nunca do `Host` da requisição |

O plano gratuito do Render bloqueia as portas SMTP de saída (25, 465 e 587) desde 09/2025; no
piloto, use o transporte `brevo` ou outro serviço por HTTPS. O provedor e o remetente ainda são
a questão Q-17 do blueprint: com um remetente `@cin.ufpe.br` enviado por terceiros, confira com o
NTI se a política de e-mail do CIn (SPF, DKIM e DMARC) aceita o envio, para os e-mails não caírem
no spam.

### Feedback por IA (S18): onde ficam as chaves

O botão **Gerar feedback** funciona sempre. A ordem é: a **IA principal**; se ela falhar, demorar
ou responder algo que não passa na validação, a **IA de reserva**; se nenhuma responder a tempo
(prazo total de 28 s), ou se nenhuma estiver configurada, o texto é **montado por modelos**, sem
IA e sem enviar nada para fora. A abertura e a frase obrigatória são as mesmas nos três casos.

As chaves ficam só em variáveis de ambiente da `api`, nunca no Git nem na página:

- **No compose (local ou Fase 2):** no `deploy/.env`, que o Git ignora. O `deploy/.env.example`
  traz o bloco pronto; depois de preencher, suba de novo com
  `docker compose -f deploy/compose.yaml up -d api`.
- **No piloto (Render):** no serviço `ip-checker-api`, em **Environment**, as mesmas variáveis
  (o `render.yaml` já as declara, vazias).

| Variável | IA principal | IA de reserva |
|---|---|---|
| Provedor: `openai_compat` (OpenAI, Groq, DeepSeek e outros compatíveis) ou `gemini` | `IPC_LLM_PROVIDER` | `IPC_LLM_FALLBACK_PROVIDER` |
| URL da API, só no `openai_compat` fora da OpenAI (Groq: `https://api.groq.com/openai/v1`; DeepSeek: `https://api.deepseek.com`) | `IPC_LLM_BASE_URL` | `IPC_LLM_FALLBACK_BASE_URL` |
| Modelo disponível na sua conta do provedor | `IPC_LLM_MODEL` | `IPC_LLM_FALLBACK_MODEL` |
| Chave da API | `IPC_LLM_API_KEY` | `IPC_LLM_FALLBACK_API_KEY` |
| Tempo de cada tentativa (padrão: 12 s) | `IPC_LLM_TIMEOUT_S` | `IPC_LLM_FALLBACK_TIMEOUT_S` |

Use provedores diferentes na principal e na reserva, para as duas não caírem juntas. Uma
configuração incompleta (provedor sem modelo ou sem chave, URL sem HTTPS, reserva sem principal)
impede a API de subir, com a mensagem dizendo o que falta. `GET /api/v1/auth/options` diz à página
se há IA (`feedback_ai`). Cada conta tem até 60 feedbacks por dia e o servidor até 1.000
(`IPC_FEEDBACK_PER_ACCOUNT_DAY` e `IPC_FEEDBACK_DAILY_CAP`), para limitar o custo.

O que vai ao provedor: só o código sem comentários, a anotação e o resultado do motor, com o nome
do aluno trocado por `[ALUNO]`; o nome e o cargo de quem avalia não vão. Antes de usar dados reais
de alunos, confira os termos do plano (retenção e uso dos dados para treinar modelos) e a
política da UFPE (Q-16).

O banco não publica porta na máquina, então não disputa a 5432 nem a 6432 de outros projetos. Para
consultá-lo, entre no contêiner:

```bash
docker compose -f deploy/compose.yaml exec db psql -U postgres -d ipchecker
```

O analyzer não publica porta na máquina. Para falar direto com ele, entre na rede dele:

```bash
docker compose -f deploy/compose.yaml exec analyzer python -c "import json, urllib.request; r = urllib.request.Request('http://127.0.0.1:8001/internal/analyze', data=json.dumps({'code': 'for i in range(3):\n    print(i)\n', 'list_number': 1}).encode(), headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(r).read().decode())"
```

Rodar a suíte de segurança (isolamento, submissões maliciosas e API pública). Ela sobe o compose
inteiro num projeto próprio (`ipc-security-test`, com a borda na porta 18180, então convive com o
compose acima), cria dois contêineres clientes, um na rede interna e outro na da borda, ataca e
derruba tudo no final:

```bash
cd backend && IPC_SECURITY_TESTS=1 uv run pytest tests/security --no-cov -v
```

Derrubar tudo:

```bash
docker compose -f deploy/compose.yaml down
```

## Borda (Caddy)

`deploy/caddy/` constrói a SPA e a serve com o Caddy, que repassa `/api/*`, `/health` e `/ready` à
`api`. O que a borda garante:

- **Corpo grande nunca chega à API** (DoD, item 1): um `Content-Length` acima de 128 KiB recebe 413
  sem que o corpo seja lido, e um corpo sem `Content-Length` recebe 411. O fetch do navegador sempre
  informa o tamanho.
- **Cabeçalhos de segurança**: CSP sem `unsafe-inline`, `nosniff`, `Referrer-Policy: no-referrer`,
  `Permissions-Policy` e `COOP`, sem o cabeçalho `Server`.
- **Erros no formato do contrato**: 411, 413 e a API fora do ar (502 a 504 viram 503
  `ANALYZER_UNAVAILABLE`) respondem com o envelope `{"error": ...}`.
- **Logs sem IP nem URL**: não há log de acesso no Caddy, e o filtro apaga IP, cabeçalhos e URL dos
  demais logs. A linha de cada requisição vem da API (S9-01).

Na Fase 0, a borda responde em HTTP só para esta máquina. TLS e HSTS entram com o domínio do
servidor do CIn (Fase 2, NFR-10).

## Controles do NFR-07

Se uma submissão explorar uma falha do parser do Python, o processo comprometido não encontra
segredo, rede, disco gravável, privilégio nem recurso ilimitado. Cada controle tem um teste em
`backend/tests/security/test_isolation.py`, que roda no job `security` da CI.

| Controle | Onde | Teste |
|---|---|---|
| UID e GID 10001 em todos os processos, nunca root | `USER` no Dockerfile, `user` no compose | `test_runs_as_unprivileged_user` |
| Raiz do sistema de arquivos só leitura | `read_only: true` | `test_root_filesystem_is_read_only` |
| Só `/tmp` e `/dev/shm` graváveis, em memória, 16 MB, `noexec`; nenhum volume | `tmpfs`, `shm_size` | `test_only_memory_areas_are_writable_and_nothing_is_mounted` |
| Nenhuma capability | `cap_drop: [ALL]` | `test_all_capabilities_are_dropped` |
| Sem ganho de privilégio; seccomp padrão do Docker ativo | `no-new-privileges:true` | `test_privileges_cannot_be_raised` |
| Até 64 processos e 512 MB de memória, sem swap | `pids_limit`, `mem_limit`, `memswap_limit` | `test_processes_and_memory_are_limited` |
| Só a rede interna, sem porta publicada e sem rota para fora | `analyzer_net` com `internal: true` | `test_only_network_is_internal_and_no_port_is_published`, `test_there_is_no_route_out` |
| Ambiente sem segredos (lista de variáveis permitidas) | `ENV` do Dockerfile | `test_environment_has_no_secrets` |
| Workers com `RLIMIT_AS` 256 MB, `RLIMIT_FSIZE` 0 e `RLIMIT_NOFILE` 32 | pool da S5-01 | `test_workers_run_with_resource_limits` |
| Imagem só com o necessário: sem uv, sem testes, sem gabaritos | build em dois estágios, `backend/Dockerfile.dockerignore` | `test_image_contains_only_runtime_files` |

Outros dois testes confirmam que o serviço funciona com todo esse endurecimento: o healthcheck
fica `healthy`, e outro contêiner na `analyzer_net` alcança o analyzer pelo nome `analyzer:8001`,
como a `api` fará.

## Submissões maliciosas (DoD, seção 8)

`backend/tests/security/test_malicious_submissions.py` ataca o endpoint interno a partir do
contêiner cliente. O cliente reprova qualquer resposta 5xx, e os tempos são medidos dentro da
rede interna.

| Item | O que é enviado | O que se espera |
|---|---|---|
| 2 | 1.000 e 1.001 linhas | 200 e 422 `INVALID_INPUT` |
| 3 | Nulo, caracteres de controle, surrogate, UTF-8 inválido ou truncado, JSON quebrado ou de outro tipo | 422 `INVALID_INPUT` |
| 4 e 5 | 1.000 níveis de `(`, `[`, `{`, `not` ou `-`; 25 mil somas encadeadas | 422 `ANALYSIS_LIMIT` em ≤ 2,5 s |
| 5 | A entrada mais larga que cabe em 50 KB (~53 mil nós) | 200 em < 2 s |
| 6 | Literal de 50 KB e f-strings aninhadas ou largas | Resposta em < 2,5 s |
| 7 | `while True`, recursão infinita, `10 ** 10 ** 10` | Resposta em < 100 ms, prova de que nada é executado |
| 8 | 12 tentativas de execução (`__import__`, `open`, `eval`, `exec`, `compile`, `breakpoint`, `getattr(__builtins__, ...)`, `__subclasses__`, `import os`, `globals`, `vars`), em todas as listas | Violações; o canário `/tmp/canary` não é criado |
| 9 | 24 evasões do motor e 3 built-ins sombreados | As violações esperadas, sem falso positivo |
| 10 | 60 requisições concorrentes com marcadores distintos | Cada resposta traz só o próprio marcador |
| 12 | Depois de tudo | Health 200, nenhum worker zumbi, 2 workers vivos, logs sem `Traceback` nem 500 |

O item 11 é o isolamento da seção anterior.

## API pública sob ataque (S9-03)

`backend/tests/security/test_api_limits.py` ataca pela borda, a partir de um contêiner só na
`edge_net`, como um navegador: Caddy, depois `api`, depois `analyzer`. Desde a Sprint 13, cada
requisição leva a sessão de uma conta ativa diferente, criada pela própria suíte direto no banco do
compose de teste (`create_sessions` em `harness.py`); as senhas desse compose são sorteadas a cada
execução.

| Item | O que é enviado | O que se espera |
|---|---|---|
| 1 | Código de 51.200 e 51.201 bytes | 200 e 413 `PAYLOAD_TOO_LARGE`, respondido pela API |
| 1 | Cabeçalhos de um corpo de 200 KB e só os primeiros bytes dele, com e sem `Content-Length` | 413 e 411 imediatos, da borda: ela responde sem esperar o resto, e a API não recebe nada |
| 3 | 15 corpos malformados (nulo, controle, surrogate, UTF-8 inválido, JSON quebrado, tipos errados, campo extra…) | 422 `INVALID_INPUT` |
| 4 | 1.000 níveis de `(`, `[` ou `not` | 422 `ANALYSIS_LIMIT` em ≤ 2,5 s |
| 13 | Marcador canário no código, na URL, na query e em cabeçalhos; IP falso em `X-Forwarded-For` | 0 ocorrências do marcador, do IP falso e do IP real do cliente nos logs dos três serviços; `docker diff` vazio; nada nas áreas em memória; nada no banco (`pg_dump`) |
| Final | `/ready` pela borda | 200 |

## Limite de taxa pela borda (S10-03)

`backend/tests/security/test_api_rate_limit_edge.py` repete, com a pilha real, os critérios da
US-17. Todos os pedidos saem de um único contêiner, ou seja, de um único IP externo.

| O que é enviado | O que se espera |
|---|---|
| 31 verificações com a sessão da mesma conta | 30 aceitas e a 31ª com 429 `RATE_LIMITED` (S13-02); o `Retry-After` atravessa a borda; outro membro do mesmo IP segue atendido |
| 31 verificações sem sessão, cada uma com um `X-Forwarded-For` forjado diferente | 30 com 401 `UNAUTHENTICATED` e a 31ª com 429: sem sessão, o cliente é o IP, a borda descarta o cabeçalho do cliente, e forjá-lo não cria identidades novas |
| 150 verificações de 150 membros, todos fingindo estar na faixa da UFPE | No máximo 120 aceitas no minuto; as demais com 429 (limite do IP externo, não o do campus) |
| Com o limite do IP esgotado: `/api/v1/lists` (com sessão), `/ready` e `/health` | 200: a página ainda carrega e o monitoramento ainda enxerga o serviço |
| Logs dos três serviços | `rate_limit` com `client` e `ip`; nenhum identificador de sessão nem endereço forjado |

No compose, a `api` roda com `IPC_TRUSTED_PROXY_HOPS=1`: o IP do cliente é o que o Caddy escreve
no `X-Forwarded-For`. De um único IP externo (120 verificações por minuto), não dá para saturar a
admissão: o limite de taxa age antes.

Desde a Sprint 13, o item 13 também procura o marcador no banco. O item 14 (Trivy, pip-audit, npm
audit e gitleaks) ainda não tem sprint no roadmap, e o 15 (TLS, HSTS e CORS) vale a partir da
Sprint 11. Os itens 16, 19 e 20 (sem sessão, 401 em tudo; cookie, `Origin` e sessão; bloqueio de
tentativas e senha fora dos logs) estão em `backend/tests/test_auth.py` e no e2e; pela borda, a
suíte confere o 401 e o limite por conta.

### Por que `/tmp` e `/dev/shm` são graváveis

Com a raiz só leitura, o `forkserver` do pool não consegue criar o socket pelo qual nascem os
workers, e o multiprocessing guarda seus semáforos em `/dev/shm`. Por isso os dois existem em
memória, com 16 MB, `noexec`, `nosuid` e `nodev`, e a memória deles conta nos 512 MB do contêiner.
O código do aluno nunca grava nesses diretórios: os workers têm `RLIMIT_FSIZE` 0.

### Atualizar a imagem base

As imagens do Python e do uv estão fixadas por digest no `backend/Dockerfile`. Para atualizar:

1. Rode `docker pull python:3.13-slim`.
2. Copie o novo digest para `PYTHON_IMAGE`.
3. Abra um PR. A CI roda de novo todos os testes, inclusive os de isolamento.

# deploy

Configuração de implantação do IP-Checker. Nas Fases 0 (local) e 2 (servidor do CIn), o compose
sobe a borda `web` (Caddy com a SPA, S9-02), a `api` pública (S8-01) e o `analyzer` endurecido
(S6-01). No piloto (Fase 1, 2027.1), a página vai para a Vercel e o backend para o Render, com o
isolamento por processo (seção "Piloto").

| Serviço | Redes | Porta na máquina | Endurecimento |
|---|---|---|---|
| `analyzer` | `analyzer_net` (interna, sem saída) | nenhuma | NFR-07 completo, testado (abaixo) |
| `api` | `analyzer_net` e `edge_net` | nenhuma | UID 10001, só leitura, sem capabilities, `no-new-privileges`, 64 processos, 256 MB |
| `web` | `edge_net` | `127.0.0.1:8180` | UID 10001, só leitura, sem capabilities (nem a de portas baixas), `no-new-privileges`, 64 processos, 128 MB |

## Piloto (Render + Vercel, Fase 1)

No piloto de 2027.1 (ADR-03), a página fica na Vercel e o backend num único serviço Docker no
Render, no plano gratuito. O Render não tem rede interna nem flags de contêiner, então o isolamento
entre a API e o analisador é feito por processo (`deploy/render/`):

| Processo | Usuário | O que recebe | Isolamento |
|---|---|---|---|
| `supervisord` | root | O ambiente do Render | Só inicia os outros dois; não abre socket de controle |
| `api` | 10001 | O ambiente do Render (CORS, limites, credenciais futuras) | Porta pública do Render |
| `analyzer` | 10002 | Ambiente vazio (`env -i`), só 6 variáveis próprias | Escuta só em `127.0.0.1:8001`; workers com seccomp (sem `socket`, `socketpair`, `execve` nem `execveat`), `RLIMIT_AS` de 160 MiB, `RLIMIT_FSIZE` 0 e `RLIMIT_NOFILE` 32 |

O UID 10002 não lê o ambiente da API nem o do supervisord: o kernel só permite isso ao dono. Com
`IPC_SANDBOX=required`, se o Render não permitir o filtro seccomp, nenhum worker nasce e o `/ready`
nunca fica verde, ou seja, o deploy falha em vez de subir sem o isolamento.

`backend/tests/security/test_pilot_isolation.py` sobe a imagem do piloto como o Render a roda e
confere tudo isso na CI, inclusive o pior caso de 50 KB dentro dos 160 MiB por worker.

### Como o deploy acontece

```
develop ──(release: fast-forward)──> main ──> CI ──(verde)──> deploy.yml
    deploy hooks do Render e da Vercel ──> espera a versão nova em /ready e /version.json
    ──> confere cabeçalhos, CORS e TLS (backend/tests/pilot) ──> smoke e2e no navegador
```

O Render e a Vercel estão com o deploy automático desligado (`render.yaml` e `frontend/vercel.json`):
nada vai ao ar sem a CI verde na `main`. Enquanto o piloto não estiver configurado no GitHub, o
pipeline só avisa e não faz nada.

### Passo a passo da configuração (uma vez)

Estes passos são feitos por você nos painéis, com as suas contas. Nenhum segredo entra no
repositório.

1. **Release na `main`.** O Render e a Vercel leem a `main`, que precisa ter o código da Sprint 11:

   ```bash
   git switch main && git merge --ff-only develop && git push origin main
   ```

   Sem as variáveis do passo 5, a CI roda e o deploy só avisa que o piloto não está configurado.

2. **Render.** Em <https://dashboard.render.com>, **New > Blueprint**, conecte o repositório
   `Lionzio/ip-checker` e confirme o `render.yaml`. Ele cria o serviço `ip-checker-api` (Docker,
   plano Free, região Virginia). Anote o endereço, por exemplo `https://ip-checker-api.onrender.com`.
   Em **Settings > Deploy Hook**, copie a URL do hook.

3. **Vercel.** Em <https://vercel.com/new>, importe o mesmo repositório com **Root Directory**
   `frontend` e **Framework Preset** "Other" (o `vercel.json` define instalação e build). Em
   **Environment Variables**, crie `VITE_API_BASE_URL` com o endereço do Render, para Production.
   Depois do primeiro deploy, anote o endereço da página, por exemplo `https://ip-checker.vercel.app`.
   Em **Settings > Git > Deploy Hooks**, crie um hook para a branch `main` e copie a URL.

4. **CORS no Render.** No serviço do Render, em **Environment**, defina `IPC_CORS_ORIGINS` com o
   endereço da página na Vercel (sem barra no fim) e salve. Sem isso, o navegador bloqueia as
   chamadas da página à API.

5. **GitHub.** Em **Settings > Secrets and variables > Actions** do repositório:
   - secrets: `RENDER_DEPLOY_HOOK_URL` e `VERCEL_DEPLOY_HOOK_URL`, com as URLs dos hooks;
   - variables: `PILOT_API_URL` (Render) e `PILOT_WEB_URL` (Vercel).

   A partir daí, toda release na `main` faz o deploy e as verificações sozinha.

6. **UptimeRobot.** Em <https://uptimerobot.com>, crie dois monitores HTTP(S) com intervalo de 5 min
   e alerta por e-mail: `<endereço do Render>/ready` e `<endereço da Vercel>/`. O primeiro também
   mantém o plano gratuito do Render acordado (ADR-03).

### Para conferir à mão depois do deploy

```bash
curl -s https://ip-checker-api.onrender.com/ready
```

A resposta traz o commit implantado em `release`. A página publica o dela em `/version.json`.

### Riscos do piloto

- **Seccomp no Render.** Testado aqui com o perfil padrão do Docker. Se o Render não permitir o
  filtro, o deploy fica vermelho (fail-closed). A saída, a decidir, é `IPC_SANDBOX=optional`, com o
  risco das ameaças 2 e 6 subindo para Médio durante o piloto (blueprint, 5.4).
- **IP do cliente.** O limite por IP supõe que a borda do Render acrescenta o IP do cliente ao fim do
  `X-Forwarded-For` (`IPC_TRUSTED_PROXY_HOPS=1`, P-12). Conferir nos primeiros dias pelos campos
  `rate_limit` do log.
- **Plano gratuito.** 0,1 CPU e 512 MB. Se o P95 passar de 200 ms numa véspera de prazo, a
  migração é para o Starter (ADR-03).

## Uso (compose, Fases 0 e 2)

Todos os comandos rodam na raiz do repositório.

Subir tudo e esperar os healthchecks (cada serviço só sobe depois que o anterior está saudável):

```bash
docker compose -f deploy/compose.yaml up --build -d --wait
```

A página fica em http://127.0.0.1:8180, e a API, na mesma origem:

```bash
curl -s http://127.0.0.1:8180/ready
```

```bash
curl -s -X POST http://127.0.0.1:8180/api/v1/validate -H "Content-Type: application/json" -d '{"code": "for i in range(3):\n    print(i)\n", "list_number": 1}'
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
`edge_net`, como um navegador: Caddy, depois `api`, depois `analyzer`.

| Item | O que é enviado | O que se espera |
|---|---|---|
| 1 | Código de 51.200 e 51.201 bytes | 200 e 413 `PAYLOAD_TOO_LARGE`, respondido pela API |
| 1 | Cabeçalhos de um corpo de 200 KB e só os primeiros bytes dele, com e sem `Content-Length` | 413 e 411 imediatos, da borda: ela responde sem esperar o resto, e a API não recebe nada |
| 3 | 15 corpos malformados (nulo, controle, surrogate, UTF-8 inválido, JSON quebrado, tipos errados, campo extra…) | 422 `INVALID_INPUT` |
| 4 | 1.000 níveis de `(`, `[` ou `not` | 422 `ANALYSIS_LIMIT` em ≤ 2,5 s |
| 13 | Marcador canário no código, na URL, na query e em cabeçalhos; IP falso em `X-Forwarded-For` | 0 ocorrências do marcador, do IP falso e do IP real do cliente nos logs dos três serviços; `docker diff` vazio; nada nas áreas em memória |
| Final | `/ready` pela borda | 200 |

## Limite de taxa pela borda (S10-03)

`backend/tests/security/test_api_rate_limit_edge.py` repete, com a pilha real, os critérios da
US-17. Todos os pedidos saem de um único contêiner, ou seja, de um único IP externo.

| O que é enviado | O que se espera |
|---|---|
| 11 verificações com o mesmo `X-Client-Id` | 10 aceitas e a 11ª com 429 `RATE_LIMITED`; o `Retry-After` atravessa a borda; outro aluno do mesmo IP segue atendido |
| 11 verificações sem identificador, cada uma com um `X-Forwarded-For` forjado diferente | A 11ª recebe 429: a borda descarta o cabeçalho do cliente, e forjá-lo não cria identidades novas |
| 150 verificações de 150 "alunos", todos fingindo estar na faixa da UFPE | No máximo 120 aceitas no minuto; as demais com 429 (limite do IP externo, não o do campus) |
| Com o limite do IP esgotado: `/api/v1/lists`, `/ready` e `/health` | 200: a página ainda carrega e o monitoramento ainda enxerga o serviço |
| Logs dos três serviços | `rate_limit` com `client` e `ip`; nenhum identificador de sessão nem endereço forjado |

No compose, a `api` roda com `IPC_TRUSTED_PROXY_HOPS=1`: o IP do cliente é o que o Caddy escreve
no `X-Forwarded-For`. De um único IP externo (120 verificações por minuto), não dá para saturar a
admissão: o limite de taxa age antes.

O item 13 ainda não cobre o banco, que entra na Sprint 14. O item 14 (Trivy, pip-audit, npm audit e
gitleaks) ainda não tem sprint no roadmap, e o 15 (TLS, HSTS e CORS) vale a partir da Sprint 11.

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

# Segurança do deploy

Separado do `deploy/README.md` na S28-03: a borda, os controles do NFR-07 e os ataques que a CI
roda contra o analisador e a API. Como relatar uma vulnerabilidade está no
[`SECURITY.md`](../SECURITY.md).

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

# deploy

Configuração de implantação do IP-Checker nas Fases 0 (local) e 2 (servidor do CIn): a borda
`web` (Caddy com a SPA, S9-02), a `api` pública (S8-01) e o `analyzer` endurecido (S6-01). O piloto
no Render (Fase 1, Sprint 11) não usa este compose: lá o isolamento é por processo (ADR-03).

| Serviço | Redes | Porta na máquina | Endurecimento |
|---|---|---|---|
| `analyzer` | `analyzer_net` (interna, sem saída) | nenhuma | NFR-07 completo, testado (abaixo) |
| `api` | `analyzer_net` e `edge_net` | nenhuma | UID 10001, só leitura, sem capabilities, `no-new-privileges`, 64 processos, 256 MB |
| `web` | `edge_net` | `127.0.0.1:8180` | UID 10001, só leitura, sem capabilities (nem a de portas baixas), `no-new-privileges`, 64 processos, 128 MB |

## Uso

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

Rodar a suíte de segurança: isolamento e submissões maliciosas. Ela sobe só o analyzer num projeto
próprio (`ipc-security-test`, sem porta nenhuma, então convive com o compose acima), cria um
contêiner cliente na rede interna, ataca o analyzer e derruba tudo no final:

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

O item 11 é o isolamento da seção anterior. Os itens 1 e 13 a 15 dependem da API, do proxy e da
telemetria e entram nas Sprints 9 a 14.

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

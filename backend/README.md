# backend

Projeto Python 3.13 do IP-Checker, com dois serviços que só conversam por HTTP: o `ipc_analyzer`
(motor de regras, pool isolado e serviço interno) e a `ipc_api` (API pública). O import-linter
garante que um nunca importa o outro e que a API nunca importa `ast`.

| Pacote | Papel | Sprint |
|---|---|---|
| `ipc_analyzer.engine` | Motor puro: ruleset, parse, fatos e política (`analyze_source`) | 1–4 |
| `ipc_analyzer.runtime` | Pool de workers com timeout de 2 s, `RLIMIT_AS` de 256 MB, sem escrita em disco | 5 |
| `ipc_analyzer.service` | Serviço interno: `POST /internal/analyze`, `GET /internal/health` e `GET /internal/ruleset/manifest` | 5, 8 |
| `ipc_api` | API pública: `POST /api/v1/validate`, `GET /api/v1/lists`, `GET /health` e `GET /ready` | 8 |

Regras de segurança do código (NFR-09, verificadas por `tests/test_code_guards.py` e pelo ruff):
nada de `eval`, `exec`, `compile`, `__import__`, `pickle` ou `subprocess`; `import ast` só dentro de
`ipc_analyzer/engine/`; YAML só com `yaml.safe_load`.

## Comandos

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest
```

Serviço interno do analisador (porta 8001):

```bash
uv run uvicorn ipc_analyzer.service.app:create_app --factory --port 8001
```

Configuração por variáveis de ambiente: `IPC_RULESET_PATH` (padrão: `rulesets/2026.2/base.yaml` do
repositório), `IPC_WORKERS` (2), `IPC_MAX_TASKS` (500), `IPC_TIMEOUT_S` (2) e `IPC_MEMORY_MB` (256).

API pública (porta 8101 fora do Docker; a 8100 fica com a API do compose), com o analisador já
rodando na 8001:

```bash
uv run uvicorn ipc_api.app:create_app --factory --port 8101
```

Configuração: `IPC_ANALYZER_URL` (`http://127.0.0.1:8001`), `IPC_ENABLED_LISTS` (`1`; por exemplo,
`1,2`), `IPC_ANALYZER_TIMEOUT_S` (3) e `IPC_MAX_BODY_BYTES` (131072, ou seja, 128 KB).

O contrato da API fica versionado em [`../docs/openapi.json`](../docs/openapi.json). O teste
`tests/test_api_contract.py` falha quando ele fica desatualizado; para regenerá-lo:

```bash
uv run python -m ipc_api.openapi ../docs/openapi.json
```

O mesmo teste roda o schemathesis: gera requisições a partir do OpenAPI publicado, manda-as à API
ligada ao analisador de verdade e confere que toda resposta está documentada e segue o esquema.

## Logs

Os dois serviços escrevem logs JSON no stdout (`structlog`, S9-01): uma linha por requisição na
API (`event: request`) e uma por análise no analyzer (`event: analysis`), ligadas pelo mesmo
`request_id`. Os campos ficam numa lista de permissão (`LOG_FIELDS`): código, IP, cabeçalhos, URL
pedida e mensagens de exceção nunca são gravados, e o log de acesso do uvicorn (que tem IP) fica
desligado. `tests/test_log_contract.py` confere o esquema e roda o teste canário (NFR-11).
Para depurar localmente com o formato padrão do uvicorn, use `IPC_JSON_LOGS=0`.

## Contêiner

A imagem do backend (`backend/Dockerfile`) roda os dois serviços, cada um com o seu comando, e é
construída a partir da raiz do repositório, porque embute os rulesets. O endurecimento e os testes de isolamento estão em
[`../deploy/README.md`](../deploy/README.md). A suíte de segurança (`tests/security/`:
isolamento e submissões maliciosas) é pulada na suíte normal e roda com `IPC_SECURITY_TESTS=1`.

## Limites só no Linux

Os limites de recursos dos workers usam o módulo `resource`, que só existe em Unix. No Windows, o
pool funciona, mas sem esses limites, e 3 testes são pulados. A CI roda em Linux e executa todos.
Para rodar a suíte completa localmente:

```bash
docker run --rm -v "$PWD/..:/repo" -w /repo/backend -e UV_PROJECT_ENVIRONMENT=/tmp/venv python:3.13-slim sh -c "pip install -q uv && uv sync --locked -q && uv run pytest"
```

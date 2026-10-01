# backend

Projeto Python 3.13 do IP-Checker. Hoje contém o pacote `ipc_analyzer` (motor de regras, pool
isolado e serviço interno); a API pública (`ipc_api`) entra na Sprint 8, no mesmo projeto.

| Pacote | Papel | Sprint |
|---|---|---|
| `ipc_analyzer.engine` | Motor puro: ruleset, parse, fatos e política (`analyze_source`) | 1–4 |
| `ipc_analyzer.runtime` | Pool de workers com timeout de 2 s, `RLIMIT_AS` de 256 MB, sem escrita em disco | 5 |
| `ipc_analyzer.service` | Serviço interno: `POST /internal/analyze` e `GET /internal/health` | 5 |
| `ipc_api` | API pública (`POST /api/v1/validate`) | 8 |

Regras de segurança do código (NFR-09, verificadas por `tests/test_code_guards.py` e pelo ruff):
nada de `eval`, `exec`, `compile`, `__import__`, `pickle` ou `subprocess`; `import ast` só dentro de
`ipc_analyzer/engine/`; YAML só com `yaml.safe_load`.

## Comandos

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Serviço interno do analisador (porta 8001):

```bash
uv run uvicorn ipc_analyzer.service.app:create_app --factory --port 8001
```

Configuração por variáveis de ambiente: `IPC_RULESET_PATH` (padrão: `rulesets/2026.2/base.yaml` do
repositório), `IPC_WORKERS` (2), `IPC_MAX_TASKS` (500), `IPC_TIMEOUT_S` (2) e `IPC_MEMORY_MB` (256).

## Limites só no Linux

Os limites de recursos dos workers usam o módulo `resource`, que só existe em Unix. No Windows, o
pool funciona, mas sem esses limites, e 3 testes são pulados. A CI roda em Linux e executa todos.
Para rodar a suíte completa localmente:

```bash
docker run --rm -v "$PWD/..:/repo" -w /repo/backend -e UV_PROJECT_ENVIRONMENT=/tmp/venv python:3.13-slim sh -c "pip install -q uv && uv sync --locked -q && uv run pytest"
```

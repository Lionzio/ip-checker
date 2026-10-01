# backend

Projeto Python 3.13 do IP-Checker. Hoje contém o pacote `ipc_analyzer` (motor de regras); a API
pública (`ipc_api`) entra na Sprint 8, no mesmo projeto.

| Pacote | Papel | Sprint |
|---|---|---|
| `ipc_analyzer.engine` | Motor puro: ruleset, parse, fatos e política | 1–4 |
| `ipc_analyzer.runtime` / `service` | Pool isolado de workers e serviço interno | 5 |
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

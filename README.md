# IP-Checker

Verificador web que confere, **sem executar o código**, se a solução em Python de um aluno de
Introdução à Programação respeita as regras de permissão da lista (e da questão) antes do envio
ao Dikastis. O código é analisado só pela árvore sintática (AST), num serviço isolado.

O blueprint completo está em [`docs/blueprint.md`](docs/blueprint.md).

## Estrutura do repositório

| Pasta | Conteúdo | Desde |
|---|---|---|
| `backend/` | Projeto Python 3.13: motor de regras (`ipc_analyzer`) e, depois, a API (`ipc_api`) | Sprint 1 |
| `frontend/` | SPA React + Vite + TypeScript | Sprint 2 |
| `rulesets/` | Regras como dados (YAML por período), editadas por monitores e professores | Sprint 1 |
| `docs/` | Blueprint e matriz de mapeamento R-xx → fatos | Sprint 1 |
| `deploy/` | Compose, Caddy, supervisord e configuração do Render | Sprint 6 |
| `database/` | Migrações SQL da telemetria (Supabase) | Sprint 14 |

`rulesets/` fica fora do `backend/` para que uma mudança de regra seja um PR só de dados
(NFR-17). `database/` também é separada: o esquema é usado pela API e pelas consultas dos
professores e é aplicado no Supabase independentemente do deploy do backend.

## Desenvolvimento

Pré-requisito: [uv](https://docs.astral.sh/uv/) (instala o Python 3.13 sozinho).

```bash
cd backend
uv sync
uv run pytest
```

A CI (`.github/workflows/ci.yml`) roda ruff, mypy strict e pytest em todo PR e em todo push na
`develop` e na `main`.

## Fluxo de branches

| Branch | Papel | Como recebe código |
|---|---|---|
| `develop` | Branch principal e padrão no GitHub | PR de uma branch de task, com a CI verde |
| `feature/<task>-<descrição>` | Uma por task (ex.: `feature/S2-01-parser`) | Criada a partir da `develop` |
| `main` | Branch de release (o deploy do piloto sai dela, Sprint 11) | Só por *fast-forward* da `develop` |

A `main` fica sempre igual ou atrás da `develop`. Por isso ela nunca recebe commit direto nem
merge de PR pelo GitHub: o botão de merge cria um commit que não existe na `develop`. Uma release
é feita assim:

```bash
git switch main
git merge --ff-only develop
git push origin main
```

O job `branch-policy` da CI falha se a `main` tiver algum commit que não esteja na `develop`.
Correções urgentes seguem o mesmo caminho: entram na `develop` e depois avançam a `main`.

## Situação

| Sprint | Entrega | Estado |
|---|---|---|
| 1 | S1-01 monorepo e CI; S1-02 modelo do ruleset, loader imutável e R-03…R-36 | Concluída |
| 2 | S2-01 parser seguro e limites; S2-02 esqueleto da SPA | Próxima |

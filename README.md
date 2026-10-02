# IP-Checker

Ferramenta web da equipe de Introdução à Programação que confere, **sem executar o código**, se a
solução em Python de um aluno respeita as regras de permissão da lista (e da questão), compara duas
soluções em busca de plágio e redige o feedback para o aluno. O código é analisado só pela árvore
sintática (AST), num serviço isolado. O acesso é restrito à equipe da disciplina, com login,
aprovação manual e cargos (P-13 do blueprint).

O blueprint completo está em [`docs/blueprint.md`](docs/blueprint.md).
O guia de uso, para a equipe da disciplina, está em [`docs/guia-da-equipe.md`](docs/guia-da-equipe.md).

## Estrutura do repositório

| Pasta | Conteúdo | Desde |
|---|---|---|
| `backend/` | Projeto Python 3.13: motor de regras e analisador isolado (`ipc_analyzer`) e API pública (`ipc_api`) | Sprint 1 |
| `frontend/` | SPA React + Vite + TypeScript | Sprint 2 |
| `rulesets/` | Regras como dados (YAML por período), editadas por monitores e professores | Sprint 1 |
| `docs/` | Blueprint, matriz de mapeamento R-xx → fatos e contrato da API (`openapi.json`) | Sprint 1 |
| `deploy/` | Compose da borda (Caddy com a SPA), da `api` e do `analyzer` endurecido; imagem do piloto no Render (`deploy/render/`) | Sprint 6 |
| `database/` | Migrações SQL das contas e sessões e da telemetria (PostgreSQL/Supabase) | Sprints 13 e 21 |

`rulesets/` fica fora do `backend/` para que uma mudança de regra seja um PR só de dados
(NFR-17). `database/` também é separada: o esquema é usado pela API e pelas consultas dos
professores e é aplicado no Supabase independentemente do deploy do backend.

## Desenvolvimento

Pré-requisitos: [uv](https://docs.astral.sh/uv/) (instala o Python 3.13 sozinho) e Node.js 24.

```bash
cd backend
uv sync
uv run pytest
```

Os testes do banco (migrações e repositório de contas) só rodam com um PostgreSQL de teste em
`IPC_TEST_DATABASE_URL`; sem ele, são pulados. Um contêiner descartável, só em `127.0.0.1` e numa
porta que não colide com outros projetos, basta (`backend/tests/db_support.py`):

```bash
docker run -d --name ipc-test-db -e POSTGRES_PASSWORD=troque -e POSTGRES_DB=ipc_test -p 127.0.0.1:55432:5432 postgres:17-alpine
```

```bash
cd frontend
npm install
npm run dev
```

O compose completo (página, API, `analyzer` endurecido e banco), com o `deploy/.env` que ele
pede e os testes de isolamento, está em [`deploy/README.md`](deploy/README.md).

A CI (`.github/workflows/ci.yml`) roda em todo PR e em todo push na `develop` e na `main`:

- backend: ruff, mypy strict, import-linter e pytest, com o contrato OpenAPI;
- segurança: build das imagens, isolamento do NFR-07, submissões maliciosas contra o analyzer e ataques à API pública pela borda;
- frontend: tipos gerados do OpenAPI em dia, ESLint, TypeScript, Vitest e build;
- e2e: o compose completo, o login e o smoke do Marco 1 no Playwright.

### Portas locais

O IP-Checker usa portas próprias, longe das padrão (5173 do Vite, 8000 do uvicorn, 5432 do
PostgreSQL), que outros projetos já ocupam na máquina de desenvolvimento. O Vite usa `strictPort`:
se a porta estiver ocupada, ele falha em vez de pular para outra.

| Serviço | Porta | Observação |
|---|---|---|
| SPA (`npm run dev`) | 5180 | |
| SPA (`npm run preview`) | 5181 | |
| `analyzer` local, sem Docker | 8001 | Só em `127.0.0.1` |
| `analyzer` em Docker | nenhuma | Só na rede interna `analyzer_net` |
| Compose: página e API pelo Caddy | 8180 | Só em `127.0.0.1` (`IPC_HTTP_PORT` muda); a API não tem porta própria |
| API pública local, sem Docker | 8101 | Só em `127.0.0.1` |
| Banco de contas em Docker | nenhuma | Só na rede interna `db_net` |
| PostgreSQL de teste (opcional) | 55432 | Só em `127.0.0.1`; a 5432 e a 6432 ficam com outros projetos |

## Fluxo de branches

| Branch | Papel | Como recebe código |
|---|---|---|
| `develop` | Branch principal e padrão no GitHub | PR de uma branch de task, com a CI verde |
| `feature/<task>-<descrição>` | Uma por task (ex.: `feature/S2-01-parser`) | Criada a partir da `develop` |
| `main` | Branch de release: cada push nela, com a CI verde, faz o deploy do piloto (`.github/workflows/deploy.yml`) | Só por *fast-forward* da `develop` |

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
| 2 | S2-01 parser seguro e limites; S2-02 esqueleto da SPA com cliente simulado | Concluída |
| 3 | S3-01 extrator de fatos e ligações de nomes (resistente a evasão por sombreamento) | Concluída |
| 4 | S4-01 avaliador de política v1; S4-02 corpus golden (120 casos, 34 de evasão) | Concluída |
| 5 | S5-01 analisador isolado: pool de workers com limites calibrados e serviço interno | Concluída |
| 6 | S6-01 contêiner endurecido do analisador, rede sem saída e testes de isolamento na CI | Concluída |
| 7 | S7-01 suíte de segurança: 70 ataques e 13 testes de isolamento contra o contêiner, na CI | Concluída |
| 8 | S8-01 API pública: validação, listas, health e ready, contrato OpenAPI e import-linter | Concluída |
| 9 | Marco 1 (MVP local): S9-01 logs sem código nem IP; S9-02 SPA na API real, borda Caddy e e2e; S9-03 segurança da API pública | Concluída |
| 10 | Proteção para exposição pública: S10-01 limite de taxa por cliente e por IP e admissão; S10-02 mensagens e contagem de espera na página; S10-03 limite de taxa atacado pela borda | Concluída |
| 11 | Deploy do piloto: S11-01 imagem do Render com isolamento por processo e seccomp; S11-02 CORS, HSTS e página para a Vercel; S11-03 deploy depois da CI e verificações do piloto no ar | Concluída (falta a configuração das contas, `deploy/README.md`) |
| 12 | Marco 2: S12-01 exigência R-02 da Lista 1 e aviso de regras de questão; S12-02 teste de carga (recomenda o Starter); S12-03 guia do piloto e apresentação | Concluída |
| 13 | Contas e sessão: S13-01 banco de contas, migrações e conta do desenvolvedor; S13-02 login por senha, sessão no servidor, bloqueio de tentativas, `Origin` e limite por conta; S13-03 telas inicial e Entrar, rotas com guarda e fim do `X-Client-Id` | Concluída |
| 14 | Registro e perfil: S14-01 registro por e-mail institucional e senha; S14-02 e-mail de verificação (SMTP ou Brevo; Mailpit no compose) com link de uso único; S14-03 perfil, tratamento e troca de senha; créditos no rodapé | Concluída |
| 15 | Cargos e gerenciamento: S15-01 política de cargos testada pela matriz completa; S15-02 API de gerenciamento (fila, aprovar com cargo, recusar, alterar cargo, remover e reativar); S15-03 tela Gerenciar com etiquetas coloridas e e2e com axe | Concluída |
| 16 | Google e mesma origem: S16-01 entrada e registro pelo Google (OIDC com `state`, `nonce` e PKCE, provedor falso nos testes); S16-02 página e API na mesma origem no piloto (*rewrite* da Vercel), migrações antes do deploy e verificações com login; S16-03 suíte de segurança da autenticação pela borda | Concluída (o primeiro deploy com login confirma a P-15) |
| 17 | Painel de plágio: S17-01 motor de similaridade (*winnowing* em tokens e na AST, corpus de pares); S17-02 comparação no analisador isolado e `POST /api/v1/similarity` com as faixas do FR-29; S17-03 painel com as duas áreas, a faixa escrita e o aviso de indício | Concluída |
| 18 | Feedback por LLM: S18-01 provedores (`openai_compat` e `gemini`), com IA principal e de reserva; S18-02 abertura e frase obrigatória pelo backend, nome do aluno trocado por `[ALUNO]`, texto validado e, sem IA, feedback montado por modelos; `POST /api/v1/feedback` | Concluída |
| 19 | Marco 2: S19-01 painel de feedback na página (nome do aluno, anotação, texto editável e Copiar); S19-02 aviso de privacidade, guia da equipe, passo a passo das contas externas e apresentação revista | Concluída (falta o primeiro deploy com login, `deploy/README.md`) |
| 20 | Lista 2: S20-01 `zip` condicional (R-37), exigência do laço (R-02) e Lista 2 habilitada; S20-02 harness e job da CI para os gabaritos de períodos anteriores | Concluída (falta o repositório privado dos gabaritos, `rulesets/README.md`) |
| 21 | Telemetria e alertas: S21-01 eventos anônimos no banco, views do FR-17 e expurgo de 12 meses; S21-02 `/health/slo` (P95 e 5xx) para o UptimeRobot e exercício de falha | Concluída (falta o terceiro monitor do UptimeRobot, `deploy/README.md`) |
| 22 | Listas 3 e 4 | Próxima |
| 23 | Listas 5 e 6 e recursão obrigatória | Planejada |
| 24 | Regras por questão e governança | Planejada |
| 25 | Carga, eficácia e passagem de bastão | Planejada |

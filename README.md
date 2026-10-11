# IP-Checker

Ferramenta web da equipe de Introdução à Programação que confere, **sem executar o código**, se a
solução em Python de um aluno respeita as regras de permissão da lista (e da questão), compara duas
soluções em busca de plágio e redige o feedback para o aluno. O código é analisado só pela árvore
sintática (AST), num serviço isolado. O acesso é restrito à equipe da disciplina, com login,
aprovação manual e cargos (P-13 do blueprint).

Hoje (11/10/2026), as Sprints 1 a 33 estão concluídas e a Sprint 34 está em andamento. As seis
listas estão habilitadas, com as regras por questão, o painel de plágio (dois códigos ou contra a
turma, por árvore canonizada), a comparação com o gabarito oficial (sem o gabarito sair do
servidor), o feedback por modelos de texto com o "Aprimorar com IA" a pedido, a correção em lote, o
gerenciamento da equipe com registro das ações, a telemetria anônima, o relatório de eficácia e os
indícios de uso de IA (desligados no piloto até a calibração com soluções de alunos). O piloto está
no ar (Render, Vercel e Supabase) desde 07/10/2026, na release `sprint-32` desde 09/10/2026; a
`main` já tem a Sprint 33 e o começo da 34, que vão ao piloto na release da Sprint 34. O uso pela
equipe é em 2027.1. As pendências restantes estão planejadas nas Sprints 34 a 36 (seção 7.12 do
blueprint), e a integração com outros 2 projetos da monitoria é só uma possibilidade, ainda não
confirmada (seção 9 do blueprint e ADR-09).

| Para | Leia |
|---|---|
| Usar (equipe da disciplina) | [`docs/guia-da-equipe.md`](docs/guia-da-equipe.md) |
| Cadastrar as regras de uma questão | [`RULES.md`](RULES.md) |
| Começar a manter o projeto | [`docs/onboarding.md`](docs/onboarding.md) e [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Relatar uma falha de segurança | [`SECURITY.md`](SECURITY.md) |
| Achar qualquer outro documento | [`docs/README.md`](docs/README.md) |
| O que cada sprint entregou | [`CHANGELOG.md`](CHANGELOG.md) |
| O que vem a seguir (Sprints 34 a 36) e as decisões em aberto | [`docs/blueprint.md`](docs/blueprint.md), seções 7.12 a 7.14 |
| A pauta do Marco 2 (casos do mapeamento e decisões da coordenação) | [`docs/marco-2.md`](docs/marco-2.md) |
| A comparação com o gabarito (Sprint 32) | [`docs/adr/ADR-11-comparacao-com-o-gabarito.md`](docs/adr/ADR-11-comparacao-com-o-gabarito.md) |
| Questões e gabaritos por período | [`docs/adr/ADR-10-questoes-e-gabaritos-por-periodo.md`](docs/adr/ADR-10-questoes-e-gabaritos-por-periodo.md), [`RULES.md`](RULES.md) e [`rulesets/README.md`](rulesets/README.md) |
| Os endpoints da API e a possível integração com outros projetos | [`docs/blueprint.md`](docs/blueprint.md), seção 9, e [`docs/adr/ADR-09-integracao-com-outros-projetos-da-monitoria.md`](docs/adr/ADR-09-integracao-com-outros-projetos-da-monitoria.md) |

## Estrutura do repositório

| Pasta | Conteúdo | Desde |
|---|---|---|
| `backend/` | Projeto Python 3.13: motor de regras e analisador isolado (`ipc_analyzer`) e API pública (`ipc_api`) | Sprint 1 |
| `frontend/` | SPA React + Vite + TypeScript | Sprint 2 |
| `rulesets/` | Regras como dados (YAML por período), editadas por monitores e professores | Sprint 1 |
| `docs/` | Blueprint, decisões, ADRs, runbook, onboarding, relatório de eficácia, matriz de mapeamento R-xx → fatos e contrato da API (`openapi.json`) | Sprint 1 (dividido na 28) |
| `deploy/` | Compose da borda (Caddy com a SPA), da `api` e do `analyzer` endurecido; imagem do piloto no Render (`deploy/render/`) | Sprint 6 |
| `database/` | Migrações SQL das contas e sessões, da telemetria, do registro de gerenciamento, da redefinição de senha, da limpeza diária e da adoção por lista (PostgreSQL/Supabase) | Sprints 13, 21, 23, 24, 25 e 28 |
| `scripts/` | `release.sh`: fast-forward da `main`, tag `sprint-NN` e GitHub Release | Sprint 28 |

`rulesets/` fica fora do `backend/` para que uma mudança de regra seja um PR só de dados
(NFR-17). `database/` também é separada: o esquema é usado pela API e pelas consultas dos
professores e é aplicado no Supabase independentemente do deploy do backend.

## Desenvolvimento

Pré-requisitos: [uv](https://docs.astral.sh/uv/) (instala o Python 3.13 sozinho) e Node.js 24.

```bash
cd backend
uv sync
uv run pytest
uv run ipc-rules validate ../rulesets --golden tests/golden
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
pede, está em [`docs/onboarding.md`](docs/onboarding.md) e [`deploy/compose.md`](deploy/compose.md);
os testes de isolamento, em [`deploy/seguranca.md`](deploy/seguranca.md).

A CI (`.github/workflows/ci.yml`) roda em todo PR e em todo push na `develop` e na `main`. Desde a
S28-04, um primeiro job decide o que roda: na `main`, o commit já passou pela CI completa na
`develop`, e só a política de branches roda; um PR ou push que só muda arquivos `.md` pula os
testes. Os jobs:

- backend: ruff, mypy strict, import-linter, `ipc-rules validate` (ruleset, questões e casos
  golden) e pytest, com o contrato OpenAPI;
- segurança: build das imagens, isolamento do NFR-07, submissões maliciosas contra o analyzer e ataques à API pública pela borda;
- frontend: tipos gerados do OpenAPI em dia, ESLint, TypeScript, Vitest e build;
- e2e: o compose completo no Playwright, com login, registro e verificação de e-mail (Mailpit),
  gerenciamento e registro de ações, as seis listas, plágio, feedback com a IA falsa e o limite
  por conta; os projetos que mexem na própria conta (senha, tratamento, limite) têm cada um a sua,
  criada pelo projeto "contas" (S28-04);
- gabaritos: as respostas oficiais de períodos anteriores com zero violação, baixadas do
  repositório privado `Lionzio/ip-checker-gabaritos` com uma chave só de leitura, só quando a
  variável `GABARITOS_REPO` está definida (`rulesets/README.md`, ADR-10);
- branch-policy: na `main`, falha se ela tiver algum commit que não esteja na `develop`.

Fora da CI, à mão: "Deploy do piloto" (também depois de cada CI verde na `main`), "Carga no
piloto" (k6 no Render, S28-01), "Backup do banco do piloto" (também todo dia, S28-03 e S30-12) e
"Auditoria de segurança" (também toda segunda-feira). Sem cota do GitHub Actions (2.000 minutos
por mês em repositório privado, P-19), a CI roda nesta máquina com `scripts/ci-local.sh` e o
backup com `scripts/backup-local.sh` (runbook, "Sem GitHub Actions").

No compose, os e-mails de verificação vão para o Mailpit (<http://127.0.0.1:8125>). Para
entregar de verdade (Gmail ou Brevo), veja "Enviar de verdade a partir do compose" em
[`deploy/compose.md`](deploy/compose.md).

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
merge de PR pelo GitHub: o botão de merge cria um commit que não existe na `develop`. Desde a
S28-04, uma release é feita pelo script, que confere a CI verde da `develop`, avança a `main` por
fast-forward, cria a tag `sprint-NN` e publica o GitHub Release com a seção do `CHANGELOG.md`:

```bash
scripts/release.sh 28
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
| 11 | Deploy do piloto: S11-01 imagem do Render com isolamento por processo e seccomp; S11-02 CORS, HSTS e página para a Vercel; S11-03 deploy depois da CI e verificações do piloto no ar | Concluída (contas configuradas em 07/10/2026; conta de verificação em 08/10/2026, S30-01) |
| 12 | Marco 2: S12-01 exigência R-02 da Lista 1 e aviso de regras de questão; S12-02 teste de carga (recomenda o Starter); S12-03 guia do piloto e apresentação | Concluída |
| 13 | Contas e sessão: S13-01 banco de contas, migrações e conta do desenvolvedor; S13-02 login por senha, sessão no servidor, bloqueio de tentativas, `Origin` e limite por conta; S13-03 telas inicial e Entrar, rotas com guarda e fim do `X-Client-Id` | Concluída |
| 14 | Registro e perfil: S14-01 registro por e-mail institucional e senha; S14-02 e-mail de verificação (SMTP ou Brevo; Mailpit no compose) com link de uso único; S14-03 perfil, tratamento e troca de senha; créditos no rodapé | Concluída |
| 15 | Cargos e gerenciamento: S15-01 política de cargos testada pela matriz completa; S15-02 API de gerenciamento (fila, aprovar com cargo, recusar, alterar cargo, remover e reativar); S15-03 tela Gerenciar com etiquetas coloridas e e2e com axe | Concluída |
| 16 | Google e mesma origem: S16-01 entrada e registro pelo Google (OIDC com `state`, `nonce` e PKCE, provedor falso nos testes); S16-02 página e API na mesma origem no piloto (*rewrite* da Vercel), migrações antes do deploy e verificações com login; S16-03 suíte de segurança da autenticação pela borda | Concluída (o primeiro deploy com login confirma a P-15) |
| 17 | Painel de plágio: S17-01 motor de similaridade (*winnowing* em tokens e na AST, corpus de pares); S17-02 comparação no analisador isolado e `POST /api/v1/similarity` com as faixas do FR-29; S17-03 painel com as duas áreas, a faixa escrita e o aviso de indício | Concluída |
| 18 | Feedback por LLM: S18-01 provedores (`openai_compat` e `gemini`), com IA principal e de reserva; S18-02 abertura e frase obrigatória pelo backend, nome do aluno trocado por `[ALUNO]`, texto validado e, sem IA, feedback montado por modelos; `POST /api/v1/feedback` | Concluída |
| 19 | Marco 2: S19-01 painel de feedback na página (nome do aluno, anotação, texto editável e Copiar); S19-02 aviso de privacidade, guia da equipe, passo a passo das contas externas e apresentação revista | Concluída (primeiro deploy com login em 08/10/2026, S30-02) |
| 20 | Lista 2: S20-01 `zip` condicional (R-37), exigência do laço (R-02) e Lista 2 habilitada; S20-02 harness e job da CI para os gabaritos de períodos anteriores | Concluída (repositório privado dos gabaritos com as Listas 1 e 2 de 2026.2 desde 08/10/2026; faltam as demais, S33-01) |
| 21 | Telemetria e alertas: S21-01 eventos anônimos no banco, views do FR-17 e expurgo de 12 meses; S21-02 `/health/slo` (P95 e 5xx) para o UptimeRobot e exercício de falha | Concluída (os três monitores do UptimeRobot no ar desde 08/10/2026, S30-04) |
| 22 | Listas 3 e 4: S22-01 regras R-38 a R-60, exigência das Listas 3 (lista ou tupla) e 4 (`def`) e função aninhada na R-04 (Q-02 f); S22-02 Listas 3 e 4 habilitadas e e2e | Concluída (os casos em aberto do mapeamento foram decididos em 09/10/2026, ruleset `2026.2.5`) |
| 23 | Listas 5 e 6: S23-01 regras R-61 a R-67, exigência do dicionário (L5) e da recursão direta ou mútua (R-68, L6); S23-02 Listas 5 e 6 habilitadas e e2e; S23-03 registro das ações de gerenciamento (REC-06); duas evasões do motor corrigidas na revisão de fim de sprint | Concluída |
| 24 | Regras por questão: S24-01 questões em `rulesets/<período>/questions/` com precedência sobre a lista e seletor na página; S24-02 `ipc-rules validate` na CI, registro único de predicados e `facts/` dividido; S24-03 `RULES.md` e modelo de PR de regras; S24-04 "esqueci minha senha" por link de e-mail | Concluída (questões reais: ensaio em 2026.2 na S31-13 e as de 2027.1 na S33-04) |
| 25 | Endurecimento para o primeiro deploy: S25-01 CI fixada por SHA, Dependabot e auditoria semanal; S25-02 deploy seguro, roteiro do primeiro deploy e runbook; S25-03 limpeza diária do banco e expurgo de contas sem atividade (Q-19 d); S25-04 prazos ponta a ponta, limite geral por IP, seccomp e rlimits ampliados; S25-05 docstrings e dados pessoais fora do feedback por IA e cota persistida | Concluída (primeiro deploy em 07/10/2026) |
| 26 | Correção em lote e relatório: S26-01 cabeçalho e navegação no celular, títulos por tela e componentes comuns; S26-02 "Próximo aluno", Ctrl+Enter, rascunho em memória e editor com Tab, Limpar e Colar; S26-03 relatório agrupado por regra, com resumo, trecho e clique na linha; S26-04 prazos, cancelamento e sessão vencida iguais em todas as telas, busca no gerenciamento | Concluída |
| 27 | Plágio por árvore canonizada (ADR-07): S27-01 árvore canonizada com reordenação por dependência, Dice e contenção; S27-02 uma solução contra até 100 da turma, com o peso pela raridade (IDF); S27-03 trechos em comum realçados nos dois códigos, Trocar A e B e Limpar | Concluída |
| 28 | Carga, eficácia e passagem de bastão: S28-01 k6 com login (local e no piloto) e recomendação do Starter; S28-02 adoção por lista e relatório de eficácia, sem a conta de verificação; S28-03 onboarding, CONTRIBUTING, SECURITY, runbook completo e backup semanal criptografado; S28-04 blueprint dividido, controles corrigidos, releases com tag, checksum das migrações, e2e sem pausa e CI mais leve | Concluída (rollback ensaiado e carga no piloto em 08/10/2026, S30-08 e S30-09) |
| 29 | Indícios de uso de IA (ADR-08): S29-01 múltiplas violações (variedade, repetição, salto de lista, fora do documento) e marcadores de estilo; S29-02 semelhança com soluções de referência por questão; S29-03 painel com motivo, linhas e perguntas para a conversa; S29-04 política, `ipc-rules calibrate` e chave `IPC_AI_INDICATORS` | Concluída (desligada no piloto até a política, S31-01, e a calibração, S33-03) |
| 30 | Piloto verificado ponta a ponta: conta de verificação, deploy com login e e2e no piloto, UptimeRobot com alerta ensaiado, backup cifrado restaurado, rollback cronometrado, carga no piloto, P-12 (a) e P-15, correção do supervisord | Concluída em 08/10/2026 |
| 31 | Decisões com a coordenação e o NTI (política dos indícios, Q-16, Q-17, Q-22), Marco 2 com os 9 casos do mapeamento, auditoria de segurança bloqueante com Semgrep, troca de período sem código (`ipc-rules new-period`) e gabaritos com as questões do próprio período (ADR-10) | Concluída em 09/10/2026 (releases `sprint-31` e `sprint-31.1`, ruleset `2026.2.5`): decisões tomadas pelo autor, casos do mapeamento decididos e ensaio do cadastro feito (L3-Q9); a apresentação do Marco 2 é em 19/10/2026 |
| 32 | Comparação com o gabarito: na verificação (semelhança, construções e linhas do aluno), no plágio (A×gabarito, B×gabarito e o alerta de possível vazamento) e nos indícios, sem o gabarito sair do servidor (ADR-11); feedback sem IA por padrão, com o "Aprimorar com IA" por uma cadeia de provedores gratuitos (Q-16) | Concluída em 09/10/2026 (release `sprint-32`); credencial dos gabaritos e chaves do Gemini e da Groq no Render em 10/10/2026 |
| 33 | Gabaritos de períodos anteriores (Q-14), calibração dos indícios, questões e referências de 2027.1 e, com a política aprovada, os indícios ligados no piloto | Engenharia concluída em 11/10/2026: `ipc-rules calibrate-gabarito` (alerta de vazamento) e `ipc-rules import-gabaritos` (exportação do Notion) e a medição preliminar dos indícios. Aguardando dados externos (P-21): gabaritos das Listas 5 e 6 de 2026.2 e de períodos anteriores, soluções anteriores a 2023 e o documento de 2027.1 |
| 34 | Prontidão para 2027.1: plano do Render, teste sintético diário, cenários de carga do NFR-04 e do NFR-05, listas validadas habilitadas | Em andamento: teste sintético diário com `Server-Timing` e exercício de alerta a cada release concluídos em 11/10/2026 (#71); cenários de carga em medição; listas e monitores de 2027.1 dependem do calendário (P-10) |
| 35 | Controles de qualidade: pytest-benchmark, Lighthouse CI, cobertura por pasta, canário mensal em produção, esquema do ruleset | Planejada |
| 36 | Fase 2: GHCR por digest, deploy no servidor do CIn e staging | Bloqueada (P-09 e Q-12) |

O detalhe de cada sprint, com as decisões de implementação, está no [`CHANGELOG.md`](CHANGELOG.md).
O plano das Sprints 24 a 29 nasceu da revisão de fim da Sprint 23 (técnica, visual, de CI e de
documentação) e está em 7.1 e 7.11 do blueprint. Cada sprint só começa com a autorização do autor.

## Decisões recentes (06/10/2026)

| ID | Decisão |
|---|---|
| P-10 | Sem calendário fixo: as datas dependem da UFPE; cada lista é habilitada antes de ser liberada aos alunos |
| Q-15 | Novos critérios de eficácia: uso por pelo menos 70% dos membros ativos em cada lista; apoio à correção só informativo; satisfação de pelo menos 70% da equipe |
| Q-18 | Toda violação anula a questão, inclusive "fora da lista", "não consta" e a falta do assunto |
| Q-19 | Sessão de 12 h sem uso e até 7 dias; contas removidas guardam os dados para a volta; contas fora do status ativo com 365 dias sem atividade são apagadas (Sprint 25); "esqueci minha senha" por e-mail (feito na Sprint 24) |
| REC-06 | Registro das ações de gerenciamento, visto pelo desenvolvedor e pelos professores, por 12 meses (feito na Sprint 23) |
| Q-20 | Supabase em us-east-1, na mesma região da API no Render |
| Q-21 | Indícios de uso de IA, nunca veredito (ADR-08, Sprint 29), com as múltiplas violações como indício (por exemplo `break`, `pass` e `continue` juntos ou recursos da Lista 6 na Lista 3) |
| Q-22 | Governança das regras por fork e check de aprovação: adiada para depois da release |
| ADR-07 | Plágio por árvore canonizada, insensível à ordem dos blocos e às formas equivalentes (Sprint 27) |

## Pendências do autor

Passos que dependem de contas, segredos, dados ou decisões do autor e de outras pessoas. O plano
completo, com responsável, entrada esperada e critério de desbloqueio de cada um, está nas seções
7.12 a 7.14 do [blueprint](docs/blueprint.md); o passo a passo das contas, em
[`deploy/piloto.md`](deploy/piloto.md) e no [runbook](docs/runbook.md).

- [x] Supabase em us-east-1 (Q-20), Render, Vercel, Brevo e o deploy hook da Vercel (07/10/2026)
- [x] Conta de verificação do deploy e os secrets `PILOT_CHECK_*` (S30-01, 08/10/2026)
- [x] Os três monitores do UptimeRobot (S30-04, 08/10/2026)
- [x] Chave do backup (`age-keygen`) e a variável `BACKUP_AGE_RECIPIENT` (S30-06, 08/10/2026)
- [x] Plano do Render: gratuito (S30-11, ADR-03, 08/10/2026)
- [x] Ensaio cronometrado do rollback pelos painéis do Render e da Vercel (S30-08, 08/10/2026)
- [x] Segredo da página `IPC_EDGE_SECRET` na Vercel e no Render: `/api/*` só pela página (S30-03,
      08/10/2026)
- [x] RPO do backup: backup diário (S30-12, 08/10/2026)
- [x] Decisões: política dos indícios de IA aprovada, Q-16 (feedback sem IA por padrão e o
      "Aprimorar com IA"), Q-17 (Brevo) e Q-22 (processo atual) (09/10/2026)
- [x] Os casos do mapeamento da pauta `docs/marco-2.md` (ruleset `2026.2.5`, 09/10/2026)
- [ ] Apresentação do Marco 2 em 19/10/2026 e revisão do guia da equipe (S31-05 e S31-12)
- [x] Repositório privado dos gabaritos e a chave só de leitura da CI (08/10/2026, ADR-10)
- [x] Gabaritos das Listas 1 e 2 de 2026.2 (15 questões) no repositório privado e o job
      "Gabaritos" ligado (`GABARITOS_REPO`), com zero violação (08/10/2026)
- [x] Gabaritos da Lista 3 de 2026.2 (8 questões; 23 no total), com zero violação (09/10/2026)
- [x] Gabaritos da Lista 4 de 2026.2 (5 questões; 28 no total), com zero violação, e a L4-Q3
      cadastrada com o `eval()` liberado pelo enunciado (11/10/2026)
- [ ] Os gabaritos das Listas 5 e 6 de 2026.2 e dos períodos anteriores (S33-01; o
      `ipc-rules import-gabaritos` lê a exportação do Notion) e as soluções anteriores a 2023 para
      calibrar os indícios (S33-02)
- [ ] Formulário da pesquisa e planilha do critério 3, com os links em `docs/eficacia.md` (S31-06)
- [x] Ensaio do cadastro de questões (S31-13, L3-Q9, 09/10/2026)
- [ ] Ruleset e questões de 2027.1, com as referências por IA (S33-04 e S33-05)
- [ ] Decidir se quer o gerador de referências por IA (S33-09)
- [ ] Datas de 2027.1, para habilitar as listas e conferir os monitores (S34-05 e S34-06)
- [x] Credencial só de leitura dos gabaritos no Render, `IPC_GABARITOS_TOKEN` (S32-01; 23
      gabaritos carregados no piloto em 10/10/2026)
- [x] Chaves gratuitas do Gemini e da Groq e a cadeia `gemini,groq` no Render (S32-11; o
      Aprimorar com IA respondeu pelo Gemini no piloto em 10/10/2026)
- [ ] Cliente OAuth do Google (opcional)
- [ ] Possível integração com outros 2 projetos da monitoria: as perguntas da seção 9.4 do
      blueprint aos monitores responsáveis (Q-23, ADR-09)

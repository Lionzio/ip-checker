# Histórico das Sprints 1 a 35

Tirado do blueprint na S39-05 (16/10/2026), sem mudança no texto: as tarefas, os critérios e as
situações das sprints já fechadas, a matriz de rastreabilidade das pendências de 07/10/2026 e as
falhas críticas corrigidas na revisão inicial. O que cada sprint entregou também está no
[`CHANGELOG.md`](../../CHANGELOG.md). Os números de seção (7.2 a 7.12, 7.14) são os do blueprint
até 15/10/2026, citados em outros documentos.

## 1.2 Falhas críticas corrigidas

| # | Problema | Evidência no rascunho | Impacto | Correção aplicada |
|---|---|---|---|---|
| 1 | O modelo de regras e o motor não conseguem representar o catálogo de permissões. | §12 (p.6–7): o esquema só tem `allowed_from_list` e `ast_nodes`, com IDs sintéticos como `Call_Attribute_split`. §11.3 e TASK-BE-002: "Verificar nome da classe do nó", com `visit_For`, `visit_Call`… escritos à mão. §12 mapeia `AsyncFor` como permitido a partir da Lista 2. | (a) R-37 (zip condicional), R-02/R-68 (exigências) e R-01 (precedência da questão) não podem ser expressos, então o veredito diverge do documento. (b) O *default deny* por classe de nó deixa passar `eval(...)`, `getattr(...)`, `__import__(...)` e métodos como `.title()`, porque `Call`, `Name` e `Attribute` são classes "permitidas". O resultado é um falso negativo e a questão anulada no Dikastis. (c) Cada regra nova exige código no Visitor, o que contraria a US-004 do rascunho. | Motor orientado a dados (ADR-02, 5.2.3). Ele usa um vocabulário de **fatos** (nó, operador, built-in, método/atributo, argumento nomeado, constante, contexto) e aplica o *default deny* a **cada fato**. Condições ficam em predicados declarativos, exigências em `requirements` e as regras da questão em `question_overrides`. Os IDs R-xx do catálogo são os IDs do ruleset, e o mapeamento foi validado em 01/10/2026 (Q-02). |
| 2 | O código do aluno é processado no mesmo processo da API, sem limite de tempo, e os controles de robustez ficam para depois da liberação aos usuários. | §8 e §10: parser, Rules Loader e cliente de telemetria (com credencial) na mesma aplicação FastAPI. §15: os únicos limites são tamanho e número de linhas. §11.3: `ast.NodeVisitor` recursivo. A captura de `SyntaxError` só vem na Sprint 6 (TASK-BE-010), o limite de profundidade e o rate limit na Sprint 9 (TASK-BE-012/013) e os logs seguros na Sprint 10 (TASK-BE-014). Enquanto isso, §25 libera o MVP 1.0 a testadores já na Sprint 4. | Uma entrada de até 50 KB com expressões encadeadas (ex.: `1+1+…`) gera uma AST mais profunda que o limite de recursão do Python, o que provoca `RecursionError` e HTTP 500. `ast.parse` roda em C e não pode ser interrompido por timeout em thread, então um único worker preso degrada todos os alunos no pico de entrega. Uma falha de memória do parser aconteceria num processo que guarda credencial do banco. Até a Sprint 6, todo erro de sintaxe vira 500. | ADR-01: serviço `analyzer` sem segredos e sem egress, com workers descartáveis, timeout de 2 s (kill) e `RLIMIT_AS`. A travessia é iterativa, com limite de profundidade e de nós. Limites, `SyntaxError` e logs sem código entram no MVP (7.2); rate limit e admissão entram antes de qualquer exposição à internet (Sprint 10). Todos fazem parte da DoD (seção 8). |
| 3 | O domínio está incompleto: a exigência do assunto de cada lista e a precedência da questão aparecem como opcionais. | Permissões p.1 §Introdução: "é obrigatória a implementação do assunto de cada lista" e "a prioridade será sempre o que está definido na questão". Rascunho §7.5 exige assunto só na Lista 6, e só auto-chamada direta. RF-012/TASK-BE-008 estão como "Medium / Recomendado" (§26), sem fonte de dados, formato ou responsável. §25: MVP 1.0 tem regras só das Listas 1–2, mas o seletor vai de 1 a 6 (RF-003). | A ferramenta aprova soluções que serão anuladas (ex.: Lista 2 sem laço) e acusa o que a questão permite. Isso contradiz o objetivo do §3 e mina a confiança na ferramenta. Com *default deny*, alunos das Listas 3–6 receberiam no MVP 1.0 violações para todo conteúdo permitido. | FR-10 e FR-11 passam a Must. R-02/R-68 entram no bloco `requirements`. Cada questão ganha um arquivo `questions/L<n>-Q<m>.yaml`, cadastrado por monitores e aprovado por monitor-chefe ou professor (aprovação conferida por quem faz o merge, Q-22, US-13, Q-08). O seletor passa a ser controlado por `IPC_ENABLED_LISTS`: L1 no MVP; as demais listas foram habilitadas nas Sprints 20 a 23 (hoje, as seis no `render.yaml`). Ver Q-04, Q-05, C-03 e Q-08. |

**Demais inconsistências encontradas (resumo):**

- **I-01** — A versão do Python se contradiz: §2 decide "3.12+" e, na mesma célula, diz "backend deve usar 3.11+"; §18 usa `python:3.12-slim` e TASK-DE-002 usa `python:3.11-slim`. Nenhuma das opções considera a versão do Dikastis. Correção: NFR-21 e Q-01.
- **I-02** — A imagem base também diverge: RNF-006 diz "Alpine-based (revisado para Debian-slim)" e o §31 diz "Alpine/Debian-slim". Correção: `python:3.13-slim` fixada por digest (5.3).
- **I-03** — O SLO de 99,9% (RNF-003) não é compatível com a hipótese de free tier com cold start (§2, linha "Render/Vercel"), nem com a ressalva "excluindo cold starts" (RNF-001). Correção: P-05, NFR-06 e ADR-03.
- **I-04** — As unidades de capacidade não batem: RNF-002 fala em "500 requests por minuto", mas o §25 (MVP 1.2) fala em "500 chamadas simultâneas". Correção: NFR-04 (vazão) separado de NFR-05 (concorrência).
- **I-05** — O rate limit de 10 req/IP/min (§2, TASK-BE-013) bloqueia laboratórios e Wi-Fi do campus atrás de NAT, e o limitador em memória não é compartilhado entre instâncias. Correção: P-04, FR-19 e ADR-03 (instância única).
- **I-06** — A precedência inclui um nível "Regra Geral" que não existe no documento de permissões (§7.4). Correção: C-02.
- **I-07** — `AsyncFor` está mapeado como permitido (§12). Correção: C-01.
- **I-08** — A detecção de métodos só olha `visit_Call` (§11.4; ADR-003 do rascunho), então não pega referências sem chamada (`f = s.split`). Correção: o fato `method:<nome>` é emitido para todo `Attribute` (5.2.3).
- **I-09** — A tabela `analytics_events` (§14) tem uma única coluna `rule_violated_id`. Ela não representa submissões com várias violações nem a questão, e não guarda `ruleset_version`. Correção: esquema `telemetry` (5.2.4).
- **I-10** — A frase "sofrer garbage collection imediatamente" (RNF-005) não pode ser verificada e o CPython não garante esse comportamento. Correção: teste canário (NFR-11).
- **I-11** — O §17 espera "400 ou 413" para "recursão infinita textual", mas entrada aninhada com até 50 KB é uma requisição bem formada. Correção: 422 `ANALYSIS_LIMIT` (5.2.2).
- **I-12** — Os KPIs não podem ser medidos: o §30.1 cita uma "base histórica" que não existe e o §3 quer "submissões inválidas… a quase zero" sem linha de base. Correção: NFR-18, P-08, Q-09 e REC-05.
- **I-13** — O §30.3 diz que `os.system("rm -rf /")` gera "bloqueio do Import". Sem `import`, porém, o nó é `Call(Attribute(Name))` e a violação correta é R-04 sobre `os`/`system`. Correção: corpus de evasão (DoD).
- **I-14** — Os RFs estão agrupados ou fora de sequência ("RF-006 a RF-010", "RF-019 e RF-026"), o que impede rastrear cada um. Correção: FR-01…FR-21 atômicos.
- **I-15** — O professor edita JSON por PR (§21), mas a validação e a documentação só chegam na Sprint 11 (TASK-DO-001). Correção: loader com validação e *fail-fast* no MVP (S1-02); FR-21 e US-14 na Sprint 24.
- **I-16** — A CI completa só vem na Sprint 8 (TASK-DE-003), enquanto a DoD do §27 exige CI desde a primeira task. Correção: S1-01.
- **I-17** — US-003 fala em "focar na lógica, não na sintaxe", mas a ferramenta verifica permissões, não lógica. Correção: US-11 reescrita.
- **I-18** — "Acessibilidade certificada" (§25) não indica norma nem método. Correção: NFR-19 (WCAG 2.1 AA, axe-core).
- **I-19** — O ADR-002 do rascunho diz que o servidor é "mais seguro" que o Pyodide. É o contrário: analisar no cliente elimina superfície de ataque no servidor. Os motivos válidos são consistência do ruleset, telemetria e custo de download. Correção: ADR-01, alternativa C.
- **I-20** — São 12 sprints sem duração, capacidade nem estimativa, e o aluno só recebe valor na Sprint 4. Correção: P-02, Q-13 e seção 7 (plano datado para um desenvolvedor, com MVP na Sprint 9 e piloto em 2027.1).
- **I-21** — O diagrama do §8 não mostra fronteiras de confiança, e o cliente de telemetria fica no mesmo processo do parser. Correção: 5.1.

## 7.2 Tasks do MVP (Sprints 1 a 9)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S1-01 | US-15 | Criar o monorepo com `pyproject.toml` (ruff com regras de segurança, `mypy --strict`, pytest), a guarda de código do NFR-09 e o workflow `ci.yml` (lint, type, test). O import-linter entra com a `ipc_api` (Sprint 8) e a governança das regras por processo, na Sprint 24 (sem CODEOWNERS; Q-22) | Repositório `ip-checker/` (`backend/`, `frontend/`, `rulesets/`, `docs/`) e `.github/workflows/ci.yml` | 2 | — | Um PR com erro de lint ou de tipo é bloqueado pela CI |
| S1-02 | US-05 | Criar o modelo Pydantic do ruleset v2 e o loader imutável (`MappingProxyType` com índice `fato → regras`, *fail-fast*). Codificar R-03…R-36 em `base.yaml` (proibições gerais, Lista 1 e Lista 2 sem o `zip`, que depende de predicado), com mensagens em PT-BR e citação da fonte | `backend/src/ipc_analyzer/engine/ruleset.py`, `rulesets/2026.2/base.yaml`, `docs/mapping-R-xx.md` | 3 | S1-01 | Ruleset inválido impede o analisador de ficar pronto. A matriz registra as decisões Q-02 a Q-07 aplicáveis. Cobertura ≥ 90% |
| S2-01 | US-03, US-15 | Implementar os guards (UTF-8, até 51.200 bytes, até 1.000 linhas, sem NUL), o `parse` com a gramática do Python 3.13 e a tradução de `SyntaxError` para PT-BR, mais a medição iterativa de profundidade (≤ 200) e de nós (≤ 60.000, calibrado na S5-01) | `backend/src/ipc_analyzer/engine/guards.py`, `engine/parse.py` (único ponto com `ast.parse`) | 3 | S1-01 | Os testes dos limites passam. Uma cadeia `1+1+…` com 25 mil termos retorna `ANALYSIS_LIMIT` sem `RecursionError` |
| S2-02 | US-01, US-03 | Montar a SPA mínima contra o contrato de 5.2.2, com respostas simuladas: área de código com numeração de linhas, seletor de lista, painel com os estados do MVP e hook `useValidateCode.ts` com `AbortController` de 10 s | `frontend/src/components/*`, `frontend/src/hooks/useValidateCode.ts`, `frontend/src/types/api.ts` | 3 | S1-01 | Os testes Vitest/RTL dos estados válido, com violações, erro de sintaxe, entrada rejeitada e falha de rede passam |
| S3-01 | US-05 | Implementar a coleta de nomes ligados pelo aluno e o extrator iterativo de fatos (`node`, `op`, `cmp`, `builtin`, `method`, `kwarg`, `const`, `param`, `target:for_unpack`) | `backend/src/ipc_analyzer/engine/symbols.py`, `engine/facts.py` (hoje `engine/facts/`, S24-02) | 5 | S2-01 | `f = s.split` produz `method:split`. Uma variável do aluno chamada `len` não produz `builtin:len`. Cobertura ≥ 90% |
| S4-01 | US-05 | Implementar o avaliador de política v1: *default deny*, cumulatividade, proibições gerais e "fora da lista", com categorias, deduplicação e truncamento. Predicados e exigências entram nas Sprints 12 e 20 a 23; overrides de questão, na Sprint 24 | `backend/src/ipc_analyzer/engine/policy.py`, `engine/models.py` (`Violation`, `AnalysisResult`) | 3 | S1-02, S3-01 | Os testes de precedência passam. `type("C", (), {})` gera R-09 e `eval(...)` gera R-04 |
| S4-02 | US-05, US-15 | Montar o corpus golden das R-03…R-36 (≥ 3 casos por regra) e o corpus de evasão (`getattr`, `eval`, `__import__`, dunders, alias, sombreamento), escritos pelo monitor-desenvolvedor (P-08) | `backend/tests/golden/*.yaml` e `backend/tests/test_golden.py` | 3 | S4-01 | 0 FP e 0 FN, com job de CI bloqueante |
| S5-01 | US-15 | Implementar o pool Pebble (`forkserver`, 2 workers, `max_tasks` 500, *initializer* com `RLIMIT_AS`, `RLIMIT_FSIZE` e `RLIMIT_NOFILE`, timeout de 2 s) e o serviço interno | `backend/src/ipc_analyzer/runtime/pool.py`, `backend/src/ipc_analyzer/service/app.py`: `POST /internal/analyze`, `GET /internal/health` | 5 | S4-01 | Timeout mata e substitui o worker. `MemoryError` vira `ANALYSIS_LIMIT`. A memória base do worker é medida e registrada em P-04 |
| S6-01 | US-15 | Escrever o Dockerfile do analyzer (`python:3.13-slim` por digest, UID 10001, sem segredos) e o compose com `read_only`, `cap_drop: [ALL]`, `security_opt: no-new-privileges`, `pids_limit: 64`, `mem_limit: 512m` e rede `analyzer_net` com `internal: true`. Só `/tmp` (socket do `forkserver`) e `/dev/shm` (semáforos do pool) são graváveis, em memória, com 16 MB e `noexec` | `backend/Dockerfile`, `deploy/compose.yaml`, `backend/tests/test_container.py` (desde a S7, `backend/tests/security/test_isolation.py`), job `container` no `ci.yml` (desde a S7, `security`) | 2 | S5-01 | O teste de configuração (`docker inspect`) passa em 100% dos itens do NFR-07 |
| S7-01 | US-15 | Escrever a suíte de segurança contra o endpoint interno do analisador (itens 2 a 12 da seção 8) e os testes de isolamento do contêiner, como job de integração na CI | `backend/tests/security/test_malicious_submissions.py`, `backend/tests/security/test_isolation.py`, job `security` no `ci.yml` | 3 | S6-01 | 100% da suíte passa, nenhum 5xx genérico ocorre e `/internal/health` responde ao final |
| S8-01 | US-01, US-03 | Implementar o endpoint de validação com modelos Pydantic, `ENABLED_LISTS=1`, cliente `httpx` (timeout 3 s), mapeamento de erros (413, 422, 503), validação da resposta do analyzer, `GET /api/v1/lists`, `/health` e `/ready`, e o contrato import-linter que proíbe `ast` na API | `backend/src/ipc_api/routes/validate.py`, `routes/meta.py`, `schemas.py`, `clients/analyzer.py`; `POST /api/v1/validate`; `docs/openapi.json` e `backend/tests/test_api_contract.py` (schemathesis) | 5 | S6-01 | Os testes de contrato OpenAPI passam. A L2 retorna 422 `LIST_NOT_ENABLED`. Com o analyzer parado, retorna 503 `ANALYZER_UNAVAILABLE` |
| S9-01 | US-01 | Configurar logs JSON (`structlog`) com `request_id`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`, um filtro que rejeita campos de código e IP, e o teste canário | `backend/src/ipc_api/logging.py`, `backend/src/ipc_analyzer/logging.py`, `backend/tests/test_log_contract.py` | 2 | S8-01 | O esquema do log é validado e o marcador canário aparece 0 vezes nos logs da suíte |
| S9-02 | US-01, US-03 | Integrar a SPA à API real (tipos gerados do OpenAPI) e escrever o smoke e2e local com Playwright | `frontend/src/services/api.ts`, `frontend/e2e/smoke.spec.ts` | 2 | S2-02, S8-01 | Código válido na L1 mostra sucesso; `for` na L1 mostra R-34 na linha 2; erro de sintaxe mostra linha e coluna |
| S9-03 | US-15 | Estender a suíte de segurança à API pública (itens 1, 3, 4 e 13 da seção 8 via `POST /api/v1/validate`) | `backend/tests/security/test_api_limits.py` | 1 | S7-01, S8-01 | 100% passa, sem 5xx genérico, e `/ready` = 200 ao final |

Total do MVP: 42 SP em 9 sprints, distribuídos conforme a capacidade de cada sprint (5, 6, 5, 6, 5, 2, 3, 5 e 5 SP).

## 7.3 Tasks da Sprint 10 (proteção para exposição pública)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S10-01 | US-17 | Implementar o limite de taxa em memória (janela deslizante de 60 s: 10/min por `X-Client-Id`, 120/min por IP externo e 1.000/min para `IPC_RATE_LIMIT_CAMPUS_CIDRS`; IPv6 por /64; IP lido do `X-Forwarded-For` conforme `IPC_TRUSTED_PROXY_HOPS`) e o controle de admissão (4 análises simultâneas, até 64 em espera por no máximo 1 s) | `backend/src/ipc_api/ratelimit.py`, `admission.py`; 429 `RATE_LIMITED` e 503 `OVERLOADED` em `POST /api/v1/validate` | 3 | S8-01, S9-01 | A 11ª verificação em 1 min do mesmo cliente recebe 429 com `Retry-After`. 60 clientes atrás de um IP do campus, com 5 verificações cada, não recebem 429. Sob saturação, 503 com `Retry-After` sem esperar a análise em curso. Nenhum IP ou `X-Client-Id` nos logs |
| S10-02 | US-18 | Gerar o `X-Client-Id` por sessão e mostrar estados distintos para limite de taxa, sobrecarga, serviço indisponível e código acima de 50 KB, com contagem regressiva da espera | `frontend/src/services/clientId.ts` (removido na S13-03, com o fim do `X-Client-Id`), `components/ResultPanel.tsx`, `e2e/smoke.spec.ts` | 2 | S9-02, S10-01 | No navegador, a 11ª verificação da mesma aba mostra o limite e o tempo de espera vindo do servidor; o botão de nova tentativa só é liberado ao final |
| S10-03 | US-15, US-17 | Estender a suíte de segurança ao limite de taxa pela borda: 11ª requisição da sessão, `X-Forwarded-For` forjado e rajada de um único IP | `backend/tests/security/test_api_rate_limit_edge.py` | 1 | S9-03, S10-01 | 100% passa. Forjar o `X-Forwarded-For` não cria identidades novas nem rende o limite do campus. Um IP externo não passa de 120 verificações por minuto |

## 7.4 Tasks da Sprint 11 (deploy do piloto)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S11-01 | US-15 | Imagem do piloto: API (UID 10001) e analisador (UID 10002, `env -i`, só em `127.0.0.1`) sob o `supervisord`; filtro seccomp nos workers (`socket`, `socketpair`, `execve`, `execveat`) com modos `off`, `optional` e `required` (fail-closed); 160 MiB por worker; Blueprint do Render sem deploy automático | `deploy/render/Dockerfile`, `deploy/render/supervisord.conf`, `backend/src/ipc_analyzer/runtime/sandbox.py`, `render.yaml`, `backend/tests/security/test_pilot_isolation.py` | 3 | S10-01 | Na imagem do piloto: UIDs separados, ambiente do analisador sem o segredo, ambiente da API ilegível para o UID 10002, worker com um filtro seccomp a mais, socket, `execve` e escrita em disco falhando, só a API fora do loopback e o pior caso de 50 KB dentro de 160 MiB |
| S11-02 | US-17 | CORS só para a origem da página (`IPC_CORS_ORIGINS`, inclusive nos erros), HSTS e `nosniff` na API, versão implantada em `/ready`; página com `VITE_API_BASE_URL` e build da Vercel (Build Output API v3) com CSP apontando só para a API, HSTS e `version.json` | `backend/src/ipc_api/edge.py`, `frontend/scripts/vercel-build.mjs`, `frontend/scripts/vercel-config.mjs`, `frontend/vercel.json` | 2 | S11-01 | Preflight da página aceito e de outra origem recusado; 429 e 413 legíveis pela página; sem nenhum cabeçalho CORS nas Fases 0 e 2; smoke e2e verde entre origens |
| S11-03 | US-17, US-19 | Deploy disparado depois da CI na `main` (deploy hooks), espera da versão nova na API e na página, verificação do piloto no ar (cabeçalhos, CORS, TLS ≥ 1.2, nada além da API exposto) e smoke e2e; UptimeRobot e contas configurados pelo autor do projeto (passo a passo em `deploy/README.md`) | `.github/workflows/deploy.yml`, `backend/tests/pilot/test_deployed_pilot.py` | 1 | S11-02 | Uma release na `main` vai ao ar sem passo manual, com as verificações e o smoke verdes e `/ready` = 200; sem a configuração, o pipeline só avisa |

## 7.5 Tasks da Sprint 12 (liberação do piloto, Marco 2)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S12-01 | US-06 (Lista 1), US-11 | Avaliar as exigências do ruleset (passo 6 do algoritmo) e ativar a R-02 da Lista 1 (`if` ou ternário, Q-05) como dado; mostrar a exigência como da solução inteira e avisar, antes da verificação, que as regras de questão ainda não valem | `backend/src/ipc_analyzer/engine/policy.py`, `rulesets/2026.2/base.yaml` (`requirements`), `backend/tests/golden/requirements.yaml`, `frontend/src/components/ResultPanel.tsx` | 2 | S11-02 | Código da Lista 1 sem `if` nem ternário recebe R-02 `EXIGENCIA`; `if` em string ou comentário não conta; 0 FP e 0 FN no corpus golden |
| S12-02 | US-22 | Teste de carga curto com o k6 contra a imagem do piloto, emulando os planos do Render, para decidir entre o plano gratuito e o Starter antes do primeiro prazo | `deploy/load/pilot-load.js`, `deploy/load/run_load.py` | 1 | S11-01 | Relatório com P95, P99 e falhas a 500/min nos dois planos e a recomendação registrada (ADR-03) |
| S12-03 | US-11 | Guia de uso para monitores e alunos no piloto (o que a ferramenta faz e não faz, leitura do relatório, limites) e roteiro da apresentação do Marco 2 | `docs/guia-do-piloto.md` (substituído por `docs/guia-da-equipe.md` na S19-02) | 1 | S12-01 | Guia revisado pelo autor do projeto antes da liberação |

## 7.6 Tasks das Sprints 13 a 19 (acesso restrito, plágio e feedback)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S13-01 | US-30 | Banco de contas: contêiner `postgres` no Compose (rede interna, sem porta no host, volume próprio), migrações SQL reversíveis com o esquema `app` (5.2.5), papel `ipc_app`, pool `asyncpg` na API (`IPC_DATABASE_URL`) e *seed* idempotente da conta do desenvolvedor (dois e-mails; senha de `IPC_DEV_INITIAL_PASSWORD` só na criação) | `database/migrations/`, `deploy/compose.yaml`, `backend/src/ipc_api/accounts/` | 2 | — | A migração aplica e reverte; o *seed* roda duas vezes sem duplicar; o `/ready` confere o banco; nenhum segredo aparece em log |
| S13-02 | US-26 | Sessão e login por senha: Argon2id, `POST /api/v1/auth/login` (nome ou e-mail), `logout`, `GET /api/v1/auth/me`, cookie de sessão (NFR-22), dependência que exige conta `ativo` em todas as rotas exceto `/health`, `/ready` e `/api/v1/auth/*`, limite de taxa por conta (recalibrar o 10/min, C-04), limite de tentativas por conta e por IP e mensagens do FR-25 | `backend/src/ipc_api/auth/`, `deps.py`, `ratelimit.py`, `docs/openapi.json` | 3 | S13-01 | Sem sessão, todas as rotas do OpenAPI respondem 401; credencial inválida tem mensagem única; o status só aparece com a senha correta; depois de 5 falhas em 15 min, a próxima tentativa espera |
| S13-03 | US-26 | Telas inicial (só Registrar e Entrar sem sessão) e Entrar, roteamento com guarda, cliente da API com o cookie da mesma origem e fim do `X-Client-Id` | `frontend/src/` (React Router), `frontend/e2e/auth.spec.ts` | 1 | S13-02 | E2E: sem login só aparecem Registrar e Entrar; o desenvolvedor entra e verifica um código |
| S14-01 | US-24 | Registro por e-mail e senha: campos obrigatórios, domínio exato (`cin.ufpe.br` e `ufpe.br`), política de senha compartilhada entre frontend e backend, nome e e-mail únicos sem diferenciar maiúsculas, e-mails do desenvolvedor reservados e status `aguardando_verificacao` | `backend/src/ipc_api/auth/accounts.py`, `frontend/src/pages/Register.tsx` | 2 | S13-02 | `x@xcin.ufpe.br`, `x@ee.ufpe.br` e senha fraca são recusados pelo backend; nome repetido com outra caixa é recusado |
| S14-02 | US-24 | E-mail de verificação: adaptador (`smtp` e `brevo`, por HTTPS; Mailpit no Compose, em `127.0.0.1` e com porta conferida contra os outros projetos da máquina), token de 256 bits guardado como hash, válido por 24 h e de uso único, reenvio limitado, link montado a partir de `IPC_PUBLIC_BASE_URL` para uma página que confirma por `POST`; depois da confirmação, `aguardando_aprovacao` | `backend/src/ipc_api/mail.py`, `frontend/src/pages/Verify.tsx`, `deploy/compose.yaml` | 2 | S14-01 | Link expirado ou usado não funciona; um `GET` no link não gasta o token; `Host` forjado não muda o link |
| S14-03 | US-29 | Perfil: editar nome, curso, tratamento e senha (com a senha atual), ou definir a senha numa conta do Google; nenhuma rota altera o próprio cargo; o tratamento só sai nas respostas ao próprio titular | `PATCH /api/v1/profile`, `POST /api/v1/profile/password`, `frontend/src/pages/Profile.tsx` | 2 | S13-02 | Nenhuma resposta sobre outra pessoa traz o tratamento (teste de contrato); trocar a senha encerra as outras sessões |
| S15-01 | US-27, US-28 | Política de cargos: função pura `can()` com a tabela do FR-27, proteção da conta do desenvolvedor, `ja_foi_monitor_chefe` permanente, remoção para Ex-monitor, Conselheiro ou inativo, reativação e encerramento das sessões do alvo | `backend/src/ipc_api/auth/policy.py`, `backend/tests/test_role_policy.py` | 2 | S13-01 | Matriz completa (4 cargos × ações × cargos-alvo) testada; remover quem já foi monitor-chefe resulta em Conselheiro, e quem nunca foi, em Ex-monitor |
| S15-02 | US-27, US-28 | API de gerenciamento: fila, aprovar com cargo, recusar, membros, alterar cargo, remover e reativar, cada item com as ações permitidas para quem consulta | `backend/src/ipc_api/routes/admin.py`, `backend/src/ipc_api/auth/management.py` | 2 | S15-01 | Monitor recebe 403 em todas as rotas de gerenciamento por chamada direta; monitor-chefe não age sobre professor; ninguém além do desenvolvedor altera a conta dele |
| S15-03 | US-27, US-28 | Tela de gerenciamento: fila (nome, e-mail, curso, método e data), membros com etiquetas coloridas e com o nome do cargo, ex-monitores e conselheiros, só os botões permitidos e confirmação antes de remover | `frontend/src/pages/Admin.tsx` | 2 | S15-02 | E2E de aprovação e remoção; axe sem violações graves |
| S16-01 | US-25 | Google com Authlib: `state`, `nonce`, PKCE e ID token validado; `hd` só como dica; `email_verified` e domínio exato conferidos no backend; vínculo por e-mail, com descarte da senha de conta não verificada; formulário complementar; Entrar com o Google sem conta leva ao registro | `backend/src/ipc_api/auth/google.py`, `backend/src/ipc_api/auth/google_accounts.py`, `backend/src/ipc_api/routes/google.py`, `frontend/src/pages/GoogleComplete.tsx` | 3 | S14-01 | Com um provedor OIDC falso nos testes: domínio fora, `hd` adulterado e `email_verified` falso são recusados; o mesmo e-mail com senha e com Google dá a mesma conta |
| S16-02 | US-25 | Mesma origem no piloto: *rewrite* de `/api/*` na Vercel, cookie na origem da página, CORS desligado, `IPC_TRUSTED_PROXY_HOPS` conferido e retorno do Google na origem da página; verificações do piloto passam a usar login | `frontend/scripts/vercel-config.mjs`, `render.yaml`, `.github/workflows/deploy.yml`, `backend/tests/pilot/` | 1 | S16-01 | O piloto no ar só responde com login; a P-15 é confirmada ou a alternativa fica registrada |
| S16-03 | US-15 | Suíte de segurança da autenticação: força bruta, CSRF (`Origin`), fixação e atributos do cookie, matriz de autorização por chamada direta, tokens vencidos e reusados, domínios parecidos, `hd` e `email_verified`, pré-sequestro de conta e nenhuma senha em log (canário) | `backend/tests/security/test_auth.py` | 2 | S15-02, S16-01 | Itens 16 a 20 da seção 8 verdes na CI |
| S17-01 | US-31 | Motor de similaridade (ADR-05): normalização por `tokenize`, nomes do aluno em marcadores (`symbols.py`), *winnowing* em tokens e em nós da AST, *score* ponderado com pesos documentados e limiares em constantes | `backend/src/ipc_analyzer/engine/similarity.py`, `backend/tests/similarity/` | 3 | — | Corpus de pares (NFR-25) verde; a cópia com variáveis renomeadas dá ≥ 99% |
| S17-02 | US-31 | `POST /internal/similarity` no analisador (worker isolado, mesmos guards e timeout) e `POST /api/v1/similarity` com sessão, classificação pelas faixas e contrato OpenAPI | `backend/src/ipc_analyzer/service/app.py`, `backend/src/ipc_api/routes/similarity.py` | 1 | S17-01, S13-02 | Valores exatos de 99, 95, 90 e 80% caem na faixa certa; entradas maliciosas não geram 5xx (seção 8, item 22) |
| S17-03 | US-31 | Painel de plágio: duas áreas lado a lado (empilhadas no celular), Verificar, porcentagem e classificação com cor e texto, aviso de indício e de código curto | `frontend/src/pages/Plagiarism.tsx` | 2 | S17-02 | E2E com cópia renomeada mostra "Plágio"; axe sem violações graves |
| S18-01 | US-32 | Camada de provedores (ADR-06): interface `generate`, adaptadores `openai_compat` (OpenAI, Groq e DeepSeek) e `gemini`, provedor `fake`, configuração por variáveis, IA principal e de reserva (`IPC_LLM_*` e `IPC_LLM_FALLBACK_*`), 12 s por tentativa e prazo total de 28 s; sem IA, o feedback é montado por modelos (ADR-06, item 6) | `backend/src/ipc_api/feedback/providers.py`, `backend/src/ipc_api/feedback/service.py` | 2 | S13-02 | Adaptadores testados contra respostas gravadas; a chave nunca aparece em log nem em resposta |
| S18-02 | US-32 | Montagem e validação: apresentação pela tabela do FR-30, abertura e frase obrigatória pelo backend, proibições pelos nomes do `display.py`, `[ALUNO]` em todo o prompt, comentários removidos pelo analisador, dados delimitados, saída validada, com a IA de reserva e, sem texto válido, o feedback montado por modelos, limite por conta e teto diário, e `POST /api/v1/feedback` | `backend/src/ipc_api/feedback/compose.py`, `backend/src/ipc_api/routes/feedback.py`, `backend/src/ipc_analyzer/engine/feedback.py`, `backend/src/ipc_analyzer/service/app.py` | 3 | S18-01 | NFR-26 atendido com o provedor falso (respostas boas e adversariais); a requisição ao provedor não traz o nome real |
| S19-01 | US-32 | Feedback na página: Nome do aluno (obrigatório), Anotação (opcional), Gerar feedback, campo editável e Copiar; o texto é exibido como texto puro | `frontend/src/components/FeedbackPanel.tsx`, `frontend/src/pages/Checker.tsx`, `frontend/e2e/feedback.spec.ts` | 2 | S18-02 | E2E com o provedor falso nos três tratamentos |
| S19-02 | US-11, US-24…US-32 | Liberação para a equipe: guia da equipe (substitui o guia do piloto), aviso de privacidade no registro (Q-19), passo a passo das contas externas (Supabase, cliente OAuth do Google, e-mail e provedor de LLM) em `deploy/README.md`, deploy e verificações do piloto com login e apresentação do Marco 2 revista | `docs/guia-da-equipe.md`, `frontend/src/pages/Privacy.tsx`, `frontend/src/components/PrivacyNotice.tsx`, `deploy/README.md` | 3 | S16-02, S19-01 | Piloto no ar com login; guia revisado pelo autor; apresentação marcada |

Total: 40 SP em 7 sprints (6, 6, 6, 6, 6, 5 e 5 SP). As Sprints 18 e 19 caem no recesso; ver a sensibilidade em 7.1. As tasks das Sprints 20 a 29 são detalhadas no início de cada uma, como nas Sprints 10 a 12 (7.7 em diante).

Situação: as Sprints 13 a 19 foram concluídas em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

## 7.7 Tasks da Sprint 20 (Lista 2 e gabaritos)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S20-01 | US-07, US-06 | R-37 com o predicado `zip_in_for_header` desenhado em 5.2.3 e no FR-09: o extrator marca o `zip()` built-in que é o iterável do comando `for` e o alvo desse `for` com o número de sequências; `builtin:zip` e `target:for_unpack` só são permitidos com 2 ou mais (Q-02 d, Q-04), nas Listas 2 a 4. Exigência R-02 da Lista 2 (`for` ou `while`, Q-05). Lista 2 habilitada (`IPC_ENABLED_LISTS=1,2`) e ruleset `2026.2.1` | `backend/src/ipc_analyzer/engine/facts.py` (hoje `engine/facts/`, S24-02), `engine/conditions.py`, `rulesets/2026.2/base.yaml`, `backend/tests/golden/list2.yaml` | 3 | S12-01 | Os três cenários da US-07 (o da Lista 5 depende da R-64, Sprint 23); pelo menos 3 casos golden por regra; e2e da Lista 2 |
| S20-02 | US-07 | Gabaritos de períodos anteriores com zero violação na sua lista (Q-14): harness que lê `IPC_GABARITOS_DIR` (`<período>/lista-<n>/*.py` e `excecoes.yaml` para o que só o enunciado libera, até a Sprint 24) e job "Gabaritos" na CI, que baixa o repositório privado com token só de leitura quando `GABARITOS_REPO` e `GABARITOS_TOKEN` estão definidos | `backend/tests/official_answers/`, `.github/workflows/ci.yml`, `rulesets/README.md` | 2 | S20-01 | Harness testado com soluções sintéticas; saída sem código; gabaritos reais rodando na CI depois que o autor criar o repositório privado |

Situação: a Sprint 20 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

## 7.8 Tasks da Sprint 21 (telemetria e alertas)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S21-01 | US-16 | Telemetria anônima (FR-16, C7): migração `0002` com o esquema `telemetry` de 5.2.4, papéis `ipc_writer` e `ipc_reader`, as views do FR-17 (`v_top_rules_by_list`, `v_syntax_error_rate` e `v_weekly_volume`) e o expurgo de 12 meses (P-06); fila limitada na API com gravação em lote, fora do caminho da resposta; evento por verificação, inclusive as recusas de código e de limite de análise | `database/migrations/0002_telemetria.up.sql`, `backend/src/ipc_api/telemetry.py`, `backend/src/ipc_api/routes/validate.py` | 3 | S13-01 | O usuário da API insere e expurga, mas não lê; o `ipc_reader` lê só as views; nenhuma coluna identifica alguém (US-16, NFR-12); banco fora não afeta a verificação |
| S21-02 | US-19 | Alertas do NFR-15: `GET /health/slo` com o P95 do `/validate` e a taxa de 5xx dos últimos 5 minutos, 503 fora da meta; terceiro monitor do UptimeRobot; exercício de falha documentado e feito no compose | `backend/src/ipc_api/slo.py`, `backend/src/ipc_api/routes/meta.py`, `deploy/README.md` | 2 | S11-03 | Exercício local: com o limite apertado, `/health/slo` vira 503 e volta a 200 ao restaurar; o exercício no piloto depende das contas do autor |

Situação: a Sprint 21 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

## 7.9 Tasks da Sprint 22 (Listas 3 e 4)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S22-01 | US-08 | Regras R-38 a R-58 (Lista 3) e R-59 e R-60 (Lista 4) no ruleset pelo mapeamento de 5.2.3; exigência R-02 das Listas 3 (lista ou tupla) e 4 (`def`), pela Q-05; fato `derived:nested_function` para a função aninhada da Q-02 (f); ruleset `2026.2.2` | `rulesets/2026.2/base.yaml`, `backend/src/ipc_analyzer/engine/facts.py` (hoje `engine/facts/`, S24-02), `backend/tests/golden/list3.yaml`, `backend/tests/golden/list4.yaml` | 3 | S20-01 | Pelo menos 3 casos golden por regra; `.append()` na L2 mostra "a partir da Lista 3"; os casos em aberto do mapeamento ficam como estão, registrados |
| S22-02 | US-08 | Listas 3 e 4 habilitadas (API, compose, Render e página simulada) e e2e das duas | `backend/src/ipc_api/settings.py`, `deploy/compose.yaml`, `render.yaml`, `frontend/e2e/smoke.spec.ts` | 1 | S22-01 | E2E: lista com `append` passa na L3, `append` na L2 é "Fora da lista", função passa na L4 e função aninhada é R-04 |

Situação: a Sprint 22 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

## 7.10 Tasks da Sprint 23 (Listas 5 e 6, recursão e registro do gerenciamento)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S23-01 | US-06 | Regras R-61 a R-67 (Lista 5) pelo mapeamento de 5.2.3, com a R-64 liberando o `zip` (Q-04); predicados `enumerate_in_for_header` e `items_in_for_header` para vários nomes no alvo do `for`; fato `derived:recursion` pelo grafo de chamadas (Tarjan iterativo) e exigências R-02 da Lista 5 (dicionário) e R-68 da Lista 6 (recursão direta ou mútua, C-03); ruleset `2026.2.3` | `rulesets/2026.2/base.yaml`, `backend/src/ipc_analyzer/engine/facts.py` (hoje `engine/facts/`, S24-02), `engine/conditions.py`, `engine/ruleset.py`, `backend/tests/golden/list5.yaml`, `list6.yaml` | 3 | S22-01 | Pelo menos 3 casos golden por regra; código sem recursão na L6 mostra R-68; recursão mútua passa; um ciclo de 400 funções é analisado sem recursão do Python |
| S23-02 | US-06 | Listas 5 e 6 habilitadas (API, compose, Render e página simulada) e e2e das duas | `backend/src/ipc_api/settings.py`, `deploy/compose.yaml`, `render.yaml`, `frontend/e2e/smoke.spec.ts` | 1 | S23-01 | E2E: dicionário com `.items()` no `for` passa na L5, dicionário na L4 é "a partir da Lista 5", recursão passa na L6 e código sem recursão mostra a R-68 |
| S23-03 | US-27 | Registro das ações de gerenciamento (REC-06): migração `0003` com `app.management_log` só de inserção para a API, gravado na mesma transação da ação, com nomes e cargos do momento; expurgo de 12 meses por função `SECURITY DEFINER`; `GET /api/v1/admin/log` e `can_view_log` na conta; seção "Registro de ações" na tela de gerenciamento | `database/migrations/0003_registro_gerenciamento.up.sql`, `backend/src/ipc_api/auth/management.py`, `accounts/store.py`, `accounts/postgres.py`, `routes/admin.py`, `frontend/src/pages/Admin.tsx` | 2 | S15-02 | Cada ação aplicada entra no registro, e as recusadas (403, 409) não; o monitor-chefe e o monitor recebem 403; o usuário da API não altera nem apaga um registro; e2e de aprovação, remoção e reativação confere o registro |

Situação: a Sprint 23 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

## 7.11 Tasks das Sprints 24 a 29 (plano de 06/10/2026)

Origem: o roadmap de 7.1 e a revisão de fim da Sprint 23 (técnica, visual, de CI e de documentação), que o autor pediu para incluir inteira em 06/10/2026. As estimativas seguem a P-02; os detalhes de cada task são refinados no início da sprint, como nas anteriores.

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S24-01 | US-04, US-13 | Overrides por questão (R-01): `rulesets/<período>/questions/L<n>-Q<m>.yaml` com `allow`, `allow_facts`, `deny` e `source`; precedência C-02; `question_id` na API e seletor de questão na página; `QUESTION_RULES_NOT_APPLIED` sem questão; as exceções dos gabaritos (`excecoes.yaml`) migram para os overrides | `engine/policy.py`, `engine/ruleset.py`, `routes/validate.py`, `frontend/src/pages/Checker.tsx` | 3 | S23-01 | Cenários da US-04; override que libera R-05…R-14 marcado como "exige professor" |
| S24-02 | US-12, US-14 | `ipc-rules validate` (CLI) bloqueante na CI e registro único dos predicados (`engine/predicates.py`), importado pelo loader e pelas condições; `facts.py` dividido em extrator, cabeçalho do `for` e grafo de chamadas | `backend/src/ipc_analyzer/cli.py`, `engine/predicates.py`, `engine/facts/` | 2 | S24-01 | Ruleset inválido sai com código ≠ 0 e o caminho do campo; nenhum predicado declarado em dois lugares |
| S24-03 | US-13 | Governança por processo (Q-22 adiada para depois da release; decidida em 09/10/2026: mantém o processo, opção A de 7.13.4): `RULES.md` com o passo a passo do cadastro de uma questão e template de PR para regras; a aprovação de monitor-chefe ou professor é conferida por quem faz o merge, sem fork nem check automático | `RULES.md`, `.github/PULL_REQUEST_TEMPLATE/regras.md` | 1 | S24-01 | Um monitor cadastra uma questão seguindo só o `RULES.md` |
| S24-04 | US-26 | "Esqueci minha senha" (Q-19 b): token de uso único por e-mail, como o da verificação, resposta sempre 202 e limite por conta | `auth/accounts.py`, `frontend/src/pages/ResetPassword.tsx` | 1 | S14-02 | Link vencido ou usado não funciona; definir a senha encerra as outras sessões |
| S25-01 | US-15 | Cadeia de suprimentos da CI: actions fixadas por SHA, `persist-credentials: false`, versão do `uv` fixada, `UV_IMAGE` com digest, `openapi-typescript` no `package.json`; Dependabot mensal para a `develop` (actions, Docker, npm, uv); segredos fora dos passos de instalação no deploy; job `audit` (gitleaks, pip-audit, npm audit, trivy) semanal e ainda não bloqueante | `.github/`, `deploy.yml`, `frontend/package.json` | 2 | — | Nenhum `uses:` por tag; nenhum passo de instalação com segredo no ambiente |
| S25-02 | US-17, US-19 | Deploy seguro e primeiro deploy: `workflow_dispatch` só para a `main` com CI verde; Render primeiro, Vercel depois do `/ready` com a versão certa; conferência de que a ponta da `main` é o commit testado; prazo no lugar do laço; `engines` do Node 24; roteiro do primeiro deploy (migração manual antes do Render, lista de conferência com a P-15); Data API do Supabase desligada ou tabela de migrações fora do `public`; health do Render em `/health`; `docs/runbook.md` com o rollback | `deploy.yml`, `deploy/README.md`, `render.yaml`, `docs/runbook.md` | 2 | S25-01 | Uma segunda release durante o deploy não publica um commit sem CI; o roteiro leva do zero ao piloto sem passo implícito |
| S25-03 | US-30 | Limpeza diária do banco: função `app.housekeeping()` (`SECURITY DEFINER`) que apaga sessões vencidas, tokens usados ou vencidos, contas não verificadas com mais de 48 h (o nome volta a ficar livre) e o registro de gerenciamento com mais de 12 meses; expurgo das contas fora do status `ativo` com 365 dias sem atividade (Q-19 d), com `last_activity_at`; roda ao subir e uma vez por dia, com as contagens em `/health/slo` | `database/migrations/0004_*.sql`, `accounts/postgres.py`, `slo.py` | 2 | S23-03 | A conta do desenvolvedor nunca é apagada; o registro de gerenciamento mantém os nomes depois do expurgo |
| S25-04 | US-15, US-22 | Robustez no plano gratuito: no Render, 1 worker e admissão igual ao número de workers; prazo da API derivado do prazo do pool, com o analisador descartando pedidos vencidos; pool do banco com `timeout` e prazo no `acquire`; sessão em uma consulta; limite por IP folgado em todo `/api/*` antes da sessão; a API não sobe com `IPC_PUBLIC_BASE_URL` sem `https://` quando o cookie é seguro; seccomp e rlimits ampliados (`io_uring_*`, `ptrace`, `process_vm_*`, `bpf`, `userfaultfd`, `unshare`, `RLIMIT_NPROC`, `RLIMIT_CORE`); um handler central de erros com 500 em JSON e `request_id` | `runtime/`, `admission.py`, `accounts/postgres.py`, `auth/middleware.py`, `app.py` | 3 | S25-02 | Nenhuma análise continua depois que a API desistiu; tokens aleatórios não chegam ao banco acima do limite |
| S25-05 | US-32 | Privacidade do feedback: docstrings removidas e matrículas (8 ou mais dígitos), e-mails e CPFs mascarados no código enviado à IA; cota diária persistida e cobrada só depois da análise | `engine/feedback.py`, `feedback/service.py` | 1 | — | Teste com cada dado mascarado; a cota não zera num deploy |
| S26-01 | US-33 | Cabeçalho e navegação no celular: nome curto, menu compacto, subtítulo só em telas maiores, alvos de 44 px; `<title>` por tela, `<nav>` com `aria-current`, `<h2>` na verificação; contraste AA no modo escuro; escala única de títulos e espaçamentos; componentes `Button`, `TextLink`, `ErrorText` e rótulos num `labels.ts` | `frontend/src/components/AppHeader.tsx`, `ui.ts`, `labels.ts` | 2 | — | Nenhuma tela passa de 375 px; axe sem violações graves nos dois temas |
| S26-02 | US-33 | Fluxo em lote: "Próximo aluno", Ctrl+Enter, foco e rolagem até o resultado, foco em Copiar depois de gerar, última lista lembrada, aviso quando o código mudou e o nome não; rascunho em memória que sobrevive à navegação e ao novo login; editor com tabulação de 4, Tab que insere espaços, altura ajustável, Limpar e Colar | `pages/Checker.tsx`, `components/CodeEditor.tsx`, `components/FeedbackPanel.tsx` | 2 | S26-01 | E2E: três alunos seguidos em até 4 ações cada, sem o nome do anterior no feedback |
| S26-03 | US-33, US-09 | Relatório: resumo por categoria, ordem por gravidade, uma linha por regra com as linhas afetadas, cores distintas para anulação e fora da lista, aviso das regras de questão uma vez só; clique na violação seleciona o trecho no editor e marca a linha; trecho do código no cartão; faixa "o código mudou desde a verificação" | `components/ResultPanel.tsx`, `components/CodeEditor.tsx` | 2 | S26-02 | E2E: clicar numa violação seleciona a linha certa |
| S26-04 | US-33, US-21 | Erros iguais em todas as telas: `useApiCall` com prazo, cancelamento e sessão vencida central; foco que não se perde ao enviar; anúncio só do resumo ao leitor de tela; listas com "Tentar novamente"; gerenciamento com busca, filtro por cargo, "Mostrar mais" no registro e ocupado por linha; o simulado exige sessão e cobre `truncated`, `ANALYSIS_LIMIT` e o texto da IA | `frontend/src/hooks/useApiCall.ts`, `pages/*`, `services/mockClient.ts` | 2 | S26-01 | Plágio e feedback têm prazo e cancelamento; sessão vencida leva a Entrar em todas as telas |
| S27-01 | US-31 | Representação canônica (ADR-07): canonização da AST, reordenação por dependência, padrões de laço e multiconjunto de subárvores com Dice e contenção, no analisador; corpus de pares ampliado com cada reescrita da ADR-07 e com soluções independentes | `engine/similarity_tree.py`, `tests/similarity/` | 3 | — | Reescritas da ADR-07 ≥ 95%; soluções independentes < 80% no corpus; 50 KB em menos de 1 s |
| S27-02 | US-31 | Uma contra várias: comparar uma solução com até 100 da turma, em memória, com o peso das subárvores pelo inverso da frequência na turma; aviso de código curto mantido | `POST /api/v1/similarity/batch`, `pages/Plagiarism.tsx` | 2 | S27-01 | Uma linha óbvia que toda a turma escreve não eleva a similaridade |
| S27-03 | US-31 | Trechos realçados: a API devolve os pares de intervalos de linhas que coincidem; o painel realça os dois códigos com rolagem sincronizada; "Trocar A e B" e "Limpar" | `routes/similarity.py`, `pages/Plagiarism.tsx` | 1 | S27-01 | E2E: a cópia reordenada mostra os trechos correspondentes nos dois lados |
| S28-01 | US-22 | Teste de carga com o k6 no Render, já com login, medindo a região do banco (Q-20), e a decisão entre o gratuito e o Starter | `deploy/load/` | 1 | S25-04 | Relatório com P95, P99 e falhas; recomendação registrada na ADR-03 |
| S28-02 | US-23 | Relatório de eficácia (P-09, Q-15): adoção por lista do critério 2 (um registro por conta, período e lista, apagado com a conta), consultas dos critérios 1 e 5 e o formulário da pesquisa do critério 4; a telemetria deixa de contar as verificações da conta de verificação do deploy | `database/migrations/`, `telemetry.py` | 2 | S25-03 | A view só devolve porcentagens por lista |
| S28-03 | US-20 | Passagem de bastão: `docs/onboarding.md` (do zero ao compose verde em 30 min), `CONTRIBUTING.md`, `SECURITY.md`, `docs/README.md` como mapa; runbook completo com o rollback cronometrado (DoD: 5 min ou menos); backup semanal criptografado dos esquemas `app` e `telemetry`; `deploy/README.md` dividido | `docs/`, `.github/workflows/backup.yml` | 2 | S25-02 | Um mantenedor novo sobe o ambiente seguindo só o onboarding |
| S28-04 | US-20 | Documentação e processo: blueprint dividido (ADRs em `docs/adr/`, situação das sprints num `CHANGELOG.md`, decisões em `docs/decisoes.md`); afirmações sobre controles que não existem corrigidas ou marcadas "[PLANEJADO]"; `scripts/release.sh` com tag e GitHub Release; template de PR ampliado; checksum das migrações aplicadas; e2e com uma conta por projeto (sai a pausa de 61 s); CI pesada pulada na `main` e na documentação | `docs/`, `scripts/`, `.github/` | 2 | S28-03 | A `main` recebe uma tag por sprint; nenhum controle descrito como ativo sem existir |
| S29-01 | US-34 | Sinal de múltiplas violações (Q-21): a partir das violações do motor, variedade de proibições gerais, repetição da mesma proibição, salto de lista (quantidade e distância) e construções fora do documento ou incomuns para o nível; faixas iniciais da ADR-08, item 1; só para a equipe, nunca no feedback ao aluno | `engine/indicators.py`, `routes/validate.py` | 2 | S24-01 | `break`, `pass` e `continue` juntos, vários `pass` e construções da Lista 6 na Lista 3 dão indício com as linhas; uma solução limpa não mostra nada |
| S29-02 | US-34 | Soluções de referência por IA: geradas pela equipe a partir só do enunciado, num repositório privado como os gabaritos; comparação pelo motor da ADR-07 | `backend/tests/official_answers/`, `routes/similarity.py` | 2 | S27-01 | Nenhum dado do aluno sai do servidor |
| S29-03 | US-34 | Painel de indícios: as múltiplas violações, a semelhança com as referências e os marcadores de estilo, cada um com motivo e trecho; texto de indício, nunca de prova; 2 ou 3 perguntas sugeridas para a conversa com o aluno | `pages/Checker.tsx`, `components/IndicatorsPanel.tsx` | 2 | S29-01, S29-02 | Falsos positivos "altos" em até 5% das soluções anteriores a 2023 |
| S29-04 | US-34 | Política e calibração: texto combinado com a coordenação (inclusive o que é dito aos alunos), definição de quem gera as referências e calibração das faixas nas soluções anteriores a 2023 e nos casos confirmados ou descartados | `docs/guia-da-equipe.md`, `docs/indicios-de-ia.md` | 1 | S29-03 | Política aprovada pela coordenação antes de o painel ser ligado no piloto |

Situação: a Sprint 24 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

Situação: a Sprint 25 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

Situação: a Sprint 26 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

Situação: a Sprint 27 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md).

Situação: a Sprint 28 foi concluída em 07/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md); ficam para depois da conta de verificação do deploy a carga no piloto de verdade (S28-01) e o primeiro ensaio cronometrado do rollback (S28-03).

Situação: a Sprint 29 foi concluída em 07/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../../CHANGELOG.md); os indícios ficam desligados no piloto até a coordenação aprovar a política e a calibração com soluções anteriores a 2023 ficar na meta (S29-04, `docs/indicios-de-ia.md`).

## 7.12 Tasks das Sprints 30 a 35 (plano de 07/10/2026)

A Sprint 36 deste plano (Fase 2) passou a ser a Sprint 41, em 7.15 (11/10/2026).

Origem: a lista de pendências de 07/10/2026, depois da release da Sprint 29 (tag `sprint-29`, commit `03e3256`, no ar no piloto), que reúne as pendências do piloto adiadas pelo autor, as decisões em aberto, as premissas a confirmar, os critérios de sprints que ficaram abertos e os controles marcados como [PLANEJADO]. A ordem segue a prioridade definida pelo autor: (1) o piloto verificado ponta a ponta; (2) as decisões com a coordenação e o NTI; (3) os dados (gabaritos, questões de 2027.1 e calibração); (4) a prontidão para 2027.1; depois, os controles [PLANEJADO] e a Fase 2. O backlog posterior ao piloto (seção 7.1, "Backlog") não vira task.

Cada task tem um **tipo**: **Engenharia** (executável pelo desenvolvedor no repositório), **Externa** (depende de outra pessoa ou de uma conta externa; a task acompanha a entrada esperada e o critério de desbloqueio, e nunca é dada como concluída sem a ação) ou **Decisão** (escolha do autor, da coordenação, do NTI ou do suporte de TI; as opções estão em 7.13). Responsáveis: **Autor** (o desenvolvedor), **Coordenação**, **NTI**, **Equipe** (monitores e monitores-chefe), **Professor**, **TI do CIn**. As estimativas seguem a P-02 (1 SP ≈ 2 h); tasks externas e de decisão não têm SP de engenharia. Nada aqui foi executado: o estado de cada pendência está na matriz de 7.14.

### 7.12.1 Base de testes de toda sprint

Vale para as Sprints 30 a 36 e não se repete nelas; cada sprint lista só os testes que acrescenta. Sem *branch protection* (GitHub Free, P-02), "bloqueante" quer dizer: o PR só é mergeado na `develop` com o CI verde, conferido por quem faz o merge (`CONTRIBUTING.md`), e a `main` só avança com o CI verde da `develop` (`scripts/release.sh`).

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Lint e tipos do backend | ruff, `mypy --strict`, import-linter | `ci.yml`, job "Backend" (`uv run ruff check .`, `uv run mypy`, `uv run lint-imports`) | PR e push na `develop` (pulado na `main` e em mudança só de `.md`, S28-04) | 0 erros; 4 contratos do import-linter mantidos |
| Unitários e integração do backend | pytest, com PostgreSQL de serviço | `ci.yml`, job "Backend" (`uv run pytest`) | idem | Todos passam; cobertura ≥ 90% (`--cov-fail-under=90`, `backend/pyproject.toml`) |
| Regras e regressão do motor | `ipc-rules validate` e casos golden | `uv run ipc-rules validate ../rulesets --golden tests/golden` (o período de `rulesets/ATIVO`, S31-09) | idem | 0 FP e 0 FN; hoje 296 de 296 casos |
| Contrato da API | pytest com schemathesis | `tests/test_api_contract.py` e `docs/openapi.json` em dia | idem | Contrato em dia e todos os status documentados conferidos |
| Unitários do frontend | Vitest com RTL | `ci.yml`, job "Frontend" (`npm test`) | idem | Todos passam (hoje 229) |
| Lint, tipos e builds do frontend | ESLint, `tsc`, Vite | `npm run lint`, `npm run typecheck`, `npm run build`, `npm run build:vercel` | idem | 0 erros; tipos gerados do OpenAPI em dia |
| Segurança e isolamento | pytest pela borda do compose e imagem do piloto | `ci.yml`, job "Segurança" (`IPC_SECURITY_TESTS=1 uv run pytest tests/security`) | idem | Itens 1 a 22 da seção 8 verdes |
| e2e no compose | Playwright com axe-core | `ci.yml`, job "Smoke e2e" (`npm run e2e`) | idem | Todos passam (hoje 51), sem violação grave no axe |
| Verificação pós-deploy | pytest contra o piloto | `deploy.yml`, passo "Conferir o piloto" (`tests/pilot`) | `workflow_run` do CI na `main` e `workflow_dispatch` | `/ready` e `/version.json` com o commit, cabeçalhos da Vercel, repasse `/api/*`, TLS ≥ 1.2, CORS desligado e `ai_indicators` como esperado |
| e2e no piloto | Playwright (`E2E_TARGET=pilot`) | `deploy.yml`, passo "Smoke e2e no piloto" | idem, só com a conta de verificação (`HAS_CHECK_ACCOUNT`) | `smoke` e `auth` verdes pela página da Vercel |
| Auditoria | gitleaks, pip-audit, npm audit, Trivy | `audit.yml` | segunda-feira 09:00 UTC e manual | Bloqueante desde a S31-03 (09/10/2026); gitleaks, pip-audit e npm audit também em todo PR, com o Semgrep (`ci.yml`, job "Auditoria") |

### Sprint 30 — Piloto verificado ponta a ponta

**Situação (08/10/2026):** concluída. O rollback foi ensaiado (S30-08), o RPO foi decidido (S30-12:
backup diário), e a API passou a atender `/api/*` só pela página, com o segredo do middleware da
Vercel (S30-03). Falta só conferir, em 09/10/2026, os 24 h verdes do UptimeRobot (critério 4). O que cada task entregou está no [CHANGELOG](../../CHANGELOG.md).

**Objetivo:** o "Deploy do piloto" fecha verde sem nenhum passo pulado (login e e2e no piloto), com alerta, backup e rollback ensaiados e medidos, e com a P-12 (a) e a P-15 confirmadas ou corrigidas por evidência registrada.

**Premissas:** confirma a P-12 (a) e a P-15 (a) e (b); mede a Q-20; usa a P-16 (UptimeRobot gratuito) e investiga a P-17 (capacidades do contêiner no Render), registradas em `docs/decisoes.md`. A P-12 (b), (c) e (d) e o repasse `/api/*` da P-15 (a) já foram confirmados no primeiro deploy (07/10/2026).

**Histórias:** US-17, US-19, US-20, US-22, US-26, US-32 e US-35 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S30-01 | US-17 | Externa | Criar a conta de verificação no piloto (registro com outro e-mail institucional, confirmação, aprovação como monitor) e gravar os secrets `PILOT_CHECK_LOGIN`, `PILOT_CHECK_PASSWORD` e `PILOT_CHECK_NAME` com `gh secret set` | `deploy/piloto.md` (passo 8), `docs/runbook.md` ("Conta de verificação") | Autor | — | — | Entrada: conta ativa como monitor. Desbloqueio: `gh secret list` mostra os três nomes, e o passo de migração do "Deploy do piloto" mostra "conta de verificação: marcada" |
| S30-02 | US-26, US-32 | Engenharia | Primeiro deploy com login: "Deploy do piloto" por `workflow_dispatch` na `main`, com o login pela página e o smoke e2e no piloto; acrescentar a `tests/pilot` uma verificação do feedback pela origem da página (`POST /api/v1/feedback`, modelos de texto) com prazo de 30 s, que fecha a P-15 (a) | `backend/tests/pilot/test_deployed_pilot.py`, `.github/workflows/deploy.yml` | Autor | 1 | S30-01 | Os passos "Conferir o piloto" e "Smoke e2e no piloto" verdes, sem o aviso de conta ausente; o teste do feedback responde 200 em ≤ 30 s pela Vercel |
| S30-03 | US-17 | Engenharia | Confirmar a P-12 (a) e a P-15 (b): uma verificação em `tests/pilot` que manda, de um mesmo cliente, logins sem sessão com valores forjados diferentes no início do `X-Forwarded-For` e confere que o limite por IP (30 por minuto sem sessão) conta todos como um só cliente; se falhar, corrigir `IPC_TRUSTED_PROXY_HOPS` no `render.yaml`. Registrar o resultado na P-12 e na P-15 | `backend/tests/pilot/test_deployed_pilot.py`, `backend/src/ipc_api/ratelimit.py` (`client_ip`), `render.yaml` | Autor | 1 | S30-01 | A 31ª tentativa em 60 s recebe 429 com `X-Forwarded-For` forjado; P-12 (a) e P-15 (b) marcadas como confirmadas, com a data e o run do workflow |
| S30-04 | US-19 | Externa | Criar no UptimeRobot os três monitores HTTP(S), de 5 em 5 minutos, com alerta por e-mail: `<Render>/ready`, `<Render>/health/slo` e `<Vercel>/` | Painel do UptimeRobot; `deploy/piloto.md` (passo 9) | Autor | — | — | Entrada: os três monitores ativos. Desbloqueio: os três verdes por 24 h e o Render sem dormência (`/ready` abaixo de 1 s na primeira chamada do dia) |
| S30-05 | US-19 | Engenharia | Exercício de alerta no piloto (pendente desde a S21): baixar `IPC_SLO_P95_MS` no Render por 10 min, gerar tráfego com o workflow "Carga no piloto" (20 por minuto) até o `/health/slo` responder 503, medir o tempo até o e-mail do UptimeRobot e voltar o valor | Painel do Render, `.github/workflows/load.yml`, `docs/runbook.md` ("Latência ou erros acima da meta") | Autor | 0,5 | S30-01, S30-04 | Alerta recebido em ≤ 5 min (NFR-15), valor restaurado, registro com data e tempos no runbook |
| S30-06 | US-20, US-35 | Externa | Gerar a chave com `age-keygen`, guardar a privada fora do GitHub e gravar a pública na variável `BACKUP_AGE_RECIPIENT` | `docs/runbook.md` ("Backup") | Autor | — | — | Desbloqueio: `gh variable list` mostra `BACKUP_AGE_RECIPIENT` |
| S30-07 | US-35 | Engenharia | Rodar o "Backup do banco do piloto" à mão e fazer o primeiro ensaio de restauração num PostgreSQL descartável, cronometrado | `.github/workflows/backup.yml`, `docs/runbook.md` ("Restaurar um backup") | Autor | 1 | S30-06 | Artefato `ipc-piloto-AAAA-MM-DD` com o `.sha256` conferido; contagens de `app.account` e `telemetry.validation_event` iguais às do piloto no momento do backup; RTO medido e registrado na tabela do runbook (NFR-20: RTO ≤ 30 min) |
| S30-08 | US-35 | Engenharia | Primeiro ensaio cronometrado do rollback (pendente da S28-03): voltar a API (Render, **Rollback**) e a página (Vercel, **Instant Rollback**) para a release anterior e depois para a atual | `docs/runbook.md` ("Voltar para a versão anterior") | Autor | 0,5 | S30-02 | Do passo 1 ao passo 3 conferido em ≤ 5 min, com `/ready` e `/version.json` no commit anterior; registro na tabela do runbook |
| S30-09 | US-22 | Engenharia | Carga no piloto de verdade (pendente da S28-01): workflow "Carga no piloto" com 20 por minuto por 5 min; registrar o P95 do servidor (`/health/slo`), o P95 do k6 e a diferença entre `sessao_ms` e `sem_banco_ms` (Q-20) | `.github/workflows/load.yml`, `deploy/load/pilot-load.js`, `docs/adr/ADR-03-topologia-de-implantacao-por-fase.md`, `docs/decisoes.md` (Q-20) | Autor | 1 | S30-01 | Resumo do workflow com os três números; ADR-03 e Q-20 atualizadas com a medição e a data |
| S30-10 | US-17 | Engenharia | Corrigir o `PermissionError` do supervisord no desligamento (ver o diagnóstico abaixo): registrar as capacidades no boot, reproduzir com `docker run --cap-drop KILL`, aplicar a correção escolhida e cobri-la com um teste na suíte do piloto | `deploy/render/supervisord.conf`, `deploy/render/Dockerfile`, `backend/tests/security/test_pilot_isolation.py` | Autor | 2 | — | Na imagem com `--cap-drop KILL`, `docker stop` encerra os dois serviços em ≤ 15 s (`stopwaitsecs`) sem a linha `CRIT unknown problem killing`; no Render, um deploy e uma dormência sem essa linha nos logs; isolamento da suíte do piloto inalterado |
| S30-11 | US-22 | Decisão | Plano do Render (ADR-03): gratuito ou Starter (cerca de US$ 7 por mês), com a medição da S30-09 (opções em 7.13.6) | `render.yaml` (`plan`), painel do Render | Autor | — | S30-09 | Decisão registrada no ADR-03; se Starter, `plan: starter` por PR e nova rodada da S30-09 com P95 do servidor ≤ 200 ms |
| S30-12 | US-35 | Decisão | RPO do banco do piloto: o backup semanal dá RPO de até 7 dias, acima da meta de 24 h da NFR-20; escolher entre o backup diário (só o `cron` do `backup.yml` muda) e revisar a NFR-20 para o piloto (opções em 7.13.8) | `.github/workflows/backup.yml`, NFR-20 | Autor | — | S30-07 | Desbloqueio: decisão registrada na NFR-20; se diário, o `cron` alterado por PR e uma semana de artefatos diários |

*Diagnóstico da S30-10 (confirmado em 08/10/2026, P-17).* O `supervisord` roda como root (`user=root`) e encerra cada programa com `stopasgroup=true` e `killasgroup=true`, ou seja, manda o sinal ao grupo de processos de `ipc-api` (UID 10001) e de `ipc-analyzer` (UID 10002). Um processo root só sinaliza processos de outro usuário com a capacidade `CAP_KILL`; a hipótese (P-17) é que o Render roda o contêiner sem ela, e o `kill()` devolve `EPERM`, que o supervisord registra como `PermissionError`. Os processos acabam encerrados quando o Render destrói o contêiner, por isso nada quebra. Opções a avaliar na task: (a) um intermediário root por programa, que inicia o serviço com `setpriv --reuid ... --pdeathsig TERM` e apenas sai ao receber o sinal, para o kernel entregar o `SIGTERM` ao filho, sem precisar de `CAP_KILL` (resolvido na S30-10; ver a P-17); (b) cada serviço encerrar-se sozinho quando o pai morre, configurando o `PR_SET_PDEATHSIG` no início do processo; (c) aceitar o registro e documentá-lo no runbook (só se (a) e (b) enfraquecerem o isolamento). A correção não pode dar ao analisador o mesmo UID da API nem rodar algum serviço como root.
*Resultado (08/10/2026):* a P-17 se confirmou no Render, e as opções (a) e (b) não servem: o kernel
entrega o `PR_SET_PDEATHSIG` com a mesma checagem de permissão do `kill()`. Foi aplicada uma quarta
opção, sem sinal entre usuários: um lançador root por serviço fecha um pipe ao receber o `SIGTERM`, e
um guardião com o usuário do serviço o encerra (`deploy/render/run_as.py`; P-17 em
`docs/decisoes.md`).

**ADRs:** atualiza o ADR-03 (medição da S30-09 e a decisão da S30-11). Sem ADR novo.

**Critérios de aceite:**
1. O run do "Deploy do piloto" na `main` termina verde com os passos "Conferir o piloto" e "Smoke e2e no piloto" executados, nenhum pulado e nenhum aviso de conta ausente.
2. O feedback pela página responde em ≤ 30 s, e o login cria o cookie `__Host-ipc_session` com `HttpOnly`, `Secure` e `SameSite=Lax` pela origem da Vercel.
3. A 31ª tentativa de login sem sessão em 60 s recebe 429, mesmo com `X-Forwarded-For` forjado.
4. Os três monitores do UptimeRobot ficam verdes por 24 h, e o alerta de latência chega em ≤ 5 min no exercício.
5. A restauração de um backup cifrado reproduz as contagens do banco, com o RTO registrado no runbook.
6. O rollback dos dois serviços leva ≤ 5 min, com o tempo registrado no runbook.
7. O ADR-03 tem o P95 do servidor medido no piloto, com login, e a decisão do plano.
8. Os logs do Render não mostram `CRIT unknown problem killing` num deploy nem numa dormência.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Login com cookie pela página | pytest | `tests/pilot::test_login_validation_and_logout_through_the_page` | `deploy.yml` | 200 no login, cookie `__Host-` com os atributos, 200 na verificação, 204 na saída e 401 depois |
| Feedback em até 30 s pela página (novo) | pytest | `tests/pilot` (S30-02) | `deploy.yml` | 200 em ≤ 30 s, `source` = `template` sem IA configurada |
| `X-Forwarded-For` e `IPC_TRUSTED_PROXY_HOPS` (novo) | pytest | `tests/pilot` (S30-03) | `deploy.yml`, depois só à mão (gasta o limite por IP do runner) | 429 na 31ª tentativa com o valor forjado |
| e2e no piloto | Playwright | `deploy.yml`, "Smoke e2e no piloto" | `deploy.yml` com a conta | `smoke.spec.ts` e `auth.spec.ts` verdes |
| Carga no piloto | k6 | `load.yml` (20 por minuto, 5 min) | à mão | Sem 5xx; P95 do servidor registrado; ≤ 200 ms no plano escolhido para o prazo |
| Encerramento sem `CAP_KILL` (novo) | pytest pela imagem do piloto | `tests/security/test_pilot_isolation.py` | job "Segurança" do CI | `docker stop` em ≤ 15 s, sem `CRIT` no log, isolamento por UID e seccomp mantidos |
| Exercício de alerta | UptimeRobot | Runbook, S30-05 | à mão, uma vez | E-mail em ≤ 5 min |
| Restauração do backup | age, `pg_restore` | Runbook, "Restaurar um backup" | à mão, uma vez por semestre | Contagens iguais; RTO registrado |
| Rollback cronometrado | Painéis do Render e da Vercel | Runbook, "Voltar para a versão anterior" | à mão, uma vez por período | ≤ 5 min do passo 1 ao 3 |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, mais: os registros de ensaio do runbook preenchidos com data, responsável e tempo; a P-12 e a P-15 atualizadas em `docs/decisoes.md` com a evidência (run do workflow); nenhum secret ou URL de hook em arquivo, log ou PR.

**Riscos e bloqueios:** S30-02, S30-03, S30-05, S30-08 e S30-09 esperam a S30-01 (ação do autor, cerca de 10 min). O e-mail de verificação da conta nova pode cair no spam (remetente Gmail pelo Brevo, Q-17). A S30-03 gasta o limite de login por IP do runner por 1 min. Se a correção da S30-10 exigir capacidades que o Render não dá, vale a opção (c), com o motivo no runbook. O backup semanal não atende o RPO de 24 h da NFR-20 (S30-12).

### Avisos de pendência das Sprints 11 a 29 (revisão de 08/10/2026)

A coluna "Situação" do README ainda trazia avisos de quando cada sprint fechou. Revistos em
08/10/2026, depois da Sprint 30:

| Sprint | Aviso | Situação em 08/10/2026 | Onde fica |
|---|---|---|---|
| 11 | Falta a configuração das contas | Resolvido: contas configuradas em 07/10/2026 e a conta de verificação em 08/10/2026 | S30-01 |
| 19 | Falta o primeiro deploy com login | Resolvido em 08/10/2026 (run 37754224989) | S30-02 |
| 20 | Falta o repositório privado dos gabaritos | Em parte: repositório e chave da CI criados hoje (H-02); faltam os gabaritos do Notion | S33-01 |
| 21 | Falta o terceiro monitor do UptimeRobot | Resolvido em 08/10/2026 | S30-04 |
| 22 | Os casos em aberto do mapeamento seguem para o Marco 2 | Resolvido: decididos pelo autor em 09/10/2026 (ruleset `2026.2.5`); Marco 2 em 19/10/2026 | S31-05, S31-12 |
| 24 | Nenhuma questão real cadastrada ainda | Ensaio feito em 09/10/2026 (L3-Q9, `docs/ensaio-cadastro.md`); falta o cadastro de 2027.1 pela equipe, com a troca de período sem código | S31-09, S31-10, S31-13, S33-04 |
| 25 | Falta o primeiro deploy | Resolvido em 07/10/2026 | S25-02 |
| 28 | Faltam o ensaio do rollback e a carga no piloto | Resolvido em 08/10/2026 | S30-08, S30-09 |
| 29 | Desligada no piloto até a política e a calibração | Planejado | S31-01, S33-02, S33-03, S33-06 |

**Feito em 08/10/2026, antes da Sprint 31:**

| ID | O que | Resultado |
|---|---|---|
| H-01 | Avisos desatualizados do README corrigidos (Sprints 11, 19, 21, 25 e 28) | README com a situação acima |
| H-02 | Repositório privado `Lionzio/ip-checker-gabaritos` criado, com as pastas de 2026.2 e um README para a equipe; chave de implantação só de leitura nele e a parte privada no segredo `GABARITOS_SSH_KEY`; o job "Gabaritos" do `ci.yml` passa a usar a chave (ADR-10) | Falta só copiar os gabaritos e gravar `GABARITOS_REPO` (S33-01) |
| H-03 | Pauta do Marco 2 em `docs/marco-2.md`: os 9 casos do mapeamento, a política dos indícios, Q-16, Q-17, Q-22, questões e gabaritos e o piloto | Usada na S31-05 e na S31-12 |
| H-04 | Plano: US-36, FR-31, NFR-27, ADR-10 e as tasks S31-09 a S31-13 | Esta seção e a Sprint 31 |

### Sprint 31 — Decisões com a coordenação e auditoria bloqueante

**Objetivo:** levar à coordenação, ao NTI e ao autor as decisões em aberto com as opções de 7.13, entregar o Marco 2 e tornar a auditoria de segurança bloqueante, com os achados triados.

**Missão, persona e execução:** a missão é sair da Sprint 31 com as decisões da coordenação registradas (ou formalmente aguardando), a auditoria bloqueante e o período pronto para trocar sem mudar código. A persona é o Tech Lead e monitor-mantenedor (US-36), com o autor como quem apresenta o Marco 2. Execução: primeiro a engenharia sem dependência externa, em PRs pequenos (S31-03, S31-04, S31-09, S31-10 e S31-11); em paralelo, o Marco 2 com a pauta de `docs/marco-2.md` (S31-05 e S31-12) e as decisões S31-01, S31-02, S31-07 e S31-08; por fim, o ensaio de cadastro de questões reais de 2026.2 pela equipe (S31-13).

**Premissas:** Q-16, Q-17, Q-22 e ADR-08 (S29-04) seguem abertas até a decisão registrada; a NFR-13 passa a ser medida a cada PR; o período ativo é 2026.2 até a S33-04.

**Histórias:** US-11, US-13, US-23, US-32, US-34, US-15 e US-36 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S31-01 | US-34 | Decisão | Levar à coordenação a política dos indícios de IA (S29-04, ADR-08): o texto aos alunos e quem gera as referências (opções em 7.13.1) | `docs/indicios-de-ia.md` | Coordenação | — | — | Entrada: aprovação ou pedido de mudança, por escrito. Desbloqueio: a decisão registrada na Q-21 e no ADR-08, com a data |
| S31-02 | US-32 | Decisão | Q-16: provedor de IA do feedback (opções em 7.13.2); se aprovado, o autor grava `IPC_LLM_*` no Render | `docs/decisoes.md` (Q-16), `deploy/compose.md` ("Feedback por IA") | Autor e Coordenação | — | — | Desbloqueio: Q-16 decidida; se houver provedor, um feedback no piloto com `source` = `llm` e o nome do aluno ausente do pedido ao provedor |
| S31-03 | US-15 | Engenharia | Triar a auditoria semanal (S25-01) e torná-la bloqueante: corrigir ou justificar cada achado alto ou crítico corrigível, tirar o `continue-on-error` do `audit.yml` e rodar gitleaks, pip-audit e npm audit também no `ci.yml`, em todo PR (Trivy fica no semanal, por demorar) | `.github/workflows/audit.yml`, `.github/workflows/ci.yml` | Autor | 2 | — | Uma rodada do `audit.yml` sem achado aberto; PR com uma dependência vulnerável de teste falha no CI; NFR-13 e item 14 da seção 8 sem a ressalva "ainda não bloqueante" |
| S31-04 | US-15 | Engenharia | Semgrep no CI (NFR-09): imagem fixada por digest, regras para Python e TypeScript, achados novos bloqueiam o PR | `.github/workflows/ci.yml`, `.semgrep/ip-checker.yml` (novo; o conjunto de regras foi decidido na P-20) | Autor | 1 | — | Job verde na `develop`; um PR com `eval` sobre dado de requisição falha; NFR-09 sem [PLANEJADO] |
| S31-05 | US-11 | Externa | Marco 2: revisar o guia da equipe e marcar a data da apresentação a monitores-chefes e professores | `docs/guia-da-equipe.md`; a pauta da apresentação, `docs/marco-2.md` (H-03) | Autor | — | — | Entrada: data marcada e guia revisado. Desbloqueio: apresentação feita, com as decisões registradas em `docs/decisoes.md` |
| S31-06 | US-23 | Externa | Criar o formulário da pesquisa de satisfação e a planilha do critério 3, como especificados (S28-02) | `docs/eficacia.md` (seções 3 e 4) | Equipe | — | — | Entrada: formulário anônimo e planilha sem dados de aluno. Desbloqueio: os dois links registrados em `docs/eficacia.md` |
| S31-07 | US-11 | Decisão | Q-17: remetente definitivo dos e-mails e, se for `@cin.ufpe.br`, SPF, DKIM e DMARC conferidos com o NTI (opções em 7.13.3) | `docs/decisoes.md` (Q-17), `deploy/compose.md` ("Registro e e-mails"), `IPC_EMAIL_FROM` no Render | Autor e NTI | — | — | Desbloqueio: um e-mail de verificação entregue na caixa de entrada de um `@cin.ufpe.br` e de um `@ufpe.br`, fora do spam |
| S31-08 | US-13 | Decisão | Q-22: governança das regras por fork e check de aprovação (opções em 7.13.4) | `RULES.md`, `.github/PULL_REQUEST_TEMPLATE/regras.md` | Autor | — | — | Desbloqueio: Q-22 decidida; se a opção B, uma task de implementação entra na sprint seguinte |
| S31-09 | US-36 | Engenharia | Período ativo num só lugar: o analisador, o compose, o `render.yaml`/supervisord e a CI leem o período de um único arquivo, e nenhum outro arquivo cita `2026.2` como período ativo | `rulesets/` (arquivo do período ativo, novo), `backend/src/ipc_analyzer/` (configuração), `deploy/render/supervisord.conf`, `backend/Dockerfile`, `.github/workflows/ci.yml` | Autor | 2 | — | Trocar de período muda uma linha; um teste falha se outro arquivo citar o período ativo; `/ready` mostra a `ruleset_version` do período do arquivo |
| S31-10 | US-36 | Engenharia | `ipc-rules new-period <novo> --from <anterior>`: copia o `base.yaml` com o período e a `ruleset_version` novos e cria `questions/` e `referencias/` vazias; recusa período existente ou fora do formato `AAAA.N` | `backend/src/ipc_analyzer/cli.py`, `RULES.md` | Autor | 1 | — | `ipc-rules new-period 2027.1 --from 2026.2` cria a pasta, e `ipc-rules validate ../rulesets/2027.1 --golden tests/golden` sai com 0 |
| S31-11 | US-36 | Engenharia | Gabaritos com as questões do próprio período: o harness usa `rulesets/<período do gabarito>/questions/` quando a pasta existe; o `excecoes.yaml` fica para períodos sem questões cadastradas | `backend/tests/official_answers/harness.py`, `test_harness.py` | Autor | 1 | — | Teste: um gabarito de 2026.2 com o período ativo 2027.1 é analisado com a questão de 2026.2 |
| S31-12 | US-11 | Externa | Levar ao Marco 2 a pauta de `docs/marco-2.md` e registrar as decisões: os 9 casos do mapeamento (aviso da Sprint 22), os indícios de IA, Q-16, Q-17, Q-22, questões e gabaritos e o piloto; cada caso liberado vira uma task de regra na sprint seguinte | `docs/marco-2.md`, `docs/mapping-R-xx.md`, `docs/decisoes.md` | Autor, monitores-chefes e professores | — | S31-05 | Desbloqueio: a tabela "Registro" preenchida e cada decisão em `docs/decisoes.md`, com a data e quem decidiu |
| S31-13 | US-13 | Externa | Ensaiar o cadastro de questões reais em 2026.2 (aviso da Sprint 24): pelo menos uma questão de cada lista já aplicada, pelo `RULES.md`, para validar o fluxo antes de 2027.1 | `rulesets/2026.2/questions/` | Equipe e Professor | — | — | Desbloqueio: `ipc-rules validate ../rulesets/2026.2` mostra as questões, com o PR aprovado por um monitor-chefe ou professor |

**ADRs:** ADR-10 (questões e gabaritos por período, aceito em 08/10/2026); se a Q-16 escolher um provedor, o ADR-06 recebe a decisão.

**Critérios de aceite:**
1. As decisões S31-01, S31-02, S31-07 e S31-08 estão registradas em `docs/decisoes.md`, com a data e quem decidiu, ou a sprint fecha com cada uma marcada "aguardando", com a entrada pendente.
2. O `audit.yml` roda sem `continue-on-error`, e a última rodada não tem achado alto ou crítico corrigível aberto.
3. Um PR de teste com um segredo falso, uma dependência vulnerável ou um `eval` sobre dado de requisição falha no CI (o PR é descartado depois).
4. Os links do formulário e da planilha estão em `docs/eficacia.md`.
5. Trocar o período ativo muda uma linha de um arquivo, e `ipc-rules new-period 2027.1 --from 2026.2` gera um período válido (S31-09, S31-10).
6. Um gabarito de um período anterior é conferido com as questões do próprio período (S31-11).
7. A pauta do Marco 2 sai com cada um dos 9 casos do mapeamento decidido ou adiado com o motivo, e o caso 10 (expressão geradora, aplicado de forma provisória em 09/10/2026) ratificado ou revertido (S31-12).

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Segredos | gitleaks | `ci.yml` (novo) e `audit.yml` | PR, push e segunda-feira | 0 achados; o PR de teste com segredo falso falha |
| Dependências Python | pip-audit 2.9.0 | `ci.yml` (novo) e `audit.yml` | idem | 0 vulnerabilidades corrigíveis |
| Dependências npm | `npm audit --audit-level=high` | `ci.yml` (novo) e `audit.yml` | idem | 0 altas ou críticas |
| Imagem do piloto | Trivy (`--severity HIGH,CRITICAL --ignore-unfixed`) | `audit.yml` | segunda-feira e manual | 0 achados |
| Análise estática | Semgrep | `ci.yml` (novo) | PR e push | 0 achados novos; o PR de teste com `eval` falha |
| Feedback com IA (se a Q-16 aprovar) | pytest com o provedor gravado | `tests/feedback` e uma verificação manual no piloto | depois da configuração | `source` = `llm`, nome do aluno trocado por `[ALUNO]`, texto validado |
| Entrega de e-mail (Q-17) | registro real | runbook, roteiro do primeiro deploy | depois da decisão | E-mail na caixa de entrada em ≤ 5 min |
| Período ativo num só lugar (novo) | pytest | `tests/test_ruleset_loader.py` e um teste que procura o período em `deploy/` e `backend/Dockerfile` | PR e `develop` | Só o arquivo do período ativo cita o período; `/ready` com a `ruleset_version` dele |
| Período novo (novo) | pytest e `ipc-rules` | `tests/test_cli.py`; `uv run ipc-rules new-period 2027.1 --from 2026.2` numa pasta temporária | PR | Pasta criada e validada; período repetido ou inválido recusado |
| Gabaritos por período (novo) | pytest | `tests/official_answers/test_harness.py` | PR | A questão do período do gabarito é usada |
| Gabaritos reais | pytest no job "Gabaritos" | `ci.yml`, com `GABARITOS_REPO` gravada (S33-01) | PR e `develop` | Zero violação em todos os gabaritos de listas habilitadas |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com o item 14 sem a ressalva de "ainda não bloqueante".

**Riscos e bloqueios:** as decisões dependem da agenda da coordenação e do NTI; a sprint não espera por elas e as mantém como "aguardando". A triagem pode revelar uma vulnerabilidade sem correção: ela é registrada com a justificativa e revista a cada rodada.

### Sprint 32 — Comparação com o gabarito (incluída em 09/10/2026)

**Objetivo:** a verificação mostra, junto com as violações, a semelhança do código do aluno com o gabarito oficial da questão; o plágio compara A e B também com o gabarito e alerta um possível vazamento; os indícios ganham o sinal do gabarito; nenhum texto do gabarito sai do servidor (ADR-11). Incluído em 09/10/2026 (Q-16): o feedback passa a ser sem IA por padrão, com o botão "Aprimorar com IA" usando uma cadeia de provedores gratuitos com fallback (S32-11 a S32-14).

**Missão, persona e execução:** a missão é dar à equipe, na hora da correção, a distância entre o código do aluno e a solução oficial, e um sinal de que o gabarito pode estar circulando, sem guardar nada e sem expor o gabarito. A persona é quem corrige (monitor, monitor-chefe ou professor; US-37 e US-38), com o Tech Lead cuidando da confidencialidade (NFR-27). Execução: a credencial do autor primeiro (S32-01); depois, em PRs pequenos, o carregamento na API (S32-02), a comparação no analisador (S32-03), as rotas (S32-04, S32-05), as telas (S32-06, S32-07), o sinal dos indícios (S32-08), os testes de confidencialidade e desempenho (S32-09) e a documentação (S32-10). O carregamento entra numa release sem migração (P-18).

**Premissas:** Q-24 decidida pelo autor (1B 2B 3A 4B 5A 6B); a troca de período sem código (S31-09, S31-10) já está pronta; o limiar do alerta (95%) e o tamanho mínimo (60 tokens) foram validados pelo autor em 12/10/2026; a credencial só de leitura é criada pelo autor, sem vencimento (P-23, decisão do autor de 12/10/2026); a troca é por evento (runbook, "Credencial dos gabaritos").

**Histórias:** US-37 e US-38 (seção 4); FR-32; NFR-27 (revisto) e NFR-28; US-32, FR-30 e NFR-26 para o "Aprimorar com IA" (Q-16).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S32-01 | US-37 | Externa | Criar a credencial só de leitura do `Lionzio/ip-checker-gabaritos` (*fine-grained token*, Contents: Read-only, só esse repositório) e gravá-la no Render (`IPC_GABARITOS_TOKEN`), com o passo a passo do runbook | Painel do GitHub e do Render; `docs/runbook.md` | Autor | — | — | Desbloqueio: o diagnóstico da API mostra "gabaritos carregados: N" no piloto, sem expor nada |
| S32-02 | US-37 | Engenharia | Carregamento na API: ao subir, baixar o repositório dos gabaritos (API do GitHub, HTTPS), só os `<período>/lista-<n>/L<n>-Q<m>.py`, com limite por arquivo e no total; índice em memória por período e questão; nunca em disco nem em log; falha → comparação desligada com aviso, `/ready` intacto; `IPC_GABARITOS_REPO` e `IPC_GABARITOS_TOKEN` (`sync: false`) no `render.yaml` | `backend/src/ipc_api/` (módulo novo), `settings.py`, `render.yaml` | Autor | 2 | S32-01 (só para o piloto) | Testes com repositório falso: carrega, ignora o que não é gabarito, respeita os limites, nada no disco nem no log (canário), falha sem derrubar a API |
| S32-03 | US-37, US-38 | Engenharia | Comparação no analisador: rota interna que recebe o código e o gabarito, prepara com cache por hash e devolve a semelhança (ADR-07), as construções em comum, só no aluno e só no gabarito (fatos do motor) e as linhas do aluno que coincidem — nunca o texto do gabarito | `backend/src/ipc_analyzer/` (similaridade e serviço) | Autor | 2 | — | Testes com gabaritos sintéticos: idêntico = 100%; renomeado ≥ 99%; independente < 80%; a resposta não contém nenhuma linha do gabarito |
| S32-04 | US-37 | Engenharia | API da verificação: `question_id` do seletor, campo `gabarito` opcional no `POST /api/v1/validate` (faixa, porcentagem, construções e linhas do aluno) e a rota que lista as questões do período ativo com gabarito (só os IDs); OpenAPI e tipos gerados | `routes/validate.py`, `routes/meta.py`, `schemas.py`, `docs/openapi.json`, `frontend/src/types/openapi.ts` | Autor | 2 | S32-02, S32-03 | Contrato atualizado; sem gabarito, `gabarito` vem nulo com o aviso; P95 local sem regressão |
| S32-05 | US-38 | Engenharia | API do plágio: com a questão, A×gabarito e B×gabarito e o alerta de possível vazamento pelas regras da ADR-11 (limiar e mínimo configuráveis) | `routes/similarity.py`, `schemas.py`, OpenAPI | Autor | 1 | S32-03 | Testes: alerta com A, B e o gabarito idênticos e grandes; sem alerta com códigos curtos ou com só um aluno parecido |
| S32-06 | US-37 | Engenharia | Tela de verificação: seletores de período, lista e questão (questões com gabarito), o bloco "Comparação com o gabarito" (faixa com cor e nome, construções, linhas do aluno destacadas no editor) e os avisos | `frontend/src/` (verificação) | Autor | 2 | S32-04 | Vitest e e2e; axe sem violações graves; cabe em 375 px |
| S32-07 | US-38 | Engenharia | Tela de plágio: o seletor da questão, os dois resultados com o gabarito e o alerta de possível vazamento, com o aviso de que é um indício | `frontend/src/` (plágio) | Autor | 1 | S32-05 | Vitest e e2e; axe; 375 px |
| S32-08 | US-34 | Engenharia | Indícios de IA: a semelhança com o gabarito como sinal novo, nas faixas de referência, só com `IPC_AI_INDICATORS` | `engine/indicators.py`, painel de indícios | Autor | 1 | S32-03 | Testes do sinal; desligado no piloto (S31-01) |
| S32-09 | US-37, US-38 | Engenharia | Confidencialidade e desempenho: testes canário (um gabarito sintético com marcador nunca aparece nas respostas, nos logs, na telemetria nem no disco), a imagem do piloto sem gabaritos, isolamento do analisador inalterado e a carga com a comparação (NFR-28) | `tests/security/`, `tests/test_log_contract.py`, `deploy/load/` | Autor | 1 | S32-04, S32-05 | Todos os canários com 0 ocorrência; P95 ≤ 200 ms local; suíte do piloto verde |
| S32-10 | US-37, US-38 | Engenharia | Documentação: guia da equipe (como ler a comparação e o alerta), runbook (credencial, troca, "gabaritos indisponíveis"), ADR-11 como Aceito, CHANGELOG e README | `docs/`, `README.md`, `CHANGELOG.md` | Autor | 0,5 | S32-02 a S32-09 | Revisados no PR |
| S32-11 | US-32 | Externa | Criar as contas gratuitas e as chaves dos provedores da cadeia do "Aprimorar com IA" (Q-16): pelo menos Gemini e Groq, e outros gratuitos que o autor escolher; gravar no Render só pelos nomes (`IPC_LLM_CHAIN` e `IPC_LLM_<PROVEDOR>_*`, `sync: false`), com o passo a passo do runbook | Painéis dos provedores e do Render; `docs/runbook.md` | Autor | — | — | Desbloqueio: o diagnóstico do feedback mostra os provedores configurados (só os nomes), e um "Aprimorar com IA" no piloto responde |
| S32-12 | US-32 | Engenharia | Feedback sem IA como padrão e o "Aprimorar com IA" no backend (Q-16, A e C): o **Gerar feedback** devolve sempre a versão determinística (`compose.template_text`), sem chamar IA; uma rota nova recebe a versão determinística e o mesmo contexto já enviado hoje (código sem comentários nem docstrings, anotação e resultado, nome trocado por `[ALUNO]`, dados pessoais mascarados) e pede à IA para detalhar, expandir, exemplificar e melhorar, mantendo a abertura e a frase obrigatória. Cadeia de N provedores (`IPC_LLM_CHAIN`, em ordem), com fallback por erro, prazo, cota esgotada (429) ou resposta reprovada na validação (NFR-26), e uma pausa por provedor depois de 429; tudo falhando, devolve a versão determinística com o aviso. A cota diária por conta e o teto do servidor valem para o aprimoramento | `backend/src/ipc_api/feedback/` (`providers.py`, `service.py`), `routes/feedback.py`, `settings.py`, `render.yaml`, OpenAPI | Autor | 2 | — | Testes com provedores falsos: ordem da cadeia, fallback em cada tipo de falha, pausa depois de 429, partes fixas preservadas, nada inventado sobre violações, chave nunca em log nem em resposta |
| S32-13 | US-32 | Engenharia | Tela do feedback: o botão **Aprimorar com IA** ao lado do texto determinístico, com a espera, o aviso quando nenhuma IA responde, o rótulo "aprimorado por IA" e **Desfazer** (volta ao texto determinístico); continua editável e com Copiar | `frontend/src/` (feedback) | Autor | 1 | S32-12 | Vitest e e2e com o provedor falso; axe sem violações graves; cabe em 375 px |
| S32-14 | US-32 | Engenharia | Privacidade e documentação do aprimoramento: o aviso de privacidade diz que o "Aprimorar com IA" envia o código (sem nome nem dados pessoais) a provedores gratuitos que podem usá-lo para treino; FR-30 e ADR-06 revistos; runbook (chaves, cotas, troca de provedor); guia da equipe | `frontend/src/` (aviso), `docs/blueprint.md`, `docs/adr/ADR-06-*.md`, `docs/runbook.md`, `docs/guia-da-equipe.md` | Autor | 0,5 | S32-12 | Revisados no PR; o aviso aparece antes do primeiro aprimoramento |

**ADRs:** ADR-11 (Proposto → Aceito no fim da sprint); ADR-10 e NFR-27 revistos pela ADR-11.

**Critérios de aceite:**
1. Com a L1-Q1 de 2026.2 escolhida, a verificação mostra a porcentagem e a faixa da semelhança com o gabarito, as construções em comum, só no aluno e só no gabarito e as linhas do aluno que coincidem.
2. Nenhuma resposta da API, linha de log, evento de telemetria ou arquivo em disco contém texto do gabarito (canário com 0 ocorrência), e a imagem do piloto não tem nenhum gabarito.
3. No plágio, A×gabarito e B×gabarito aparecem com a questão escolhida; o alerta aparece com os três acima do limiar e os códigos acima do tamanho mínimo, e não aparece nos pares independentes do corpus de `tests/similarity` (0 alerta falso).
4. Sem a credencial ou com o download falho, a verificação e o plágio funcionam como antes, com o aviso, e o `/ready` responde 200.
5. P95 do `/validate` com a comparação ≤ 200 ms (NFR-28), medido localmente e, com a cota do Actions de volta, pelo "Carga no piloto".
6. O **Gerar feedback** devolve o texto determinístico sem chamar nenhuma IA; o **Aprimorar com IA** passa pela cadeia na ordem configurada e, com o primeiro provedor fora do ar ou sem cota, responde pelo seguinte; com todos falhando, volta o texto determinístico com o aviso (S32-12, S32-13).
7. O texto aprimorado mantém a abertura e a frase obrigatória, não cita violação que o motor não achou (NFR-26) e não leva o nome do aluno ao provedor; o aviso de privacidade fala do envio a provedores gratuitos (S32-14).

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Carregamento dos gabaritos | pytest com repositório falso | `tests/test_gabaritos_loader.py` (novo) | PR | Carrega, filtra, limita, falha sem derrubar a API |
| Comparação no analisador | pytest | `tests/similarity/` | PR | Faixas esperadas nos pares sintéticos; nada do gabarito na saída |
| Contrato da API | pytest e `gen:api` | `tests/test_api_contract.py`, tipos em dia | PR | Verde |
| Confidencialidade (canário) | pytest | `tests/security/`, `tests/test_log_contract.py` | PR | 0 ocorrência do marcador |
| Telas | Vitest e Playwright | `npm test`, `npm run e2e` | PR | Verde; axe sem violações graves; 375 px |
| Desempenho | pytest e k6 | orçamento da similaridade; "Carga no piloto" | PR; à mão | NFR-28 |
| Gabaritos reais | harness | `tests/official_answers` | PR | Zero violação, como antes |
| Cadeia do "Aprimorar com IA" | pytest com provedores falsos | `tests/feedback/` | PR | Ordem, fallback por erro, prazo, 429 e validação; partes fixas preservadas; nenhuma chave em log |
| Feedback na tela | Vitest e Playwright (provedor falso) | `npm test`, `npm run e2e` | PR | Determinístico por padrão; Aprimorar e Desfazer; axe; 375 px |
| Regressão | `scripts/ci-local.sh --e2e` (P-19) | — | PR | Verde |

**Definition of Done:** a da seção 8, mais: nenhum texto do gabarito fora do servidor (critério 2); a credencial só no Render e no runbook pelo nome; o ADR-11 como Aceito.

**Riscos e bloqueios:** os provedores gratuitos mudam limites e termos sem aviso e podem usar os dados para treino (risco aceito pelo autor, Q-16), e as chaves dependem do autor (S32-11); a credencial depende do autor (S32-01) e vence (troca no runbook); o limiar do alerta é premissa até a S33-02 e a S33-03; a comparação aumenta o tempo da verificação (NFR-28); sem a cota do Actions até 01/11 (P-19), a evidência vem da CI local.


### Sprint 33 — Dados: gabaritos, questões de 2027.1 e calibração dos indícios

**Objetivo:** rodar os gabaritos de períodos anteriores no CI, calibrar os indícios de IA com soluções humanas (meta da ADR-08: no máximo 5% de faixa alta), cadastrar as questões de 2027.1 com as referências e, só com a política aprovada, ligar os indícios no piloto.

**Missão, persona e execução:** a missão é pôr dados reais no motor: os gabaritos protegendo contra falsos positivos, as questões de 2027.1 cadastradas e os indícios calibrados. As personas são o monitor-chefe e o professor que cadastram e aprovam questões (US-13) e o monitor-mantenedor que calibra (US-34, US-36). Execução: o autor copia os gabaritos e liga o job (S33-01); a equipe cria 2027.1 com `ipc-rules new-period` e cadastra as questões (S33-04); com as soluções da S33-02, a calibração (S33-03); com a política aprovada, as referências e os indícios ligados (S33-05, S33-06).

**Premissas:** Q-14 (gabaritos fora do repositório); ADR-08 (faixas iniciais a calibrar); P-07 (numeração das questões por período).

**Histórias:** US-13, US-14 e US-34 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S33-01 | US-14 | Externa | Copiar os gabaritos do Notion para o repositório privado já criado (`Lionzio/ip-checker-gabaritos`, H-02), em `<período>/lista-<n>/L<n>-Q<m>.py`, dar acesso à equipe (colaboradores) e, depois do primeiro gabarito, gravar a variável `GABARITOS_REPO` | `rulesets/README.md` ("Gabaritos"), README do repositório dos gabaritos, `backend/tests/official_answers/` | Autor e Equipe | — | — | Desbloqueio: o job "Gabaritos (zero violação, Q-14)" do `ci.yml` roda (não fica "skipped") e passa |
| S33-02 | US-34 | Externa | **Descartada pelo autor em 12/10/2026.** Obter as soluções humanas de períodos anteriores a 2023 para a calibração, no mesmo formato, fora do repositório. A dúvida sobre a fonte (os gabaritos da Q-14 ou a coordenação) perdeu o objeto com o descarte: a calibração usa os gabaritos e soluções novas geradas por IA (Q-35) | Pasta local fora do repositório | Autor e Coordenação | — | — | Entrada: pelo menos 200 soluções [PREMISSA] distribuídas pelas 6 listas. Desbloqueio: pasta disponível ao autor, sem dado de aluno no repositório |
| S33-03 | US-34 | Engenharia | Calibrar os indícios: rodar `ipc-rules calibrate` nas soluções da S33-02, ajustar as faixas de `engine/indicators.py` por PR até a faixa alta ficar em ≤ 5%, e registrar a distribuição no ADR-08 | `backend/src/ipc_analyzer/cli.py`, `backend/src/ipc_analyzer/engine/indicators.py`, `docs/adr/ADR-08-indicios-de-uso-de-ia-nunca.md` | Autor | 2 | S33-02 | `uv run ipc-rules calibrate ../rulesets/2026.2 <pasta> --max-alto 5` sai com 0; os testes de `test_indicators.py` atualizados para as faixas novas |
| S33-04 | US-13 | Externa | Criar o período 2027.1 com `ipc-rules new-period 2027.1 --from 2026.2` (S31-10), ajustar o `base.yaml` ao documento de permissões validado pelo professor, trocar o período ativo (S31-09) e cadastrar as questões das listas liberadas (R-01) pelo `RULES.md` | `rulesets/2027.1/base.yaml` e `questions/` (novos) | Professor e Equipe | — | Documento de permissões de 2027.1; S31-09, S31-10 | Desbloqueio: `ipc-rules validate ../rulesets/2027.1 --golden tests/golden` verde, com pelo menos uma questão por lista habilitada |
| S33-05 | US-34 | Externa | Gerar as referências por IA das questões cadastradas (S29-02), conforme a decisão da S31-01 sobre quem gera | `rulesets/2027.1/referencias/<questão>/*.py` (novos), `RULES.md` (passo 5) | Equipe (a decidir na S31-01) | — | S31-01, S33-04 | Desbloqueio: `ipc-rules validate` mostra "referências de IA: N em M questões", com M igual ao número de questões cadastradas |
| S33-06 | US-34 | Engenharia | Ligar os indícios no piloto: `IPC_AI_INDICATORS` = `"1"` no `render.yaml`, o teste correspondente atualizado e a variável `PILOT_AI_INDICATORS` = `1` | `render.yaml`, `backend/tests/test_indicators_api.py`, `.github/workflows/deploy.yml` | Autor | 0,5 | S31-01 (aprovada), S33-03 | Deploy verde com `ai_indicators: true` no `/api/v1/auth/options` da Vercel e o painel visível numa verificação de teste com a conta de verificação |

**ADRs:** atualiza o ADR-08 (faixas calibradas e, se for o caso, o status "ligado no piloto"). Sem ADR novo.

**Critérios de aceite:**
1. O job dos gabaritos roda no CI e passa com zero violação.
2. A calibração mostra no máximo 5% de faixa alta nas soluções anteriores a 2023, e o ADR-08 registra a distribuição.
3. O ruleset de 2027.1 é válido, com as questões e as referências das listas liberadas.
4. Os indícios só ficam ligados no piloto se a S31-01 estiver aprovada e o critério 2 for cumprido; senão, a S33-06 continua bloqueada.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Gabaritos | pytest (`tests/official_answers`) | `ci.yml`, job "Gabaritos" | PR e push, com `GABARITOS_REPO` definido | Zero violação em cada gabarito |
| Calibração dos indícios | `ipc-rules calibrate` | comando da S33-03 | à mão, a cada período | Sai com 0 (≤ 5% de faixa alta); a saída nunca mostra código |
| Regras R-01 de 2027.1 | `ipc-rules validate` e casos golden | `uv run ipc-rules validate ../rulesets/2027.1 --golden tests/golden` | PR de regras | 0 FP e 0 FN; referências válidas |
| Indícios no piloto (S33-06) | pytest | `tests/pilot::test_ai_indicators_are_on_only_when_expected` com `PILOT_AI_INDICATORS=1` | `deploy.yml` | `ai_indicators` igual ao esperado |
| Caso de uso dos indícios | Playwright | `frontend/e2e/indicators.spec.ts` | CI (compose) | Faixa alta com `break`, `continue` e `pass`; nada numa solução limpa |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Tasks acrescentadas em 11/10/2026 (início da sprint):**

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S33-07 | US-38 | Engenharia | `ipc-rules calibrate-gabarito`: em soluções humanas independentes, a distribuição de semelhança com o gabarito nas faixas do FR-29 e os alarmes falsos do alerta de vazamento (ADR-11), com limiar e tamanho mínimo ajustáveis; saída só com contagens e caminhos | `backend/src/ipc_analyzer/gabarito_calibration.py`, `cli.py` | Autor | 1 | — | Testes com soluções sintéticas: cópias do gabarito geram o alarme, soluções diferentes não; nenhum código na saída |
| S33-08 | US-14 | Engenharia | `ipc-rules import-gabaritos`: lê uma exportação do Notion em Markdown e grava `<período>/lista-<n>/L<n>-Q<m>.py` no repositório privado, nunca neste; questão pelo título, pela página ou pelas pastas; conflitos e blocos sem questão ficam para decisão manual | `backend/src/ipc_analyzer/gabarito_import.py`, `cli.py`, `rulesets/README.md` | Autor | 1 | — | Testes com uma exportação sintética; o destino neste repositório é recusado (NFR-27) |
| S33-09 | US-34 | Engenharia | (Opcional, a decidir pelo autor) gerar as referências por IA a partir do enunciado, pela cadeia do Aprimorar com IA, para quem cadastra revisar | a definir | Autor | 1 | S33-04 | Aguardando a decisão |
| S33-10 | US-15 | Externa | Volta da cota do Actions (01/11/2026): CI com o job "Gabaritos", "Deploy do piloto", backup e auditoria rodando no Actions (runbook, "Sem GitHub Actions") | `.github/workflows/` | Autor | — | 01/11/2026 | Os quatro workflows verdes |

**Situação (11/10/2026):** S33-07 e S33-08 entregues. S33-03 em parte: a medição preliminar nos 23 gabaritos de 2026.2 deu 0% na faixa alta (ADR-08), sem valor de calibração. Aguardando, com as premissas da P-21: S33-01 (períodos anteriores e Listas 4 a 6 de 2026.2), S33-02, S33-04, S33-05, S33-06 (depois da S33-02), S33-09 (decisão do autor) e S33-10 (01/11/2026). **Proposta de 12/10/2026:** as S33-03, S33-05, S33-06 e S33-09 passam para a Sprint 42 (7.16), que liga os indícios no piloto. **Decisões do autor (12/10/2026):** a S33-02 foi descartada, porque as soluções anteriores a 2023 não existem e não serão buscadas; a S33-09 foi aprovada; as questões de 2027.1 (S33-04) ficam prontas perto de março de 2027, até uma semana antes de cada lista.

**Definition of Done:** a da seção 8; nenhum gabarito ou solução de aluno no repositório (Q-14, NFR-11).

**Riscos e bloqueios:** a sprint inteira depende de dados externos (S33-01, S33-02 e S33-04). Sem as soluções anteriores a 2023, a calibração não sai, e os indícios continuam desligados no piloto. O documento de permissões de 2027.1 tem data incerta (P-10).

### Sprint 34 — Prontidão para 2027.1

**Objetivo:** antes da primeira lista de 2027.1, ter o plano do Render decidido e aplicado, o monitoramento estável, um teste sintético diário da primeira verificação, os cenários de carga do NFR-04 e do NFR-05 e as listas habilitadas conforme o professor validar.

**Missão, persona e execução:** a missão é chegar ao primeiro prazo de 2027.1 sabendo como o piloto se comporta no pico, no plano gratuito (S30-11). A persona é o monitor-mantenedor que opera o piloto (US-19, US-22). Execução: medir o pico no gratuito (S34-01) e os cenários do NFR-04 e do NFR-05 (S34-03), o teste sintético diário (S34-02), o alerta a cada release (S34-04), as listas habilitadas (S34-05) e 7 dias de monitores verdes (S34-06).

**Premissas:** P-01 (pico de 500 por minuto), P-04 (NAT do campus), P-05 (disponibilidade), P-10 (calendário), ADR-03.

**Histórias:** US-19, US-22 e US-12 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S34-01 | US-22 | Engenharia | Medir o pico no plano gratuito (S30-11, troca aceita pelo autor em 08/10/2026): "Carga no piloto" em degraus até o `OVERLOADED` aparecer, com a taxa máxima sem recusa e a porcentagem de recusas a 500 por minuto registradas no ADR-03 | `.github/workflows/load.yml`, `docs/adr/ADR-03-topologia-de-implantacao-por-fase.md` | Autor | 0,5 | S30-11 | Taxa máxima sem `OVERLOADED` e recusas a 500 por minuto no ADR-03; nenhum 500/502/504 |
| S34-02 | US-19 | Engenharia | Teste sintético diário da primeira verificação (NFR-06): workflow agendado que entra com a conta de verificação, verifica uma solução da Lista 1 e mede o tempo | `.github/workflows/synthetic.yml` (novo), `backend/tests/pilot/` | Autor | 1 | S30-01 | Roda todo dia útil às 07:00 (horário de Brasília), falha se a verificação passar de 300 ms no servidor (medido pelo `Server-Timing`; ver a situação da Sprint 34) ou se der erro |
| S34-03 | US-22 | Engenharia | Cenários de carga por release: o NFR-04 (500 por minuto por 15 min, 80% de 4 IPs) e o NFR-05 (1.500 por minuto, recusa com `Retry-After` em ≤ 100 ms e recuperação em ≤ 60 s), na emulação local, com `X-Forwarded-For` simulado e `IPC_TRUSTED_PROXY_HOPS` = 1 só no contêiner de teste | `deploy/load/run_load.py`, `deploy/load/pilot-load.js` | Autor | 2 | — | Relatório dos dois cenários no plano escolhido: 0 respostas 500, 502 ou 504; 503 com `Retry-After`; recuperação ≤ 60 s |
| S34-04 | US-19 | Engenharia | Exercício de alertas a cada release (NFR-15): o roteiro da S30-05 entra no checklist da release e no runbook, com uma linha por release | `docs/runbook.md`, `scripts/release.sh` (mensagem final) | Autor | 0,5 | S30-05 | Tabela do runbook com uma linha por release desde a Sprint 34 |
| S34-05 | US-12 | Externa | Habilitar as listas no piloto conforme o professor validar o ruleset de 2027.1 (`IPC_ENABLED_LISTS`) | `render.yaml` | Professor e Autor | — | S33-04 | Desbloqueio: `/api/v1/lists` do piloto mostra só as listas validadas, antes da data de liberação de cada uma |
| S34-06 | US-19 | Externa | Conferir os monitores no início do período: UptimeRobot verde nos 7 dias anteriores à primeira lista, e os contatos de alerta atualizados | Painel do UptimeRobot | Autor | — | S30-04 | Disponibilidade ≥ 99,5% nos 7 dias (P-05, NFR-06) |

**ADRs:** atualiza o ADR-03 com a medição da S34-01.

**Situação (11/10/2026):** S34-02 e S34-04 entregues (#71): o `Server-Timing` da verificação, o
workflow "Sintético diário", que começa a rodar com a volta da cota em 01/11/2026, os scripts
`sintetico-local.sh` e `carga-piloto.sh` e o exercício de alerta a cada release. S34-01 e S34-03
medidos na emulação do gratuito (ADR-03, "Pico no plano gratuito"): no máximo 100 verificações por
minuto sem recusa; sob sobrecarga, nenhum 500, 502 ou 504, todo 503 com `Retry-After` e
recuperação em 5,7 s, mas o NFR-04 e o tempo do 503 no NFR-05 não são atingíveis com 0,1 CPU (a
consequência aceita na S30-11). Achado para a Sprint 35: sob sobrecarga, o pool do banco esgotado
vira `DATABASE_UNAVAILABLE` em vez de `OVERLOADED`. O [A CONFIRMAR] da S34-02 foi resolvido pelo
`Server-Timing`, em vez do log ou do `/health/slo`. Aguardando: S34-05 (documento de 2027.1,
S33-04) e S34-06 (datas de 2027.1, P-10); os "7 dias seguidos" do sintético contam a partir de
01/11/2026.

**Critérios de aceite:**
1. O plano do Render está aplicado e medido.
2. O teste sintético roda há pelo menos 7 dias seguidos, sem falha.
3. Os relatórios do NFR-04 e do NFR-05 estão anexados ao ADR-03.
4. Só as listas validadas pelo professor estão habilitadas no piloto.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Sintético diário (novo) | pytest ou k6 contra o piloto | `synthetic.yml` | `schedule`, dias úteis | Verificação ≤ 300 ms e sem erro |
| Capacidade (NFR-04) | k6 | `python deploy/load/run_load.py --plan <plano> --rate 500 --duration 15m` | antes de cada release | 0% de 5xx e < 0,1% de timeouts |
| Estresse (NFR-05) | k6 | `run_load.py` com 1.500 por minuto | antes de cada release | 0 respostas 500, 502 ou 504; `Retry-After` em ≤ 100 ms; recuperação ≤ 60 s |
| Carga no piloto | k6 | `load.yml` | depois da mudança de plano | P95 do servidor ≤ 200 ms |
| Exercício de alerta | UptimeRobot | runbook | a cada release | E-mail em ≤ 5 min |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com o item do UptimeRobot cumprido.

**Riscos e bloqueios:** o custo do Starter é decisão do autor (S30-11); sem ele, o NFR-01 não é atendido com login (ADR-03, S28-01). O calendário de 2027.1 depende da UFPE (P-10).

### Sprint 35 — Controles de qualidade e observabilidade

**Objetivo:** tirar do estado [PLANEJADO] os controles de qualidade que não dependem da Fase 2: benchmark do motor, Lighthouse, cobertura por pasta, canário em produção e esquema do ruleset; a observabilidade com Prometheus e Grafana entra só se o autor decidir.

**Missão, persona e execução:** a missão é tirar do estado [PLANEJADO] os controles de qualidade. A persona é o Tech Lead que cuida da qualidade (US-14, US-15, US-17, US-21). Execução: um controle por PR (S35-01 a S35-05), cada um entrando no CI só depois de verde na `develop`, e a decisão do `/metrics` (S35-06).

**Premissas:** NFR-02, NFR-03, NFR-11 e NFR-16, com as metas da seção 3.3.

**Histórias:** US-14, US-15, US-17 e US-21 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S35-01 | US-15 | Engenharia | `pytest-benchmark` no CI (NFR-02: P95 ≤ 50 ms por entrada de até 50 KB; até 5 KB desde a Q-25, e a CI usa um benchmark próprio): corpus fixo de entradas, linha de base versionada, e o CI falha se o P95 regredir mais de 20% | `backend/pyproject.toml` (dependência de dev), `backend/tests/benchmark/` (novo), `.github/workflows/ci.yml` | Autor | 2 | — | Um PR que deixa o motor 30% mais lento falha; o item do benchmark da seção 8 sem [PLANEJADO] |
| S35-02 | US-21 | Engenharia | Lighthouse CI nos PRs do `frontend/` (NFR-03): perfil móvel ("Slow 4G") sobre o build de produção | `.github/workflows/ci.yml`, `frontend/lighthouserc.json` (novo) | Autor | 1 | — | FCP < 1,5 s (≤ 1,65 s desde a Q-25) e JS inicial ≤ 350 KB gzip (NFR-03); um PR que estoura a meta falha |
| S35-03 | US-15 | Engenharia | Cobertura com limite por pasta (NFR-16): ≥ 90% em `ipc_analyzer/engine` e ≥ 80% no restante, além do total | `backend/pyproject.toml`, `.github/workflows/ci.yml` | Autor | 0,5 | — | O CI falha se a pasta do motor cair abaixo de 90% |
| S35-04 | US-17 | Engenharia | Busca mensal do canário em produção (NFR-11): um workflow agendado verifica, com a conta de verificação, um código com um marcador e procura o marcador no banco (com a credencial de administrador) e nos logs do Render **Decidido pelo autor em 11/10/2026:** sem chave de API do Render (ela não tem escopo e daria acesso total ao serviço); o workflow procura no banco, e os logs são conferidos pelo painel com a marca que ele mostra (runbook, "Canário mensal") | `.github/workflows/canary.yml` (novo) | Autor | 2 | S30-01 | 0 ocorrências no banco e nos logs; o workflow falha com uma ocorrência plantada num teste |
| S35-05 | US-14 | Engenharia | JSON Schema do ruleset e `ipc-rules compile` (C6): esquema gerado do modelo do carregador, para editores e para o CI, e um compilado com o SHA-256 | `rulesets/schema/ruleset.schema.json` (novo), `backend/src/ipc_analyzer/cli.py` | Autor | 2 | — | O esquema valida os rulesets de 2026.2 e 2027.1; o compilado tem o mesmo `ruleset_sha256` do manifesto; o item da C6 sem [PLANEJADO] |
| S35-06 | US-17 | Decisão | Métricas `/metrics`, Grafana e Prometheus (opcionais, C8): manter o `/health/slo` com o UptimeRobot ou acrescentar o Grafana Cloud gratuito (opções em 7.13.7) | `docs/blueprint.md` (C8) | Autor | — | — | Desbloqueio: decisão registrada na C8; se aprovada, uma task de implementação entra na sprint seguinte |

**ADRs:** nenhum; a decisão da S35-06, se positiva, atualiza a C8 da seção 5.2.1.

**Tasks acrescentadas em 11/10/2026 (início da sprint), dos achados das Sprints 34 e do roteiro de
testes manuais:**

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S35-07 | US-08 | Engenharia | Plágio resistente a linhas inseridas dentro de um bloco copiado (cenários P-11 e P-12 do roteiro): comparar também os comandos de cada bloco, além das subárvores inteiras (ADR-07) | `backend/src/ipc_analyzer/engine/similarity_tree.py`, `docs/adr/ADR-07-*.md` | Autor | 3 | — | P-11 ≥ 95% e P-12 ≥ 90%; as soluções independentes do roteiro (P-09) e o corpus de pares continuam baixos |
| S35-08 | US-22 | Engenharia | Sob sobrecarga, o pool do banco esgotado responde `OVERLOADED` com `Retry-After`, e não `DATABASE_UNAVAILABLE` (achado da S34-03, ADR-03) | `backend/src/ipc_api/accounts/postgres.py`, `backend/src/ipc_api/errors.py` | Autor | 1 | — | Teste com o pool esgotado; a medição do NFR-05 no gratuito sem `DATABASE_UNAVAILABLE` |
| S35-09 | US-12 | Engenharia | Período 2027.1 criado como cópia do 2026.2 (P-22), inativo até a troca do `rulesets/ATIVO` | `rulesets/2027.1/` | Autor | 0,5 | — | Todo período do repositório carrega; 2027.1 com as permissões de 2026.2 |
| S35-10 | US-14 | Externa | Campanha de testes manuais pela equipe com o `docs/testes-manuais.md`; cada falha confirmada vira um teste automático | `docs/testes-manuais.md` | Equipe | — | — | Fichas de falha respondidas |

**Decisão da S35-06 (11/10/2026, autor):** manter só o `/health/slo` com o UptimeRobot, sem Grafana
nem `/metrics` (C8 atualizada).

**Situação (11/10/2026):** engenharia concluída. S35-01, S35-02 e S35-03 na CI (#84), com as metas
do NFR-02 e do NFR-03 medidas pela primeira vez e abertas na Q-25 (a CI usa as proteções descritas
lá até a decisão); S35-04 (canário só no banco, logs pelo painel); S35-05 (#83); S35-07 (#82);
S35-08 (#81); S35-09 (#80); S35-06 decidida. Aguardando: S35-10 (equipe) e o primeiro canário
mensal no piloto. A Q-25 foi decidida pelo autor no mesmo dia: o NFR-02 e o NFR-03 passaram às metas
que a CI já usava (seção 3.3).

**Critérios de aceite:**
1. O CI falha num PR que regride o motor mais de 20%, ou que estoura a meta do Lighthouse, ou que baixa a cobertura do motor abaixo de 90%.
2. O canário mensal roda e acha 0 ocorrências.
3. O esquema e o compilado do ruleset existem e conferem com o manifesto.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Desempenho do motor | pytest-benchmark | `ci.yml` (novo) | PR e push | P95 ≤ 50 ms por entrada (até 5 KB desde a Q-25) e regressão ≤ 20% sobre a linha de base |
| Desempenho da página | Lighthouse CI | `ci.yml` (novo) | PR que muda `frontend/` | FCP < 1,5 s (móvel; ≤ 1,65 s desde a Q-25) e JS inicial ≤ 350 KB gzip |
| Cobertura por pasta | pytest-cov | `ci.yml` | PR e push | ≥ 90% no motor, ≥ 80% no resto |
| Canário em produção | pytest ou script, banco e logs | `canary.yml` (novo) | `schedule`, mensal | 0 ocorrências |
| Esquema do ruleset | JSON Schema | `ipc-rules validate` e o esquema | PR de regras | Válido |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com os itens de benchmark e de cobertura sem [PLANEJADO].

**Riscos e bloqueios:** a variação de tempo dos runners do GitHub pode gerar falsos alarmes no benchmark (mitigação: comparar mediana de 5 rodadas). O canário nos logs depende de uma chave de API do Render, que é um secret novo, gravado pelo autor.

## 7.14 Matriz de rastreabilidade das pendências (07/10/2026, atualizada em 12/10/2026)

Criada em 07/10/2026 e atualizada em 12/10/2026 pelo CHANGELOG e pelas decisões do autor. A última coluna diz o que já foi resolvido; quando uma task fechar, o item é marcado aqui e na origem.

| Pendência original | Seção da lista de 07/10/2026 | Sprint/Task | Tipo | Situação em 12/10/2026 |
|---|---|---|---|---|
| Conta de verificação e `PILOT_CHECK_*` | 2 | S30-01 | Externa | Feito (08/10/2026) |
| Primeiro deploy com login (S11, S16, S19, S25; P-15) | 2 e 5 | S30-02 | Engenharia | Feito (08/10/2026) |
| UptimeRobot, três monitores (S11, S21) | 2 e 5 | S30-04, S34-06 | Externa | Feito (08/10/2026); a conferência para 2027.1 (S34-06) espera as datas |
| Exercício de alerta no piloto (S21; NFR-15) | 5 e 6 | S30-05, S34-04 | Engenharia | Feito; repetido a cada release (runbook) |
| Chave do backup e `BACKUP_AGE_RECIPIENT` (S28-03) | 2 | S30-06 | Externa | Feito (08/10/2026) |
| Ensaio de restauração do backup (S28-03; NFR-20) | 5 | S30-07 | Engenharia | Feito (S30-07) |
| Ensaio cronometrado do rollback (S28-03) | 2 e 5 | S30-08 | Engenharia | Feito (08/10/2026) |
| Carga no piloto de verdade (S28-01) e latência até o Supabase (Q-20) | 2, 4 e 5 | S30-09 | Engenharia | Feito (S30-09) |
| Plano Starter (ADR-03) | 2 e 3 | S30-11 (decisão), S34-01 (aplicação) | Decisão | Decidido: plano gratuito (08/10/2026); medido na S34-01 |
| P-12 (a): `X-Forwarded-For` | 4 | S30-03 | Engenharia | Resolvido (08/10/2026) |
| P-15 (a): login com cookie e feedback em até 30 s | 4 | S30-02 | Engenharia | Resolvido (08/10/2026) |
| P-15 (b): IP do cliente como penúltimo endereço | 4 | S30-03 | Engenharia | Resolvido (08/10/2026) |
| `PermissionError` do supervisord | Dívida técnica | S30-10 | Engenharia | Resolvido (08/10/2026, P-17) |
| Política dos indícios (S29-04, ADR-08) | 3 | S31-01 | Decisão | Decidido: aprovada (09/10/2026, Q-21) |
| Q-16: provedor de IA | 3 | S31-02 | Decisão | Decidido (09/10/2026) |
| Q-17: remetente dos e-mails | 3 | S31-07 | Decisão | Decidido (09/10/2026) |
| Q-22: governança das regras | 3 | S31-08 | Decisão | Decidido (09/10/2026) |
| Q-12: servidor do CIn | 3 | S41-02 | Externa | Adiada até a P-09 |
| Auditoria bloqueante (S25-01; NFR-13) | 5 e 6 | S31-03 | Engenharia | Feito (09/10/2026) |
| Semgrep (NFR-09) | 6 | S31-04 | Engenharia | Feito (09/10/2026, P-20) |
| Marco 2: guia e apresentação | 5 | S31-05 | Externa | Pendente: apresentação em 19/10/2026 |
| Formulário e planilha do critério 3 (S28-02) | 5 | S31-06 | Externa | Descartado pelo autor; a satisfação será medida com os feedbacks coletados pelo autor (Q-36, 12/10/2026) |
| Gabaritos de períodos anteriores (S20, Q-14) | 5 | S33-01 | Externa | Em parte: Listas 1 a 4 de 2026.2 carregadas; faltam as Listas 5 e 6 e os períodos anteriores |
| Calibração dos indícios (S29-03/04) e faixas (ADR-08) | 4 e 5 | S33-02 (dados), S33-03; S42-01 e S42-02 (12/10/2026) | Externa e Engenharia | Soluções anteriores a 2023 descartadas (12/10/2026); critérios e base aprovados (Q-35, 12/10/2026); calibração na S42-02 |
| Questões reais de 2027.1 (S24, R-01) | 5 | S33-04 | Externa | Perto de março de 2027, até uma semana antes de cada lista |
| Referências reais por IA (S29-02) | 5 | S33-05; S42-04 (12/10/2026) | Externa | Gerador aprovado (S33-09, 12/10/2026); na Sprint 42 |
| Ligar os indícios no piloto | 3 | S33-06; S42-05 e S42-06 (12/10/2026) | Engenharia | Sprint 42 (critérios aprovados em 12/10/2026) |
| Listas habilitadas conforme o professor | Prioridade 4 | S34-05 | Externa | Espera as datas de 2027.1 |
| Teste sintético diário (NFR-06) | 6 | S34-02 | Engenharia | Feito (11/10/2026) |
| k6 por release: NFR-04 e NFR-05 | 6 | S34-03 | Engenharia | Feito (11/10/2026) |
| Membros ativos sem o desenvolvedor (S28-02) | 4 | Premissa mantida; revista com a coordenação na S31-05 | Decisão | Premissa mantida; revisão no Marco 2 |
| Backup do Supabase gratuito (premissa) | 4 | Premissa mantida; o `backup.yml` já cobre (S30-07 ensaia) | Engenharia | Resolvido: o `backup.yml` cobre, ensaiado na S30-07 |
| RPO de 24 h da NFR-20 com backup semanal (achado de 07/10/2026) | — | S30-12 | Decisão | Decidido: backup diário (08/10/2026) |
| `pytest-benchmark` (NFR-02) | 6 | S35-01 | Engenharia | Feito (11/10/2026) |
| Lighthouse CI (NFR-03) | 6 | S35-02 | Engenharia | Feito (11/10/2026) |
| Cobertura por pasta (NFR-16) | 6 | S35-03 | Engenharia | Feito (11/10/2026) |
| Canário mensal em produção (NFR-11) | 6 | S35-04 | Engenharia | Feito (11/10/2026): só no banco, com os logs pelo painel |
| JSON Schema e `ipc-rules compile` (C6) | 6 | S35-05 | Engenharia | Feito (11/10/2026) |
| `/metrics`, Grafana e Prometheus (C8, opcionais) | 6 | S35-06 | Decisão | Decidido: só o `/health/slo` com o UptimeRobot (11/10/2026) |
| GHCR por digest, deploy por SSH e staging (Fase 2) | 6 | S41-03, S41-04 | Engenharia (bloqueada) | Bloqueado (Sprint 41) |
| Backlog de experiência e REC fora do escopo | 7 | Seção 7.1, "Backlog"; sem task | — | — |
| Comparação com o gabarito na verificação, no plágio e nos indícios (pedido do autor, 09/10/2026) | Q-24 | S32-01 a S32-10 | Externa e Engenharia | Feito (Sprint 32; 23 gabaritos no piloto em 10/10/2026) |
| Aviso da Sprint 20: repositório privado dos gabaritos | Revisão de 08/10/2026 | H-02, S33-01 | Engenharia e Externa | Feito (08/10/2026) |
| Aviso da Sprint 22: casos em aberto do mapeamento | Revisão de 08/10/2026 | H-03, S31-05, S31-12 | Externa | Casos decididos (ruleset 2026.2.5, 09/10/2026); a revisão do guia fica para o Marco 2 |
| Aviso da Sprint 24: nenhuma questão real cadastrada | Revisão de 08/10/2026 | S31-09, S31-10, S31-11, S31-13, S33-04 | Engenharia e Externa | Em parte: 3 questões em 2026.2; as de 2027.1 perto de março de 2027 |
| Aviso da Sprint 29: indícios desligados no piloto | Revisão de 08/10/2026 | S31-01, S33-02, S33-03, S33-06; Sprint 42 (12/10/2026) | Decisão, Externa e Engenharia | Sprint 42 (critérios aprovados em 12/10/2026) |
| Avisos das Sprints 11, 19, 21, 25 e 28 | Revisão de 08/10/2026 | Resolvidos (S30); README corrigido (H-01) | — | Resolvidos (S30) |

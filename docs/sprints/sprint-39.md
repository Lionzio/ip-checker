# Sprint 39 — Qualidade interna, operação e documentação

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

**Objetivo:** reduzir o custo de manter o projeto: arquivos menores, testes mais rápidos e completos,
backup automático e restauração ensaiada, e a documentação reorganizada para quem chega.

**Missão:** que o próximo monitor-mantenedor assuma o projeto sem depender do autor.

**Persona:** o monitor-mantenedor (US-20, US-35).

**Execução:**
1. Os testes que faltam (S39-03), antes das refatorações.
2. As refatorações do frontend e do backend (S39-01 e S39-02), cada uma num PR, sem mudar comportamento.
3. A operação (S39-04).
4. A documentação (S39-05), num PR só de `.md`.

**Histórias:** US-14, US-15, US-20 e US-35.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S39-01 | US-20 | Engenharia | Frontend em arquivos menores. `Plagiarism.tsx` (511 linhas) vira os modos "Dois códigos" e "Contra a turma" e os resultados em arquivos próprios. `Admin.tsx` (420) ganha as tabelas em componentes. O `parseClass` da turma deixa de rodar a cada tecla (`useMemo`) | `frontend/src/pages/` | Autor | 1,5 | S39-03 | Nenhum arquivo de página com mais de 300 linhas; os mesmos testes verdes |
| S39-02 | US-14, US-20 | Engenharia | Backend em módulos menores. As listas de palavras dos indícios (cerca de 180 linhas de `indicators.py`) vão para um arquivo de dados. O `ruleset.py` se divide em esquema, compilação e carga. Os DTOs saem do `service/app.py` para `service/schemas.py` | `backend/src/ipc_analyzer/` | Autor | 1,5 | S39-03 | Import-linter e testes verdes; nenhum módulo com mais de 500 linhas |
| S39-03 | US-15, US-20 | Engenharia | Os testes que faltam: `Login`, `Register`, `Profile`, `Verify`, `ForgotPassword` e `Landing` no Vitest. Os testes lentos ganham o marcador `slow`, e as esperas reais viram eventos ou relógio injetado. `pytest-xdist` nos testes sem banco | `frontend/src/pages/*.test.tsx`, `backend/tests/`, `backend/pyproject.toml` | Autor | 1,5 | — | Cobertura das páginas ≥ 80%; a etapa de pytest da CI local ≥ 30% mais rápida |
| S39-04 | US-35 | Engenharia | Operação. O `scripts/backup-local.sh` agendado no Agendador de Tarefas do Windows (o backup do Actions volta com a cota). Um ensaio de restauração completo num PostgreSQL descartável, comparando as contagens. A troca do token dos gabaritos por evento, porque ele não vence (P-23, decisão do autor de 12/10/2026): o roteiro do runbook para suspeita de vazamento, mudança de quem administra a conta e 401 nos logs | `scripts/`, `docs/runbook.md` | Autor | 0,5 | — | Restauração ensaiada com o tempo no runbook; tarefa agendada documentada |
| S39-05 | US-20 | Engenharia | Documentação reorganizada. Ver a lista logo abaixo da tabela | `docs/` | Autor | 1 | S36-07 | O blueprint com menos de 1.000 linhas; os documentos novos no mapa (`docs/README.md`) |
| S39-06 | US-14 | Engenharia | 429 enganoso com o banco lento (achado na CI local da Sprint 40, em 15/10/2026): quando o `SessionMiddleware` recebe `StoreUnavailable`/`StoreBusy` ao resolver a sessão, a requisição fica sem `account_id` e o `RateLimitMiddleware` a conta como cliente anônimo pelo IP; com o balde do IP cheio, o monitor logado recebe 429 "Você fez muitas requisições" em vez de 503 `OVERLOADED`, e todos atrás do mesmo IP dividem 30 por minuto até 60 s depois de o banco voltar. Uma requisição com `session_error` conta só o balde do IP e responde 503 com `Retry-After`; os testes de borda (`tests/security/test_api_rate_limit_edge.py`) deixam de depender da virada do minuto e do que sobrou dos testes anteriores | `ratelimit.py`, `auth/middleware.py`, `tests/security` | Autor | 0,5 | — | Teste de unidade com um autenticador que levanta `StoreBusy`; a etapa de segurança da CI local passa 3 vezes seguidas com a máquina carregada; nenhum limite afrouxado |

**O que a S39-05 reorganiza:**
- O histórico das tasks das Sprints 1 a 35 sai do blueprint para `docs/historico/`.
- O `decisoes.md` ganha uma tabela-resumo (ID, situação, data e uma frase) e uma seção por ID.
- Documentos novos:
  - um glossário (R-xx, P/C/Q/REC, Snn-mm, FR/NFR/US, fato, faixa, contenção);
  - uma página única de estado e pendências;
  - um FAQ do mantenedor (habilitar lista, trocar de período, gabarito novo e reinício do Render);
  - a agenda das rotinas (backup, sintético, canário, auditoria, rollback e restauração) e os eventos que pedem a troca do token dos gabaritos, que não vence (P-23);
  - quem cuida de cada conta (Render, Vercel, Supabase, Brevo, UptimeRobot, gabaritos, chaves das IAs).
- O índice de sintomas do runbook ganha os gabaritos indisponíveis, o "Aprimorar com IA" sem cota e a falha do sintético ou do canário.

**ADRs:** nenhum.

**Critérios de aceite:**
1. Nenhum arquivo de página com mais de 300 linhas e nenhum módulo do backend com mais de 500.
2. As páginas sem teste agora têm teste.
3. A CI local mais rápida.
4. Backup agendado e restauração ensaiada.
5. Documentação reorganizada e no mapa.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Testes novos das páginas | Vitest | PR | Verdes; cobertura das páginas ≥ 80% |
| Refatorações | toda a base de 7.12.1 | PR | Nada muda de comportamento |
| Restauração | `pg_restore` num PostgreSQL descartável e `contagens.sql` | Uma vez | Contagens iguais; tempo no runbook |
| Tempo da CI | `ci-local.sh` | PR | Etapa de pytest ≥ 30% mais rápida |

**Deploy:** release `sprint-39`.
- **Render:** Manual Deploy (o backend é refatorado, sem mudar comportamento).
- **Vercel:** Create Deployment (a página é refatorada). Sem migração.
- **Depois:** sintético, exercício de alerta e o roteiro de testes manuais na parte do plágio e do gerenciamento.

**Riscos:** refatorar sem mudar comportamento exige os testes primeiro (S39-03), por isso eles vêm antes.

**Situação (16/10/2026):** engenharia concluída na release `sprint-39`, num PR por task (#131 a #136), com a S39-06 primeiro. Decisões da sprint (detalhes no `CHANGELOG.md`): os testes das páginas que o `App.test.tsx` já cobria não foram duplicados, e a cobertura passou a ser cobrada por página; os testes que medem o relógio ganharam o marcador `timing` e rodam em série com os do banco; os `sleep` dos analisadores simulados ficaram, porque simulam a análise lenta que os testes de admissão precisam; o Plágio, o Gerenciar e o Perfil passaram a carregar sob demanda depois de o FCP pular 150 ms com 0,3 KB a mais de JS; ficam acima de 500 linhas `accounts/postgres.py`, `engine/similarity_tree.py` e `accounts/store.py`, e o `components/ResultPanel.tsx` (424). Aguardando: o autor gravar o segredo do backup e registrar a tarefa agendada, e o deploy.

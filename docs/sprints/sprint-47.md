# Sprint 47 — Grupos de acompanhamento e histórico dos alunos (vai ao piloto com o aviso de privacidade aprovado)

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** cada monitor cadastra os alunos pelos quais é responsável e acompanha o histórico
deles, sozinho, em dupla ou em trio.

**Missão:** que um grupo de acompanhamento (N monitores e M alunos, por período) compartilhe as
verificações, os indícios e os alertas de plágio como resultados resumidos, sem o feedback (Q-28) e
sem nada do código do aluno (Q-27).

**Personas:** o monitor (US-45, US-46) e o monitor-chefe e o professor que supervisionam (US-47).

**Execução:**
1. A migração com as tabelas, o expurgo e os papéis (S47-01).
2. A política de acesso e as rotas (S47-02).
3. A gravação assíncrona do registro (S47-03).
4. As telas (S47-04) e a privacidade (S47-05).

**Histórias:** US-45, US-46 e US-47.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S47-01 | US-45 | Engenharia | Migração `0007_acompanhamento`: `app.student` (período, nome de exibição e, opcionalmente, o login do Dikastis, Q-26; nunca CPF, e-mail ou matrícula), `app.follow_group`, `app.group_member` (convite e aceite), `app.group_student`, `app.check_record` (só inserção; o resultado resumido, como "L3-Q1 anulada por Laços de repetição" ou "L4-Q2 validada", com as regras, a faixa dos indícios de IA e a do alerta de plágio quando houver e quem executou; sem código, hash, linhas, trechos ou feedback, Q-27 e Q-28) e `app.group_log`; `app.purge_semester()` `SECURITY DEFINER`; o `ipc_app` sem `DELETE` direto | `database/migrations/0007_*` | Autor | 2 | — | Ida e volta testadas (`test_migrations.py`) |
| S47-02 | US-45, US-47 | Engenharia | Política cargo × ação × alvo em `auth/policy.py` (membro vê e edita o próprio grupo; monitor-chefe, professor e desenvolvedor leem todos os grupos do período); rotas `groups`, `invites`, `students` e `history` | `auth/policy.py`, `routes/groups.py`, OpenAPI | Autor | 2 | S47-01 | Matriz testada por chamada direta (NFR-23) |
| S47-03 | US-46 | Engenharia | `student_id` e `group_id` opcionais em `/validate`, `/feedback` e `/similarity`; o registro é gravado em segundo plano e descartado sob `StoreBusy`, como a telemetria | `routes/*`, `telemetry.py` (padrão) | Autor | 1 | S47-02 | A resposta não muda com o banco ocupado |
| S47-04 | US-45, US-46, US-47 | Engenharia | Telas "Meus alunos" (grupos, convites, alunos), campo "Aluno" no verificador e no plágio, "Histórico do aluno" (linha do tempo com quem executou) e a leitura no Gerenciar | `frontend/src/pages/` | Autor | 3 | S47-02 | e2e: criar grupo, convidar, aceitar, adicionar aluno fictício, verificar e ver no histórico |
| S47-05 | US-45 | Documentação | Aviso de privacidade, seção 9.2, NFR-29, ADR-13, runbook (expurgo por período), guia da equipe | docs, `Privacy.tsx` | Autor e coordenação | 1 | — | Aprovação da coordenação |

**ADRs:** ADR-13 (novo) e ADR-04 (rotas novas na matriz de autorização).

**Critérios de aceite:**
1. Um aluno em dois grupos aparece nos dois; sair de um grupo não apaga os registros.
2. Nenhuma coluna guarda código (canário do NFR-11 estendido às tabelas novas).
3. O expurgo de um período remove alunos, grupos e registros daquele período.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Migração e expurgo | pytest com PostgreSQL | PR | Ida e volta; `purge_semester` |
| Autorização | pytest (matriz) | PR | 403 fora do grupo; leitura pela chefia |
| Sem código guardado | canário do NFR-11 | PR | 0 ocorrências |
| Fluxo completo | e2e | PR | Criar, convidar, aceitar, verificar e ver no histórico |
| Carga | `run_load.py` | Uma vez | Sem 500; registros descartados sob carga |

**Deploy:** release `sprint-47`, só depois da aprovação do aviso de privacidade (S47-05). Migração antes da release e nunca junto com o `render.yaml` (P-18);
depois, Render e Vercel.

**Riscos:** dado pessoal novo de terceiros (os alunos não usam a ferramenta, P-13); a base legal e o
aviso dependem da coordenação. Mais escritas no banco do plano gratuito (`POOL_SIZE=5`).

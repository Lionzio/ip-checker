# Sprint 54 — Sincronização automática e painel de sincronizações

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seção 4.1); o plano comum está no [README](README.md).

**Objetivo:** o catálogo e os códigos chegando sozinhos, com o histórico de cada sincronização visível e um aviso quando algo para.

**Missão:** que ninguém precise lembrar de sincronizar, e que a chefia saiba o que entrou, quando e por quem.

**Personas:** o membro da chefia que liga o automático (US-55) e o monitor-mantenedor que investiga uma sincronização que parou (US-20).

**Execução:**
1. O modo automático com a trava (S54-01).
2. A tela "Sincronizações" (S54-02).
3. O spike do automático sem navegador (S54-03), o aviso quando para (S54-04) e os documentos (S54-05).

**Histórias:** US-55 e US-20.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S54-01 | US-55 | Engenharia | Modo automático: `chrome.alarms` a cada 6 horas (configurável no popup), só com o Dikastis logado; uma pessoa por vez por período (trava na API, com validade); notificação do navegador com o resumo (novidades, códigos, erros) | Extensão, API | Autor | 2 | Sprints 50 e 52 | Testes do alarme e da trava com o Dikastis falso; sem login, a extensão espera e avisa |
| S54-02 | US-20 | Engenharia | Tela "Sincronizações" (chefia): o histórico de `import_runs` com quem, modo, o que entrou e mudou, erros e duração; `GET /import/runs` paginado | Página, API | Autor | 2 | — | Vitest e e2e |
| S54-03 | US-55 | Engenharia | Spike do automático sem navegador: uma tarefa agendada no Windows do autor (como o backup da S39-04) com um navegador sem janela e um perfil persistente já logado no Dikastis; só vale se o login do Dikastis durar sem interação. Relatório do spike em `decisoes.md`; se viável, o script e a tarefa (registrada pelo autor) | Script, runbook | Autor | 2 | S54-01 | Relatório do spike; se viável, a tarefa registrada e um registro em `import_runs` com modo "agendado" |
| S54-04 | US-20 | Engenharia | Aviso quando a sincronização para (formato do Dikastis mudou, token vencido, sem sincronização há mais de 7 dias com listas abertas): e-mail para a chefia pelo mesmo envio da API, no máximo um por dia | API | Autor | 1 | S54-02 | Teste do aviso com o relógio injetado; o e-mail não traz dado de aluno |
| S54-05 | US-20 | Documentação | Guia ("Ligar a sincronização automática"); runbook ("A sincronização parou", revisado com os três motivos); FR-39 fechado; a situação da Fase 1h no blueprint | docs | Autor | 1 | — | Revisão |

**ADRs:** nenhum novo; ADR-15 ganha a seção do modo automático.

**Critérios de aceite:**
1. Com o automático ligado, 6 horas com o navegador aberto e o Dikastis logado, a extensão sincroniza e mostra uma notificação com o resumo; a tela "Sincronizações" registra a rodada com o modo "automático".
2. Duas extensões com o automático ligado no mesmo período não sincronizam ao mesmo tempo (a segunda espera a trava).
3. Sem sincronização há mais de 7 dias com uma lista aberta, a chefia recebe um e-mail.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Alarme e trava | Vitest com o Dikastis falso; pytest | PR | A trava impede duas rodadas; sem login, espera e avisa |
| Tela | Vitest e e2e | PR | Histórico com todos os campos; paginação |
| Aviso | pytest com o relógio injetado | PR | Um e-mail por dia; sem dado de aluno |
| Regressão | `scripts/ci-local.sh` | Todo PR | Verde; o resumo colado no PR |

**Deploy:** release `sprint-54`. Render e Vercel com "faça o deploy"; a tarefa agendada, se o spike for viável, é registrada pelo autor no Windows dele; depois, o exercício de alerta e o sintético.

**Riscos:**
- A sessão do Dikastis expira: o automático avisa e espera o próximo login; o semi-automático cobre.
- O navegador fechado na máquina de todos: o aviso de 7 dias chama alguém.
- A tarefa agendada depende da máquina do autor ligada: fica como opcional, com o alarme da extensão como padrão.

# Sprint 44 — Feedback rastreável e o padrão do monitor

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** que cada violação citada no feedback traga a linha e o motivo, e que o tom da equipe
fique num arquivo revisável.

**Missão:** o aluno sabe onde e por que a questão foi anulada, e o monitor-chefe ajusta o tom sem
programar.

**Personas:** o monitor que manda o feedback (US-41) e o monitor-chefe (US-42).

**Execução:**
1. Os itens do feedback com regra, linhas, explicação e alternativa (S44-01), sobre a S38-01 e a S38-02.
2. O `estilo.yaml` com o esquema (S44-02).
3. A tela destaca as linhas citadas (S44-03) e os documentos (S44-04).

**Histórias:** US-32, US-41 e US-42.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S44-01 | US-41 | Engenharia | `FeedbackItem` ganha `rule_id`, `lines`, `explanation` e `alternative` (do ruleset); o trecho sem IA cita cada item na ordem do motor, com o nome da regra (Q-30), a linha, o porquê e um caminho, sem a solução; a frase obrigatória não muda (NFR-26) | `engine/feedback.py`, `feedback/compose.py` | Autor | 2 | S38-01, S38-02 | Casos T1 a T3 da revisão; NFR-26 intacto |
| S44-02 | US-42 | Engenharia | `backend/src/ipc_api/feedback/estilo.yaml` (tom, dicas, fechamentos e 3 a 5 exemplos com `[ALUNO]`) com esquema JSON validado na CI; os prompts usam o tom e os exemplos | `feedback/estilo.yaml`, `estilo.schema.json`, `compose.py` | Autor | 1 | — | Arquivo inválido falha na CI; a mudança aparece no próximo feedback |
| S44-03 | US-41 | Engenharia | `FeedbackResponse.items`; a página destaca no editor a linha de cada item citado | `schemas.py`, `FeedbackPanel.tsx`, OpenAPI | Autor | 1 | S44-01 | Vitest |
| S44-04 | US-42 | Documentação | `docs/estilo-do-feedback.md` (como editar e quem revisa, Q-31); FR-34 e FR-35; revisão da ADR-06; guia da equipe | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-06 (revisão).

**Critérios de aceite:**
1. Para `for` e `range()` na Lista 1, o feedback sem IA cita as duas construções com a linha e diz que são liberadas na Lista 2.
2. Um `estilo.yaml` inválido não passa na CI.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Itens rastreáveis | pytest (`test_compose.py`, `test_feedback_engine.py`) | PR | Linha e motivo em todo item; ordem do motor |
| Esquema do estilo | pytest | PR | Arquivo inválido recusado |
| Destaque na página | Vitest e e2e | PR | A linha citada é marcada no editor |

**Deploy:** release `sprint-44`. Render e Vercel.

**Riscos:** um texto mais longo pode passar do que cabe no Dikastis (**hipótese**; medir com a equipe
na campanha de testes).

# Sprint 43 — Período na interface e retenção por encerramento

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** corrigir uma lista atrasada com as regras do período certo e manter só os períodos
recentes carregados.

**Missão:** que o monitor escolha Período → Lista → Questão, com o período ativo já escolhido, e que
o mantenedor encerre períodos antigos sem perder nada do Git.

**Personas:** o monitor que corrige uma lista de outro período (US-39) e o monitor-mantenedor
(US-40).

**Execução:**
1. O analisador carrega o ativo e os 5 anteriores (S43-01), e a API aceita o período (S43-02).
2. O seletor na página (S43-03).
3. O encerramento por CLI com simulação (S43-04) e os documentos (S43-05).

**Histórias:** US-37, US-39 e US-40.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S43-01 | US-39 | Engenharia | `load_rulesets(root)` carrega o período do `ATIVO` e os 5 anteriores presentes em `rulesets/` (ignora `rulesets/encerrados/`); o manifesto passa a listar `periods` (período, ativo, `ruleset_version`, questões); cache de preparação por (período, hash) | `engine/ruleset/load.py`, `service/app.py`, `/internal/ruleset/manifest` | Autor | 2 | — | Testes com 7 períodos em `tmp_path` (6 carregados); hash por período; subida até +2 s em relação a um período (premissa validada pelo autor em 12/10/2026) |
| S43-02 | US-39 | Engenharia | `period` opcional em `/validate`, `/similarity`, `/similarity/batch` e `/feedback` (padrão: o ativo); `GET /api/v1/periods`; 422 `UNKNOWN_PERIOD`; `questions.py` resolve por (período, questão); a telemetria e a adoção gravam o período da requisição | `ipc_api/schemas/`, `routes/*`, `questions.py`, `telemetry.py`, `adoption.py`, OpenAPI | Autor | 1 | S43-01 | Contrato OpenAPI; teste com `L3-Q9` de 2026.2 e o ativo em 2027.1 |
| S43-03 | US-39 | Engenharia | `PeriodSelector` antes de `ListSelector` no verificador e no plágio, com "(ativo)" no rótulo; o rascunho (S37-05) guarda o período; "Próximo aluno" mantém o período | `frontend/src/components/`, `Checker.tsx`, `Plagiarism.tsx` | Autor | 1 | S43-02 | Vitest e e2e da lista atrasada |
| S43-04 | US-40 | Engenharia | `ipc-rules retire-period <período> [--dry-run]` move a pasta para `rulesets/encerrados/` e recusa o ativo e os períodos da janela; o índice de gabaritos ignora `encerrados/`; aviso em `/health/slo` quando o `ATIVO` parece defasado em relação à data (só aviso, nunca troca automática) | `cli.py`, `gabaritos.py`, `routes/meta.py` | Autor | 1 | S43-01 | `--dry-run` não toca no disco; recusas testadas |
| S43-05 | US-40 | Documentação | ADR-12; revisão da ADR-10 (decisão 3); `rulesets/README.md` ("Encerrar um período"); README dos gabaritos (`encerrados/`); FR-32 e US-37 sem a nota de "até a Sprint 43"; `new-period` deixa de copiar a lista de questões do `LEIA-ME.md` (hoje `rulesets/2027.1/questions/LEIA-ME.md` cita questões que não existem) | docs, `cli.py` | Autor | 1 | — | Revisão |

**ADRs:** ADR-12 (novo) e ADR-10 (revisão).

**Critérios de aceite:**
1. Com o `ATIVO` em 2027.1, o monitor escolhe 2026.2, a Lista 3 e a L3-Q9, e a resposta traz a `ruleset_version` de 2026.2.
2. Sem período na requisição, tudo funciona como hoje.
3. O `retire-period --dry-run` mostra o que sairia, e o ativo nunca é encerrado.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Carregamento de vários períodos | pytest | PR | 6 carregados, `encerrados/` ignorado, hash por período |
| Período na API | pytest e contrato OpenAPI | PR | Padrão = ativo; 422 para período desconhecido |
| Seletor | Vitest e e2e | PR | Lista atrasada verificada com as regras do período |
| Encerramento | pytest com `tmp_path` | PR | Simulação sem efeito; recusas |

**Deploy:** release `sprint-43`. Render (analisador e API) e Vercel; sem migração.

**Riscos:** as views que agrupam por `ruleset_version` passam a misturar períodos na mesma semana
(conferir `v_top_rules_by_list`); mais memória no analisador (dezenas de KB por período).

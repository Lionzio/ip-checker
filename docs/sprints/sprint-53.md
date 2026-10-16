# Sprint 53 — Plágio por turma e por período

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seção 4.4); o plano comum está no [README](README.md). Absorve a S46-03 (100 soluções) e a amplia para o período.

**Objetivo:** comparar todos os códigos de uma questão numa turma (até 100) ou no período inteiro (até 600), em segundo plano e sem estourar o plano gratuito, com os grupos e os trechos lado a lado.

**Missão:** que a equipe ache plágio entre turmas, e não só dentro de uma, sem esperar na tela nem subir um arquivo.

**Personas:** o membro da equipe que corrige a lista (US-54) e o monitor-chefe que revisa os grupos entre turmas.

**Execução:**
1. A impressão MinHash e o LSH no analisador (S53-01 e S53-02).
2. Os jobs assíncronos (S53-03) e os dois escopos, incrementais (S53-04).
3. A tela (S53-05), a medida no piloto (S53-06) e os documentos (S53-07).

**Histórias:** US-54, US-44 e US-31.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S53-01 | US-54 | Engenharia | Impressão MinHash (128 valores) sobre os k-gramas da árvore canonizada da ADR-07, calculada na etapa 2 e guardada em `fingerprints`; não reconstrói o código | Analisador, banco | Autor | 2 | Sprint 52 | Soluções com nomes trocados têm impressões próximas; a impressão não permite recuperar o código (teste) |
| S53-02 | US-54 | Engenharia | LSH sobre as impressões para os pares candidatos, com a meta de revocação: nenhum par acima de 90% perdido no corpus sintético de plágio (o da S46-01, criado aqui se a 46 ainda não rodou) | Analisador | Autor | 2 | S53-01 | Medida com o corpus sintético registrada; candidatos abaixo de 5% dos pares |
| S53-03 | US-54 | Engenharia | Jobs assíncronos no Postgres (`similarity_jobs`): criar, dividir em pedaços que cabem no prazo de uma análise, enviar ao analisador, progresso, retomada depois de reinício, um job por questão e escopo por vez; `POST /similarity/jobs` e `GET /similarity/jobs/{id}` | API | Autor | 3 | S53-02 | Testes com o relógio injetado e reinício no meio; nenhum pedaço perdido nem repetido |
| S53-04 | US-54 | Engenharia | Escopos turma e período; incremental: um código novo é comparado só com os da mesma questão e escopo; gabaritos (Notion e IP CC) e referências de IA como linhas especiais; pares a partir de 80% guardados em `similarity_pairs`, pela retenção dos períodos | API, analisador | Autor | 2 | S53-03 | 242 códigos sintéticos em três turmas: grupos certos; o incremental compara só o novo |
| S53-05 | US-44 | Engenharia | Tela de plágio com o escopo (dois códigos, turma, período), o progresso do job, os grupos acima de 90% e os trechos lado a lado; o "todos contra todos" por upload (S40-02) continua para quem não sincroniza | Página | Autor | 2 | S53-04 | Vitest e e2e |
| S53-06 | US-22 | Engenharia | Medida no piloto (0,1 CPU) contra o NFR-35, com 600 códigos sintéticos de uma questão: tempo total, candidatos e CPU; o resultado no CHANGELOG; se passar do limite, ajustar o pré-filtro antes da release | Piloto | Autor | 1 | S53-04 | Números registrados; NFR-35 cumprido ou o ajuste feito |
| S53-07 | US-20 | Documentação | ADR-18 aceita; ADR-07 revisada (escala); FR-42; NFR-35; guia ("Plágio na turma e no período"); o fechamento da S46-03 no plano da Sprint 46 | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-18 (novo); ADR-07 (revisão).

**Critérios de aceite:**
1. Dados 242 códigos da L3-Q2 em três turmas, "período" mostra o progresso e, ao fim, os grupos acima de 90% com os trechos lado a lado.
2. Um código novo na L3-Q2 entra na comparação sem refazer a matriz inteira.
3. 600 códigos de uma questão terminam em até 10 minutos no piloto; 100, em até 2 (NFR-35).
4. Nenhum par acima de 90% do corpus sintético é perdido pelo pré-filtro.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Impressões e LSH | pytest com o corpus sintético | PR | Revocação na faixa de 90%; candidatos abaixo de 5% |
| Jobs | pytest com o relógio injetado | PR | Retomada sem perda nem repetição |
| Escala | pytest com 600 códigos sintéticos e a medida no piloto | PR e antes da release | NFR-35 |
| Regressão | `scripts/ci-local.sh` | Todo PR | Verde; o resumo colado no PR |

**Deploy:** release `sprint-53`. Render e Vercel com "faça o deploy"; sem migração além das tabelas de jobs e pares (migração pelo autor); depois, o exercício de alerta e o sintético. A medida da S53-06 roda no piloto depois do deploy, com dados sintéticos, fora do horário de uso.

**Riscos:**
- O 0,1 CPU não cumpre o NFR-35: o pré-filtro fica mais estrito (menos candidatos) e o incremental dilui o custo ao longo do período.
- Grupos grandes em questões curtas (soluções convergem): o aviso de questão curta da ADR-07 aparece na tela, e o peso de base por questão (S46-02) entra quando a 46 rodar.

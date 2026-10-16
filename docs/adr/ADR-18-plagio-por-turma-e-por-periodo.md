# ADR-18 — Plágio por turma (até 100) e por período (até 600), assíncrono, com pré-filtro

**Título:** Como comparar todos os códigos de uma questão numa turma ou no período inteiro sem sair do plano gratuito.

**Status:** Proposto em 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md)), aprovado pelo autor no mesmo dia (Q-39); Sprint 53. Revisa a ADR-07 (escala) e absorve a S46-03 (100 soluções).

**Contexto:** O "todos contra todos" da S40-02 compara até 60 soluções enviadas por upload, de forma síncrona, dentro do prazo de uma requisição. As turmas de 2026.2 têm de 74 a 86 alunos, e o período soma cerca de 240; o autor pediu a comparação por turma (até 100) e por período (até 600). A comparação completa da ADR-07 é quadrática: 600 códigos são 179.700 pares, que não cabem numa requisição no plano gratuito (0,1 CPU). Com os códigos no banco (ADR-16), a comparação pode ser incremental e rodar em segundo plano.

**Decisão:**
1. **Impressão MinHash** (128 valores) de cada código, sobre os k-gramas da árvore canonizada da ADR-07, calculada na etapa 2 (ADR-19) e guardada; ela não reconstrói o código.
2. **Pré-filtro por LSH:** no escopo do período, os pares candidatos saem do LSH sobre as impressões (tipicamente menos de 5% dos pares); só eles passam pela comparação completa da ADR-07. A meta é não perder nenhum par acima de 90% no corpus sintético de plágio.
3. **Jobs assíncronos** em tabelas do Postgres: a página pede o job, a API o divide em pedaços que cabem no prazo de uma análise e os envia ao analisador, com progresso e retomada depois de reinício; um job por questão e escopo por vez. Nenhum serviço novo no Render.
4. **Incremental:** um código novo é comparado só com os da mesma questão e escopo. Os pares a partir de 80% (a faixa "Ligeiramente suspeito" do FR-29) ficam guardados pelo mesmo prazo dos códigos (NFR-31). Gabaritos (Notion e IP CC) e referências de IA entram como linhas especiais da matriz.
5. **Dois escopos novos** na tela de plágio, além dos dois códigos e do upload: turma (uma turma do Dikastis) e período (todas). Meta (NFR-35): 600 códigos em até 10 minutos no piloto; 100 em até 2.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Síncrono, como hoje, até 100 | Simples | O período não cabe; a página espera minutos |
| B. Escolhida: assíncrono, MinHash/LSH, incremental | Período inteiro no plano gratuito; o custo se dilui ao longo do período | Mais tabelas e um job a operar; o pré-filtro pode perder pares abaixo de 90% |
| C. Um serviço de fila dedicado (worker separado) | Isolamento do trabalho pesado | Serviço novo no Render, fora do plano gratuito |
| D. Comparação completa de todos os pares em lote | Sem perda | 179.700 comparações por questão a cada rodada no 0,1 CPU |

**Consequências positivas:** plágio entre turmas; grupos do período inteiro; o detector passa a trabalhar enquanto a equipe faz outra coisa.

**Consequências negativas:** pares abaixo de 80% não ficam guardados e pares entre 80% e 90% podem escapar do pré-filtro (a meta é só acima de 90%); mais tabelas e um job a monitorar; a medida real no 0,1 CPU é obrigatória antes da release (S53-06).

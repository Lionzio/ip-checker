# ADR-14 — Impressões digitais persistentes para plágio entre períodos e sinais com histórico

**Título:** O que guardar das soluções para comparar com períodos anteriores e com o histórico do próprio aluno, sem guardar o código.

**Status:** Proposto em 12/10/2026 (revisão das seis frentes, [`revisao-seis-frentes.md`](../revisao-seis-frentes.md)); Sprint 48, bloqueada pela Q-27. Depende da ADR-13.

**Contexto:** O plágio compara só o que é enviado na hora (ADR-05 e ADR-07). Não há comparação entre turmas nem entre períodos, porque nada das soluções é guardado (NFR-11). A mudança de estilo em relação ao histórico do próprio aluno é o sinal de indício mais forte da literatura. Ele ficou de fora pela REC-07 e pela ADR-08, porque exige guardar código ligado à pessoa.

**Decisão (proposta, só se a Q-27 for respondida com a opção b):**
1. Guardar, em cada registro da ADR-13, a **impressão digital** da solução: o multiconjunto de hashes de subárvores canonizadas da ADR-07, com os pesos, e os marcadores de estilo da ADR-08. Esses hashes não permitem reconstruir o código.
2. Comparar uma solução nova com as impressões da mesma questão em períodos anteriores e mostrar o resultado como indício, nunca como veredito.
3. Mostrar a mudança de estilo em relação às soluções anteriores do mesmo aluno como mais um indício, com a meta de calibração da ADR-08 (no máximo 5% de faixa alta em soluções humanas).
4. As impressões seguem a retenção da ADR-13.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Não guardar nada (situação atual) | NFR-11 e REC-07 intactos | Sem plágio entre períodos e sem sinal de histórico |
| B. Proposta: impressão digital não reversível | Habilita os dois sinais sem guardar código | Dado derivado ligado à pessoa; sem trechos lado a lado entre períodos |
| C. Guardar o código | Trechos lado a lado entre períodos | Revoga o NFR-11; risco alto de vazamento e de LGPD |

**Consequências positivas:** detecção de soluções que passam de um semestre a outro; um sinal de IA ancorado no próprio aluno.

**Consequências negativas:** a decisão reabre a REC-07 e exige base legal e o aviso de privacidade revisto. A comparação com o histórico só funciona depois de algumas listas do mesmo aluno.

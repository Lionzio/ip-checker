# Sprint 38 — Explicar cada regra e exportar o resultado

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

**Objetivo:** cada violação passa a dizer por que a construção é proibida e o que usar no lugar, o
feedback sem IA aproveita isso, e o resultado pode ser exportado e o código carregado de um arquivo.

**Missão:** que o monitor explique a violação ao aluno sem reler o documento de permissões, e que o
feedback sem IA seja bom o bastante para dispensar o "Aprimorar com IA" na maioria dos casos.

**Personas:** o monitor que dá o feedback (US-32) e o professor que mantém as regras (US-12).

**Execução:**
1. Os campos novos do ruleset (S38-01), com os textos revisados por um monitor-chefe ou professor.
2. O feedback (S38-02).
3. Exportar e carregar arquivo (S38-03).
4. O feedback sem nova análise (S38-04) e o desempenho da extração de fatos (S38-05).

**Histórias:** US-02, US-08, US-10, US-12, US-22, US-32 e US-33.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S38-01 | US-10, US-08 | Engenharia | Explicação de cada regra: campos `explicacao` (por que é proibida) e `alternativa` (o que usar nesta lista) no `base.yaml`, mostrados no cartão da violação. Os textos saem do documento de permissões, sem inventar regra; quem revisa é um monitor-chefe, um professor ou o desenvolvedor (Q-31). Rulesets `2026.2.6` e `2027.1.1` | `rulesets/*/base.yaml`, `engine/ruleset.py`, esquema JSON (S35-05), `ResultPanel.tsx` | Autor e revisor | 2 | — | Todas as regras com os dois campos; esquema e golden verdes; revisão registrada no PR |
| S38-02 | US-32 | Engenharia | O feedback sem IA usa a explicação e a alternativa de cada regra violada | `engine/feedback.py` | Autor | 1 | S38-01 | Testes do texto montado; a frase obrigatória e o `[ALUNO]` inalterados |
| S38-03 | US-02, US-33 | Engenharia | Carregar um `.py` no editor (botão e arrastar; UTF-8 de até 50 KB). Exportar o relatório: copiar como texto e baixar um `.txt` com a lista, a questão, as regras e as linhas. Nada é guardado | `frontend/src/pages/Checker.tsx`, `ResultPanel.tsx` | Autor | 1 | — | Testes de arquivo grande demais, de encoding errado e do texto exportado |
| S38-04 | US-32, US-22 | Engenharia | O feedback deixa de reanalisar o código: a API guarda em memória, por 10 min, só o resultado (nunca o código), pela chave do hash do código, da lista e da questão. "Gerar" e "Aprimorar" reaproveitam o resultado; sem ele, a API analisa como hoje | `ipc_api/routes/feedback.py`, um cache com limite de itens | Autor | 1,5 | — | Teste: o segundo "Gerar" não chama o analisador; nenhum código no cache |
| S38-05 | US-22 | Engenharia | Desempenho da extração de fatos: o `SourceMap.column` deixa de converter a linha a cada fato (atalho para linha ASCII e tabela por linha). A linha de base do benchmark é regravada | `engine/facts/model.py`, `tests/benchmark` | Autor | 0,5 | — | O benchmark mostra o ganho; nenhuma coluna diferente no golden |

**ADRs:** nenhum; o FR-30 (feedback) ganha a explicação da regra.

**Critérios de aceite:**
1. Toda violação mostra o porquê e a alternativa.
2. O feedback sem IA usa esses textos.
3. Dá para exportar o relatório e carregar um `.py`.
4. "Gerar" e "Aprimorar" não reanalisam o código.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Campos novos do ruleset | `ipc-rules validate`, esquema JSON e golden | PR | Todas as regras com os dois campos |
| Texto do feedback | pytest (`test_feedback_engine.py`) | PR | Usa a explicação; frase obrigatória e `[ALUNO]` mantidos |
| Exportar e carregar | Vitest e e2e | PR | Texto exportado correto; limites do arquivo |
| Cache do feedback | pytest | PR | O segundo pedido não chama o analisador; o cache não guarda código |
| Desempenho | benchmark (S35-01) | PR | Ganho registrado; linha de base nova |

**Deploy:** release `sprint-38`, com o ruleset novo.
- **Render:** Manual Deploy (o analisador e a API mudam).
- **Vercel:** Create Deployment (a página muda). Sem migração.
- **Depois:** sintético e exercício de alerta.

**Riscos:** os textos de explicação precisam de revisão de quem conhece o documento de permissões; sem
ela, a task fica aguardando, e o resto da sprint segue.

**Situação (15/10/2026):** engenharia concluída na release `sprint-38`: S38-01 a S38-05, num PR só. Decisões da sprint (detalhes no `CHANGELOG.md`): os campos do ruleset se chamam `explicacao` e `alternativa`, obrigatórios também nas exigências e na R-04, e a R-01 tem textos fixos no motor; o feedback sem IA usa as alternativas enquanto couberem no NFR-26; o "Aprimorar com IA" continua analisando, porque precisa do código sem comentários; o ganho do S38-05 ficou dentro do ruído (4%), e a linha de base não foi regravada. Aguardando: a revisão dos 71 pares de textos pelo autor ou pela chefia (Q-31), antes do deploy.

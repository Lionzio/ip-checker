# Sprint 46 — Plágio calibrado

Do blueprint até 15/10/2026, seção 7.16 (proposta de 12/10/2026); o plano comum está no [README](README.md).

**Objetivo:** limiares medidos, código comum descontado e a matriz da turma com trechos.

**Missão:** que a equipe saiba quanto o detector acerta (precisão e revocação) e que soluções curtas
e naturais da mesma questão não pareçam cópia.

**Personas:** o membro da equipe que compara a turma (US-44).

**Execução:**
1. O gerador de plágio sintético e a medição (S46-01).
2. O peso de base por questão e a parte explicada pelo gabarito (S46-02).
3. A matriz com grupos e trechos (S46-03), sobre a S40-02, e os documentos (S46-04).

**Histórias:** US-31, US-38 e US-44.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S46-01 | US-44 | Engenharia | Gerador de plágio sintético (variáveis renomeadas, blocos reordenados, `for` trocado por `while`, linha inerte e a combinação) sobre o corpus de `pares.yaml`, as referências e, só com `IPC_GABARITOS_DIR` na CI local, os gabaritos; `ipc-rules calibrate-plagio` imprime precisão e revocação por faixa e falha abaixo das metas (Q-32) | `backend/tests/similarity/sintetico.py`, `cli.py` | Autor | 2 | — | Relatório por faixa; gate na CI local |
| S46-02 | US-31, US-38 | Engenharia | IDF de base por questão (gabarito, referências e soluções independentes) combinado com o IDF da turma; o par mostra a parte da semelhança explicada pelo gabarito, sem descontá-la (descontar esconderia uma cópia do gabarito) | `engine/similarity_tree.py`, `routes/similarity.py`, `Plagiarism.tsx` | Autor | 2 | S46-01 | Pares independentes curtos abaixo de 80% |
| S46-03 | US-44 | Engenharia | Na matriz da S40-02, os trechos de cada par sob demanda e os grupos acima de 90% | `engine/similarity.py`, `Plagiarism.tsx` | Autor | 1 | S40-02 | Turma de 100 soluções (120 KB) em até 5 s no worker (NFR-30) |
| S46-04 | US-44 | Documentação | NFR-25 com os valores medidos; revisão da ADR-07 (IDF de base; alternativa D reavaliada com os números); seção "Plágio" em `docs/eficacia.md` | docs | Autor | 1 | S46-01 | Revisão |

**ADRs:** ADR-07 (revisão).

**Critérios de aceite:**
1. A medição mostra revocação ≥ 95% na faixa de 90% para as três transformações e precisão de 100% na faixa de 95% (Q-32).
2. A turma sintética de 30 soluções tem os dois grupos achados e nenhum independente acima de 90%.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Precisão e revocação | `ipc-rules calibrate-plagio` | PR que toca o plágio | Metas da Q-32 |
| Peso de base | pytest | PR | Independentes curtos abaixo de 80% |
| Matriz e orçamento | pytest | PR | 100 soluções em até 5 s |

**Deploy:** release `sprint-46`. Render e Vercel.

**Riscos:** o corpus de independentes é pequeno até chegarem as soluções anteriores a 2023 (P-21);
os números da primeira medição são provisórios.

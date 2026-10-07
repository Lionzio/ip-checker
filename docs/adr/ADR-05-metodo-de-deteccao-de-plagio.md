# ADR-05 — Método de detecção de plágio

**Título:** Similaridade por *winnowing* sobre tokens normalizados e sobre a sequência de nós da AST, calculada no analisador isolado.

**Status:** Proposto e implementado em 02/10/2026 (Sprint 17), com a calibração do item 6.

**Contexto:** O FR-29 exige resistência a renomear identificadores, mudar o espaçamento, mexer em comentários e reordenar trechos independentes, com faixas fixas de classificação. Os dois códigos são de alunos e não são confiáveis; tokenizá-los já é processá-los, então a comparação fica no `analyzer` (ADR-01).

**Decisão:**
1. Normalização com `tokenize`: saem comentários, linhas em branco e espaços redundantes; os nomes ligados pelo aluno (variáveis, funções e parâmetros), coletados pelo `symbols.py`, viram marcadores numerados por ordem de aparição; built-ins, métodos e palavras-chave ficam como estão; o conteúdo das strings vira `STR`.
2. Métrica A, com peso 0,6: *fingerprints* por *winnowing* (k-gramas de 5 tokens e janela de 4, como no MOSS) e coeficiente de Dice entre os dois conjuntos.
3. Métrica B, com peso 0,4: o mesmo *winnowing* sobre a sequência de tipos de nó da AST, que ignora nomes e literais e capta a estrutura.
4. *Score* = 0,6 · A + 0,4 · B, em porcentagem com uma casa decimal. Pesos, k e janela ficam documentados no código e são recalibrados no corpus de pares (NFR-25). Códigos com menos de k tokens são comparados diretamente pela sequência normalizada.
5. Os dois códigos precisam ser sintaticamente válidos; senão, a resposta diz qual deles tem erro e onde.
6. Calibração no corpus de pares (Sprint 17): as duas sequências são separadas por comando do nível do módulo, os k-gramas não atravessam dois comandos, e a numeração dos marcadores recomeça em cada um. Com a numeração e os k-gramas no arquivo inteiro, reordenar três funções dava 86,8%, abaixo dos 90% do NFR-25; por bloco, dá 100%. Um comando menor que k vira um *fingerprint* só. Os nomes lidos mas nunca ligados pelo aluno ficam como estão, porque o `symbols.py` não os reconhece como dele.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: *winnowing* em tokens e em nós da AST | Linear no tamanho do código, resistente a renomeação e reordenação, sem dependências | Pesos e parâmetros exigem calibração |
| B. `difflib.SequenceMatcher` sobre tokens | Simples | Sensível à reordenação e quadrático no pior caso |
| C. *Greedy String Tiling* (JPlag) | Muito bom contra reordenação | Mais complexo e caro no pior caso de 50 KB |
| D. MOSS ou JPlag como serviço | Referência na área | Envia o código a terceiros ou exige Java; o MOSS precisa de conta e não garante disponibilidade |
| E. Similaridade por *embeddings* de LLM | Capta semelhança semântica | Não determinística, cara, envia o código a terceiros e é difícil de explicar a um aluno |

**Consequências positivas:** resultado determinístico e explicável, sem rede nem segredo no caminho e dentro do isolamento existente.

**Consequências negativas:** exercícios curtos geram similaridade alta entre soluções independentes (ameaça 20); só cobre Python.

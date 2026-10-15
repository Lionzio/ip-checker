# ADR-07 — Plágio por árvore canonizada, insensível à ordem

**Título:** Similaridade sobre a AST canonizada (formas equivalentes reescritas numa só), com reordenação por dependência de dados e comparação de subárvores, no lugar do *winnowing* sobre a sequência de tokens.

**Status:** Proposto em 06/10/2026 (revisão de fim da Sprint 23); implementado na Sprint 27 (06/10/2026), com as decisões registradas na Situação da Sprint 27 (seção 7.11).

**Contexto:** O motor da ADR-05 já resiste a renomear variáveis e a reordenar funções inteiras, mas compara sequências: qualquer mudança de ordem dentro de um bloco, ou uma forma equivalente, quebra os k-gramas. Medido em 06/10/2026 com uma função de média copiada e reescrita:

| Reescrita da cópia | Motor atual (ADR-05) | Protótipo desta ADR |
|---|---|---|
| Só nomes trocados | 100,0% | 100,0% |
| Duas linhas independentes trocadas de lugar | 59,2% | 100,0% |
| `if` invertido (`!=` e ramos trocados) | 72,8% | 100,0% |
| `x += 1` reescrito como `x = x + 1` | 67,6% | 100,0% |
| Operandos de `==` trocados | 74,1% | 100,0% |
| Código morto acrescentado (enchimento) | 74,0% | 72,6% (Dice) / 100,0% (contenção) |
| `for` reescrito como `while` com índice | 51,6% | 40,0% (contenção) |
| Solução independente da mesma questão | 18,0% | 0,0% |

Todas as cópias reescritas ficavam abaixo de 80%, a faixa "sem indício" do FR-29. O Python já tem um parser exato da gramática (o `ast`, o mesmo que o motor usa); um parser novo (tree-sitter, LibCST) não acrescenta poder de comparação. O ganho está nas camadas de normalização sobre a árvore.

**Decisão (proposta):**
1. **Canonização da AST**, no analisador isolado: nomes do aluno viram marcadores; `x op= y` vira `x = x op y`; operandos de operadores comutativos (`+`, `*`, `and`, `or`, `==`, `!=`) ficam em ordem canônica pelo hash da subárvore; `a > b` vira `b < a`; `if not c` e `!=` viram a forma positiva com os ramos trocados; `if c: return X` seguido do resto vira `if c: return X else: resto`; `for` e `while` viram um nó de laço genérico.
2. **Reordenação por dependência:** em cada bloco, comandos vizinhos sem dependência de dados entre si (definição e uso de nomes, sem controle de fluxo no meio) são ordenados pelo hash canônico, numa ordenação topológica determinística. Trocar a ordem de linhas independentes deixa de mudar a árvore.
3. **Padrões de laço** reconhecidos e reescritos numa forma só: `for x in v` ≡ `i = 0; while i < len(v): x = v[i] ... i += 1`, e `for i in range(len(v))` com `v[i]`.
4. **Comparação:** o multiconjunto dos hashes de todas as subárvores com 3 ou mais nós, cada uma pesada pelo seu tamanho (como na detecção de clones Deckard), com dois números: **Dice**, a similaridade, e **contenção** (o quanto do menor código está no maior), que denuncia o enchimento com código morto. A classificação do FR-29 usa o maior dos dois, e a tela mostra os dois.
5. **Uma contra várias:** comparar uma solução com as da turma, em memória, e pesar cada subárvore pelo inverso da sua frequência na turma (IDF). O que todos escrevem (a leitura da entrada, o laço óbvio) quase não conta, o que resolve a ameaça 20 dos exercícios curtos.
6. **Trechos:** a resposta traz os pares de intervalos de linhas que coincidem, para o painel realçar os dois códigos lado a lado.
7. O motor da ADR-05 continua como segunda métrica até o novo ser calibrado no corpus de pares (NFR-25), ampliado com cada reescrita da tabela acima e com soluções independentes de períodos anteriores.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Proposta: AST canonizada + reordenação por dependência + subárvores | Insensível à ordem e às formas equivalentes, determinística, linear no tamanho, explicável por trechos | A canonização aproxima soluções independentes de exercícios curtos; exige calibração e o IDF da turma |
| B. Grafo de dependência de programa (PDG) com isomorfismo de subgrafos (GPLAG) | O mais resistente a reordenação | Isomorfismo é caro (NP-difícil no geral); difícil de explicar e de manter por um monitor |
| C. Distância de edição de árvores (Zhang-Shasha, APTED) | Mede a diferença exata entre duas árvores | Cúbica no tamanho; só viável por função, como desempate |
| D. *Hash* de Weisfeiler-Lehman sobre o grafo de fluxo de controle | Compara a estrutura de decisões, ignora a ordem | Perde os detalhes das expressões; bom como terceira métrica |
| E. Um parser novo (tree-sitter, LibCST) | Multilinguagem; LibCST preserva formatação | Não acrescenta nada à comparação de Python; dependência nova |
| F. *Embeddings* de LLM | Captam semelhança semântica | Não determinísticos, enviam o código a terceiros, difíceis de explicar (como na ADR-05) |

**Consequências positivas:** cópias disfarçadas por reordenação e por formas equivalentes passam a cair em "Plágio"; o enchimento com código morto aparece na contenção; os trechos realçados explicam o número.

**Consequências negativas:** soluções independentes de exercícios muito curtos ficam mais parecidas (a canonização junta formas diferentes), o que torna o IDF da turma e o aviso de código curto obrigatórios; mais código no motor para manter.

## Revisão da S35-07 (11/10/2026): linhas inseridas dentro de um bloco copiado

**Achado:** ao montar o roteiro de testes manuais (`docs/testes-manuais.md`), uma cópia com **uma
linha acrescentada dentro do laço** deu 83,2% ("Ligeiramente suspeito", cenário P-11), e com um
`else` e um contador acrescentados, 76,1% ("Sem suspeitas", P-12). O motivo: o multiconjunto pesava
cada subárvore pelo tamanho, e uma linha a mais dentro de um laço muda o hash do laço inteiro e de
todos os blocos acima dele, justamente os de maior peso. Linhas acrescentadas antes ou depois do
trecho copiado não enganavam (contenção de 100%, P-08).

**Decisão:** um comando com blocos (`if`, laço, `def`, `with`, `try`) deixa de entrar inteiro no
multiconjunto. Entram:

1. o **cabeçalho** dele (o comando sem os blocos: a condição, o que o laço percorre, a assinatura),
   com o peso do cabeçalho;
2. cada **comando de dentro**, junto com o cabeçalho, o nome do bloco (`body`, `orelse`, `except`...)
   e o **comando anterior** do mesmo bloco, com o peso do comando. Um bloco dentro de outro entra
   pelo cabeçalho dele.

Os hashes exatos (e, com eles, os trechos em comum, a reordenação por dependência e as reescritas)
não mudam. Com o comando anterior no par, a ordem que a reordenação por dependência mantém
continua contando (ler as entradas em outra ordem ainda é diferença), e uma linha inserida só
desfaz um par.

**Medido em 11/10/2026**, no corpus de pares e nos cenários do roteiro:

| Par | Antes | Depois |
|---|---|---|
| Linha acrescentada dentro do laço (P-11) | 83,2% | 100,0% (contenção; Dice 94,9%) |
| `else` e contador acrescentados no laço (P-12) | 76,1% | 100,0% (contenção; Dice 88,4%) |
| As 14 cópias do corpus | 100,0% | 100,0% |
| Soluções independentes do corpus (6 pares) | de 0,0% a 22,1% | iguais (uma subiu de 6,6% para 11,0%) |
| Três independentes novas, uma com o mesmo laço e outra conta | 0,0%, 32,2% e 58,3% | iguais |

Os cinco pares novos entram no corpus (`tests/similarity/pares.yaml`), com mínimo de 95% para as
duas cópias e máximo de 79,9% para as três independentes.


## Revisão da S40-02 (15/10/2026): todos contra todos

**Contexto:** o "Contra a turma" (S27-02) compara uma solução com até 100 da turma; para achar quem
copiou de quem numa lista inteira, o monitor precisava repetir a comparação aluno por aluno.

**Decisão:** o motor ganha o `compare_all`, que compara cada solução com todas as outras, com o mesmo
multiconjunto, a mesma árvore e o mesmo IDF da turma inteira do "Contra a turma" (o que toda a
turma escreve quase não conta). Além dos pares, do mais parecido para o menos, ele devolve os
**grupos**: os componentes ligados por pares a partir de "Requer atenção" (90%), por *union-find*.
A ligação é transitiva de propósito: se A parece com B e B com C, os três aparecem juntos, mesmo
que A e C não passem da faixa, porque é assim que uma cópia passa de mão em mão. O grupo só aponta
o que ler; a decisão continua sendo do monitor, no lado a lado.

**Limites:** de 2 a 60 soluções e 120 KB juntas (1.770 pares); a API devolve os 200 pares mais
parecidos. Medido em 15/10/2026 na máquina do autor: 60 soluções de 1,2 KB em 0,35 s, dentro dos
10 s do analisador para a turma, com folga para a 0,1 CPU do piloto. As 100 soluções do NFR-30
ficam para a S46-03.

**Teste:** uma turma sintética de 30 soluções, com dois grupos de cópias disfarçadas (nomes
trocados, ordem das entradas, `elif` reescrito) e o resto independente; os dois grupos são achados,
e nenhuma solução independente entra neles (`tests/test_similarity_matrix.py`).

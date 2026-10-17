# ADR-08 — Indícios de uso de IA, nunca veredito

**Título:** Painel de indícios explicáveis de uso de IA, calibrado em soluções humanas, com a conversa com o aluno como a única confirmação.

**Status:** Aceito em 06/10/2026 (Q-21), com o sinal de múltiplas violações pedido pelo autor; implementado na Sprint 29 (07/10/2026), desligado no piloto até a calibração ficar na meta (S33-03); a política (`docs/indicios-de-ia.md`) foi aprovada em 09/10/2026. **Medição preliminar (11/10/2026, S33-03):** nos 23 gabaritos oficiais de 2026.2 (Listas 1 a 3), `ipc-rules calibrate` deu 100% na faixa "nenhum" e 0% na alta. É só um primeiro ponto: as soluções oficiais seguem as regras por construção, e a calibração que liga os indícios no piloto continua dependendo das soluções humanas da S33-02. **Calibração da Q-35 (17/10/2026, Sprint 42.1):** com as 102 referências geradas a partir dos enunciados do catálogo, os 28 gabaritos de 2026.2 ficam fora da faixa alta (2 na média e 1 na baixa, depois de remover as 8 referências que repetiam o gabarito) e 83,0% das 206 soluções novas geradas por IA caem na média ou alta (meta: 50%). As faixas não mudaram. Pronto para ligar para a chefia (`IPC_AI_INDICATORS: chefia`) com o deploy da `sprint-42.1`.

**Revisão (12/10/2026):** o autor descartou as soluções anteriores a 2023 que a calibração usaria (S33-02) e pediu os indícios ligados no piloto (Sprint 42). O autor aprovou no mesmo dia os critérios e a nova base de calibração (Q-35, `docs/indicios-de-ia.md`): a repetição da mesma proibição vai no máximo à faixa média, entram dois marcadores sem faixa (texto dentro do `input()` e validação de entrada não pedida), e a calibração usa os gabaritos da equipe e soluções novas geradas por IA. O painel continua desligado no piloto até a Sprint 42.

**Sprint 42 (16/10/2026):** os critérios da Q-35 entraram no motor (S42-03), com a evidência (regra
ou marcador, linhas e trecho) e a confiança, separada da faixa, em cada indício; o painel liga por
cargo, `IPC_AI_INDICATORS` = `0`, `chefia` ou `1` (S42-05); as referências de IA valem também para
as questões só com gabarito, e há um gerador a partir só do enunciado (S42-04); `ipc-rules
calibrate` mede a base da Q-35 (S42-02). **Calibração, alarmes falsos (16/10/2026):** nos 28
gabaritos de 2026.2 (Listas 1 a 4), 28 na faixa "nenhum" e 0 na alta, meta cumprida. **Acertos:**
esperam as soluções geradas por IA (os enunciados e as chaves das IAs, com o autor). O piloto segue
em `0` até as duas metas.

**Contexto:** O uso frequente de proibições já é o principal indício que a equipe usa (P-13). Detectores genéricos de texto gerado por IA não servem para código de alunos de introdução: o código é curto, convergente (muitas soluções corretas são quase iguais) e parecido com o que um modelo escreve; esses detectores têm muitos falsos positivos, penalizam quem escreve bem ou estudou fora, e a própria OpenAI retirou o seu classificador em 2023 por baixa precisão. Não há marca d'água nas respostas dos assistentes que a equipe possa conferir.

**Decisão (proposta):**
1. **Sinal 1, múltiplas violações (pedido do autor, Q-21):** o padrão das violações que o motor já encontra, sem análise nova do código, medido de quatro formas e mostrado com as linhas de cada ocorrência:
   - **Variedade de proibições gerais:** quantas regras diferentes entre R-05 e R-14 aparecem juntas (por exemplo `break`, `pass` e `continue` no mesmo código).
   - **Repetição:** a mesma proibição várias vezes (por exemplo vários `pass`).
   - **Salto de lista:** construções liberadas só duas ou mais listas depois da escolhida, com a quantidade e a distância (por exemplo permissões da Lista 6 numa solução da Lista 3, que saltam 3 listas).
   - **Fora do documento e incomum para o nível:** violações R-04 e construções como anotações de tipo, docstrings, `if __name__` e especificadores de formato, comparadas com a turma.
   As faixas (nenhum, baixo, médio, alto) começam com valores iniciais [PREMISSA: alto com 3 ou mais proibições gerais diferentes, 3 ou mais repetições da mesma, ou 2 ou mais construções com salto de 2 listas ou mais] e são calibradas como no item 5. Este é o sinal mais barato e o primeiro a entrar (S29-01).
2. **Sinal 2, semelhança com soluções de referência geradas por IA:** para cada questão, a equipe gera algumas soluções com 2 ou 3 assistentes, a partir só do enunciado, e as guarda num repositório privado, como os gabaritos (Q-14). O motor de plágio da ADR-07 compara a solução do aluno com elas e mostra a mais parecida, com os trechos. Nenhum dado do aluno sai do servidor.
3. **Sinal 3, marcadores de estilo:** identificadores e comentários em inglês num curso em português, tratamento de erros e validações que a questão não pede. São mostrados como fatos, sem peso automático, porque alguns alunos escrevem assim por conta própria.
4. **Linguagem e decisão:** a tela diz "indícios" e "vale conversar com o aluno", nunca "gerado por IA". Não há punição automática: a confirmação é uma conversa em que o aluno explica ou modifica o próprio código. O IP-Checker pode sugerir 2 ou 3 perguntas sobre o código para essa conversa.
5. **Calibração e justiça:** antes de ligar, medir a taxa de falsos positivos em soluções de períodos anteriores a 2023 (humanas por definição). Meta: até 5% delas com indício "alto". Revisar a cada período, com os casos confirmados e descartados.
6. **Privacidade:** nada é guardado além do que já se guarda; comparar com o histórico do próprio aluno fica fora (REC-07).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Proposta: indícios explicáveis + referências de IA por questão + conversa | Explicável, determinística, sem enviar dado do aluno, calibrável | Gerar as referências dá trabalho a cada questão; um aluno que reescreve o código gerado escapa |
| B. Detector comercial de texto de IA | Pronto | Pouco confiável em código, injusto, envia o código a terceiros |
| C. Perguntar a uma LLM se o código foi gerado por IA | Simples | Não determinístico, sem base verificável; a LLM não sabe responder isso |
| D. Estilometria contra o histórico do aluno | O sinal mais forte na literatura | Exige guardar o código ligado à pessoa (REC-07) |
| E. Não fazer nada além das proibições | Zero risco de injustiça nova | Perde as referências por questão, que são baratas de comparar |

**Consequências positivas:** a equipe ganha um motivo concreto para conversar com o aluno, sem acusações por um número.

**Consequências negativas:** custo de gerar referências por questão; os indícios precisam de calibração contínua; o painel pode ser mal interpretado como prova se a linguagem não for cuidadosa.

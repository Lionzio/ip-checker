# ADR-11 — Comparação com o gabarito na verificação, no plágio e nos indícios

**Título:** Como o código do aluno é comparado com o gabarito oficial da questão, sem que o gabarito saia do servidor.

**Status:** Proposto em 09/10/2026, com as escolhas do autor (Q-24: 1B, 2B, 3A, 4B, 5A, 6B). Implementação na Sprint 32 (seção 7.12 do blueprint); vira Aceito quando a sprint fechar.

**Contexto:** O autor pediu que a verificação mostre uma análise comparativa entre o código do aluno e o gabarito da questão escolhida, e que o painel de plágio compare os dois alunos também com o gabarito, para sinalizar um possível vazamento do gabarito (US-37, US-38). Os gabaritos ficam no repositório privado `Lionzio/ip-checker-gabaritos` (ADR-10) e, pelo NFR-27 até 09/10/2026, nunca entravam no repositório principal, na imagem do piloto nem nos logs. O motor já compara uma submissão com soluções guardadas por questão: o sinal "referência por IA" dos indícios usa a métrica da ADR-07 (`compare_prepared`) contra `rulesets/<período>/referencias/` (S29-02). O analisador roda isolado, sem rede (ADR-01), e nada do código do aluno é guardado (NFR-11). Hoje há um período ativo só (a troca sem código vem na S31-09 e na S31-10) e nenhuma questão cadastrada no ruleset.

**Decisão:**
1. **Onde o gabarito fica em produção (Q-24, 1B):** a API baixa o repositório dos gabaritos ao subir, pela API do GitHub por HTTPS, com uma credencial só de leitura restrita a esse repositório (`IPC_GABARITOS_TOKEN`, cadastrada pelo autor no Render; `IPC_GABARITOS_REPO`), e guarda os arquivos **só na memória do processo da API**: nunca em disco, na imagem, no log, na telemetria ou no navegador. Limites de tamanho por arquivo e no total. Sem credencial ou com falha no download, a comparação fica desligada, com um aviso na página, e o resto da API segue normal (`/ready` não depende dela).
2. **Quem compara:** o analisador, sem rede, recebe o gabarito da questão no corpo da chamada interna, como já recebe o código, e reaproveita a preparação por hash (cache em memória do worker).
3. **O que a página mostra (Q-24, 2B):** a porcentagem e a faixa do FR-29, as construções em comum, só no aluno e só no gabarito (pelos fatos do motor), e as **linhas do aluno** que coincidem com o gabarito. Nenhum texto do gabarito sai do servidor.
4. **Como a análise é escrita (Q-24, 3A):** de forma determinística, a partir da AST e da métrica da ADR-07; sem IA (a Q-16 segue pendente). Nos indícios de IA (ADR-08), a semelhança com o gabarito entra como mais um sinal, só quando `IPC_AI_INDICATORS` estiver ligado.
5. **Alerta de possível vazamento (Q-24, 4B):** no plágio, com a questão escolhida, o alerta aparece só se o aluno A e o aluno B passarem do limiar com o gabarito **e** entre si, e se os dois códigos tiverem um tamanho mínimo; abaixo disso, só as porcentagens. Limiar inicial de 95% e tamanho mínimo [PREMISSA, configuráveis; calibrados com soluções reais, S33-02]. O alerta aparece só para quem fez a verificação, não é registrado e diz que os códigos coincidem com o gabarito, não quem o vazou.
6. **Períodos e questões (Q-24, 5A):** o seletor lista as questões do período ativo que têm gabarito, mesmo sem regras cadastradas (com o aviso de que as regras da questão não se aplicam); vários períodos ao mesmo tempo só depois da S31-09 e da S31-10. Questão sem gabarito: a verificação segue normal, com o aviso "sem gabarito para comparar".
7. **Sprint (Q-24, 6B):** nova Sprint 32, depois da Sprint 31; as Sprints 32 a 35 de 07/10/2026 passam a 33 a 36.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Só no ambiente local | NFR-27 intacto | Os monitores não teriam a função no piloto |
| B. Escolhida: download pela API, só em memória | Fora da imagem e do repositório; revogável; atualiza sem deploy | Credencial nova no Render; o NFR-27 passa a admitir a memória da API |
| C. Gabaritos empacotados na imagem | Simples | Viola o NFR-27; o gabarito fica guardado no Render |
| D. Análise comparativa por IA | Texto mais natural | Depende da Q-16; envia código a terceiros |
| E. Alerta pelas faixas do FR-29 (≥ 95%) | Mesma métrica | Falsos positivos nas questões curtas, que se parecem com o gabarito por natureza |

**Consequências positivas:** a equipe vê na hora quanto o código do aluno se afasta da solução oficial e em quê; um gabarito que circula entre os alunos aparece no plágio sem nenhum dado novo guardado.

**Consequências negativas:** uma credencial a mais para trocar (runbook); a API passa a guardar respostas oficiais na memória; o limiar do alerta é uma premissa até a calibração; uma reinicialização do Render é necessária para carregar gabaritos novos (ou uma rota de recarga, a avaliar na sprint).

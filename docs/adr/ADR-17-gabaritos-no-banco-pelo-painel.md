# ADR-17 — Gabaritos no banco, até dois por questão, cadastrados pelo painel

**Título:** Onde os gabaritos ficam, quem os cadastra e como dois gabaritos válidos convivem.

**Status:** Proposto em 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md)), aprovado pelo autor no mesmo dia (Q-40); Sprint 51. Revisa a ADR-10 (item 2: o repositório privado de gabaritos) e a ADR-11 (item 2: quem vê o gabarito).

**Contexto:** Os gabaritos ficam no repositório privado `ip-checker-gabaritos`, editado só pelo autor por Git, e a API os baixa do GitHub com um token. Cadastrar um gabarito exige clonar, copiar o arquivo, rodar o harness e abrir um PR. A monitoria tem duas fontes de gabarito, igualmente válidas e às vezes diferentes: a página do Notion e a solução enviada pela conta IP CC UFPE no Dikastis. O autor pediu um painel com cliques para a chefia cadastrar os dois e perguntou se o repositório de gabaritos deve entrar no repositório principal.

**Decisão:**
1. **O banco é a fonte da verdade:** tabela `gabaritos` com até dois registros por questão, `notion` e `ip_cc`, com quem cadastrou, quando e as violações encontradas ao salvar.
2. **Cadastro pelo painel, pela chefia:** a tela "Gabaritos" (período → lista → questão) tem dois cartões, "Gabarito Notion" e "Gabarito IP CC", onde a chefia cola ou arrasta o `.py`. Ao salvar, o analisador roda o gabarito com as regras do período e da questão, e o painel mostra na hora "sem violação" ou as regras e linhas acionadas, com a pergunta "o enunciado libera?". O cartão IP CC pode ser preenchido pela extensão com a última submissão aceita da conta IP CC UFPE (marcada "veio do Dikastis", editável), se essa conta enviar soluções.
3. **Os dois são igualmente válidos:** na comparação com o gabarito (ADR-11), vale o mais parecido com o código do aluno, e o resultado diz qual; no alerta de possível vazamento, basta um.
4. **O repositório de gabaritos não entra no principal.** Ele vira arquivo somente leitura: os 28 gabaritos de 2026.2 entram no banco como `notion`; `ipc-rules export-gabaritos` gera a mesma árvore a partir do banco para o harness da CI; a API deixa de baixar do GitHub, e `IPC_GABARITOS_TOKEN` sai do Render.
5. **Quem vê o código do gabarito:** só a chefia e o desenvolvedor; o monitor vê a existência, a data e a comparação, nunca o texto (revisa a ADR-11, item 2, que já proibia o gabarito no navegador do monitor).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Continuar no repositório privado, por Git | Nada muda | Só o autor cadastra; minutos viram horas; sem o segundo gabarito |
| B. Juntar o repositório de gabaritos ao principal | Um repositório só | O principal é lido por mais gente e ferramentas (agentes, CI, imagem, futuros mantenedores); um gabarito no histórico do Git não sai mais (P-13, ADR-10) |
| C. Escolhida: banco, pelo painel, com o repositório como arquivo | A chefia cadastra em um minuto; validação ao salvar; dois tipos; o harness continua pelo export | Gabaritos entram nos backups (já cifrados) e na retenção dos períodos |
| D. Extrair do Notion automaticamente | Sem colar | Depende da API do Notion e de um conector; o autor dispensou |

**Consequências positivas:** cadastro em minutos pela chefia; a validação no momento certo; o segundo gabarito melhora a comparação e o alerta; o Render perde um segredo.

**Consequências negativas:** a confidencialidade dos gabaritos passa a depender do banco e dos backups (cifrados) e das permissões por cargo, testadas por chamada direta; o repositório antigo precisa de um README claro para ninguém cadastrar lá por engano.

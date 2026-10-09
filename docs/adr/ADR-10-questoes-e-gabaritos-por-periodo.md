# ADR-10 — Questões e gabaritos por período

**Título:** Onde ficam as regras das questões e os gabaritos de cada período, e como se troca de período.

**Status:** Aceito em 08/10/2026 (decisão de engenharia sobre a Q-14, já aprovada pelo autor). O repositório dos gabaritos e a chave da CI foram criados no mesmo dia; a troca de período por um arquivo (S31-09), o `ipc-rules new-period` (S31-10) e os gabaritos com as questões do próprio período (S31-11) entram na Sprint 31.

**Revisão (09/10/2026):** a ADR-11 permite que a API do piloto baixe os gabaritos e os guarde só em memória, para a comparação com o gabarito (Q-24); eles continuam fora do repositório principal, da imagem, do disco, dos logs e do navegador. Os dois repositórios continuam (decisão do autor de 09/10/2026).

**Contexto:** A numeração das questões reinicia a cada período (P-07), e as regras de cada questão (R-01) mudam com os enunciados. Os enunciados ficam no Dikastis e os gabaritos oficiais no Notion (Q-14). O ruleset precisa de revisão por PR com professor ou monitor-chefe (C-02, `RULES.md`), histórico e validação no CI (FR-21), e o analisador isolado não acessa banco nem rede (ADR-01). Os gabaritos são respostas oficiais: não podem ir para o repositório principal, para a imagem do piloto nem para os logs. Até 08/10/2026, o período ativo estava escrito em dois arquivos (`deploy/render/supervisord.conf` e `backend/Dockerfile`), e o teste dos gabaritos só usava as questões do período ativo.

**Decisão:**
1. **Questões são arquivos versionados, por período, no repositório principal:** `rulesets/<período>/base.yaml`, `rulesets/<período>/questions/L<lista>-Q<n>.yaml` e `rulesets/<período>/referencias/`. Não há banco de dados de questões: o Git dá a revisão por PR, o histórico e o hash do ruleset (`ruleset_version`), e o analisador lê os arquivos sem rede. A pasta de um período encerrado continua no repositório.
2. **Gabaritos ficam num repositório privado separado,** `Lionzio/ip-checker-gabaritos`, em `<período>/lista-<n>/L<n>-Q<m>.py`, com acesso só da equipe da disciplina. A CI o baixa com uma **chave de implantação só de leitura** (segredo `GABARITOS_SSH_KEY`), restrita a esse repositório e sem validade a renovar, no lugar do token pessoal previsto na S20. O job só roda com a variável `GABARITOS_REPO`, e os testes mostram arquivo, regra e linha, nunca o código.
3. **Trocar de período é mudar um arquivo** (S31-09): o período ativo fica num só lugar, e o deploy, o compose e a CI o leem dali. Um período novo nasce com `ipc-rules new-period <novo> --from <anterior>` (S31-10).
4. **Cada gabarito é conferido com as questões do próprio período** (S31-11), quando a pasta dele existe no repositório; o `excecoes.yaml` fica para períodos sem as questões cadastradas.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: arquivos por período no Git e gabaritos num repositório privado | Revisão por PR, histórico, validação no CI, nada de rede no analisador | Cadastrar exige um PR (o `RULES.md` ensina, e dá para fazer pelo navegador) |
| B. Banco de dados de questões, com tela de cadastro | Cadastro sem Git | Tela, permissões e migrações novas; perde a revisão por PR e o hash; o analisador teria de ler do banco (contra a ADR-01) |
| C. Gabaritos numa pasta ignorada do repositório principal | Um repositório só | Fácil de publicar por engano; sem controle de acesso separado |
| D. Token pessoal (fine-grained) para a CI | O que a S20 previa | Expira, fica ligado à conta de uma pessoa e só pode ser criado pela tela do GitHub |

**Consequências positivas:** começar um período é rápido e revisável; os gabaritos de cada período encerrado passam a proteger os seguintes contra falsos positivos; a CI acessa só o repositório dos gabaritos, só para leitura.

**Consequências negativas:** a equipe precisa de conta no GitHub para cadastrar questões e gabaritos; quem sai da equipe precisa ser removido dos colaboradores dos dois repositórios, e a chave da CI trocada se alguém da equipe técnica sair (`rulesets/README.md`).

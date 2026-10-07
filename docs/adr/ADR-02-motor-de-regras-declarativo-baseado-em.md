# ADR-02 — Motor de regras declarativo baseado em fatos

**Por que está entre as três mais críticas:** é o ponto que decide se a ferramenta é fiel ao documento de permissões (prioridade 2 do projeto), e foi a falha nº 1 do rascunho.

**Título:** Ruleset versionado em YAML com JSON Schema, avaliado sobre um vocabulário fechado de fatos e uma biblioteca de predicados, com *default deny* por fato.

**Status:** Aceito.

**Contexto:** O catálogo combina permissões cumulativas (R-03), *default deny* (R-04), proibições gerais com anulação (R-05…R-14), uma permissão condicional (R-37), exigências (R-02 e R-68) e precedência da questão (R-01). O esquema do rascunho (`allowed_from_list` e `ast_nodes`) não expressa quatro desses seis mecanismos, e o *default deny* por classe de nó deixa passar `eval` e `getattr` (1.2 #1). Professores e monitores rotativos precisam mudar regras sem programar (US-12).

**Decisão:** Adotar o formato e o algoritmo de 5.2.3:
- os IDs do ruleset são os R-xx do catálogo;
- cada regra tem `effect`, `since_list`/`until_list`, `match` (lista de fatos), `when` (predicado da biblioteca) e `message`;
- as exigências ficam em `requirements`;
- os overrides de questão ficam em arquivos por `question_id`;
- o ruleset é compilado e carregado imutável, com *fail-fast*;
- a CI valida schema, referências e corpus golden (FR-21);
- O ruleset base precisa da aprovação de professor, e os arquivos de questão, de monitor-chefe ou professor, sem autoaprovação; overrides que liberam R-05…R-14 exigem professor (C-02, Q-08). Desde a Q-22 (adiada), quem faz o merge confere essa aprovação pelo `RULES.md` e pelo modelo de PR de regras: o GitHub Free não aplica CODEOWNERS em repositório privado.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: ruleset declarativo sobre fatos | Representa todos os mecanismos do catálogo. Mudar regras não exige código (NFR-17). O *default deny* granular fecha a evasão dinâmica. É auditável por PR | Depende da matriz de mapeamento (validada nas decisões Q-02 a Q-07). Um fato ou predicado novo exige código e um ADR |
| B. Esquema do rascunho com métodos `visit_*` por regra | Simples de começar | Não expressa R-01, R-02, R-37 nem R-68. Deixa passar built-ins e métodos não catalogados. Toda regra nova é código |
| C. Motor de terceiros (regras Semgrep ou OPA/Rego) | Linguagem de regras madura e com ferramentas | O Semgrep foi feito para lista de bloqueio, não para lista de permissão cumulativa, e seu runtime custa centenas de ms por chamada. O OPA acrescenta uma linguagem e um runtime a mais para a equipe |
| D. Regras em banco de dados, com UI de administração | O professor edita sem Git | Exige autenticação, autorização e UI, que estão fora do escopo. Perde a revisão por PR e o gate de testes golden |

**Consequências positivas:** o veredito pode ser rastreado até o R-xx e a página do documento. Adicionar uma lista ou uma questão é um PR só de dados. O corpus golden funciona como especificação executável do documento.

**Consequências negativas:** a semântica depende da qualidade da matriz de mapeamento. Casos ambíguos novos, não cobertos pelas decisões Q-02 a Q-07, exigem decisão registrada antes de entrar no ruleset. Há uma curva de aprendizado do vocabulário de fatos para os mantenedores.

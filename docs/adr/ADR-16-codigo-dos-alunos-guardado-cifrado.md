# ADR-16 — Código dos alunos guardado, cifrado, por 6 períodos

**Título:** O que o IP-Checker passa a guardar das soluções dos alunos, por quanto tempo, com que proteção e com que base legal.

**Status:** Proposto em 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md)), aprovado pelo autor no mesmo dia (Q-37 e Q-38), com a autorização dos professores e dos monitores-chefes; Sprint 52. Revisa a Q-27 (que guardava só o resultado resumido), o NFR-11 ("o código não persiste") e a ADR-13 (que convive com esta); retoma, em outra forma, a alternativa C da ADR-14 (rejeitada em 12/10/2026). Vai ao piloto só com o aviso aos alunos publicado e a ciência do encarregado de dados da UFPE.

**Contexto:** Até aqui, nada das soluções era guardado (NFR-11, REC-07): o plágio comparava só o que era enviado na hora, e a Q-27 limitou o histórico ao resultado resumido. A integração com o Dikastis (ADR-15) traz o último código de cada aluno em cada questão, o que permite a correção da turma sem colar nada, o plágio por turma e por período (ADR-18) e, no futuro, o plágio entre períodos. O código de um aluno é dado pessoal. A LGPD não proíbe guardá-lo: exige base legal e os princípios do art. 6. A UFPE é órgão público e já trata esse dado no próprio Dikastis, para a avaliação da disciplina.

**Decisão:**
1. **O que:** só o último código de cada aluno em cada questão (o anterior é substituído), com a data, o veredito do Dikastis e o resultado resumido da ADR-13. Nada de histórico de tentativas.
2. **Base legal e finalidade:** tratamento pelo órgão público para cumprir sua atribuição, a avaliação acadêmica da disciplina (LGPD, arts. 7º, III, e 23), para a correção e a detecção de plágio da própria disciplina. Nunca para outra finalidade, e nunca enviado a uma IA externa.
3. **Transparência:** um aviso aos alunos no plano de ensino e na página da disciplina no Dikastis; o aviso de privacidade do IP-Checker atualizado.
4. **Segurança (NFR-32):** o código fica cifrado em repouso (AES-256-GCM) com a chave `IPC_CODE_KEY`, que existe só no Render e é gravada pelo autor; nonce por registro e o identificador da submissão como dado associado; os backups já são cifrados (age); o acesso é só da equipe que já vê os códigos no Dikastis; nada de código em log, telemetria, feedback ou resumo (canário).
5. **Retenção (NFR-31, Q-38):** 6 períodos (3 anos). Quando a primeira lista de um período novo entra, o mais antigo sai inteiro: códigos, resultados, pares, catálogo e gabaritos (enunciados e gabaritos vão antes para o arquivo, porque não são dado pessoal). O job de manutenção faz isso e registra a contagem.
6. **Direitos do titular:** exclusão a pedido do aluno (art. 18), atendida pela chefia em até 15 dias, com o registro do pedido.
7. **Registro:** um relatório de impacto de uma página (art. 38) e a ciência do encarregado de dados da UFPE (art. 41). Isto não é parecer jurídico.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Não guardar nada (situação até aqui) | NFR-11 intacto | Sem turma pela sincronização, sem plágio por período |
| B. Impressão digital não reversível (ADR-14) | Habilita o plágio sem guardar código | Sem trechos lado a lado; não serve à correção da turma |
| C. Escolhida: o último código, cifrado, por 6 períodos | Correção da turma e plágio em escala; o dado já é tratado pela UFPE no Dikastis | Dado pessoal no IP-Checker: exige cifra, aviso, retenção e exclusão a pedido |
| D. Guardar todo o histórico de tentativas | Análise da evolução do aluno | Muito mais dado pessoal, sem uso previsto |

**Consequências positivas:** a correção de uma lista inteira sem colar nada; o plágio entre turmas e, depois, entre períodos; a base para a estilometria no futuro, se a coordenação quiser.

**Consequências negativas:** o IP-Checker passa a ter dados pessoais sensíveis à exposição e precisa do aviso, da cifra, da rotação de chave documentada e do procedimento de exclusão; o NFR-11 e o canário são revistos para distinguir "em claro" (proibido) de "cifrado na tabela própria" (permitido).

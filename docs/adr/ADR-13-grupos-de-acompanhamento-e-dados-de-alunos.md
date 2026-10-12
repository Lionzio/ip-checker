# ADR-13 — Grupos de acompanhamento e dados de alunos

**Título:** Como cada monitor cadastra os alunos pelos quais é responsável e como dois ou mais monitores compartilham o histórico deles.

**Status:** Proposto em 12/10/2026 (revisão das seis frentes, [`revisao-seis-frentes.md`](../revisao-seis-frentes.md)); Sprint 47. As Q-26 a Q-29 foram decididas pelo autor em 12/10/2026; a release espera a coordenação aprovar o aviso de privacidade.

**Contexto:** Até aqui o IP-Checker não guarda nada sobre alunos. O código não persiste (NFR-11), o nome do aluno existe só no navegador para o feedback e nunca vai ao provedor de IA (NFR-24), e o histórico do aluno ficou fora do escopo (REC-07). O autor quer que cada monitor cadastre os seus alunos, sem limite, com um painel e o histórico das verificações. Quer também que dois ou três monitores possam compartilhar o mesmo conjunto de alunos e o mesmo histórico (verificações, indícios de IA, indícios de plágio e feedbacks), com a composição mudando ao longo do tempo. Um aluno não é exclusivo de um monitor. A persistência e a autenticação já existem (PostgreSQL, esquema `app`, ADR-04).

**Decisão (proposta):**
1. **Um conceito só, o grupo de acompanhamento:** N monitores e M alunos, por período. O monitor que trabalha sozinho é um grupo de um, criado automaticamente.
2. **Convite e aceite:** um membro convida outro monitor ativo, e o acesso começa no aceite. Sair do grupo não apaga os registros.
3. **Dados mínimos (Q-26 a Q-28):** do aluno, só o nome de exibição e, opcionalmente, o login do Dikastis, nunca CPF, e-mail ou matrícula. De cada verificação, só o **resultado resumido**, como "L3-Q1 anulada por Laços de repetição" ou "L4-Q2 validada", com a faixa dos indícios de IA e do alerta de plágio quando houver e quem executou. **Nada do código** é guardado, nem o hash, as linhas ou trechos, e o NFR-11 continua valendo. O feedback enviado ao aluno também não é guardado.
4. **Acesso:** o membro vê e edita o próprio grupo. Monitor-chefe, professor e desenvolvedor leem todos os grupos do período, sem editar.
5. **Auditoria e concorrência:** os registros são só inseridos; as remoções são marcadas com data (`removed_at`, `left_at`); as ações do grupo vão para um registro como o `management_log`.
6. **Retenção coerente com a ADR-12:** tudo do período é expurgado quando ele é encerrado ou 12 meses depois do fim do período, o que vier primeiro (Q-29), por uma função `SECURITY DEFINER`.
7. **Gravação descartável:** o registro é gravado em segundo plano e descartado sob carga, como a telemetria. A verificação nunca falha por causa dele.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: grupo de acompanhamento (N monitores × M alunos) | Cobre solo, dupla e trio; o histórico tem dono; a composição muda sem mover registros | Um grupo a mais para quem trabalha sozinho (criado automaticamente) |
| B. Vínculo direto monitor ↔ aluno | Mais simples no início | "Mesmo histórico" não tem dono; não se sabe o que fica quando um monitor sai |
| C. Só no navegador, com exportação em JSON | Nenhum dado pessoal no servidor | Não compartilha entre monitores; perde ao trocar de máquina; sem auditoria |

**Consequências positivas:** acompanhamento por aluno e divisão do trabalho na equipe; supervisão pela chefia; nenhum código guardado.

**Consequências negativas:** primeiro dado pessoal de terceiros, já que os alunos não usam a ferramenta (P-13). Aviso de privacidade, base legal e retenção precisam ser combinados com a coordenação. Há mais escritas no banco do plano gratuito.

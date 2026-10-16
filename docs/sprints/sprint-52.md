# Sprint 52 — Códigos dos alunos (parte 2): guarda, retenção e a etapa 2

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seções 4.1 e 4.2); o plano comum está no [README](README.md). Primeira sprint que guarda código de aluno (Q-37, ADR-16); só vai ao piloto com o aviso aos alunos publicado e a `IPC_CODE_KEY` gravada pelo autor.

**Objetivo:** o último código de cada aluno em cada questão guardado no banco, cifrado, por 6 períodos, com a etapa 2 (verificador, indícios e plágio incremental) rodando a cada código novo.

**Missão:** que a equipe abra a turma e veja o resultado de cada aluno em cada questão sem colar nada, e que o aluno tenha a garantia de que o código dele fica cifrado, só para a correção, e some em 3 anos ou quando ele pedir.

**Personas:** a coordenação, dona da base legal (US-52); o membro da equipe que corrige a lista (US-53); o aluno, titular dos dados (US-56).

**Execução:**
1. A decisão registrada, o aviso aos alunos e o relatório de impacto (S52-01).
2. A migração `0009` e a cifra (S52-02).
3. A extensão trazendo as submissões (S52-03) e a fila da etapa 2 (S52-04).
4. A tela da turma (S52-05), a retenção e a exclusão a pedido (S52-06), os documentos (S52-07).

**Histórias:** US-52, US-53 e US-56.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S52-01 | US-52 | Documentação | Q-37 registrada com a autorização dos professores e dos monitores-chefes; o aviso aos alunos (texto para o plano de ensino e para a página da disciplina no Dikastis); o relatório de impacto de uma página (LGPD, art. 38); o pedido de ciência ao encarregado de dados da UFPE | docs (`privacidade.md`, `decisoes.md`) | Autor | 1 | — | Textos aprovados pelo autor; o pedido enviado |
| S52-02 | US-52 | Engenharia | Migração `0009` (`students`, `submissions` com `code_ciphertext`, `code_sha256`, `verdict`, `stage2_status`, `summary`); cifra AES-256-GCM na API com `IPC_CODE_KEY` (só no Render), nonce por registro e o identificador da submissão como dado associado; a rotação da chave documentada (recifrar em lote) | API (`crypto.py`), banco | Autor | 3 | Sprint 50 | O banco não tem o código em claro (teste lê a tabela); chave errada falha; o canário não aparece em log nem na telemetria |
| S52-03 | US-53 | Engenharia | Extensão: `POST /import/submissions/manifest` com os identificadores das submissões de cada questão por turma; o IP-Checker devolve as novas; `PUT /import/submissions` grava só o último código de cada aluno em cada questão (o anterior é substituído) | Extensão, API | Autor | 3 | S52-02 | Reenvio sem novidade não grava; um código novo substitui o anterior; o ritmo no Dikastis respeita o NFR-33 |
| S52-04 | US-53 | Engenharia | Etapa 2: fila de códigos novos (`stage2_status`); o verificador em lote, com o resumo da ADR-13 e, para quem vê, os indícios; "aguardando a questão" quando a etapa 1 falta; a fila retoma depois de um reinício | API, analisador | Autor | 3 | S52-02 | Testes da fila e dos estados; nada de código no resumo; um reinício no meio não perde nem duplica |
| S52-05 | US-53 | Engenharia | Tela da turma: alunos × questões com o resultado resumido e o estado da etapa 2; abrir o código de um aluno (a equipe, como no Dikastis), decifrado na hora, nunca em cache | Página, API | Autor | 2 | S52-04 | Vitest; e2e com dados sintéticos; a resposta do código tem `Cache-Control: no-store` |
| S52-06 | US-52, US-56 | Engenharia | Retenção de 6 períodos no `Housekeeping`: quando a primeira lista de um período novo entra, o mais antigo sai inteiro (códigos, resultados, pares, catálogo, gabaritos), com enunciados e gabaritos arquivados antes; exclusão a pedido do aluno (rota da chefia por login, registro do pedido, prazo de 15 dias no runbook) | API, runbook | Autor | 2 | S52-02 | Teste com 7 períodos: o mais antigo sai inteiro, com a contagem no registro; a exclusão a pedido apaga códigos e pares e registra |
| S52-07 | US-20 | Documentação | ADR-16 aceita; NFR-11 revisado; NFR-31 e NFR-32; FR-41; guia ("A turma pela sincronização"); runbook ("Exclusão a pedido", "Rotação da chave dos códigos") | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-16 (novo); ADR-13 (revisão: o resumo convive com o código cifrado); ADR-14 (o status registra que a alternativa C voltou em outra forma).

**Critérios de aceite:**
1. Um código de 2026.2 está cifrado no banco; quando as listas de 2029.2 entram, os códigos de 2026.2 são apagados, e o registro mostra a contagem.
2. Depois de uma sincronização, a tela da turma mostra o resultado resumido de cada aluno na L1-Q3; um código de uma questão ainda sem catálogo aparece "aguardando a questão".
3. Um pedido de exclusão apaga os códigos e os pares do aluno, e fica no registro.
4. O canário de privacidade não acha o código em log, telemetria, feedback nem resumo.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Cifra | pytest | PR | Sem código em claro no banco; chave errada falha |
| Privacidade | pytest com canário | PR | Nada de código em log, telemetria, feedback ou resumo |
| Etapa 2 | pytest com o banco e o relógio injetado | PR | Fila, estados, retomada |
| Retenção e exclusão | pytest com 7 períodos | PR | O mais antigo sai inteiro; a exclusão a pedido registra |
| Regressão | `scripts/ci-local.sh` | Todo PR | Verde; o resumo colado no PR |

**Deploy:** release `sprint-52`. Antes: o aviso aos alunos publicado e a `IPC_CODE_KEY` gerada e gravada pelo autor no Render (nunca por agente). Depois: a migração `0009` pelo autor, Render e Vercel com "faça o deploy", o exercício de alerta e o sintético.

**Riscos:**
- Vazamento de código de aluno: cifra, backups cifrados, acesso só da equipe, nada em log, retenção curta e exclusão a pedido.
- A base legal questionada: o tratamento já existe no Dikastis para a mesma finalidade; a ciência do encarregado e o aviso ficam registrados antes do deploy.
- O volume no plano gratuito: cerca de 10 MB por período; o `/health/slo` ganha o tamanho do banco se passar de 300 MB.

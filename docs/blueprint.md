# IP-Checker — Blueprint Definitivo e Acionável

## 1. Visão Geral e Melhorias Aplicadas

### 1.1 Visão geral do IP-Checker

O IP-Checker é um verificador web de uso restrito à equipe da disciplina (desenvolvedor, professores, monitores-chefe e monitores), sem execução de código, que confere se uma solução em Python de um aluno de Introdução à Programação respeita as regras de permissão da lista e da questão selecionadas (catálogo R-01…R-68, seção 3.1). Ele apoia a correção feita pela equipe: aponta as proibições, compara duas soluções em busca de plágio e redige, com uma LLM, um feedback para o aluno a partir do resultado do motor, que continua sendo o único a decidir se houve violação. O acesso é restrito porque o uso frequente de proibições é um dos principais indícios de solução gerada por IA: com a ferramenta aberta, um aluno poderia gerar o código com IA, ver as proibições e pedir à IA que as removesse (P-13, decisão de 02/10/2026). Todas as funções exigem conta aprovada e ativa, com e-mail `@cin.ufpe.br` ou `@ufpe.br`, criada por e-mail e senha ou pelo Google e aprovada manualmente por monitor-chefe, professor ou pelo desenvolvedor (ADR-04). O código é analisado apenas pela sua árvore sintática (AST), dentro de um serviço analisador isolado, sem segredos, sem rede de saída e com limites de tamanho, tempo e memória (ADR-01); a comparação de plágio roda no mesmo analisador (ADR-05). As regras ficam em um ruleset versionado e declarativo, sob a responsabilidade do professor (regras das listas) e dos monitores (regras das questões, com aprovação de monitor-chefe ou professor). Assim, mudar uma lista não exige mudar o motor (ADR-02). Cada violação aparece com regra, linha, coluna e mensagem em PT-BR. A telemetria agregada e anônima não guarda código, IP nem identificador de pessoa. As Sprints 1 a 12 foram concluídas em 01/10/2026: o MVP (Sprint 9) entregou o fluxo ponta a ponta seguro para a Lista 1, rodando localmente. As Sprints 13 a 19 (contas, registro com verificação por e-mail, perfil, gerenciamento da equipe, Google, mesma origem no piloto, painel de plágio, a montagem do feedback, o feedback na página, o aviso de privacidade e o guia da equipe) foram concluídas em 02/10/2026; falta o primeiro deploy com login, que depende das contas do autor. A Sprint 20 habilitou a Lista 2, com o `zip` condicional (R-37) e a exigência do laço (R-02), e deixou pronta a validação com os gabaritos de períodos anteriores. A Sprint 21 ligou a telemetria anônima (views do FR-17 e expurgo de 12 meses) e os alertas de latência e de erro, a Sprint 22 habilitou as Listas 3 e 4, e a Sprint 23, as Listas 5 e 6, com a recursão obrigatória (R-68), e o registro das ações de gerenciamento (REC-06). O acesso restrito, o painel de plágio e o feedback entram nas Sprints 13 a 19, antes de qualquer exposição na internet; as Listas 2 a 6 e a telemetria vieram em seguida (Sprints 20 a 23); a Sprint 24 trouxe as regras por questão, o comando `ipc-rules` e o "esqueci minha senha"; as Sprints 25 a 28 trouxeram o endurecimento para o primeiro deploy, a correção em lote, o plágio por árvore e a passagem de bastão (carga com login, relatório de eficácia, runbook, backup, onboarding e releases), e o piloto subiu em 07/10/2026 (Render, Vercel e Supabase), faltando o primeiro deploy pelo pipeline com a conta de verificação, que confirma a P-15; a Sprint 29 trouxe os indícios de uso de IA (ADR-08, Q-21), desligados no piloto até a coordenação aprovar a política. As Sprints 30 a 36 (plano de 07/10/2026, seção 7.12) tratam as pendências restantes: o piloto verificado ponta a ponta, as decisões com a coordenação e o NTI, a comparação com o gabarito (ADR-11), os dados de calibração e de 2027.1, a prontidão para o período, os controles ainda [PLANEJADO] e a Fase 2; a integração com outros 2 projetos da monitoria é só uma possibilidade (seção 9, ADR-09). O piloto acontece em 2027.1, com a SPA na Vercel e o backend no Render, usado pela equipe na correção, e cada lista é habilitada antes de ser liberada aos alunos. O servidor do CIn só será adotado depois que os critérios de eficácia (P-09, em revisão na Q-15) forem atingidos (seção 7).

### 1.2 Falhas críticas corrigidas

As falhas da revisão inicial e como foram corrigidas estão em
[`historico/sprints-01-35.md`](historico/sprints-01-35.md) (S39-05).

### 1.3 Premissas, conflitos, questões em aberto e recomendações

A tabela completa (P-xx, C-xx, Q-xx e REC-xx), com o impacto e quem valida cada item, fica em
[`docs/decisoes.md`](decisoes.md) desde a S28-04.

## 2. Mapa de Personas

| Persona | Objetivo | Necessidades | Dores | Interação com o sistema |
|---|---|---|---|---|
| Aluno de IP (rascunho §3 "Público"; US-001, US-002 e US-005 do rascunho; Permissões p.1 "anulação imediata da questão") | Submeter ao Dikastis soluções que respeitem as permissões da lista e da questão, sem perder pontos. | Saber antes do envio se usou algo proibido, com a linha exata. Entender a partir de qual lista um recurso é liberado. Saber se a questão tem regra própria (R-01) e se cumpriu o assunto obrigatório (R-02). | Perde pontos por usar comandos não ensinados (rascunho §3 "Problema"). As regras cumulativas (R-03), as proibições gerais (R-05…R-14) e as exceções por questão são difíceis de memorizar. | Desde a P-13 (02/10/2026), não usa a ferramenta: recebe da equipe o resultado da correção e o feedback redigido a partir do relatório do IP-Checker. |
| Monitor e monitor-chefe (rascunho §3; US-003 do rascunho; resposta à Q-08) | Concentrar o atendimento na lógica do aluno, não em dúvidas de permissão, e manter atualizadas as regras específicas das questões. | Verificar em segundos o código de um aluno, comparar soluções suspeitas de plágio e devolver ao aluno um feedback coerente com o resultado. Cadastrar as permissões e proibições explícitas de cada questão sem programar. O monitor-chefe revisa e aprova o cadastro feito pelos monitores. | Monitoria sobrecarregada por dúvidas de permissão (rascunho §3 "Problema"). Risco de cadastrar uma regra de questão diferente do enunciado. | Entra com conta aprovada (P-13), verifica o código do aluno, compara soluções no painel de plágio e gera o feedback. O monitor-chefe aprova cadastros e gerencia monitores e monitores-chefe (FR-27). Cadastra regras de questão por PR em `questions/*.yaml`; o monitor-chefe aprova como CODEOWNER. |
| Professor/Coordenação (rascunho §3; US-004 do rascunho; §16; §30.1 "a confirmar com a coordenação"; resposta à Q-08) | Garantir que a ferramenta aplica exatamente o documento de permissões e as regras de cada questão, e acompanhar onde os alunos mais erram. | Alterar as regras das listas sem reprogramar a ferramenta. Aprovar overrides de questão, obrigatoriamente os que liberam proibições gerais (C-02). Consultar violações agregadas por lista. Decidir a migração para o servidor do CIn com base nos critérios de eficácia (P-09). | No rascunho, editar o JSON exige PR sem validação nem documentação até a Sprint 11 (I-15). Não havia fonte nem responsável para as regras de questão (1.2 #3). | Edita o ruleset base (YAML) por PR e aprova como CODEOWNER. Consulta views SQL somente leitura. Aprova cadastros e gerencia professores, monitores-chefe e monitores (FR-27). |
| Monitor-mantenedor, equipe técnica futura (rascunho §1 "manutenção por futuras equipes de monitores"; §21; §31 "handover") | Manter e evoluir a ferramenta apesar da rotatividade semestral. | Motor desacoplado das regras. Testes golden e de segurança na CI. Runbook e guia de onboarding. Observabilidade. | Conhecimento se perde a cada troca de equipe. Risco de quebrar regras ao mexer no código. Incidentes em véspera de prazo. | Repositório GitHub, CI/CD, CLI `ipc-rules`, painéis e alertas. O desenvolvedor atual tem conta criada por *seed* e o cargo mais alto (P-14). |

## 3. Requisitos

### 3.1 Catálogo de Regras de Permissão

**Linguagem e tipo de verificação (Etapa A2).** A linguagem é **Python 3**: o rascunho fala em "AST do Python" (§1, §11) e o catálogo usa built-ins e sintaxe do Python (R-22…R-67). A verificação é **apenas estática**. O rascunho diz "zero execução de código" (§1), "analisa o código (sem executá-lo)" (§3), põe a "execução de testes unitários" fora de escopo (§3) e reforça isso no §15.1. O documento de permissões não trata do assunto. A hipótese dinâmica é avaliada e descartada no ADR-01, e a versão alvo é Python 3.13+ (Q-01). Abreviação usada na coluna "Fonte": "Perm." é o documento "Permissões das listas de Introdução à Programação", igual nos formatos .docx e .pdf.

| ID | Lista | Recurso/construção | Tipo | Regra (redação original resumida) | Fonte no documento |
|---|---|---|---|---|---|
| R-01 | Todas | Regra específica da questão | condicional | O que a questão proíbe ou permite explicitamente tem prioridade sobre as regras gerais; havendo permissão explícita na questão, o uso é permitido. | Perm. p.1 §Introdução; p.3 §final |
| R-02 | Todas (1–6) | Assunto da lista | condicional (exigência) | A solução das questões deve obrigatoriamente implementar o assunto da lista. | Perm. p.1 §Introdução |
| R-03 | Todas | Cumulatividade | permitido | As permissões de cada lista incluem as das listas anteriores. | Perm. p.1 "Obs." |
| R-04 | Todas | Tudo que não consta no documento nem na questão | proibido | "Tudo que não está presente nesse documento e nas questões é proibido." | Perm. p.1 |
| R-05 | Todas | Bibliotecas externas | proibido | Proibição geral; o uso anula a questão imediatamente. | Perm. p.1 §Proibições gerais |
| R-06 | Todas | `try`/`except` | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-07 | Todas | Sets | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-08 | Todas | `exit()` | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-09 | Todas | Classes | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-10 | Todas | Args e Kwargs | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-11 | Todas | `break`, `continue` | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-12 | Todas | `pass` | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-13 | Todas | `None` | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-14 | Todas | Variáveis globais | proibido | Proibição geral (anulação imediata). | Perm. p.1 §Proibições gerais |
| R-15 | 1 → 6 | `if`, `elif`, `else` | permitido | Comandos condicionais. | Perm. p.1 §Lista 1 |
| R-16 | 1 → 6 | Variáveis e atribuições | permitido | Variáveis e atribuições. | Perm. p.1 §Lista 1 |
| R-17 | 1 → 6 | `is` | permitido | Operador "is". | Perm. p.1 §Lista 1 |
| R-18 | 1 → 6 | Operações matemáticas e abreviações | permitido | Operações matemáticas e abreviações (`+=`, `*=` etc.). | Perm. p.1 §Lista 1 |
| R-19 | 1 → 6 | Operadores lógicos, relacionais e booleanos | permitido | Operadores lógicos, relacionais e booleanos. | Perm. p.1 §Lista 1 |
| R-20 | 1 → 6 | Operador ternário | permitido | Operador ternário. | Perm. p.1 §Lista 1 |
| R-21 | 1 → 6 | Concatenação | permitido | Concatenação. | Perm. p.1 §Lista 1 |
| R-22 | 1 → 6 | `print()`, `input()` | permitido | `print()` e `input()`. | Perm. p.1 §Lista 1 |
| R-23 | 1 → 6 | `abs()` | permitido | `abs()`. | Perm. p.1 §Lista 1 |
| R-24 | 1 → 6 | `int()`, `float()`, `str()` | permitido | `int()`, `float()`, `str()`. | Perm. p.2 §Lista 1 |
| R-25 | 1 → 6 | `max()`, `min()` | permitido | `max()`, `min()`. | Perm. p.2 §Lista 1 |
| R-26 | 1 → 6 | `round()` | permitido | `round()`. | Perm. p.2 §Lista 1 |
| R-27 | 1 → 6 | `len()` | permitido | `len()`. | Perm. p.2 §Lista 1 |
| R-28 | 1 → 6 | `format()` | permitido | `format()`. | Perm. p.2 §Lista 1 |
| R-29 | 1 → 6 | Métodos de string | permitido | `capitalize()`, `upper()`, `lower()`, `isupper()`, `islower()`, `isnumeric()`. | Perm. p.2 §Lista 1 |
| R-30 | 1 → 6 | `in` para strings | permitido | "in" para strings. | Perm. p.2 §Lista 1 |
| R-31 | 1 → 6 | f-strings | permitido | f-strings (formatação). | Perm. p.2 §Lista 1 |
| R-32 | 1 → 6 | `\n` e `end=` no `print()` | permitido | `\n` e `end =` no `print()`. | Perm. p.2 §Lista 1 |
| R-33 | 1 → 6 | `type()` | permitido | `type()`. | Perm. p.2 §Lista 1 |
| R-34 | 2 → 6 | `for`, `while` | permitido | Laços de repetição. | Perm. p.2 §Lista 2 |
| R-35 | 2 → 6 | `range()` | permitido | `range()`. | Perm. p.2 §Lista 2 |
| R-36 | 2 → 6 | `in` para `range()` | permitido | "in" para `range()`. | Perm. p.2 §Lista 2 |
| R-37 | 2 → 4 (Q-04) | `zip()` | condicional | `zip()` somente para variar mais de um índice no comando `for`. | Perm. p.2 §Lista 2 |
| R-38 | 3 → 6 | Listas | permitido | Listas. | Perm. p.2 §Lista 3 |
| R-39 | 3 → 6 | Matrizes | permitido | Matrizes. | Perm. p.2 §Lista 3 |
| R-40 | 3 → 6 | Tuplas | permitido | Tuplas. | Perm. p.2 §Lista 3 |
| R-41 | 3 → 6 | List comprehension | permitido | List comprehension e, desde 09/10/2026, a expressão geradora (Q-02 e revista, provisória até o Marco 2). | Perm. p.2 §Lista 3; Q-02 (e) |
| R-42 | 3 → 6 | Indexação de listas e strings | permitido | Indexação de listas e strings. | Perm. p.2 §Lista 3 |
| R-43 | 3 → 6 | Slicing | permitido | Slicing. | Perm. p.2 §Lista 3 |
| R-44 | 3 → 6 | `in` para listas | permitido | "in" para listas. | Perm. p.2 §Lista 3 |
| R-45 | 3 → 6 | `list()` | permitido | `list()`. | Perm. p.2 §Lista 3 |
| R-46 | 3 → 6 | `append()`, `insert()`, `pop()`, `remove()` | permitido | `append()`, `insert()`, `pop()`, `remove()`. | Perm. p.2 §Lista 3 |
| R-47 | 3 → 6 | `del` | permitido | `del`. | Perm. p.2 §Lista 3 |
| R-48 | 3 → 6 | `sort()`, `sorted()` | permitido | `sort()`, `sorted()`. | Perm. p.2 §Lista 3 |
| R-49 | 3 → 6 | `reverse()`, `reversed()` | permitido | `reverse()`, `reversed()`. | Perm. p.2 §Lista 3 |
| R-50 | 3 → 6 | `strip()` | permitido | `strip()`. | Perm. p.2 §Lista 3 |
| R-51 | 3 → 6 | `replace()` | permitido | `replace()`. | Perm. p.2 §Lista 3 |
| R-52 | 3 → 6 | `index()` | permitido | `index()`. | Perm. p.2 §Lista 3 |
| R-53 | 3 → 6 | `join()` | permitido | `join()`. | Perm. p.2 §Lista 3 |
| R-54 | 3 → 6 | `split()`, `rsplit()` | permitido | `split()`, `rsplit()`. | Perm. p.2 §Lista 3 |
| R-55 | 3 → 6 | `sum()` | permitido | `sum()`. | Perm. p.2 §Lista 3 |
| R-56 | 3 → 6 | `count()` | permitido | `count()`. | Perm. p.2 §Lista 3 |
| R-57 | 3 → 6 | `copy()` | permitido | `copy()`. | Perm. p.2 §Lista 3 |
| R-58 | 3 → 6 | `tuple()` | permitido | `tuple()`. | Perm. p.2 §Lista 3 |
| R-59 | 4 → 6 | Funções (`def`, parâmetros, `return`) | permitido | Funções com `def`, parâmetros e `return`. | Perm. p.2 §Lista 4 |
| R-60 | 4 → 6 | Retorno de múltiplos valores | permitido | Retornar mais de um valor. | Perm. p.2 §Lista 4 |
| R-61 | 5 → 6 | Dicionários | permitido | Dicionários. | Perm. p.3 §Lista 5 |
| R-62 | 5 → 6 | `dict()` | permitido | `dict()`. | Perm. p.3 §Lista 5 |
| R-63 | 5 → 6 | `enumerate()` | permitido | `enumerate()`. | Perm. p.3 §Lista 5 |
| R-64 | 5 → 6 | `zip()` | permitido | `zip()`, listado sem restrição; livre a partir da L5 (Q-04). | Perm. p.3 §Lista 5 |
| R-65 | 5 → 6 | `keys()`, `values()`, `items()` | permitido | `keys()`, `values()`, `items()`. | Perm. p.3 §Lista 5 |
| R-66 | 5 → 6 | `get()`, `update()` | permitido | `get()`, `update()`. | Perm. p.3 §Lista 5 |
| R-67 | 5 → 6 | Função `lambda` | permitido | Função lambda. | Perm. p.3 §Lista 5 |
| R-68 | 6 | Recursão | condicional (exigência) | Recursão permitida e obrigatória em todas as questões da Lista 6. | Perm. p.3 §Lista 6 |

### 3.2 Requisitos Funcionais

- **FR-01** — Editor web para colar e editar código Python, com numeração de linhas e realce de sintaxe. Origem: RF-002 do rascunho.
- **FR-02** — Upload de arquivo `.py` (até 50 KB, UTF-8). O arquivo é lido no navegador e carregado no editor; o servidor só recebe o texto pelo mesmo contrato do FR-01. Origem: RF-001.
- **FR-03** — Seleção obrigatória da lista. Só aparecem as listas habilitadas pela configuração `IPC_ENABLED_LISTS` (1 no MVP; as seis desde a Sprint 23, no `render.yaml` e no `deploy/compose.yaml`; a S34-05 ajusta o piloto conforme o professor validar o ruleset de 2027.1). A questão é opcional e é escolhida entre as cadastradas no ruleset do período ativo, já que a numeração reinicia a cada período (R-01, P-07). Origem: RF-003.
- **FR-04** — Validação da entrada antes da análise: UTF-8 válido, até 51.200 bytes, até 1.000 linhas e nenhum byte nulo. Entradas fora disso são rejeitadas com código específico: 413 `PAYLOAD_TOO_LARGE` ou 422 `INVALID_INPUT`. Origem: RF-021 e §15.2.
- **FR-05** — Análise sintática sem execução, na gramática do Python 3.13 (Q-01). Um erro de sintaxe é reportado com linha, coluna e mensagem em PT-BR, e nesse caso as regras não são avaliadas. Origem: RF-004 e RF-005.
- **FR-06** — *Default deny*: todo fato extraído do código (nó, operador, built-in, método ou atributo, argumento nomeado, constante) que nenhuma regra permitida até a lista selecionada cubra gera violação (R-04, R-15…R-67).
- **FR-07** — Cumulatividade: uma regra permitida na lista *k* vale para todas as listas ≥ *k* (R-03).
- **FR-08** — As proibições gerais valem em todas as listas e aparecem com a categoria `ANULACAO` (R-05…R-14).
- **FR-09** — Regras condicionais são avaliadas por predicados declarados no ruleset. Exemplo: `zip()` só como iterável de `for` com ≥ 2 argumentos (R-37, R-64, Q-04).
- **FR-10** — Exigências: o sistema verifica se o assunto obrigatório da lista está presente (R-02, Q-05) e se há recursão em toda questão da Lista 6 (R-68, C-03). A ausência gera violação de categoria `EXIGENCIA`.
- **FR-11** — Regras por questão: os overrides `allow`/`deny` de um `question_id` prevalecem sobre as regras base (R-01, C-02). Se a questão não for informada, a resposta traz o aviso `QUESTION_RULES_NOT_APPLIED`.
- **FR-12** — Relatório de resultado com:
  - `status` (`valid`, `invalid` ou `syntax_error`);
  - violações com `rule_id` (R-xx), `category` (`ANULACAO`, `PROIBIDO_NA_QUESTAO`, `FORA_DA_LISTA`, `NAO_CONSTA` ou `EXIGENCIA`), `line`, `col`, `end_line`, `end_col`, `construct`, `message` em PT-BR e `allowed_from_list` quando houver;
  - ordenação por linha e coluna, sem duplicatas, com no máximo 200 itens (P-04);
  - `ruleset_version` e `request_id`.

  Origem: RF-013 a RF-016.
- **FR-13** — Destaque das violações no editor (sublinhado e marcador na margem) e navegação do card para a linha, por clique ou teclado. Origem: US-002 e TASK-FE-004 do rascunho.
- **FR-14** — Consulta das permissões efetivas de uma lista (e da questão, se houver): regras permitidas, proibições gerais, exigências e overrides (R-01…R-68). Origem: US-005 do rascunho.
- **FR-15** — O ruleset é versionado em arquivos YAML validados por JSON Schema. Ele é carregado como estrutura imutável na inicialização do analisador e, se for inválido, o serviço não fica pronto (*fail-fast*). A versão (`ruleset_version`) é exposta em todas as respostas. Origem: RF-018.
- **FR-16** — Telemetria anônima e assíncrona por validação: lista, questão, versão do ruleset, resultado, `rule_id`s e tempo de análise. Nunca registra código, IP nem identificador de cliente ou de conta. Origem: RF-019 e RF-026.
- **FR-17** — Consultas agregadas pré-definidas (views SQL somente leitura) para professores: regras mais violadas por lista, questão e período, taxa de erro de sintaxe e volume de verificações por lista e por semana, usado na avaliação de eficácia do piloto (P-09). Origem: §16.
- **FR-18** — Endpoints `GET /health` (o processo está vivo) e `GET /ready` (o analisador responde e o ruleset está carregado). Origem: RF-020.
- **FR-19** — Rate limit por cliente anônimo (10 req/min) e por IP (120 req/min para IPs externos; 1.000 req/min para as faixas do campus em `IPC_RATE_LIMIT_CAMPUS_CIDRS`), mais controle de admissão. Respostas 429 ou 503 sempre trazem `Retry-After`. Origem: RF-022 e P-04. Com o acesso restrito (P-13, a partir da Sprint 13), o limite por cliente passa a ser por conta, com valor a recalibrar para a correção em lote (C-04), e as rotas de autenticação ganham limites próprios contra força bruta (FR-25).
- **FR-20** — Interface web responsiva (≥ 360 px) com os estados: válido, com violações, erro de sintaxe, entrada rejeitada, limite de taxa, sobrecarga e falha de rede (com opção de nova tentativa). Origem: RF-017.
- **FR-21** — Ferramenta de validação do ruleset: o comando `ipc-rules validate` e o mesmo job na CI verificam schema, existência dos R-xx referenciados, consistência de `since_list`/`until_list` e os testes golden. Também sinaliza overrides de questão que liberam R-05…R-14, que só podem entrar com aprovação de professor (C-02). Origem: US-004 do rascunho e §21.
- **FR-22** — Acesso restrito (P-13): toda rota da API exige uma sessão de conta com status `ativo`, exceto `GET /health`, `GET /ready` e as rotas de autenticação (`/api/v1/auth/*`). Sem sessão, a resposta é 401 `UNAUTHENTICATED` e nenhum dado é retornado; a verificação fica no backend, não só na interface. Sem login, a SPA mostra apenas as opções **Registrar** e **Entrar**.
- **FR-23** — Registro por e-mail e senha, com os campos obrigatórios Nome, E-mail institucional, Senha, Curso e Tratamento (FR-26):
  - e-mail único e só dos domínios `cin.ufpe.br` e `ufpe.br`, comparados exatamente depois do `@` e sem diferenciar maiúsculas (`x@xcin.ufpe.br` e `x@ee.ufpe.br` são recusados); a interface recomenda o `@cin.ufpe.br`;
  - senha com pelo menos 9 caracteres, 1 letra maiúscula e 1 caractere especial, com os requisitos na tela e validação no frontend e no backend; só o hash Argon2id é guardado;
  - nome único sem diferenciar maiúsculas, porque também serve para entrar;
  - fluxo de status: `aguardando_verificacao`, até o clique no link "Clique aqui para verificar seu acesso." (token aleatório, de uso único, válido por 24 h, com reenvio); depois `aguardando_aprovacao`; por fim `ativo`, com o cargo escolhido por quem aprovou, ou `recusado`;
  - o envio de e-mail é configurável por variáveis de ambiente (SMTP ou serviço transacional, Q-17).
- **FR-24** — Registro e login pelo Google (OAuth 2.0 / OpenID Connect), com biblioteca consolidada (Authlib, ADR-04), `state` contra CSRF, `nonce`, PKCE e validação da assinatura, do emissor e da audiência do ID token; client ID e client secret ficam em variáveis de ambiente. O parâmetro `hd` só sugere a conta institucional na tela do Google: o backend aceita apenas `email_verified` verdadeiro e domínio exato `cin.ufpe.br` ou `ufpe.br`, e recusa os demais explicando que só e-mails institucionais da equipe são aceitos. Não há etapa de link: um formulário complementar pede Nome (pré-preenchido pelo Google, editável e único), Curso e Tratamento, sem senha, e o status vai direto a `aguardando_aprovacao`. Entrar com o Google sem ter conta encaminha a esse registro.
- **FR-25** — Contas e entrada:
  - cada e-mail corresponde a uma única conta, e senha e Google levam à mesma conta; os dois e-mails do desenvolvedor levam à conta dele (P-14);
  - ao vincular o Google a uma conta cujo e-mail nunca foi verificado, a senha e os dados pendentes dessa conta são descartados, o que impede o pré-sequestro de conta (5.4, ameaça 16);
  - entrar por senha pede "Nome ou e-mail institucional" e "Senha"; numa conta criada pelo Google, que não tem senha, a mensagem orienta a usar o Google ou a definir uma senha no perfil;
  - há mensagens distintas para credenciais inválidas, e-mail fora dos domínios aceitos, e-mail não verificado, cadastro aguardando aprovação, cadastro recusado e conta removida; as que revelam o status da conta só aparecem depois de a senha, ou o Google, confirmar a identidade;
  - as rotas de autenticação têm limite de tentativas por conta e por IP (NFR-22).
- **FR-26** — Perfil e tratamento: cada pessoa edita o próprio nome, curso, tratamento e senha, ou define uma senha se a conta veio do Google; ninguém altera o próprio cargo. O tratamento define como a pessoa quer ser tratada, conforme a identidade de gênero com que se identifica, e cada opção aparece com um exemplo: Masculino ("sou o monitor..."), Feminino ("sou a monitora...") e Neutro ("aqui é ..., da monitoria"). É obrigatório no cadastro pelos dois métodos, editável no perfil, nunca aparece em listas nem para outras pessoas e só é usado no feedback (FR-30).
- **FR-27** — Cargos e permissões (P-14), sempre verificados no backend, conforme a tabela abaixo. Ao aprovar, o aprovador escolhe o cargo entre os que ele mesmo pode atribuir (um monitor-chefe só aprova como monitor-chefe ou monitor), e a fila tem as ações Aprovar (com o cargo) e Recusar. "Remover conta" segue a mesma tabela e não apaga o registro: a conta perde o acesso e passa a **Ex-monitor**, se a pessoa nunca foi monitor-chefe, ou a **Conselheiro**, se já foi, pelo campo `ja_foi_monitor_chefe`, que vira verdadeiro na primeira vez que a pessoa recebe esse cargo e nunca volta a falso; professor removido fica apenas `inativo`. Uma conta removida pode ser reativada por quem tem permissão sobre o cargo que ela vai receber. Só o próprio desenvolvedor altera a conta do desenvolvedor.

| Cargo | Aprova cadastros | Atribui cargo, altera cargo e remove contas de |
|---|---|---|
| Desenvolvedor | Sim | Professores, monitores-chefe e monitores |
| Professor | Sim | Professores, monitores-chefe e monitores (nunca o desenvolvedor) |
| Monitor-chefe | Sim | Monitores-chefe e monitores |
| Monitor | Não | Ninguém, nem a si mesmo |

- **FR-28** — Tela de gerenciamento, acessível ao desenvolvedor, aos professores e aos monitores-chefe: fila de pedidos pendentes (nome, e-mail, curso, método de cadastro e data do pedido), membros ativos com o cargo de cada um e lista de ex-monitores e conselheiros. Cada linha mostra só os botões que a pessoa logada pode usar. Etiquetas de cargo: professor verde, monitor-chefe azul-claro, monitor roxo, desenvolvedor dourado (Q-19 e), ex-monitor e conselheiro cinza; a etiqueta sempre traz o nome do cargo escrito, não só a cor (NFR-19).
- **FR-29** — Painel de plágio, secundário e acessível a qualquer conta ativa: duas áreas de texto lado a lado (empilhadas em telas estreitas), uma para o código de cada aluno, o botão **Verificar** abaixo delas e o resultado com a porcentagem de similaridade *X* e a classificação, cada faixa com uma cor e o nome escrito. Faixas: *X* ≥ 99%, Plágio; 95% ≤ *X* < 99%, Altas chances de plágio; 90% ≤ *X* < 95%, Requer atenção; 80% ≤ *X* < 90%, Ligeiramente suspeito; *X* < 80%, Sem suspeitas. Os limiares ficam em constantes configuráveis, e a classificação usa o valor exibido, com uma casa decimal, para que um 99,0% na tela nunca apareça como "Altas chances". Um aviso discreto diz que o resultado é um indício e que a decisão final é da equipe; códigos muito curtos recebem um aviso a mais, porque soluções independentes de questões simples tendem a se parecer. O método resiste a renomear identificadores, mudar o espaçamento, adicionar ou remover comentários e reordenar trechos independentes (ADR-05). A comparação roda no analisador isolado, e nada é guardado.
- **FR-30** — (Revisto em 09/10/2026, Q-16 e S32-12: o texto sem IA é o padrão do **Gerar feedback**; a IA entra só no **Aprimorar com IA**, por uma cadeia de provedores gratuitos com fallback, com as mesmas partes fixas e a mesma validação; ADR-06 revisto.) Feedback por LLM no painel principal: o botão **Gerar feedback** pede Nome do aluno (obrigatório, digitado por quem avalia) e Anotação importante (opcional, com observações e dicas para o aluno); nome, cargo e tratamento de quem avalia, o código analisado e o resultado do IP-Checker entram automaticamente. A LLM só redige: quem decide se houve violação é o motor. O backend monta a apresentação pela tabela abaixo (o desenvolvedor usa a linha "Monitor"), a abertura ("Olá, {Nome_Aluno}, {apresentação} e seu código estava {resultado}...", com a pontuação ajustada) e a frase obrigatória: "Sua questão apresenta problemas, como o uso de {proibições}, portanto ela foi anulada.", com as proibições encontradas pelo IP-Checker, ou "Sua questão está ótima, não houve nenhuma violação de regras." (Q-18). A LLM escreve o restante em português brasileiro, na primeira pessoa do singular, com linguagem natural e tom cordial e didático: incorpora a anotação no estilo "Notei que você fez X, foi bom, mas Y teria sido melhor" ou, sem anotação, faz no máximo uma sugestão curta baseada no código, sem contradizer o resultado. Toda autorreferência concorda com o tratamento ("fiquei satisfeito" ou "fiquei satisfeita"; no neutro, nenhuma palavra com marcação de gênero, como em "gostei bastante"); o gênero do aluno não é coletado, e o texto usa construções neutras ao falar dele ("você teve cuidado com..."). O resultado aparece num campo editável, com botão **Copiar**. Provedor e modelo vêm da configuração, por adaptadores (Gemini, OpenAI, Groq, DeepSeek e outros); as chaves ficam só no servidor, e o nome real do aluno nunca vai ao provedor: o prompt usa `[ALUNO]`, trocado pelo nome quando a resposta volta (ADR-06, Q-16).

| Cargo | Masculino | Feminino | Neutro |
|---|---|---|---|
| Monitor | sou o monitor {nome} | sou a monitora {nome} | aqui é {nome}, da monitoria |
| Monitor-chefe | sou o monitor-chefe {nome} | sou a monitora-chefe {nome} | aqui é {nome}, da chefia da monitoria |
| Professor | sou o professor {nome} | sou a professora {nome} | aqui é {nome}, docente da disciplina |

- **FR-31** — Questões e gabaritos por período (ADR-10, US-36): as regras das questões ficam em `rulesets/<período>/questions/`, uma pasta por período, e o período ativo é escolhido num só lugar, sem mudar código (S31-09). `ipc-rules new-period <novo> --from <anterior>` cria a pasta de um período novo a partir do anterior (S31-10). Os gabaritos oficiais ficam no repositório privado `Lionzio/ip-checker-gabaritos`, em `<período>/lista-<n>/L<n>-Q<m>.py`, e cada um é conferido com zero violação usando as questões do próprio período (S31-11).

- **FR-32** — Comparação com o gabarito (ADR-11, US-37, US-38): (1) na verificação, com a questão escolhida no seletor de período, lista e questão (as questões do período ativo que têm gabarito; o seletor de período entra na Sprint 43, FR-33, e até lá vale o período ativo), o resultado traz a semelhança com o gabarito pela métrica da ADR-07, a faixa do FR-29, as construções em comum, só no aluno e só no gabarito e as linhas do aluno que coincidem; (2) no plágio, com a questão escolhida, A×gabarito e B×gabarito, e o alerta de possível vazamento quando A×B, A×gabarito e B×gabarito passam do limiar e os códigos têm o tamanho mínimo (95% e o mínimo de 60 tokens, configuráveis; premissa validada pelo autor em 12/10/2026); (3) nos indícios de IA, a semelhança com o gabarito como mais um sinal, só com `IPC_AI_INDICATORS`. A análise é determinística (sem IA); nenhum texto do gabarito vai ao navegador; sem gabarito ou com o download falho, a comparação fica de fora com um aviso, e o resto funciona.

- **FR-33** — Vários períodos na página (ADR-12, US-39, US-40) [PLANEJADO, Sprint 43]: o analisador carrega o período do `ATIVO` e os 5 anteriores; a página mostra Período antes de Lista e Questão, com o ativo já escolhido; a API aceita `period` opcional na verificação, no plágio e no feedback. Um período sai da janela por `ipc-rules retire-period`, que o move para `rulesets/encerrados/`, sem apagar nada do Git.

- **FR-34** — Feedback rastreável (US-41) [PLANEJADO, Sprint 44]: no feedback sem IA, cada violação citada traz o nome da regra, a linha, o motivo e um caminho de correção sem a solução (a explicação e a alternativa da S38-01), na ordem do motor; a frase obrigatória do FR-30 não muda.

- **FR-35** — Padrão do monitor (US-42, US-43) [PLANEJADO, Sprints 44 e 45]: o tom, as dicas e os exemplos do feedback ficam em `backend/src/ipc_api/feedback/estilo.yaml`, validado por esquema na CI e revisado por PR; o "Aprimorar com IA" usa esses exemplos, recusa qualquer construção que o motor não apontou, código de 3 ou mais linhas e trechos iguais ao gabarito, faz no máximo uma rodada de crítica e, se nada passar, devolve o texto sem IA.

- **FR-36** — Grupos de acompanhamento (ADR-13, US-45 a US-47) [PLANEJADO, Sprint 47; Q-26 a Q-29 decididas em 12/10/2026]: cada monitor cadastra os alunos pelos quais é responsável, sozinho ou num grupo com outros monitores (convite e aceite), por período; o grupo compartilha o histórico das verificações como resultados resumidos (por exemplo, "L3-Q1 anulada por Laços de repetição" ou "L4-Q2 validada"), com a faixa dos indícios de IA e do alerta de plágio quando houver e quem executou cada uma; nem o código nem o feedback são guardados (Q-27, Q-28).

- **FR-37** — Plágio medido (US-44) [PLANEJADO, Sprint 46]: precisão e revocação por faixa, num conjunto rotulado com plágio sintético (variáveis renomeadas, blocos reordenados, `for` trocado por `while`), a cada mudança no plágio; o par mostra quanto da semelhança o gabarito explica.

### 3.3 Requisitos Não Funcionais

| ID | Categoria | Requisito | Métrica | Valor-alvo | Método de verificação |
|---|---|---|---|---|---|
| NFR-01 | Desempenho | Latência do `POST /api/v1/validate` medida no servidor (borda → resposta) | P95 e P99 em janelas de 5 min | P95 ≤ 200 ms e P99 ≤ 500 ms, com 500 req/min e payload ≤ 5 KB | P95 do `/health/slo` em produção (memória da API, 5 min); k6 à mão: capacidade por plano com o `deploy/load/run_load.py` e o piloto de verdade com o workflow "Carga no piloto" (S28-01). k6 em staging [PLANEJADO, Fase 2]; sem histograma Prometheus (S35-06) |
| NFR-02 | Desempenho | Tempo de análise no worker (parse, fatos e política) | P95 por entrada do corpus | ≤ 50 ms para entradas ≤ 5 KB (as do NFR-01) e linear até 50 KB, com o limite de 2 s por análise como teto (Q-25, 11/10/2026; antes, ≤ 50 ms até 50 KB) | Benchmark do motor na CI desde a S35-01 (`tests/benchmark`, `IPC_BENCHMARK=1`): P95 ≤ 50 ms nas entradas de até 5 KB e regressão ≤ 20% sobre a linha de base em todas; a entrada de 50 KB leva cerca de 260 ms (Q-25) |
| NFR-03 | Desempenho | Carregamento da SPA | FCP e tamanho do JS inicial (gzip) | FCP ≤ 1,65 s no perfil móvel do Lighthouse ("Slow 4G"; Q-25, 11/10/2026; antes, < 1,5 s); JS inicial ≤ 350 KB gzip (Q-25) | Lighthouse CI e orçamento do JS na CI desde a S35-02 (`frontend/lighthouserc.json`, `scripts/js-budget.mjs`): JS inicial de 104,5 KB com gzip; FCP de 1,51 s no perfil móvel, com a CI falhando acima de 1,65 s, a meta desde a Q-25 |
| NFR-04 | Capacidade | Vazão sustentada no pico de entrega (P-01) | req/min, taxa de 5xx, taxa de timeout | 500 req/min por 15 min com 0% de 5xx e < 0,1% de timeouts | Cenário k6 `nfr04` do `deploy/load/run_load.py` (S34-03): 80% do tráfego de 4 IPs do campus (NAT, P-04) e o resto de IPs externos, com os limites por IP do piloto e o limite por conta aumentado só no teste; por release, à mão. No gratuito, não atingível (ADR-03, 11/10/2026) |
| NFR-05 | Concorrência | Degradação controlada sob sobrecarga | Respostas 500/502/504, tempo de emissão do 503, tempo de recuperação | A 1.500 req/min: 0 respostas 500/502/504; 503 com `Retry-After` em ≤ 100 ms quando a fila de admissão está cheia (quem já esperava uma vaga recebe o 503 em até 1 s, P-11); recuperação ≤ 60 s após a carga | Cenário k6 `nfr05` do `run_load.py` (S34-03), com a recuperação medida em 90 s a 20 por minuto; por release, à mão. A recusa rápida com `Retry-After` também é testada no pytest (S10). No gratuito, sem 500/502/504 e com recuperação em 5,7 s, mas o 503 leva segundos (ADR-03, 11/10/2026) |
| NFR-06 | Disponibilidade | Disponibilidade externa no período letivo, sem cold start | % mensal de checks OK; latência da 1ª verificação de usuário do dia | ≥ 99,5% (P-05); 1ª verificação do dia ≤ 300 ms | UptimeRobot a cada 5 min em `/ready`, que também mantém o plano gratuito do Render acordado (ADR-03), configurado pelo autor (`deploy/piloto.md`); teste sintético da 1ª verificação nos dias úteis desde a S34-02 (`synthetic.yml`, `docs/runbook.md`, "Sintético diário") |
| NFR-07 | Segurança | Isolamento do `analyzer` | % dos controles conferidos | Fases 0 e 2 (contêiner próprio): 100% de nenhum segredo no ambiente, nenhuma rota de egress, rootfs read-only, UID ≠ 0, `cap_drop: ALL`, `no-new-privileges`, `pids_limit` ≤ 64 e memória ≤ 512 MB. Fase 1 (processo no Render): 100% de UID próprio (10002), ambiente sem segredos, seccomp bloqueando sockets de rede e `execve`, `RLIMIT_FSIZE` = 0 | Fases 0 e 2: teste de configuração (`docker inspect`) e teste de egress na CI. Fase 1: teste automatizado na imagem do Render (abrir socket, executar programa, gravar em disco e ler o ambiente da `api` falham) |
| NFR-08 | Segurança | Limites por análise (P-04) | Limites aplicados; % do corpus malicioso tratado sem 5xx | Timeout de 2 s (kill), `RLIMIT_AS` de 256 MB, ≤ 60.000 nós, profundidade ≤ 200, ≤ 50 KB, ≤ 1.000 linhas; 100% do corpus | Suíte de segurança da DoD (seção 8) na CI |
| NFR-09 | Segurança | Código do aluno nunca executado nem importado | Usos proibidos no código-fonte do projeto | 0 usos de `eval`, `exec`, `compile` (fora de `engine/parse.py`), `__import__`, `importlib`, `runpy` ou `pickle` sobre a entrada | Regras de segurança do ruff (Bandit), guarda de código em pytest e Semgrep com regras próprias (`.semgrep/ip-checker.yml`, S31-04, P-20), bloqueantes em todo PR |
| NFR-10 | Segurança | Transporte, cabeçalhos e CORS | Versão de TLS, cabeçalhos presentes, origens aceitas, nota | TLS ≥ 1.2, HSTS e CSP sem `unsafe-inline` em scripts. Na Fase 1 (SPA na Vercel, API no Render), mesma origem desde a Sprint 16, pelo *rewrite* de `/api/*` na Vercel (ADR-04), com o CORS só como plano B (`IPC_CORS_ORIGINS`, P-15); nas Fases 0 e 2, mesma origem e nenhum cabeçalho CORS. SSL Labs ≥ A | Teste automatizado de cabeçalhos e CORS pós-deploy; SSL Labs por release |
| NFR-11 | Privacidade | O código não persiste em logs, banco ou disco | Ocorrências de um marcador canário | 0 ocorrências | Teste canário na CI (pytest, pelos logs, pelo banco e pela borda); a busca mensal em produção desde a S35-04 (`canary.yml`, `docs/runbook.md`, "Canário mensal") |
| NFR-12 | Privacidade | Minimização e retenção da telemetria | Colunas existentes; idade máxima dos registros | Só as colunas do esquema 5.2.4; nenhum registro com mais de 12 meses (P-06) | Teste de esquema na CI; verificação mensal do job de expurgo |
| NFR-13 | Segurança | Dependências e imagens | CVEs críticas ou altas corrigíveis | 0 | gitleaks, `pip-audit` e `npm audit` em todo PR (`ci.yml`, job "Auditoria") e, com o Trivy da imagem do piloto, no workflow semanal `audit.yml`; bloqueantes desde a S31-03 (09/10/2026), depois da primeira triagem (P-20) |
| NFR-14 | Observabilidade | Logs estruturados | % de requisições com os campos obrigatórios; campos proibidos | 100% com `request_id`, `route`, `status`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`; 0 campos com código ou IP | Teste de esquema de log na CI |
| NFR-15 | Observabilidade | Métricas e alertas | Tempo até o alerta | Alerta em ≤ 5 min se P95 > 200 ms ou 5xx > 1%; em ≤ 10 min se `/ready` falhar (2 checks de 5 min do UptimeRobot) | Exercício de disparo de alertas feito na S21-02 (compose); no piloto, a cada release desde a S34-04 (`docs/runbook.md`, "Registro dos exercícios de alerta") |
| NFR-16 | Manutenibilidade | Qualidade estática e cobertura | % de cobertura; erros de lint/tipo | ≥ 90% em `ipc_analyzer/engine` (valor do rascunho) e ≥ 80% no restante; 0 erros de ruff, `mypy --strict`, ESLint e `tsc` | Gate na CI |
| NFR-17 | Manutenibilidade | Evolução de regras sem tocar no código | % de PRs de regra que alteram só dados | 100% dos PRs com label `rules` alteram apenas `rulesets/**` e `backend/tests/golden/**` | Conferido por quem faz o merge, com o modelo `.github/PULL_REQUEST_TEMPLATE/regras.md` (sem job de CI nem CODEOWNERS; Q-22) |
| NFR-18 | Correção | Precisão do motor | Falsos positivos e falsos negativos no corpus golden | 0 FP e 0 FN, com ≥ 3 casos por R-xx (P-08) | `pytest` golden na CI |
| NFR-19 | Acessibilidade | Conformidade com WCAG 2.1 AA | Violações axe *critical/serious*; fluxo por teclado | 0 violações; fluxo completo operável só pelo teclado | Playwright com axe-core na CI e checklist manual por release |
| NFR-20 | Portabilidade e recuperação | Implantação reproduzível | RTO; RPO da telemetria | RTO ≤ 30 min (VM limpa + `docker compose up`); RPO ≤ 24 h | Backup diário criptografado (`backup.yml`, S28-03; diário desde a S30-12) e ensaio de restauração uma vez por semestre (`docs/runbook.md`) |
| NFR-21 | Compatibilidade | Gramática alinhada à do Dikastis, Python 3.13+ (Q-01) | Divergências no corpus de sintaxe específica de versão | 0 | Testes de corpus por versão na CI |
| NFR-22 | Segurança | Autenticação e sessão | Parâmetros e atributos conferidos | Senha em Argon2id com os parâmetros mínimos da OWASP (19 MiB, 2 iterações, paralelismo 1); sessão no servidor com identificador aleatório de 256 bits guardado só como hash; cookie `HttpOnly`, `Secure` e `SameSite=Lax`, rotacionado no login e invalidado no logout, na troca de senha, na mudança de cargo e na remoção; expiração após 12 h sem uso e em no máximo 7 dias (Q-19); tokens de verificação de 256 bits, de uso único e válidos por 24 h; limite de tentativas por conta e por IP nas rotas de autenticação, com espera progressiva depois de 5 falhas em 15 min (premissa validada pelo autor em 12/10/2026) | Suíte de segurança da autenticação (seção 8, itens 16 a 20) |
| NFR-23 | Segurança | Autorização sem brechas | Rotas sem verificação; combinações cargo × ação × alvo testadas | 0 rotas da API sem exigência de sessão, além das listadas no FR-22; 100% da matriz do FR-27 testada por chamada direta à API | Teste que percorre o OpenAPI sem sessão (401 em tudo) e teste de matriz na CI |
| NFR-24 | Privacidade | Dados de conta e envio à LLM | Campos expostos; ocorrências do nome do aluno nas requisições ao provedor | Dados de conta mínimos (nome, e-mail, curso, tratamento, cargo, status e datas); tratamento visível só ao titular; 0 ocorrências do nome real do aluno nas requisições ao provedor; código nunca persistido, também no plágio e no feedback (NFR-11) | Provedor falso que inspeciona a requisição; teste de contrato das respostas sobre outras pessoas (sem tratamento); canário do NFR-11 estendido às rotas novas |
| NFR-25 | Correção | Precisão do detector de plágio | Similaridade nos pares de referência; tempo | Cópia com identificadores renomeados ≥ 99%; cópia com espaços e comentários alterados = 100%; funções ou blocos independentes reordenados ≥ 90% (premissa validada pelo autor em 12/10/2026); valores exatos de 99, 95, 90 e 80% na faixa que começa neles; dois códigos de 50 KB em ≤ 2 s no worker | Corpus de pares (`backend/tests/similarity/`) na CI |
| NFR-26 | Correção | Fidelidade do feedback ao motor | % de textos com apresentação e frase obrigatória exatas; contradições | 100% com a apresentação da tabela do FR-30 e a frase obrigatória do resultado; 0 textos que contradizem o motor ou que, no tratamento neutro, trazem autorreferência com marcação de gênero (lista de termos); IA principal e de reserva com 12 s por tentativa e prazo total de 28 s (com uma IA só, uma nova tentativa) e, se nenhuma devolver texto válido, o feedback montado por modelos, sem IA (ADR-06, item 6) | Testes com provedor falso, com respostas boas e adversariais, na CI; amostra manual com o provedor real a cada mudança de prompt ou de modelo |
| NFR-27 | Segurança | Confidencialidade dos gabaritos (ADR-10, revisto pela ADR-11 em 09/10/2026) | Gabaritos fora do repositório principal, da imagem, do disco, dos logs, da telemetria e do navegador; acesso da CI e da API | 0 arquivo de gabarito no `ip-checker` e na imagem; no piloto, só na memória do processo da API, baixados com credencial só de leitura; 0 bytes de texto do gabarito nas respostas, nos logs e na telemetria (teste canário); saída dos testes só com arquivo, regra e linha | `.gitignore` (`gabaritos/`), job "Gabaritos" do `ci.yml`, `backend/tests/official_answers/`, testes canário da Sprint 32, `rulesets/README.md` |
| NFR-28 | Desempenho | Custo da comparação com o gabarito (ADR-11) | P95 do `POST /api/v1/validate` com a comparação; tempo da comparação no analisador | P95 ≤ 200 ms e P99 ≤ 500 ms (os do NFR-01) com a comparação ligada; comparação de 2 códigos de 50 KB dentro do orçamento da similaridade (NFR-25) | "Carga no piloto" com uma questão com gabarito; teste de orçamento em `tests/similarity` |
| NFR-29 | Privacidade | Dados de alunos nos grupos de acompanhamento (ADR-13) [PLANEJADO, Sprint 47] | Colunas guardadas; idade dos registros; ocorrências de código | Só o nome de exibição e, opcionalmente, o login do Dikastis (Q-26), nunca CPF, e-mail ou matrícula; de cada verificação, só o resultado resumido (Q-27), sem o feedback (Q-28); 0 ocorrências de código (canário do NFR-11); nada de um período depois do encerramento dele ou de 12 meses do fim, o que vier primeiro (Q-29) | Teste de esquema e canário na CI; teste do expurgo por período |
| NFR-30 | Desempenho | Plágio da turma inteira (S40-02, S46-03) [PARCIAL: 60 soluções na S40-02; 100 na S46-03] | Tempo no worker | Matriz de 100 soluções (120 KB no total) em ≤ 5 s | Teste de orçamento com a turma sintética |

## 4. Backlog de User Stories

Toda história segue o formato "Como <persona>, quero <ação>, para <valor>". A tabela traz apenas a ação e o valor.

Desde a P-13 (02/10/2026), quem usa a ferramenta é a equipe da disciplina: nas histórias dos épicos E1 a E3 e E5 com persona "Aluno", leia-se "membro da equipe verificando o código de um aluno" (C-04). As histórias do acesso restrito, do plágio e do feedback estão nos épicos E6 e E7.

### Épico E1 — Submissão e verificação

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-01 | Aluno | colar meu código no editor, escolher a lista e pedir a verificação | saber, antes de enviar ao Dikastis, se usei algo não permitido | Dado um código sem violações e a Lista 1, Quando clico em "Verificar", Então vejo "Nenhuma violação encontrada" e a `ruleset_version`; Dado um código com `for` e a Lista 1, Quando verifico, Então vejo a violação R-34 com a linha e a coluna do `for`; Dado que nenhuma lista foi escolhida, Quando vejo o botão "Verificar", Então ele está desabilitado | Must | FR-01, FR-03, FR-04, FR-06, FR-12 |
| US-02 | Aluno | enviar um arquivo `.py` | não precisar copiar e colar à mão | Dado um `.py` UTF-8 de até 50 KB, Quando o seleciono ou arrasto, Então o conteúdo aparece no editor sem nenhum envio ao servidor; Dado um arquivo de mais de 50 KB ou com outra extensão, Quando o seleciono, Então vejo uma mensagem de rejeição e nada é enviado | Should | FR-02, FR-04 |
| US-03 | Aluno | ver o erro de sintaxe com linha e coluna | corrigir o código antes da verificação de permissões | Dado um código com parêntese não fechado na linha 5, Quando verifico, Então recebo `syntax_error` com linha 5, coluna e mensagem em PT-BR e nenhuma violação de regra; Dado um código com byte nulo, Quando verifico, Então recebo 422 `INVALID_INPUT` | Must | FR-04, FR-05, FR-12 |
| US-04 | Aluno | selecionar a questão que estou resolvendo | que as permissões e proibições explícitas da questão prevaleçam (R-01) | Dado a questão `L3-Q2` cadastrada com `allow` para um construto, Quando verifico um código que o usa com essa questão selecionada, Então não aparece violação desse construto; Dado o mesmo código sem questão selecionada, Quando verifico, Então a violação aparece com o aviso `QUESTION_RULES_NOT_APPLIED`; Dado uma lista sem questões cadastradas, Quando abro o seletor, Então vejo "Nenhuma questão com regra específica cadastrada" | Must | FR-03, FR-11, FR-12 |
| US-39 | Monitor | escolher o período antes da lista e da questão | corrigir uma lista atrasada com as regras do período certo | Dado o `ATIVO` em 2027.1, Quando escolho 2026.2, a Lista 3 e a L3-Q9, Então a resposta traz a `ruleset_version` de 2026.2; Dado nenhum período escolhido, Então vale o ativo | Should | FR-33 |

### Épico E2 — Conformidade com o documento de permissões

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-05 | Aluno | ver as proibições gerais marcadas como "Anulação imediata" | corrigir primeiro o que anula a questão | Dado um código com `try`/`except` em qualquer lista, Quando verifico, Então recebo R-06 com categoria `ANULACAO`; Dado um código com `import`, `{1, 2}`, `exit()`, `class`, `*args`, `break`, `pass`, `None` e `global`, Quando verifico, Então cada ocorrência gera a regra correspondente entre R-05 e R-14 | Must | FR-08, FR-12 |
| US-06 | Aluno | ser avisado quando a solução não implementa o assunto obrigatório da lista | não ter a questão anulada por deixar de usar o tópico treinado | Dado a Lista 6 e um código sem recursão, Quando verifico, Então recebo R-68 com categoria `EXIGENCIA`; Dado a Lista 6 e uma função que chama a si mesma, Quando verifico, Então não há violação R-68; Dado a Lista 2 e um código sem `for` nem `while`, Quando verifico, Então recebo R-02 `EXIGENCIA` (mapeamento de Q-05) | Must | FR-10 |
| US-07 | Aluno | usar `zip()` para percorrer mais de um índice no `for` a partir da Lista 2 | que a permissão condicional seja aplicada exatamente como no documento | Dado a Lista 2 e `for a, b in zip(x, y):`, Quando verifico, Então não aparece violação de `zip` nem do desempacotamento `a, b`; Dado a Lista 2 e `z = zip(x, y)`, Quando verifico, Então recebo R-37 com a mensagem da condição; Dado a Lista 5 e `z = zip(x, y)`, Quando verifico, Então não há violação (R-64, Q-04) | Must | FR-09 |
| US-08 | Aluno | saber a partir de qual lista um construto é permitido | entender a progressão cumulativa | Dado a Lista 2 e `.append()`, Quando verifico, Então a violação diz "permitido a partir da Lista 3" (R-46, `FORA_DA_LISTA`); Dado a Lista 4 e `.append()`, Quando verifico, Então não há violação (R-03); Dado `eval(...)`, Quando verifico, Então recebo R-04 `NAO_CONSTA` sem lista de liberação | Must | FR-06, FR-07, FR-12 |

### Épico E3 — Feedback e consulta

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-09 | Aluno | clicar em uma violação e ir à linha destacada no editor | corrigir rapidamente | Dado um relatório com violação na linha 7, Quando clico no card, Então o cursor vai para a linha 7 e o trecho aparece sublinhado; Dado o foco no card, Quando pressiono Enter, Então acontece o mesmo | Should | FR-13, FR-20 |
| US-10 | Aluno | consultar as permissões vigentes da lista e da questão | planejar a solução sem reler o documento | Dado a Lista 3, Quando abro "Permissões", Então vejo R-15…R-58 como permitidas, R-05…R-14 como proibições gerais e a exigência R-02; Dado uma questão com override, Quando a seleciono, Então o override aparece destacado | Could | FR-14 |
| US-11 | Monitor | verificar o código de um aluno durante a correção ou o atendimento, com a minha conta (P-13) | dedicar o atendimento à lógica, não às permissões | Dado o código colado e a lista do aluno, Quando verifico, Então obtenho o relatório da lista e da questão; Dado o fim da verificação, Quando procuro o canário em logs e no banco, Então não há cópia do código (NFR-11) | Should | FR-01, FR-12 |
| US-41 | Membro da equipe | ver no feedback a linha e o motivo de cada violação | que o aluno saiba onde e por que a questão foi anulada | Dado `for` e `range()` na Lista 1, Quando gero o feedback sem IA, Então cada construção aparece com a linha e com a lista que a libera; Dado qualquer feedback, Então a frase obrigatória do FR-30 é a mesma | Should | FR-34 |
| US-42 | Monitor-chefe | ajustar o tom, as dicas e os exemplos do feedback por PR | padronizar a equipe sem programar | Dado um `estilo.yaml` inválido, Quando a CI roda, Então falha; Dado uma mudança aprovada, Quando o deploy termina, Então o próximo feedback a usa | Could | FR-35 |
| US-43 | Membro da equipe | receber do "Aprimorar com IA" um texto que só fala do que o verificador achou | nunca mandar ao aluno um erro inventado ou a solução pronta | Dado um texto da IA que cita uma construção ausente dos achados, Então ele é recusado e reescrito ou trocado pelo texto sem IA; Dado um texto com 3 ou mais linhas de código ou com um trecho igual ao gabarito, Então é recusado | Should | FR-35 |

### Épico E4 — Governança do ruleset

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-12 | Professor/Coordenação | alterar as regras das listas editando o ruleset, sem mexer no código | manter a ferramenta fiel ao documento de permissões | Dado um PR que altera só `rulesets/`, Quando a CI roda, Então o `ipc-rules validate` e o golden rodam e quem faz o merge confere a minha aprovação (Q-22); Dado o merge na `main`, Quando o deploy termina, Então a nova `ruleset_version` aparece nas respostas; Dado um ruleset inválido em produção, Quando o analisador inicia, Então ele não fica pronto e a versão anterior continua atendendo | Must | FR-15, FR-21 |
| US-13 | Monitor | cadastrar as permissões e proibições explícitas de uma questão | que a ferramenta reflita o enunciado (R-01) | Dado `questions/L3-Q2.yaml` com `allow`/`deny` de R-xx ou de fatos e o campo `source`, Quando o PR passa na CI, é aprovado e publicado, Então a questão aparece no seletor; Dado um PR aberto por mim, Quando tento fazer o merge, Então ele exige a aprovação de um monitor-chefe ou professor, e não a minha; Dado um override que libera uma proibição geral (R-05…R-14), Quando a CI roda, Então o PR exige aprovação de professor; Dado um override que cita um R-xx inexistente, Quando a CI roda, Então o PR falha com o caminho do erro | Must | FR-11, FR-15, FR-21 |
| US-14 | Monitor-mantenedor | validar o ruleset com um comando, localmente e na CI | impedir que uma regra inválida chegue à produção | Dado um ruleset válido, Quando executo `ipc-rules validate rulesets/2026.2`, Então o comando sai com código 0; Dado um ruleset inválido, Quando executo, Então recebo erros com o caminho do campo e código ≠ 0; Dado um PR, Quando a CI roda, Então o mesmo comando é bloqueante | Must | FR-15, FR-21 |
| US-36 | Monitor-mantenedor | começar um período novo e guardar os gabaritos do anterior sem mudar código | as questões mudam a cada período, e os gabaritos de cada período encerrado protegem os seguintes contra falsos positivos | Dado o fim de 2026.2, Quando rodo `ipc-rules new-period 2027.1 --from 2026.2` e troco o período ativo num só arquivo, Então o deploy usa 2027.1 sem outra mudança; Dado um gabarito de 2026.2 no repositório privado, Quando a CI roda com 2027.1 ativo, Então ele é conferido com as questões de 2026.2 e tem zero violação | Should | FR-31, NFR-27 |
| US-40 | Monitor-mantenedor | encerrar um período antigo com uma simulação antes | manter só os 6 períodos mais recentes carregados, sem perder nada do Git | Dado `retire-period --dry-run`, Então nada muda no disco; Dado o período ativo ou um da janela, Quando tento encerrar, Então o comando recusa | Could | FR-33 |

### Épico E5 — Operação, segurança e telemetria

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-15 | Monitor-mantenedor | que todo código submetido seja analisado só no `analyzer` isolado e com limites | que nenhuma submissão derrube o serviço nem acesse dados ou credenciais | Dado um payload com 1.000 níveis de parênteses, Quando é enviado, Então recebo 422 `ANALYSIS_LIMIT` em ≤ 2,5 s e `/ready` continua 200; Dado `__import__("os").system("touch /tmp/canary")`, Quando é enviado, Então recebo violações e o arquivo não é criado; Dado o contêiner `analyzer`, Quando a CI o inspeciona, Então ele não tem segredo, egress, root nem FS gravável | Must | FR-04, FR-05 |
| US-16 | Professor/Coordenação | consultar as regras mais violadas por lista, questão e período | ajustar o ensino e os enunciados | Dado validações registradas, Quando consulto `telemetry.v_top_rules_by_list` com o papel `ipc_reader`, Então vejo contagens por `rule_id`; Dado qualquer view, Quando inspeciono as colunas, Então não há código, IP nem identificador de cliente | Should | FR-16, FR-17 |
| US-17 | Monitor-mantenedor | ter health/readiness, rate limit e logs estruturados sem código | operar e diagnosticar com segurança | Dado o analisador fora do ar, Quando consulto `/ready`, Então recebo 503; Dado 11 requisições em 1 min do mesmo cliente anônimo, Quando chega a 11ª, Então recebo 429 com `Retry-After`; Dado 60 clientes anônimos distintos atrás de um mesmo IP do campus, Quando cada um faz 5 verificações em 1 min, Então nenhum recebe 429; Dado qualquer requisição, Quando leio o log, Então há `request_id` e `latency_ms` e não há campo com código ou IP | Must | FR-18, FR-19 |
| US-18 | Aluno | receber uma mensagem clara quando minha entrada for rejeitada ou o serviço estiver sobrecarregado | saber se devo corrigir algo ou tentar de novo | Dado um código acima de 50 KB, Quando verifico, Então vejo "O código excede 50 KB" (413); Dado uma resposta 429 ou 503, Quando ela é exibida, Então vejo o tempo de espera vindo do `Retry-After`; Dado um timeout de rede de 10 s, Quando ele ocorre, Então vejo a opção "Tentar novamente" | Must | FR-04, FR-19, FR-20 |
| US-19 | Monitor-mantenedor | receber alertas de latência, erro e indisponibilidade | agir antes que os alunos sejam afetados na véspera do prazo | Dado P95 > 200 ms por 5 min, Quando isso ocorre, Então chega um alerta no e-mail da equipe; Dado `/ready` falhando em 2 checks seguidos do UptimeRobot (5 min cada), Quando isso ocorre, Então chega um alerta de indisponibilidade por e-mail | Should | FR-18 |
| US-20 | Monitor-mantenedor | ter guia de onboarding, runbook e guia de manutenção do ruleset | assumir o projeto na troca semestral de monitores | Dado um mantenedor novo, Quando segue o README, Então sobe o ambiente local com `docker compose up` em ≤ 30 min; Dado um incidente de perda da VM, Quando segue o runbook, Então restaura o serviço em uma VM limpa em ≤ 30 min (NFR-20) | Should | FR-15, FR-21 |
| US-21 | Aluno | usar a interface no celular, pelo teclado e com leitor de tela | verificar meu código em qualquer dispositivo | Dado uma viewport de 360 px, Quando uso o fluxo completo, Então não há rolagem horizontal; Dado a CI, Quando roda o axe-core, Então há 0 violações *critical/serious* (NFR-19) | Should | FR-20 |
| US-22 | Aluno | receber a verificação em menos de 1 s mesmo na véspera do prazo | não abandonar a ferramenta no momento de maior uso | Dado uma carga de 500 req/min, Quando verifico, Então o P95 no servidor é ≤ 200 ms (NFR-01, NFR-04); Dado uma carga de 1.500 req/min, Quando o sistema satura, Então recebo 503 com `Retry-After` em vez de um erro genérico (NFR-05) | Must | FR-19 |
| US-23 | Professor/Coordenação | receber, ao fim do piloto, um relatório com os critérios de eficácia medidos | decidir com dados se o projeto migra para o servidor do CIn | Dado o fim do piloto, Quando o relatório é gerado, Então ele mostra, para cada critério da P-09, o valor medido, a meta e se foi atingido; Dado que a coordenação aprova a migração, Quando o runbook de migração é executado, Então o serviço passa a rodar no servidor do CIn com a mesma `ruleset_version` e sem perda da telemetria | Should | FR-17 |
| US-35 | Monitor-mantenedor | ensaiar o rollback e a restauração do backup do piloto, com o tempo medido | saber, antes de um incidente de verdade, que o piloto volta ao ar e não perde as contas | Dado o runbook, Quando faço o rollback da API e da página, Então as duas voltam à versão anterior em ≤ 5 min e o tempo fica registrado; Dado o backup cifrado mais recente, Quando o restauro num banco descartável, Então as contagens batem com as do piloto e o RTO fica registrado (NFR-20) | Should | — |

### Épico E6 — Acesso restrito e gestão da equipe (P-13)

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-24 | Membro da equipe | me registrar com e-mail institucional e senha | ter acesso depois de verificar o e-mail e ser aprovado | Dado um e-mail fora de `@cin.ufpe.br` ou `@ufpe.br`, inclusive `x@xcin.ufpe.br` e `x@ee.ufpe.br`, Quando me registro, Então o cadastro é recusado; Dado uma senha que viole qualquer regra, Quando ela chega direto à API, Então o backend a recusa; Dado o cadastro enviado, Quando confirmo pelo link do e-mail, Então o status passa a `aguardando_aprovacao`; Dado um link expirado ou já usado, Quando o abro, Então ele não funciona; Dado o e-mail verificado e o cadastro ainda não aprovado, Quando tento entrar, Então vejo "aguardando aprovação" e nenhum endpoint me retorna dados | Must | FR-22, FR-23, FR-25 |
| US-25 | Membro da equipe | me registrar e entrar com o Google | não precisar de outra senha | Dado um e-mail Google fora dos domínios, Quando tento entrar, Então sou recusado, mesmo com o `hd` alterado na requisição; Dado `email_verified` falso, Quando tento entrar, Então sou recusado; Dado um registro pelo Google, Quando envio o formulário complementar, Então entro na fila de aprovação e não tenho acesso antes dela; Dado uma conta criada com senha, Quando entro pelo Google com o mesmo e-mail, Então chego à mesma conta | Must | FR-24, FR-25 |
| US-26 | Membro da equipe | entrar com nome ou e-mail e senha | começar a correção | Dado nome ou e-mail e senha corretos de uma conta ativa, Quando entro, Então vejo o painel principal; Dado credenciais inválidas, Quando tento entrar, Então vejo "credenciais inválidas" sem saber se a conta existe; Dado uma conta aguardando aprovação, recusada ou removida, Quando entro com a senha correta, Então vejo a mensagem do status; Dado nenhum login, Quando abro a página, Então só vejo Registrar e Entrar, e nenhum endpoint retorna dados | Must | FR-22, FR-25 |
| US-27 | Monitor-chefe, professor ou desenvolvedor | aprovar ou recusar pedidos, escolhendo o cargo | que só a equipe tenha acesso | Dado um pedido pendente, Quando aprovo como monitor-chefe, Então só posso escolher monitor-chefe ou monitor; Dado um pedido aprovado, Quando a pessoa entra, Então tem acesso com o cargo escolhido; Dado um pedido recusado, Quando a pessoa entra com a senha correta, Então vê "cadastro recusado"; Dado um monitor, Quando chama a rota de aprovação diretamente, Então recebe 403 | Must | FR-27, FR-28 |
| US-28 | Monitor-chefe, professor ou desenvolvedor | alterar cargos, remover e reativar contas dentro da minha alçada | manter a equipe de cada período atualizada | Dado alguém que já foi monitor-chefe, Quando o removo, Então a conta vira "Conselheiro"; Dado alguém que nunca foi, Quando o removo, Então vira "Ex-monitor"; Dado um professor, Quando é removido, Então fica inativo; Dado um monitor-chefe, Quando tenta alterar ou remover um professor, inclusive pela API, Então recebe 403; Dado qualquer pessoa que não seja o desenvolvedor, Quando tenta alterar a conta dele, Então recebe 403 | Must | FR-27, FR-28 |
| US-29 | Membro da equipe | editar meu nome, curso, tratamento e senha | manter meus dados e o tratamento do feedback corretos | Dado o perfil, Quando mudo o tratamento, Então o próximo feedback usa o novo; Dado uma conta do Google, Quando defino uma senha, Então passo a entrar também por senha; Dado qualquer tela ou resposta da API sobre outra pessoa, Quando a inspeciono, Então o tratamento dela não aparece; Dado o perfil, Quando procuro mudar o meu cargo, Então não há opção, e a API recusa a tentativa | Must | FR-26 |
| US-30 | Desenvolvedor | ter a minha conta criada por *seed* e protegida | administrar a ferramenta desde o primeiro deploy | Dado um banco vazio, Quando o serviço sobe, Então a conta do desenvolvedor existe, ativa, com os dois e-mails e a senha da variável de ambiente; Dado outra pessoa, Quando tenta registrar `vlacg@cin.ufpe.br` ou `vinicius.leoncio@ufpe.br`, Então é recusada; Dado a tela de gerenciamento, Quando outra pessoa vê o desenvolvedor, Então ele aparece como "Monitor e desenvolvedor" | Must | FR-25, FR-27 |

### Épico E7 — Apoio à correção (P-13)

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-31 | Membro da equipe | comparar duas soluções e ver a similaridade e a classificação | encontrar indícios de plágio sem depender só da leitura | Dado um código e uma cópia em que só as variáveis foram renomeadas, Quando verifico, Então a similaridade é ≥ 99% e aparece "Plágio"; Dado similaridades de exatamente 99, 95, 90 e 80%, Quando são classificadas, Então caem na faixa que começa nesse valor; Dado qualquer resultado, Quando ele aparece, Então há o aviso de que é um indício e de que a decisão é da equipe | Must | FR-29 |
| US-33 | Membro da equipe | corrigir várias soluções seguidas, no computador ou no celular | verificar, gerar o feedback e copiar em poucas ações, sem levar o nome de um aluno para o próximo | Dado um feedback gerado, Quando aciono "Próximo aluno", Então código, nome, anotação e resultado são limpos, a lista continua escolhida e o foco vai para o editor; Dado o editor com foco, Quando aperto Ctrl+Enter, Então o código é verificado e o foco vai para o título do resultado; Dado um celular de 375 px, Quando abro qualquer tela, Então nada passa da largura da tela; Dado um relatório, Quando clico numa violação, Então o trecho fica selecionado no editor | Must | FR-07, FR-30 |
| US-34 | Membro da equipe | ver indícios de que uma solução pode ter sido gerada por IA, com o motivo de cada um | decidir com quem conversar, sem acusar ninguém por um número | Dado uma solução com várias violações (por exemplo `break`, `pass` e `continue` juntos, vários `pass` ou construções da Lista 6 numa solução da Lista 3), com construções acima da lista ou muito parecida com uma solução de referência gerada por IA para a questão, Quando verifico, Então vejo cada indício com o motivo e o trecho, e o texto diz que não é prova; Dado uma solução sem indícios, Então nada é mostrado; Dado o painel, Então nenhum dado do aluno sai do servidor | Should (Q-21) | FR-29 |
| US-32 | Membro da equipe | gerar um feedback para o aluno a partir do resultado do IP-Checker | devolver um texto cordial e coerente sem escrever do zero | Dado um código com violações, Quando gero o feedback, Então ele contém "Sua questão apresenta problemas, como o uso de ..., portanto ela foi anulada." com as proibições encontradas; Dado um código sem violações, Então contém "Sua questão está ótima, não houve nenhuma violação de regras."; Dado o tratamento feminino, Então a apresentação e todas as autorreferências estão no feminino; Dado o tratamento neutro, Então não há autorreferência com marcação de gênero; Dado a requisição ao provedor, Quando a inspeciono, Então o nome real do aluno não aparece | Must | FR-30 |
| US-37 | Membro da equipe | escolher o período (seletor na Sprint 43; até lá, o ativo), a lista e a questão e ver, junto com as violações, o quanto o código do aluno se parece com o gabarito oficial e em quê | entender a solução do aluno em relação à esperada, sem ver nem expor o gabarito | Dada a questão L1-Q1 de 2026.2 com gabarito, Quando verifico o código de um aluno, Então vejo a porcentagem e a faixa (FR-29), as construções em comum, só no aluno e só no gabarito e as linhas do aluno que coincidem, e nenhum texto do gabarito; Dada uma questão sem gabarito, Então a verificação segue normal, com o aviso "sem gabarito para comparar" | Should | FR-32, NFR-27, NFR-28 |
| US-38 | Membro da equipe | no plágio, ver também a semelhança de cada aluno com o gabarito e um alerta quando os dois códigos coincidem com ele | perceber que o gabarito pode estar circulando entre os alunos (má conduta) sem acusar ninguém por um número | Dados os códigos A e B de uma questão com gabarito, Quando comparo, Então vejo A×B, A×gabarito e B×gabarito na métrica da ADR-07; Quando os três passam do limiar e os códigos têm o tamanho mínimo, Então aparece o alerta "possível vazamento do gabarito", só para mim e sem registro | Should | FR-32, NFR-27 |
| US-44 | Membro da equipe | ver a turma inteira como matriz, com grupos de soluções parecidas e os trechos de cada par | achar os grupos de cópias de uma vez e saber quanto o detector acerta | Dada a turma sintética de 30 soluções, Então os dois grupos de cópias aparecem e nenhuma independente passa de 90%; Dado um par com gabarito, Então vejo quanto da semelhança o gabarito explica | Should | FR-29, FR-37 |

### Épico E8 — Acompanhamento dos alunos (proposta de 12/10/2026; Q-26 a Q-29 decididas no mesmo dia)

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-45 | Monitor | criar o meu grupo de acompanhamento, convidar colegas e cadastrar os alunos pelos quais sou responsável | acompanhar os mesmos alunos sozinho, em dupla ou em trio | Dado um convite, Quando o colega aceita, Então ele vê o histórico do grupo; Dado um aluno em dois grupos, Então aparece nos dois; Dado alguém que sai do grupo, Então os registros continuam | Could | FR-36 |
| US-46 | Monitor | ver o histórico de um aluno meu, com quem fez cada verificação | acompanhar a evolução e dividir o trabalho | Dado um aluno do grupo, Quando abro o histórico, Então vejo, de cada verificação, o resultado resumido (lista, questão, validada ou anulada e por quê), a faixa dos indícios e do alerta de plágio e quem executou, sem o código nem o feedback; Dado um monitor fora do grupo, Quando chama a rota, Então recebe 403 | Could | FR-36 |
| US-47 | Monitor-chefe ou professor | ver todos os grupos do período, só para leitura | supervisionar a monitoria sem editar o trabalho dos monitores | Dado o Gerenciar, Então vejo os grupos e o histórico; Dado uma tentativa de edição, inclusive pela API, Então recebo 403 | Could | FR-36 |

## 5. Arquitetura do Sistema e Stack

### 5.1 Diagrama conceitual

Topologia de referência, usada localmente na Fase 0 e no servidor do CIn na Fase 2:

```
 ZONA NÃO CONFIÁVEL (Internet)
 +--------------------------------------------+
 | Navegador do Aluno / Monitor               |
 | SPA React + editor próprio (código só em RAM) |
 +----------------------+---------------------+
                        | (1) HTTPS POST /api/v1/validate {code, list_number, question_id?}
========================|============ TB-1: Internet -> Borda ===================================
 FASES 0 E 2: MÁQUINA LOCAL OU SERVIDOR DO CIn + DOCKER COMPOSE (P-03)
 +----------------------v---------------------+
 | caddy: TLS, HSTS, CSP, corpo <= 128 KB     |
 | timeouts 10 s, serve a SPA, log sem IP     |
 +----------------------+---------------------+
                        | (2) HTTP interno, rede edge_net
========================|============ TB-2: Borda -> API =======================================
 +----------------------v---------------------+       +-----------------------------------+
 | api (FastAPI): NUNCA faz parse nem exec    |  (8)  | PostgreSQL gerenciado (Supabase)  |
 | (3) schema, 50 KB, 1000 linhas, rate limit |------>| schema telemetry: sem código/IP   |
 |     e admissão; (7) valida resposta        | async | papel ipc_writer: só INSERT       |
 +----------------------+---------------------+ TB-4  +-----------------------------------+
                        | (4) HTTP interno, rede analyzer_net (internal: true, sem egress)
========================|============ TB-3: API -> zona contaminada ============================
 +----------------------v----------------------------------------------------------------+
 | analyzer: sem segredos, rootfs read-only, UID 10001, cap_drop ALL, pids<=64, 512 MB   |
 |  supervisor Pebble -(5)-> worker descartável [RLIMIT_AS 256 MB, timeout 2 s, kill]    |
 |  worker: guards -> ast.parse -> limites AST -> fatos -> política -> exigências        |
 |  (6) resultado JSON <- worker; ruleset compilado e imutável embutido na imagem        |
 +---------------------------------------------------------------------------------------+

 TB-5 CADEIA DE ENTREGA: rulesets/*.yaml + código (GitHub, PR revisado) -> GitHub Actions
 (lint, testes, golden, segurança) -> Fase 1: deploy hooks do Render e da Vercel; Fase 2 [PLANEJADO]: GHCR por digest -> deploy SSH -> compose
```

Topologia do piloto (Fase 1, 2027.1), em que o Render não oferece rede interna nem flags de contêiner e o isolamento passa a ser por processo (ADR-03):

```
 +-----------------------------+  (1) HTTPS GET da SPA   +-----------------------------+
 | Navegador do aluno/monitor  |------------------------>| Vercel: SPA estática        |
 +--------------+--------------+                         | CSP e HSTS (vercel.json)    |
                |                                        +-----------------------------+
                | (2) HTTPS POST /api/v1/validate (CORS: só a origem da SPA)
                | (5) UptimeRobot: GET /ready a cada 5 min (mantém o Render acordado; alerta)
================|============ TB-1: Internet -> Render ============================================
 +--------------v-----------------------------------------------------------------------+
 | Render: 1 serviço Docker (TLS na borda do Render), supervisord como processo pai     |
 |  api (UID 10001): FastAPI, limites, rate limit, admissão; credencial ipc_writer      |
 |     | (3) HTTP em 127.0.0.1:8001                                                     |
 |  ===|======== TB-3: processo da API -> processo contaminado =====================    |
 |     v                                                                                |
 |  analyzer (UID 10002, ambiente vazio): pool Pebble; workers com seccomp (sem         |
 |  socket de rede, sem execve), RLIMIT_AS 160 MB, RLIMIT_FSIZE=0, timeout de 2 s       |
 +--------------+-----------------------------------------------------------------------+
                | (4) assíncrono, TLS (contas a partir da Sprint 13; telemetria na 21)
================|============ TB-4: Render -> banco =============================================
 +--------------v---------------+
 | Supabase (PostgreSQL): papel |
 | ipc_writer, só INSERT        |
 +------------------------------+
```

Topologia com acesso restrito (a partir da Sprint 16, ADR-04): a página e a API ficam na mesma origem por um *rewrite* na Vercel, o que mantém o cookie de sessão como primário e dispensa o CORS. Só a `api` fala com o Google, com o serviço de e-mail e com o provedor de LLM; o analisador continua sem rede e sem segredos:

```
 +-----------------------------+  (1) HTTPS, mesma origem  +----------------------------------+
 | Navegador da equipe         |-------------------------->| Vercel: SPA estática e rewrite   |
 | cookie de sessão HttpOnly   |                           | de /api/* para o Render          |
 +--------------+--------------+                           +---------------+------------------+
                | (2) login com Google: redirecionamento OIDC              | (3) /api/*
                v     (state, nonce, PKCE)                                 |
 +-----------------------------+                                           |
 | Google: tela de login       |                                           |
 +-----------------------------+                                           |
============================ TB-1: Internet -> Render =====================|====================
 +-------------------------------------------------------------------------v--------------------+
 | Render: api (UID 10001): sessão, cargos (FR-27), autenticação, plágio e feedback             |
 |   segredos só aqui: banco, cliente OAuth do Google, e-mail e chave da LLM                    |
 |     | (4) HTTP em 127.0.0.1:8001                                                             |
 |  ===|======== TB-3: processo da API -> processo contaminado ===============================  |
 |     v                                                                                        |
 |  analyzer (UID 10002, ambiente vazio, sem rede): análise, similaridade (FR-29) e remoção     |
 |  de comentários para o feedback; workers com seccomp, limites e timeout de 2 s               |
 +--------------+-------------------------------------------------------------------------------+
                | (5) só a api sai para a internet, com TLS
================|============ TB-4 e TB-6: Render -> serviços externos ==========================
                +--> Supabase (PostgreSQL): contas e sessões, depois telemetria (papel ipc_app)
                +--> Google: troca do código, chaves públicas (JWKS) e validação do ID token
                +--> E-mail: SMTP ou API transacional (Q-17)
                +--> Provedor de LLM (Q-16): código sem comentários e [ALUNO] no lugar do nome
```

### 5.2 Descrição dos componentes e do fluxo

#### 5.2.1 Componentes

- **C1 — SPA web (`frontend/`).** Editor próprio (`components/CodeEditor.tsx`: área de texto com numeração de linhas, Tab e marcação das linhas no gutter; CodeMirror 6 e a leitura de `.py` com `FileReader` (FR-02) ficaram no backlog), seletores de lista e questão alimentados por `GET /api/v1/lists`, que já traz as questões (FR-03), chamada a `/validate` com `AbortController` de 10 s, violações agrupadas com clique na linha (FR-13, S26-03) e renderização dos estados (FR-20). Até a S13-03, gerava um `X-Client-Id` (`crypto.randomUUID()` guardado em `sessionStorage`), usado só pelo rate limit. O código **não** é gravado em `localStorage`, para não ficar exposto em computadores compartilhados de laboratório. Na Fase 1, a SPA é servida pela Vercel; até a Sprint 16, chamava a API no Render com CORS restrito à sua origem, e desde então a Vercel repassa `/api/*` ao Render na mesma origem (ADR-04). A partir da Sprint 13, a SPA ganha as telas Entrar, Registrar, verificação de e-mail, espera de aprovação, Perfil, Gerenciamento (FR-28) e Plágio (FR-29) e o botão Gerar feedback (FR-30), com roteamento no cliente; as chamadas usam o cookie de sessão da mesma origem (ADR-04), e o `X-Client-Id` deixa de ser necessário.
- **C2 — Borda (`caddy`).** TLS automático via ACME e HSTS (Fase 2), CSP sem `unsafe-inline` e os demais cabeçalhos de segurança, barreira anti-abuso de 128 KiB aplicada antes de ler o corpo (um `Content-Length` maior recebe 413 com `Connection: close`, e um corpo sem `Content-Length` recebe 411; o limite contratual de 50 KB fica na API), timeouts de leitura e escrita de 10 s, *reverse proxy* de `/api/*`, `/health` e `/ready` para `api:8000` e arquivos estáticos da SPA. O Caddy não tem log de acesso (a API registra cada requisição, sem IP), e o filtro dos demais logs remove IP, cabeçalhos e URL. Os erros da borda (411, 413 e API fora do ar) seguem o envelope do contrato. Na Fase 0, responde em HTTP só em `127.0.0.1:8180` (S9-02). A SPA e a API ficam na mesma origem, então não há cabeçalho CORS. Na Fase 1 não há Caddy: a borda é a do Render (TLS) e a da Vercel, e o limite de corpo é aplicado pela própria `api`.
- **C3 — `api` (FastAPI).** Cadeia de middlewares nesta ordem: `request_id`, guarda de tamanho (413), rate limit em memória (janela deslizante de 60 s, P-11: 10/min por `X-Client-Id`; por IP, 120/min para IPs externos e 1.000/min para as faixas do campus em `IPC_RATE_LIMIT_CAMPUS_CIDRS`; IPv6 pelo prefixo /64; IP e identificador só em RAM, como hash com sal do processo, e TTL de 2 min), validação Pydantic (FR-04), admissão (`asyncio.Semaphore` com capacidade = 2 × workers, fila de até 64 e espera máxima de 1 s, senão 503 `OVERLOADED`), cliente `httpx` para o analisador (timeout de 3 s), validação de esquema e tamanho (≤ 256 KB) da resposta do analisador, resposta ao cliente e enfileiramento da telemetria. Um contrato `import-linter` proíbe `import ast` no pacote `ipc_api`, de modo que a API nunca analisa código (NFR-09). O IP do cliente usado no rate limit é o da conexão ou, com `IPC_TRUSTED_PROXY_HOPS` = 1 (Caddy nas Fases 0 e 2), o último endereço do `X-Forwarded-For`, escrito pelo proxy; o que o cliente manda nesse cabeçalho é ignorado. No piloto, desde a S30-03 (P-12 e P-15 b), o cliente vem do IP que o middleware da página manda com o `IPC_EDGE_SECRET`, do `for=` do `Forwarded` (`IPC_TRUST_FORWARDED_HEADER=1`) ou da 4ª entrada do `X-Forwarded-For` a partir do fim (`IPC_TRUSTED_PROXY_HOPS=4`), nessa ordem (`deploy/piloto.md`). Com o acesso restrito (Sprint 13), uma dependência de sessão vem antes do limite de taxa, que passa a ser por conta. Desde a Sprint 25, um limite folgado por IP (600/min; 6.000/min no campus) vale para todo `/api/*` antes da sessão, o prazo do cliente do analisador vale para a chamada inteira e segue para o analisador em `X-IPC-Budget-Ms`, e uma exceção inesperada vira 500 `INTERNAL_ERROR` em JSON (S25-04).
- **C4 — `analyzer`.** FastAPI interno com 1 processo uvicorn e um `pebble.ProcessPool` (2 workers [PREMISSA P-04], contexto `forkserver`, `max_tasks=500`). O *initializer* de cada worker aplica `RLIMIT_AS` = 256 MB, `RLIMIT_FSIZE` = 0 e `RLIMIT_NOFILE` = 32. `RLIMIT_CPU` não é usado porque é cumulativo por processo; o limite de tempo é o timeout de parede de 2 s, com *kill* e substituição do worker. Endpoints internos: `POST /internal/analyze`, `GET /internal/ruleset/manifest`, `GET /internal/rulesets/effective`, `GET /internal/health`. Na Fase 1, o `analyzer` roda como processo separado dentro do serviço do Render: UID 10002, ambiente vazio, escuta só em `127.0.0.1` e workers com seccomp sem sockets de rede nem `execve` (biblioteca `pyseccomp`); são 2 workers de até 160 MB para caber nos 512 MB do plano (calibrado na S11-01: o pior caso de 50 KB é analisado dentro desse limite).
- **C5 — Motor de regras (`backend/src/ipc_analyzer/engine`).** Funções puras sem estado global mutável, detalhadas em 5.2.3.
- **C6 — Ruleset (`rulesets/`).** YAML validado pelo carregador do analisador e pelo `ipc-rules validate` na CI (S24-02). O analisador carrega o ruleset uma vez, como estrutura imutável (FR-15), e publica o `ruleset_sha256` no manifesto. Desde a S35-05, o `ipc-rules schema` gera os esquemas JSON (`rulesets/schema/`), que a CI confere, e o `ipc-rules compile` grava o ruleset em JSON com o mesmo `ruleset_sha256`.
- **C7 — Telemetria (Sprint 21).** Fila `asyncio.Queue` limitada a 10.000 eventos, gravação em lote (100 eventos ou 2 s) via `asyncpg` com o papel `ipc_writer`. Se a fila transbordar, o evento é descartado e a métrica `telemetry_dropped_total` é incrementada; a resposta ao aluno nunca é bloqueada. **Implementado na Sprint 21** (`backend/src/ipc_api/telemetry.py`): o mesmo vale quando o banco falha; os contadores de gravados, descartados e lotes com falha aparecem em `GET /health/slo`, já que o `/metrics` ainda não existe.
- **C8 — Observabilidade.** Logs JSON em stdout (`structlog`), lidos no painel do Render; o P95 e a taxa de 5xx ficam na memória da API e saem em `/health/slo` (S21-02). Grafana Alloy, Grafana Cloud e métricas `/metrics` (`prometheus-client`) **não entram** (decisão do autor na S35-06, 11/10/2026: fica só o `/health/slo` com o UptimeRobot). Monitoramento externo pelo UptimeRobot (plano gratuito, intervalo de 5 min): um monitor em `/ready` do backend, que também impede o serviço gratuito do Render de dormir, e outro na SPA da Vercel, ambos com alerta por e-mail. **Sprint 21:** os alertas de latência e de erro do NFR-15 saem da própria API, sem outra conta externa: `GET /health/slo` responde 503 quando, nos últimos 5 minutos, o P95 do `POST /api/v1/validate` passa de 200 ms ou mais de 1% das respostas são 5xx (com pelo menos 20 requisições na janela), e um terceiro monitor do UptimeRobot manda o e-mail. Com o intervalo de 5 min do UptimeRobot, o alerta chega em até 10 min, e não em 5. O Grafana Cloud e o `/metrics` ficam opcionais.
- **C9 — CI/CD.** GitHub Actions com as actions fixadas por SHA; no piloto, o deploy sai da `main` depois da CI, pelos deploy hooks do Render e da Vercel (`deploy.yml`). Imagens no GHCR por digest, deploy por SSH com aprovação de *environment* e staging separado são [PLANEJADO, Fase 2].
- **C10 — Contas e sessão (`backend/src/ipc_api/auth/`, Sprints 13 a 16).** Rotas `/api/v1/auth/*` (registrar, confirmar e-mail, reenviar, entrar, sair, Google e perfil) e `/api/v1/admin/*` (fila, aprovar, recusar, cargo, remover e reativar); uma dependência FastAPI que carrega a sessão e a conta a cada requisição; e uma função pura de política, `can(ator, ação, alvo, cargo_novo)`, que implementa o FR-27, é usada por todas as rotas e é testada como matriz. Senhas com `argon2-cffi`, Google com Authlib e e-mails por um adaptador (`smtp`, `http` e, no desenvolvimento, o Mailpit do Compose), tudo configurado por variáveis `IPC_*`. Contas e sessões ficam no PostgreSQL (5.2.5), acessado com `asyncpg` pelo papel `ipc_app`; a API continua sem `import ast` (NFR-09).
- **C11 — Similaridade (`backend/src/ipc_analyzer/engine/similarity.py`, Sprint 17).** Função pura que recebe dois códigos e devolve a porcentagem e os componentes do *score* (ADR-05). Roda no worker isolado, pelo endpoint interno `POST /internal/similarity`, com os mesmos guards, limites e timeout da análise. A API expõe `POST /api/v1/similarity` e classifica o resultado pelas faixas do FR-29.
- **C12 — Feedback (`backend/src/ipc_api/feedback/`, Sprints 18 e 19).** Monta a apresentação, a abertura e a frase obrigatória; pede ao analisador o código sem comentários; troca o nome do aluno por `[ALUNO]`; chama o provedor configurado por um adaptador (`openai_compat` para OpenAI, Groq e DeepSeek, `gemini` e `fake` nos testes) com `httpx`; valida a saída e devolve o texto final (ADR-06). Tem limite por conta e teto diário de chamadas.

#### 5.2.2 Fluxo de uma submissão e contrato da API

1. A SPA envia `POST /api/v1/validate` com `{ "code": str, "list_number": 1..6, "question_id": "L3-Q2" | null }` e o cookie da sessão (até a S13-03, o cabeçalho `X-Client-Id`).
2. A borda aplica TLS e repassa à `api`: o Caddy nas Fases 0 e 2, com limite de corpo de 128 KB (413), e o Render na Fase 1, quando o limite de corpo fica na `api`.
3. A `api` aplica, nesta ordem: limite de taxa (429, antes de ler o corpo), validação e admissão (503, só em torno da chamada ao analisador; P-11). A validação recusa lista fora de `ENABLED_LISTS`, questão inexistente no período do ruleset ativo (P-07), UTF-8 inválido, byte nulo, código acima de 51.200 bytes ou acima de 1.000 linhas, com 413 ou 422.
4. A `api` chama `POST /internal/analyze` no `analyzer`, com timeout de 3 s.
5. O supervisor agenda a tarefa no pool, com timeout de 2 s.
6. O worker executa guards, `ast.parse` (`feature_version` alvo), limites de AST, extração de fatos, política e exigências, e devolve JSON. Em timeout ou `MemoryError`, o supervisor mata o worker e responde `ANALYSIS_LIMIT`.
7. A `api` valida o esquema da resposta e devolve ao cliente: 200 com o relatório (FR-12); 422 `ANALYSIS_LIMIT` se a análise excedeu os limites; 503 `ANALYZER_UNAVAILABLE` se o analisador não respondeu. Respostas 5xx genéricas não fazem parte do contrato.
8. Fora do caminho da resposta, a `api` enfileira o evento de telemetria (sem código).
9. A SPA exibe o resultado e marca as linhas no editor.

Endpoints públicos: `POST /api/v1/validate`, `GET /api/v1/lists` (listas habilitadas), `GET /api/v1/questions?list=N`, `GET /api/v1/lists/{n}/permissions?question_id=` (FR-14), `GET /health`, `GET /ready`.

Exemplo de resposta 200 (`invalid`):

```
{ "request_id": "01J9Z...", "ruleset_version": "2026.2.0", "status": "invalid",
  "list_number": 2, "question_id": null, "notices": ["QUESTION_RULES_NOT_APPLIED"],
  "syntax_error": null, "truncated": false,
  "violations": [ { "rule_id": "R-46", "category": "FORA_DA_LISTA", "line": 4, "col": 2,
    "end_line": 4, "end_col": 15, "construct": "method:append", "allowed_from_list": 3,
    "message": "O método append() só é permitido a partir da Lista 3." } ] }
```

`truncated` é verdadeiro quando havia mais de 200 violações; o relatório traz as 200 primeiras. Toda resposta traz o cabeçalho `X-Request-Id`, e a de `/validate` traz `Cache-Control: no-store`.

Códigos de erro: 413 `PAYLOAD_TOO_LARGE`, 422 `INVALID_INPUT` / `LIST_NOT_ENABLED` / `UNKNOWN_QUESTION` / `ANALYSIS_LIMIT`, 429 `RATE_LIMITED`, 503 `OVERLOADED` / `ANALYZER_UNAVAILABLE`, sempre no formato `{ "error": { "code", "message", "retry_after_s" } }`; quando há espera sugerida, ela também vai no cabeçalho `Retry-After`. O contrato fica versionado em `docs/openapi.json` (S8-01).

**Rotas do acesso restrito, do plágio e do feedback (Sprints 13 a 19).** `POST /api/v1/auth/register`, `POST /api/v1/auth/verify`, `POST /api/v1/auth/verify/resend`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, `GET /api/v1/auth/options`, `GET /api/v1/auth/google/start`, `GET /api/v1/auth/google/callback`, `GET /api/v1/auth/google/pending`, `POST /api/v1/auth/google/complete`, `PATCH /api/v1/profile`, `POST /api/v1/profile/password`, `GET /api/v1/admin/requests`, `POST /api/v1/admin/requests/{id}/approve`, `POST /api/v1/admin/requests/{id}/reject`, `GET /api/v1/admin/members`, `PATCH /api/v1/admin/members/{id}/role`, `POST /api/v1/admin/members/{id}/remove`, `POST /api/v1/admin/members/{id}/reactivate`, `POST /api/v1/similarity` e `POST /api/v1/feedback`. As rotas que já existiam passam a exigir sessão (FR-22). Códigos novos, no mesmo envelope de erro: 401 `UNAUTHENTICATED` e `INVALID_CREDENTIALS` (mensagem única para senha errada e conta inexistente); 403 `FORBIDDEN`, `ORIGIN_MISMATCH`, `ACCOUNT_PENDING_VERIFICATION`, `ACCOUNT_PENDING_APPROVAL`, `ACCOUNT_REJECTED` e `ACCOUNT_REMOVED` (os de status só depois de a identidade ser confirmada, FR-25); 409 `NAME_TAKEN` e `EMAIL_TAKEN`; 422 `DOMAIN_NOT_ALLOWED`, `WEAK_PASSWORD` e `INVALID_TOKEN`; 429 `RATE_LIMITED` também para repetidas senhas atuais erradas na troca de senha; 404 `ACCOUNT_NOT_FOUND` e 409 `ACCOUNT_STATE_CHANGED` no gerenciamento (a conta não existe, ou outra pessoa agiu sobre ela desde que a lista foi carregada); 503 `DATABASE_UNAVAILABLE` (o banco de contas não respondeu; também no `/ready`), `EMAIL_UNAVAILABLE` (o e-mail de verificação não pôde ser enviado; o cadastro fica guardado e o link pode ser reenviado). O feedback não tem código de indisponibilidade: sem IA, o texto é montado por modelos (ADR-06, item 6). Toda rota que muda estado exige o cabeçalho `Origin` igual à origem da página (ADR-04).

#### 5.2.3 Motor de regras orientado a dados (Etapa F2)

**Vocabulário de fatos.** O extrator percorre a AST de forma iterativa, com pilha explícita e sem recursão Python, e emite fatos com localização (`line`, `col`, `end_line`, `end_col`):

| Tipo de fato | Origem na AST | Exemplos |
|---|---|---|
| `node:<Classe>` | Toda classe de nó, exceto as estruturais | `node:For`, `node:Try`, `node:ListComp` |
| `op:<Op>` / `cmp:<Op>` | Operadores de `BinOp`, `UnaryOp`, `BoolOp`, `AugAssign` e `Compare` | `op:Add`, `op:Not`, `cmp:In`, `cmp:Is` |
| `builtin:<nome>` | `Name` em contexto Load **não** ligado pelo aluno e presente em `builtins` | `builtin:len`, `builtin:eval`, `builtin:getattr` |
| `method:<nome>` | Todo `Attribute`, chamado ou não | `method:split` em `s.split()` e em `f = s.split` |
| `kwarg:<função>.<nome>` | `keyword` em chamada (`**` vira `kwarg:**`) | `kwarg:print.end`, `kwarg:print.sep` |
| `const:<tipo>` | `Constant` | `const:int`, `const:str`, `const:None` |
| `param:<tipo>` | `arguments` de `def`/`lambda` | `param:vararg`, `param:kwarg`, `param:default` |
| `call:user`, `return:multi`, `target:for_unpack` | Contexto estrutural | Chamada de função do aluno; `return a, b`; `for a, b in ...` |
| `derived:recursion` | Grafo de chamadas entre `FunctionDef` do aluno, com detecção de ciclo por Tarjan (iterativo); as chamadas são pelo nome, como `call:user`, e um `lambda` não entra no grafo | Recursão direta ou mútua (C-03). Da Sprint 23 à S36-09 foi um fato estrutural, só para a exigência da R-68; desde a Q-33, a R-68 também o permite só a partir da Lista 6, e nas Listas 1 a 5 ele é "Fora da lista" (o `def` e a chamada seguem decididos pela R-59) |
| `derived:loop_else`, `derived:decorator`, `derived:dict_unpack` | Sintaxe sem nó próprio na AST: o `else` de um laço, cada `@decorador` e cada `**d` num dicionário literal | Nenhuma regra os permite, então viram R-04 (Q-02 g; DoD, item 9) |

Fatos estruturais sempre aceitos, porque sua presença já é controlada pelo nó pai: `node:Module`, `node:Expr`, `node:Name`, `node:Call`, `node:keyword`, `node:Load`, `node:Store`, `node:arguments`, `node:arg` e `node:comprehension`. Nomes ligados pelo aluno (alvos de atribuição, `for` e compreensões, parâmetros e nomes de `def`) são coletados antes, para distinguir `len` (built-in) de uma variável do aluno chamada `len`. Assim, `getattr`, `eval`, `exec`, `__import__`, `globals` e atributos *dunder* caem no *default deny*, o que fecha a evasão por acesso dinâmico.

**Formato do ruleset (trecho com regras reais do catálogo):**

```
schema_version: 2
ruleset_version: "2026.2.0"
source_sha256: "<hash do PDF de Permissões>"
target_python: "3.13"                      # Q-01
structural_facts: [node:Module, node:Expr, node:Name, node:Call, node:keyword]
rules:
  - id: R-06
    effect: deny
    category: ANULACAO
    match: [node:Try, node:TryStar]
    message: "try/except é proibido em todas as listas (anulação imediata)."
  - id: R-34
    effect: allow
    since_list: 2
    match: [node:For, node:While]
    message: "Laços for/while são permitidos a partir da Lista {allowed_from_list}."
  - id: R-37
    effect: allow
    since_list: 2
    until_list: 4                            # Q-04
    match: [builtin:zip, target:for_unpack]
    when: { predicate: zip_in_for_header, min_args: 2 }
    message: "zip() só é permitido no cabeçalho do for, com 2 ou mais sequências."
requirements:
  - { id: R-02, list: 2, require_any: [node:For, node:While] }      # Q-05
  - { id: R-68, list: 6, require_any: [derived:recursion] }         # C-03
```

Formato de override por questão em `rulesets/<período>/questions/L<n>-Q<m>.yaml` (desde a Sprint 24); a pasta do período resolve a reinicialização da numeração a cada período (P-07). Os campos são `question_id` (igual ao nome do arquivo), `list`, `title` (mostrado no seletor), `source` (o trecho do enunciado), `allow` (R-xx, que valem com as condições da regra), `allow_facts` (fatos fora do catálogo que o enunciado permita explicitamente), `deny` (R-xx ou fatos) e `message` (opcional, com `{construct}` e `{question_id}`). Uma questão não altera as meta-regras nem as exigências (R-02 e R-68). O passo a passo para monitores está no `RULES.md`. **As primeiras questões reais são a L4-Q4 e a L4-Q5 de 2026.2 (11/10/2026): a L4-Q4 libera `eval()` e o `reverse=` no `sort()`; a L4-Q5, o valor padrão de parâmetro. O conteúdo vem do enunciado e é cadastrado por monitores, monitores-chefe ou professores, com aprovação de monitor-chefe ou professor (US-13, Q-08).**

**Algoritmo de avaliação.** Para a lista *n* e a questão *q*:

1. Os guards de entrada (FR-04) e o `ast.parse` (FR-05) são executados.
2. Os limites de AST são verificados: profundidade até 200 e no máximo 60.000 nós.
3. As ligações de nomes do aluno são coletadas.
4. Os fatos são extraídos.
5. Cada ocorrência de fato *f* é classificada pela primeira condição verdadeira:
   1. *f* é estrutural: aceito.
   2. *f* está em `q.deny`: `PROIBIDO_NA_QUESTAO`, com o ID R-01.
   3. *f* casa uma regra de `q.allow` cuja condição vale, ou está em `q.allow_facts`: aceito (R-01).
   4. *f* casa com uma regra `deny` geral: `ANULACAO`.
   5. *f* casa com uma regra `allow` em que `since_list ≤ n ≤ until_list` e o predicado `when` é verdadeiro: aceito (R-03).
   6. *f* casa com uma regra `allow` cujo predicado é falso: violação com o ID dessa regra (ex.: R-37).
   7. *f* casa com uma regra `allow` em que `since_list > n`: `FORA_DA_LISTA`, com `allowed_from_list`.
   8. Nenhuma das anteriores: R-04, `NAO_CONSTA`.
6. Cada `requirement` com `list = n` exige pelo menos um fato de `require_any`; se faltar, gera `EXIGENCIA`.
7. As violações são deduplicadas por (`rule_id`, `line`, `col`), ordenadas e truncadas em 200.

O índice `fato → regras` é um dicionário montado na carga, com busca O(1) por fato.

**Fronteira de extensibilidade.** Criar, alterar ou remover regras, mudar listas, condições que usam predicados existentes, exigências e overrides de questão são mudanças **só de dados** (NFR-17). Criar um **novo tipo de fato** ou um **novo predicado** exige código no motor, com ADR e testes, e é o único ponto de extensão programática.

**Biblioteca de predicados (`engine/conditions.py`), complemento da ADR-02:**

| Predicado | Parâmetros | Vale quando | Usado por | Desde |
|---|---|---|---|---|
| `call_args` | `min`, `max` | a chamada tem entre `min` e `max` argumentos | R-09 e R-33 (`type()`, Q-07) | Sprint 4 |
| `zip_in_for_header` | `min` (≥ 1) | o fato é o `zip()` built-in que é o iterável do comando `for`, ou o alvo desse `for`, com `min` ou mais sequências | R-37 (`min: 2`, Listas 2 a 4) e R-64 (`min: 1`, alvo do `for` a partir da Lista 5) | Sprint 20 |
| `enumerate_in_for_header` | nenhum | o fato é o alvo de um comando `for` cujo iterável é o `enumerate(...)` built-in | R-63 | Sprint 23 |
| `items_in_for_header` | nenhum | o fato é o alvo de um comando `for` cujo iterável é `x.items()`, sem argumentos | R-65 | Sprint 23 |

Decisão da Sprint 23 (06/10/2026): a partir da Lista 5, vários nomes no alvo do `for` (`for a, b in ...`) só são permitidos quando o `for` percorre `zip()`, `enumerate()` ou `.items()`, as três construções da Lista 5 que entregam pares. Os dois predicados novos seguem o desenho do `zip_in_for_header`: só o comando `for` conta, e o iterável dentro de outra chamada, numa compreensão ou com um nome do aluno não marca o alvo. Alternativas descartadas: liberar `target:for_unpack` sem condição na Lista 5 (abriria `for a, b in pares`, um caso ainda em aberto no mapeamento) e inferir o tipo do iterável (o motor não infere tipos, ameaça 8).

**Mapeamento R-xx → fatos (validado em 01/10/2026 pelas decisões Q-02 a Q-07):**

| Regra | Fatos |
|---|---|
| R-02 | `require_any` por lista (Q-05) |
| R-05 | `node:Import`, `node:ImportFrom` (Q-06) |
| R-06 | `node:Try`, `node:TryStar` |
| R-07 | `node:Set`, `node:SetComp`, `builtin:set`, `builtin:frozenset` |
| R-08 | `builtin:exit`, `method:exit` |
| R-09 | `node:ClassDef`; `builtin:type` com 3 argumentos (Q-07) |
| R-10 | `param:vararg`, `param:kwarg`, `node:Starred` em chamada, `kwarg:**` (Q-02) |
| R-11, R-12, R-13, R-14 | `node:Break`, `node:Continue`; `node:Pass`; `const:None`; `node:Global` (Q-03) |
| R-15, R-16 | `node:If`; `node:Assign`, `const:int`, `const:float`, `const:str` |
| R-17 | `cmp:Is`, `cmp:IsNot` (Q-02) |
| R-18 | `node:BinOp`, `node:UnaryOp`, `node:AugAssign`, `op:Add`, `op:Sub`, `op:Mult`, `op:Div`, `op:FloorDiv`, `op:Mod`, `op:Pow`, `op:UAdd`, `op:USub` |
| R-19 | `node:BoolOp`, `node:Compare`, `op:And`, `op:Or`, `op:Not`, `cmp:Eq`, `cmp:NotEq`, `cmp:Lt`, `cmp:LtE`, `cmp:Gt`, `cmp:GtE`, `const:bool` |
| R-20, R-21 | `node:IfExp`; `op:Add` entre strings (sintaticamente igual a R-18) |
| R-22…R-27 | `builtin:print`, `input`, `abs`, `int`, `float`, `str`, `max`, `min`, `round`, `len` |
| R-28, R-29 | `builtin:format`, `method:format` (Q-02); `method:capitalize`, `upper`, `lower`, `isupper`, `islower`, `isnumeric` |
| R-30, R-36, R-44 | `cmp:In`, `cmp:NotIn` (Q-02); o tipo do operando não é distinguível estaticamente (ver 5.4, ameaça 8) |
| R-31, R-32, R-33 | `node:JoinedStr`, `node:FormattedValue`; `kwarg:print.end`; `builtin:type` com 1 argumento |
| R-34, R-35, R-37 | `node:For`, `node:While`; `builtin:range`; `builtin:zip` + `target:for_unpack` com o predicado `zip_in_for_header` |
| R-38…R-43 | `node:List` (matriz = lista aninhada); `node:Tuple`; `node:ListComp`; `node:Subscript`; `node:Slice` |
| R-45…R-49 | `builtin:list`; `method:append`, `insert`, `pop`, `remove`; `node:Delete`, `node:Del`; `method:sort`, `builtin:sorted`; `method:reverse`, `builtin:reversed` |
| R-50…R-58 | `method:strip`, `replace`, `index`, `join`, `split`, `rsplit`, `count`, `copy`; `builtin:sum`, `builtin:tuple` |
| R-59, R-60 | `node:FunctionDef`, `node:Return`, `call:user`; `return:multi` |
| R-61…R-67 | `node:Dict`; `builtin:dict`, `enumerate`, `zip` (R-64, livre); `method:keys`, `values`, `items`, `get`, `update`; `node:Lambda`; `target:for_unpack` com `enumerate_in_for_header` (R-63), `zip_in_for_header` (R-64) ou `items_in_for_header` (R-65) |
| R-68 | `derived:recursion` (permitido a partir da Lista 6 e exigido nela; Q-33, S36-09) |

#### 5.2.4 Modelo de dados (telemetria, Sprint 21)

```
CREATE SCHEMA telemetry;
CREATE TYPE telemetry.outcome AS ENUM
  ('valid','invalid','syntax_error','rejected','analysis_limit');
CREATE TABLE telemetry.validation_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  semester text NOT NULL CHECK (semester ~ '^[0-9]{4}[.][12]$'),
  list_number smallint NOT NULL CHECK (list_number BETWEEN 1 AND 6),
  question_id text NULL CHECK (question_id ~ '^L[1-6]-Q[0-9]{1,3}$'),
  ruleset_version text NOT NULL,
  outcome telemetry.outcome NOT NULL,
  violation_count smallint NOT NULL DEFAULT 0,
  analysis_ms integer NOT NULL);
CREATE TABLE telemetry.validation_event_rule (
  event_id uuid REFERENCES telemetry.validation_event(id) ON DELETE CASCADE,
  rule_id text NOT NULL CHECK (rule_id ~ '^R-[0-9]{2}$'),
  occurrences smallint NOT NULL,
  PRIMARY KEY (event_id, rule_id));
-- papéis: ipc_writer (INSERT nas 2 tabelas e EXECUTE no expurgo); ipc_reader (SELECT só nas views v_*)
-- views agrupam por (semester, list_number, question_id): v_top_rules_by_list, v_syntax_error_rate,
--   v_weekly_volume (por semana)
-- expurgo de registros com mais de 12 meses (P-06): telemetry.purge_expired(), SECURITY DEFINER
```

**Implementação (Sprint 21, `database/migrations/0002_telemetria.up.sql`):** as colunas ganharam limites (`ruleset_version` no formato `AAAA.P.N`, `violation_count` de 0 a 200, `analysis_ms` ≥ 0, `occurrences` de 1 a 200) e um índice em `created_at`. O `id` vem da API, porque o `ipc_writer` não pode ler a tabela (nem `RETURNING`). O expurgo é uma função `SECURITY DEFINER` que o `ipc_writer` executa sem ter `DELETE`; a API a chama ao subir e uma vez por dia, no lugar do `pg_cron`, que não existe no PostgreSQL das Fases 0 e 2. O usuário da API (membro de `ipc_app`) recebe `ipc_writer` pela migração; o `ipc_reader` é dado a quem consulta (`deploy/README.md`).

#### 5.2.5 Modelo de dados (contas e sessões, Sprint 13)

```
CREATE SCHEMA app;
CREATE TYPE app.role AS ENUM ('desenvolvedor','professor','monitor_chefe','monitor');
CREATE TYPE app.status AS ENUM ('aguardando_verificacao','aguardando_aprovacao','ativo',
  'recusado','ex_monitor','conselheiro','inativo');
CREATE TYPE app.treatment AS ENUM ('masculino','feminino','neutro');
CREATE TABLE app.account (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
  course text NOT NULL CHECK (length(course) BETWEEN 2 AND 120),
  treatment app.treatment NOT NULL,         -- só o titular vê (FR-26)
  role app.role NULL,                       -- definido na aprovação (FR-27)
  status app.status NOT NULL,
  ja_foi_monitor_chefe boolean NOT NULL DEFAULT false,  -- nunca volta a false
  password_hash text NULL,                  -- Argon2id; NULL em conta só do Google
  google_sub text NULL UNIQUE,
  signup_method text NOT NULL CHECK (signup_method IN ('senha','google','seed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_by uuid NULL REFERENCES app.account(id),
  decided_at timestamptz NULL);
CREATE UNIQUE INDEX account_name_ci ON app.account (lower(name));
CREATE TABLE app.account_email (            -- o desenvolvedor tem dois (P-14)
  email text PRIMARY KEY CHECK (email = lower(email)
    AND split_part(email, '@', 2) IN ('cin.ufpe.br','ufpe.br')),
  account_id uuid NOT NULL REFERENCES app.account(id),
  is_primary boolean NOT NULL DEFAULT true,
  verified_at timestamptz NULL);
CREATE TABLE app.session (
  token_hash bytea PRIMARY KEY,             -- SHA-256 do identificador do cookie
  account_id uuid NOT NULL REFERENCES app.account(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL);
CREATE TABLE app.email_token (
  token_hash bytea PRIMARY KEY,
  account_id uuid NOT NULL REFERENCES app.account(id) ON DELETE CASCADE,
  purpose text NOT NULL CHECK (purpose IN ('verificacao')),
  expires_at timestamptz NOT NULL,          -- 24 h
  used_at timestamptz NULL);
-- papel ipc_app: SELECT, INSERT e UPDATE em app.*; sem DELETE em app.account (remover = status)
-- os papéis ipc_writer e ipc_reader (5.2.4) não têm acesso ao esquema app

-- Sprint 23 (migração 0003, REC-06): registro das ações de gerenciamento
CREATE TABLE app.management_log (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  at timestamptz NOT NULL,
  action text NOT NULL,                     -- aprovar, recusar, alterar_cargo, remover, reativar
  actor_id uuid NULL REFERENCES app.account(id) ON DELETE SET NULL,
  actor_name text NOT NULL, actor_role app.role NULL,   -- cópias do momento da ação
  target_id uuid NULL REFERENCES app.account(id) ON DELETE SET NULL,
  target_name text NOT NULL,
  from_status app.status NOT NULL, to_status app.status NOT NULL,
  from_role app.role NULL, to_role app.role NULL);
-- ipc_app: só SELECT e INSERT; o expurgo de 12 meses é a função app.purge_management_log
-- (SECURITY DEFINER), que conta o prazo pelo relógio do banco
```

Nas Fases 0 e 2, o banco é um contêiner `postgres` fixado por digest, só na rede interna da `api` e sem porta publicada no host, o que também evita conflito com os bancos de outros projetos na mesma máquina; na Fase 1, é o Supabase. As migrações ficam em `database/migrations/`, cada uma com ida e volta testadas (DoD).

### 5.3 Tabela de tecnologias

| Camada | Tecnologia | Justificativa técnica | Alternativa descartada e motivo |
|---|---|---|---|
| Parser do analisador | Python 3.13, a mesma versão do Dikastis (Q-01), com o módulo `ast` da stdlib | A gramática é idêntica à do interpretador que corrige (NFR-21), sem dependência externa no caminho crítico, e `ast.parse` não executa código | tree-sitter-python: tolera erros e serve a várias linguagens, mas tem gramática própria que pode divergir do CPython e não reproduz o `SyntaxError` do Dikastis |
| Isolamento de processo | Pebble 5.x (`ProcessPool` com timeout por tarefa e `max_tasks`) e `resource.setrlimit` | Mata o worker em timeout, o que não é possível com threads. A reciclagem limita vazamento de memória. É uma biblioteca pequena e madura | `concurrent.futures.ProcessPoolExecutor`: não cancela uma tarefa em execução, e um worker travado fica preso |
| API e serviço interno | FastAPI, Uvicorn e Pydantic v2 | Mesmo ecossistema do motor, o que significa uma única linguagem para uma equipe rotativa. Contrato validado de forma declarativa e OpenAPI gerado automaticamente. Modelo async adequado ao I/O com o analisador e a telemetria | Node.js/Express: segunda linguagem para a equipe e modelos de contrato duplicados. Django REST: ORM e admin desnecessários num caminho sem estado |
| Ruleset | YAML, mais JSON Schema 2020-12 validado com `jsonschema`, compilado para JSON na build | O YAML aceita comentários, onde o professor cita a fonte de cada regra. O schema aponta o caminho do campo com erro. A compilação evita o parse de YAML em produção | JSON puro (§12 do rascunho): não aceita comentários. Banco de dados com UI de administração: exige autenticação e UI fora do escopo e perde a revisão por PR |
| Frontend | React 18, Vite, TypeScript e Tailwind CSS (§9 do rascunho) | Tipos gerados do OpenAPI (`openapi-typescript`), build rápido e ecossistema maduro | Vanilla JS: difícil de manter com os estados exigidos pelo FR-20 |
| Editor | Planejado: CodeMirror 6 com `@codemirror/lang-python` e `@codemirror/lint`. Hoje: editor próprio sobre `<textarea>` (S26-02), com numeração e marcação de linhas | Diagnósticos por intervalo de forma nativa (FR-13), operável por teclado, bundle bem menor que o do Monaco | Monaco: alguns MB a mais, o que compromete o NFR-03 em rede móvel |
| Borda | Caddy 2 nas Fases 0 e 2; na Fase 1, a borda gerenciada do Render e da Vercel | TLS automático via ACME, limite de corpo e filtro de log nativos, configuração curta | Nginx com certbot: renovação de certificado e configuração manuais, mais passos para uma equipe rotativa |
| Hospedagem | Fase 0: Docker Compose local. Fase 1 (piloto em 2027.1): SPA na Vercel e backend em 1 serviço Docker no Render (plano Starter recomendado). Fase 2: Docker Compose no servidor do CIn (ADR-03) | No piloto, custo baixo e nenhum servidor para administrar (decisão do projeto, Q-10). Nas Fases 0 e 2, redes `internal: true`, `read_only`, `cap_drop`, `pids_limit` e `mem_limit` testáveis (NFR-07) | VM de nuvem com Compose já no piloto: isolamento completo, mas exige administrar o sistema operacional com 4 a 8 h por semana. Kubernetes: custo operacional desproporcional |
| Isolamento por processo (Fase 1) | `supervisord`, UIDs distintos para `api` e `analyzer` e `pyseccomp` (libseccomp) nos workers | Compensa a falta de rede interna e de flags de contêiner no Render: o analisador não lê o ambiente da API, não abre sockets de rede e não executa programas | nsjail ou bubblewrap: dependem de *user namespaces*, em geral indisponíveis em PaaS |
| Imagem base | `python:3.13-slim` (Debian), fixada por digest | glibc instala wheels binárias sem compilação, a superfície é reduzida e há atualizações de segurança do Debian | Alpine: o musl força compilar wheels e tem diferenças de comportamento. Distroless: depuração mais difícil para a equipe (reavaliar após o MVP) |
| Telemetria/BD | PostgreSQL gerenciado (Supabase, §2 do rascunho) com `asyncpg` e o papel `ipc_writer`, que só faz INSERT | Backup diário próprio e criptografado (`backup.yml`, S28-03 e S30-12) [PREMISSA: o plano gratuito do Supabase não guarda backups que se possam baixar], SQL para as views do FR-17 e menor privilégio via conexão Postgres direta | supabase-py/REST com chave de serviço: credencial com privilégio amplo. SQLite: perde dados a cada deploy (§19 do rascunho) |
| Observabilidade | structlog (JSON) nos logs do Render, o `/health/slo` e o UptimeRobot (linha seguinte); sem Grafana nem `/metrics` (S35-06, decisão do autor de 11/10/2026) | Logs, métricas e alertas (NFR-14, NFR-15) sem servidor próprio | `/metrics` com Grafana Cloud (7.13.7, opção B, não adotada); Prometheus, Grafana e Loki auto-hospedados: três serviços a mais para operar na VM |
| Keep-alive e monitoramento externo (Fase 1) | UptimeRobot, plano gratuito, checagem de `/ready` a cada 5 min e da SPA | O serviço gratuito do Render dorme após 15 min sem tráfego; uma checagem a cada 5 min o mantém acordado e ainda mede a disponibilidade (NFR-06) e alerta por e-mail (US-19). Um único serviço acordado o mês todo cabe nas 750 h/mês do plano gratuito | Cron do GitHub Actions: o intervalo mínimo é de 5 min e as execuções costumam atrasar, o que deixaria o serviço dormir. Render Starter: elimina a dormência, mas custa cerca de US$ 7/mês |
| Repositório e CI/CD | Monorepo no GitHub e GitHub Actions (GHCR [PLANEJADO, Fase 2]) | Ruleset, motor e contrato mudam no mesmo PR; a aprovação de regras é conferida por quem faz o merge (Q-22), porque o GitHub Free não aplica CODEOWNERS em repositório privado | Dois repositórios (§20–21 do rascunho): contrato e ruleset ficam dessincronizados entre front e back |
| Qualidade e segurança na CI | Na CI: ruff (com as regras do Bandit), `mypy --strict`, import-linter, pytest (com schemathesis para o contrato), Vitest com RTL e Playwright com axe-core; gitleaks, Semgrep, pip-audit e npm audit em todo PR e, com o Trivy, no workflow semanal (S31-03 e S31-04); desde a S35-01 a S35-03, o benchmark do motor (próprio, em `backend/tests/benchmark/`, sem o pytest-benchmark), o Lighthouse CI, o orçamento do JS e a cobertura por pasta; à mão: k6 | Cada ferramenta verifica um NFR específico (NFR-02, 04, 05, 09, 13, 16, 18, 19) | Só linters e testes unitários (§18 do rascunho): não verificam isolamento, evasão nem carga |
| Contas e sessões | PostgreSQL (Supabase no piloto; contêiner `postgres` nas Fases 0 e 2, só em rede interna) com `asyncpg` e migrações SQL reversíveis em `database/migrations/` | Reaproveita o banco já previsto para a telemetria (P-03); sessões revogáveis na hora; unicidade de nome e e-mail garantida pelo banco | JWT sem estado: não dá para revogar na hora uma conta removida ou com cargo alterado. SQLite: perde dados a cada deploy |
| Senhas | `argon2-cffi` (Argon2id) | Recomendação atual da OWASP, resistente a ataque por GPU | bcrypt: aceitável, mas corta a senha em 72 bytes. PBKDF2: sem custo de memória |
| Login com Google | Authlib (cliente OpenID Connect para Starlette e FastAPI) | Descoberta, `state`, `nonce`, PKCE e validação do ID token (assinatura por JWKS, `iss`, `aud` e `exp`) prontos e mantidos | OIDC escrito à mão: fácil errar a validação. `google-auth`: valida o token, mas não cobre o fluxo |
| E-mail | Adaptador próprio com `aiosmtplib` (SMTP) ou `httpx` (serviço transacional); Mailpit no Compose local | Trocar de provedor é só configuração (Q-17), e nenhum e-mail real sai no desenvolvimento | SDK de um provedor específico: prende o projeto a ele |
| LLM | Adaptadores próprios com `httpx`: `openai_compat` (OpenAI, Groq, DeepSeek e outros compatíveis), `gemini` e `fake` | Uma interface pequena (`generate`) cobre os provedores pedidos sem SDKs pesados, e o provedor falso deixa os testes determinísticos | LangChain e afins: muitas dependências para uma chamada só. Um SDK por provedor: quatro dependências e quatro formatos de erro |
| Plágio | `tokenize` e `ast` da stdlib, no analisador, com *winnowing* próprio (ADR-05) | Nenhuma dependência nova, o mesmo isolamento da análise e o reaproveitamento da coleta de nomes do aluno (`symbols.py`) | MOSS ou JPlag como serviço: enviam o código a terceiros ou exigem Java no servidor |
| Roteamento da SPA | React Router | Telas novas (Entrar, Registrar, Perfil, Gerenciamento e Plágio) com URL própria e guarda de rota | Estado manual no `App`: não escala bem para sete telas |

### 5.4 Modelo de ameaças

Premissa operacional (Zero Trust): todo código submetido e toda requisição anônima são não confiáveis, e a resposta do `analyzer` também é tratada como não confiável pela `api`. Cada componente roda com o menor privilégio possível. A segurança não é absoluta, e o risco residual de cada ameaça está declarado abaixo.

| Ameaça | Vetor | Controle | Como é verificado | Risco residual |
|---|---|---|---|---|
| 1. Execução remota de código (RCE) no servidor | O código chega a `eval`/`exec`/`compile`/`import`/`pickle` por erro de implementação, ou um payload como `__import__("os").system(...)` é enviado | Nenhum caminho de execução: a entrada só passa por `ast.parse`, num único ponto (`engine/parse.py`). O import-linter proíbe `ast` na `api`. A análise roda só no `analyzer`, sem segredos, sem root e com FS read-only, além de `RLIMIT_FSIZE` = 0 | Semgrep e Bandit bloqueantes (NFR-09); corpus de RCE com canário (`/tmp/canary`), cuja ausência é verificada após a suíte | Baixo: depende de uma regressão humana, barrada pela CI |
| 2. RCE por vulnerabilidade do parser do CPython | Entrada artesanal que explora um bug de memória em `ast.parse` (código C) | Versão do Python suportada e atualizada. O parse só ocorre no worker isolado: sem segredos, sem egress, sem escrita, sem root, com `cap_drop: ALL`, `no-new-privileges` e o seccomp padrão do Docker. O worker é reciclado | Teste de configuração (NFR-07), suíte maliciosa na CI, varredura semanal com Trivy | Baixo: exige um 0-day, e o impacto fica contido num contêiner sem dados e sem rede Na Fase 1, o worker divide o contêiner com a API e a contenção depende de UID separado e seccomp: risco Médio-baixo durante o piloto. |
| 3. Esgotamento por arquivo enorme | Corpo com vários MB, ou 50 KB com milhares de linhas | Caddy recusa acima de 128 KB (413). A `api` recusa acima de 51.200 bytes ou 1.000 linhas (413/422) antes de chegar ao analisador. A SPA bloqueia arquivos acima de 50 KB | Testes de segurança 1 e 2 (seção 8) | Muito baixo |
| 4. Esgotamento por código que trava o analisador | Aninhamento profundo (`((((…`), cadeia `1+1+…` com 25 mil termos, f-strings aninhadas, literais gigantes | Travessia iterativa, sem `RecursionError`. Profundidade até 200 e no máximo 60.000 nós. Timeout de parede de 2 s com kill. `RLIMIT_AS` de 256 MB. A admissão limita a concorrência | Testes 4 a 6 (seção 8), `/ready` = 200 após a suíte | Baixo: cada requisição de ataque consome no máximo 2 s de um dos 2 workers, e o rate limit limita a taxa |
| 5. Laço infinito | `while True:` ou recursão infinita no código do aluno | O código nunca é executado. O custo do motor é proporcional ao número de nós, que já é limitado | Teste 7: `while True: pass` responde em menos de 100 ms | Nulo para o código do aluno; um bug do próprio motor é contido pelo timeout |
| 6. Acesso indevido à rede e ao sistema de arquivos | Um worker comprometido tenta exfiltrar dados ou ler e escrever arquivos | `analyzer_net` com `internal: true` (sem rota externa), rootfs read-only, nenhum volume, `RLIMIT_FSIZE` = 0, UID 10001, nenhum segredo no ambiente ou no FS | Teste 11 na CI: conexões TCP e DNS externas falham, a escrita falha, `env` não tem segredos | Baixo: só é possível ler o código da imagem, que é público Na Fase 1, sem rede interna no Render, o bloqueio de rede é feito por seccomp no worker; se o Render não permitir seccomp, o risco sobe para Médio durante o piloto e fica registrado. |
| 7. Vazamento de dados de outros alunos | Mistura de estado entre requisições, código em logs ou telemetria, computador de laboratório compartilhado | Motor puro, sem estado global mutável. Worker reciclado. Código nunca logado nem persistido. Telemetria sem código e sem IP. A SPA não grava código em `localStorage` | Teste de concorrência com marcadores distintos (eles nunca se cruzam), teste canário (NFR-11), esquema de log (NFR-14) | Baixo: resta o próprio aluno deixar o código visível na aba aberta |
| 8. Evasão das regras por construções indiretas ou dinâmicas | `getattr(s, "split")()`, `f = s.split`, `eval("…")`, `__import__`, `globals()`, `__builtins__`, `type("C", (), {})`, sombreamento de built-ins, `{*x}` | *Default deny* por fato (5.2.3): built-ins fora do catálogo, todo `Attribute` e todo dunder geram violação. Nomes ligados pelo aluno são distinguidos de built-ins. `type` com 3 argumentos cai em R-09 (Q-07) | Corpus golden de evasão com ≥ 30 casos (NFR-18) e matriz de mapeamento revisada pelo professor (Q-02) | Médio-baixo: o tipo do receptor não é inferido (`x.count()` em string ou lista; `in` em string ou lista). Isso é mitigado porque listas, tuplas e dicionários só podem ser criados a partir das listas que os liberam. Aceito e documentado |
| 9. Abuso volumétrico (DoS) | Rajadas na véspera do prazo, scripts, botnets | Rate limit por cliente e por IP (com limite próprio para os IPs de NAT do campus, P-04), admissão com 503 rápido, timeouts na borda | Teste de stress do NFR-05, com tráfego concentrado em poucos IPs | Médio: um DDoS distribuído supera a VM única (ver REC-01). Um usuário mal-intencionado dentro do campus pode trocar de `X-Client-Id` e usar até 1.000 req/min do IP compartilhado; nesse caso, a admissão devolve 503 aos demais até o limite do campus ser reduzido |
| 10. Adulteração do ruleset ou da cadeia de suprimentos | PR malicioso liberando construções, dependência comprometida, imagem trocada | Revisão de PR por processo (Q-22): quem faz o merge confere a aprovação do professor no ruleset base, de monitor-chefe ou professor nas questões, sem autoaprovação, e do professor nos overrides que liberam R-05…R-14 (sem CODEOWNERS nem *branch protection*, que o GitHub Free não aplica em repositório privado); golden e `ipc-rules validate` bloqueantes, lockfiles com hash, actions fixadas por SHA, imagens base por digest, Trivy semanal | CI bloqueante, política de branches na CI e auditoria de PR | Baixo |
| 11. XSS na SPA | Código ou mensagem contendo `<script>` renderizado na página | O editor é um `<textarea>`, que só mostra texto. As mensagens são exibidas como texto, sem `dangerouslySetInnerHTML`. CSP estrita | Teste e2e com payload de XSS e regra de lint React | Baixo |
| 12. Vazamento da credencial do banco | Leitura das variáveis de ambiente da `api` | A credencial existe só no ambiente da `api` (variável lida do `deploy/.env`), com papel que só faz INSERT. O `analyzer` não tem nenhum segredo | Teste de configuração (NFR-07) e gitleaks | Baixo: a credencial vazada só permite inserir eventos falsos Na Fase 1, a credencial existe só no ambiente do processo da API (UID 10001), que o UID 10002 do analisador não consegue ler. Com o acesso restrito (Sprint 13), a `api` também guarda a credencial do banco de contas (papel `ipc_app`, que lê e escreve em `app.*`), o segredo do cliente OAuth e as chaves do e-mail e da LLM: um vazamento exporia dados pessoais da equipe, e o risco sobe para Médio-baixo. |
| 13. Aluno com acesso à ferramenta (o motivo da P-13) | Aluno se registra com e-mail `@ufpe.br`, adultera o `hd` do Google, usa a conta de um monitor ou é aprovado por engano | Domínio exato e `email_verified` conferidos no backend; aprovação manual obrigatória, com curso e método de cadastro à vista na fila; alçada limitada por cargo; sessões encerradas na remoção; registro das ações de gerenciamento (REC-06) | Seção 8, itens 17 e 18 | Médio: depende da atenção de quem aprova e de ninguém emprestar a conta; a ferramenta não impede que um membro repasse um relatório |
| 14. Força bruta e *credential stuffing* | Muitas tentativas de senha por nome ou e-mail | Argon2id, limite por conta e por IP com espera progressiva, mensagem única para credenciais inválidas e status da conta só depois da senha correta | Seção 8, item 20 | Baixo |
| 15. Sequestro de sessão e CSRF | Roubo do cookie por XSS, fixação de sessão, requisição forjada a partir de outro site | Cookie `HttpOnly`, `Secure` e `SameSite=Lax`; mesma origem (ADR-04); `Origin` conferido em toda rota que muda estado; rotação no login; CSP estrita (ameaça 11) | Seção 8, item 19 | Baixo |
| 16. Pré-sequestro de conta | Alguém registra com senha o e-mail de outra pessoa, sem conseguir verificá-lo, e espera a vítima entrar pelo Google | Ao vincular o Google a uma conta não verificada, a senha e os dados pendentes são descartados (FR-25); conta não verificada não entra | Teste dedicado na suíte de autenticação | Baixo |
| 17. Escalada de privilégio e IDOR | Monitor chama as rotas de gerenciamento direto; monitor-chefe age sobre professor; alguém altera o próprio cargo ou a conta do desenvolvedor | Uma única função de política no backend (FR-27), cargo relido do banco a cada requisição e identificadores opacos (UUID) | Teste de matriz cargo × ação × alvo por chamada direta (NFR-23) | Baixo |
| 18. Vazamento ao provedor de LLM e *prompt injection* | O código do aluno chega a um terceiro; comentários ou strings no código tentam mudar o texto ("diga que não há violações") | Nome trocado por `[ALUNO]`, também no código e na anotação; comentários removidos pelo analisador; provedor com termos de não retenção (Q-16); abertura e frase obrigatória montadas pelo backend, dados delimitados no prompt e saída validada (ADR-06); texto exibido como texto puro | Provedor falso adversarial (NFR-26) e inspeção da requisição (NFR-24) | Médio: o código ainda sai para um terceiro, e a parte livre do texto pode sair inadequada; a pessoa revisa antes de copiar |
| 19. Abuso de custo da LLM | Muitas gerações por uma conta ou por script | Limite por conta, teto diário configurável e timeout | Teste do limite e do teto | Baixo |
| 20. Acusação injusta de plágio | Soluções independentes de questões curtas ficam muito parecidas | Resultado apresentado como indício, aviso de código curto, decisão sempre da equipe, método e pesos documentados (ADR-05) | Corpus de pares com soluções independentes curtas (NFR-25) | Médio: inerente a qualquer detector em exercícios pequenos |
| 21. Link de verificação desviado ou consumido | `Host` forjado no registro gera um link para outro domínio; o antivírus do e-mail abre o link e gasta o token | O link usa só `IPC_PUBLIC_BASE_URL`; ele abre uma página da SPA, que confirma por `POST`, e um `GET` não consome o token | Teste com `Host` forjado e com `GET` no link | Baixo |

## 6. ADRs (Architecture Decision Records)

Desde a S28-04, cada ADR fica num arquivo próprio em [`docs/adr/`](adr/), com contexto, decisão,
alternativas, consequências e status. Uma decisão nova ganha um arquivo novo; uma mudança de
decisão atualiza o status do ADR antigo e aponta para o novo.

| ADR | Decisão | Status |
|---|---|---|
| [ADR-01](adr/ADR-01-modelo-de-analise-e-isolamento-do.md) | Modelo de análise e isolamento do código do aluno | Aceito |
| [ADR-02](adr/ADR-02-motor-de-regras-declarativo-baseado-em.md) | Motor de regras declarativo baseado em fatos | Aceito |
| [ADR-03](adr/ADR-03-topologia-de-implantacao-por-fase.md) | Topologia de implantação por fase | Aceito em 01/10/2026 (Q-10); plano do Render revisto na S28-01; fica no plano gratuito (S30-11) |
| [ADR-04](adr/ADR-04-autenticacao-sessao-e-autorizacao-da-equipe.md) | Autenticação, sessão e autorização da equipe | Proposto em 02/10/2026 (P-13 e P-14); implementado nas Sprints 13 a 16; confirmado no piloto em 08/10/2026 (P-15) |
| [ADR-05](adr/ADR-05-metodo-de-deteccao-de-plagio.md) | Método de detecção de plágio | Implementado na Sprint 17 |
| [ADR-06](adr/ADR-06-feedback-por-llm-com-moldura-deterministica.md) | Feedback por LLM com moldura determinística | Implementado na Sprint 18; revisão proposta nas Sprints 44 e 45 (7.16) |
| [ADR-07](adr/ADR-07-plagio-por-arvore-canonizada-insensivel-a.md) | Plágio por árvore canonizada, insensível à ordem | Implementado na Sprint 27; revisão proposta na Sprint 46 (7.16) |
| [ADR-08](adr/ADR-08-indicios-de-uso-de-ia-nunca.md) | Indícios de uso de IA, nunca veredito | Aceito em 06/10/2026 (Q-21); implementado na Sprint 29; política aprovada em 09/10/2026; desligado no piloto até a calibração, na Sprint 42 (7.16) |
| [ADR-09](adr/ADR-09-integracao-com-outros-projetos-da-monitoria.md) | Integração com outros projetos da monitoria | Proposto em 07/10/2026 (Q-23); não confirmada |
| [ADR-10](adr/ADR-10-questoes-e-gabaritos-por-periodo.md) | Questões e gabaritos por período | Aceito em 08/10/2026 (Q-14); decisão 3 revista pela ADR-12 (proposta) |
| [ADR-11](adr/ADR-11-comparacao-com-o-gabarito.md) | Comparação com o gabarito na verificação, no plágio e nos indícios | Aceito em 09/10/2026 (Q-24); implementado na Sprint 32 |
| [ADR-12](adr/ADR-12-varios-periodos-e-retencao-por-encerramento.md) | Vários períodos carregados e retenção por encerramento | Proposto em 12/10/2026; Sprint 43 |
| [ADR-13](adr/ADR-13-grupos-de-acompanhamento-e-dados-de-alunos.md) | Grupos de acompanhamento e dados de alunos | Proposto em 12/10/2026; Q-26 a Q-29 decididas no mesmo dia; Sprint 47 |
| [ADR-14](adr/ADR-14-impressoes-digitais-persistentes.md) | Impressões digitais persistentes para plágio entre períodos e sinais com histórico | Rejeitado em 12/10/2026 (Q-27: só o resultado resumido é guardado) |

## 7. Roadmap de Sprints e Tasks do MVP

### 7.1 Roadmap

Cadência e capacidade conforme P-02 e Q-13: um único desenvolvedor, com 4 a 8 h por semana, em sprints de 2 semanas a partir de 05/10/2026. O plano usa 6 SP por sprint (1 SP ≈ 2 h de trabalho focado; premissa validada pelo autor em 12/10/2026) e metade disso nos recessos de fim de ano e de Carnaval. A meta é ter a equipe da disciplina usando a ferramenta em 2027.1 (Q-10, P-13), com início do período estimado em março de 2027 (P-10). As Sprints 1 a 12 foram concluídas em 01/10/2026, muito antes do calendário previsto. Em 02/10/2026, o roadmap foi refeito a partir da Sprint 13, com o acesso restrito, o plágio e o feedback antes das listas; as datas da Sprint 13 em diante foram re-estimadas a partir de 05/10/2026, com a mesma premissa de 6 SP por sprint, que serve de teto.

- **Fase 0 — MVP local (Sprints 1–9):** tudo roda com Docker Compose na máquina do desenvolvedor. O MVP (Marco 1) ficou pronto em 01/10/2026.
- **Fase 1a — Preparação do piloto (Sprints 10–12, concluídas):** rate limit, isolamento por processo no Render, pipeline de deploy na Vercel e no Render, exigência da Lista 1, teste de carga e material da apresentação.
- **Fase 1b — Acesso restrito e apoio à correção (Sprints 13–19):** login com aprovação, cargos e gerenciamento, Google, painel de plágio e feedback por LLM (P-13). Nada vai ao ar na internet antes do login completo (Sprint 16), e a apresentação a monitores-chefes e professores (Marco 2) passa para a Sprint 19.
- **Fase 1c — Listas e governança (Sprints 20–24), com o piloto em 2027.1:** cada lista é habilitada (`IPC_ENABLED_LISTS`) antes da data em que é liberada aos alunos; telemetria e regras por questão.
- **Fase 1d — Endurecimento, experiência e passagem de bastão (Sprints 25–29), criada em 06/10/2026 a partir da revisão de fim da Sprint 23:** primeiro deploy seguro, correção em lote, plágio por árvore, carga e eficácia, documentação para o próximo mantenedor e, se a Q-21 aprovar, os indícios de uso de IA. Como o ritmo real tem sido muito maior que 6 SP por sprint e não há calendário fixo (P-10), as datas da tabela são só a ordem prevista.
- **Fase 1e — Piloto verificado, decisões, dados e prontidão (Sprints 30–36), criada em 07/10/2026 a partir da lista de pendências depois da release da Sprint 29:** o pipeline do piloto sem passo pulado, com alerta, backup e rollback ensaiados (30); as decisões com a coordenação e o NTI e a auditoria bloqueante (31); a comparação com o gabarito na verificação, no plágio e nos indícios (32, ADR-11, incluída em 09/10/2026); os gabaritos, as questões de 2027.1 e a calibração dos indícios (33); a prontidão para 2027.1 (34); os controles ainda [PLANEJADO] (35); e a Fase 2, bloqueada pela P-09 e pela Q-12 (renumerada para 41 em 11/10/2026). As tasks estão em 7.12, as opções das decisões em 7.13 e a rastreabilidade em 7.14.
- **Fase 1f — Polimento (Sprints 36–40), criada em 11/10/2026:** até o fim do piloto, melhorar o que existe: os defeitos e os documentos da equipe (36), a tela de verificação (37), a explicação de cada regra e a exportação (38), a qualidade interna, a operação e a documentação (39) e a correção da turma inteira (40). As tasks estão em 7.15.
- **Fase 1g — Indícios, período, feedback, plágio, acompanhamento e Google (Sprints 42–48), proposta de 12/10/2026:** a partir da revisão das seis frentes ([`revisao-seis-frentes.md`](revisao-seis-frentes.md)): os indícios de IA ligados no piloto (42, a pedido do autor), o período na página e a retenção por encerramento (43), o feedback rastreável e o padrão do monitor (44), o "Aprimorar com IA" com validação e crítica (45), o plágio calibrado (46), os grupos de acompanhamento dos alunos (47) e a entrada com o Google no piloto (48, no fim da fila). As decisões sobre dados de alunos (Q-26 a Q-29) foram tomadas em 12/10/2026, e a 47 só vai ao piloto com o aviso de privacidade aprovado pela coordenação. As tasks estão em 7.16.
- **Fase 2 — Servidor do CIn (Sprint 41):** após 2027.1 e só se a P-09 for atingida. Adiada, junto com a Q-12, para depois do piloto. Desde 15/10/2026 (P-24), é a última da fila: a entrada no servidor do CIn depende da apresentação e da validação com monitores, monitores-chefe, professores, coordenadores e diretores, e o piloto de 2027.1 deve rodar no Render e na Vercel.

Sensibilidade ao ritmo: as Sprints 18 e 19 caem no recesso de fim de ano, com metade da capacidade (P-02); se isso se confirmar, o feedback termina na Sprint 20 e as listas deslocam uma sprint, ainda antes do início de 2027.1. Com 4 h por semana em todo o período (cerca de 4 SP por sprint), o bloco novo só termina em fevereiro de 2027, a Lista 2 fica pronta no início de março e as Listas 3 a 6 ficam no limite das suas liberações. O ritmo real das Sprints 1 a 12 foi bem maior que 6 SP por sprint; a premissa continua como teto até ser recalibrada.

| Sprint | Objetivo | Histórias | Entregável demonstrável | Riscos |
|---|---|---|---|---|
| 1 (05/10–18/10) | Base do repositório e ruleset das proibições gerais e das Listas 1–2 | US-05 (início) | CI verde; `base.yaml` com R-03…R-36 carregado e validado nos testes | Primeira sprint sem histórico de velocidade (recalibrar ao final) |
| 2 (19/10–01/11) | Parser seguro e esqueleto da SPA | US-01, US-03 (início) | Erro de sintaxe e entradas fora dos limites tratados nos testes; SPA com os estados do MVP sobre respostas simuladas | — |
| 3 (02/11–15/11) | Extrator de fatos | US-05 (continuação) | `f = s.split` gera `method:split` e variável do aluno chamada `len` não gera `builtin:len` | Tarefa mais complexa do MVP (5 SP) |
| 4 (16/11–29/11) | Política v1 e corpus golden | US-05 | `for` na L1 gera R-34 ("permitido a partir da Lista 2"); `try/except` gera R-06 `ANULACAO`; corpus golden e de evasão sem FP nem FN | Casos de mapeamento não previstos (registrar em `docs/mapping-R-xx.md`) |
| 5 (30/11–13/12) | Analisador isolado com limites | US-15 (início) | Pool com timeout de 2 s e `RLIMIT_AS`; o worker é substituído após um payload que excede os limites | Calibração de memória com Python 3.13 |
| 6 (14/12–27/12, recesso) | Contêiner endurecido | US-15 (continuação) | `docker inspect` confirma os controles do NFR-07 | Capacidade reduzida no recesso |
| 7 (28/12–10/01, recesso) | Suíte de segurança contra o analisador | US-15 | Suíte maliciosa e testes de isolamento verdes na CI | Capacidade reduzida no recesso |
| 8 (11/01–24/01) | API de validação | US-01, US-03 | `POST /api/v1/validate` com limites, erros mapeados e resposta do analisador validada | — |
| 9 (25/01–07/02, Marco 1: MVP) | Fluxo ponta a ponta local e seguro | US-01, US-03, US-05, US-15 | Com `docker compose up`: colar código, escolher a Lista 1 e ver violações ou erro de sintaxe com linha e coluna; logs sem código; smoke e2e local verde | Atraso acumulado nas sprints anteriores empurra o piloto (ver sensibilidade) |
| 10 (08/02–21/02, Carnaval) | Proteção para exposição pública: rate limit e admissão | US-17, US-18 | 429 por cliente e por IP (faixa da UFPE com limite próprio, IP lido do `X-Forwarded-For` do Render); 503 rápido com `Retry-After`; mensagens na SPA | Capacidade reduzida no Carnaval |
| 11 (22/02–07/03) | Deploy do piloto: isolamento por processo no Render e SPA na Vercel | US-15, US-17 | Backend no Render com `api` (UID 10001) e `analyzer` (UID 10002, ambiente vazio, seccomp); SPA na Vercel com CORS restrito; deploy disparado após a CI; UptimeRobot acessando `/ready` a cada 5 min, com alerta por e-mail | O Render pode não permitir seccomp (ver 5.4, ameaça 6). O plano gratuito tem só 0,1 CPU; a dormência é evitada pelo UptimeRobot (ver ADR-03) |
| 12 (08/03–21/03, Marco 2) | Apresentação e liberação do piloto com a Lista 1 | US-06 (Lista 1), US-11 | Apresentação a monitores-chefes e professores; exigência R-02 da L1 ativa; aviso de que regras específicas de questão ainda não são consideradas; monitores e alunos usando a Lista 1; teste de carga curto (k6) no plano gratuito decide se o backend precisa do Starter antes do primeiro prazo | Data de liberação da Lista 1 ainda estimada (P-10). Se o teste indicar o Starter, há custo a partir de março (cerca de US$ 7/mês). Desde a P-13 (02/10/2026), não há liberação a alunos, e a apresentação passa para a Sprint 19 |
| 13 (05/10–18/10) | Contas, sessão e login por senha | US-26, US-30 | Banco de contas com migrações; conta do desenvolvedor por *seed*; login por nome ou e-mail e senha; sem sessão, a página só mostra Registrar e Entrar, e toda rota da API responde 401 | Primeira sprint com banco no caminho da requisição; o Postgres local fica sem porta no host, para não colidir com outros projetos |
| 14 (19/10–01/11) | Registro por e-mail, verificação e perfil | US-24, US-29 | Registro com domínio exato e regras de senha; e-mail de verificação com link de uso único (Mailpit no ambiente local); fila de aprovação; perfil com tratamento | Serviço de e-mail ainda não escolhido (Q-17) |
| 15 (02/11–15/11) | Cargos, aprovação e gerenciamento | US-27, US-28 | Aprovar com cargo, recusar, alterar cargo, remover (Ex-monitor, Conselheiro ou inativo) e reativar pela tela de gerenciamento, com a matriz de permissões testada por chamada direta | Muitas combinações de alçada; a matriz de testes é a especificação |
| 16 (16/11–29/11) | Google, mesma origem e segurança da autenticação | US-25 | Registro e login pelo Google com validação no backend; página e API na mesma origem no piloto; suíte de segurança da autenticação verde | Depende do *rewrite* da Vercel (P-15) e do cliente OAuth criado pelo autor no Google Cloud |
| 17 (30/11–13/12) | Painel de plágio | US-31 | Similaridade e faixas na página; cópia com variáveis renomeadas dá ≥ 99%; comparação no analisador isolado | Falsos positivos em exercícios curtos (ameaça 20) |
| 18 (14/12–27/12, recesso) | Feedback por LLM: provedores e montagem | US-32 | Adaptadores e provedor falso; apresentação, abertura e frase obrigatória montadas pelo backend; nome trocado por `[ALUNO]`; saída validada | Capacidade reduzida no recesso; o provedor depende da Q-16 |
| 19 (28/12–10/01, recesso; Marco 2) | Feedback na página e liberação para a equipe | US-32, US-11 | Botão Gerar feedback com campo editável e Copiar; guia da equipe; piloto no ar com login; apresentação a monitores-chefes e professores | Capacidade reduzida no recesso; contas externas configuradas pelo autor (Supabase, Google, e-mail e LLM) |
| 20 (11/01–24/01) | Lista 2 e validação com gabaritos | US-07 | `zip` condicional e R-02 da L2 ativos; gabaritos de períodos anteriores sem violação (corpus privado, Q-14); L2 habilitada | Gabaritos que usam permissões de questão aparecem como violação até a Sprint 24 |
| 21 (25/01–07/02) | Telemetria mínima e alertas | US-16, US-19 | Eventos anônimos no Supabase; `v_top_rules_by_list` consultável; alertas do UptimeRobot (ativos desde a Sprint 11) revisados num exercício de falha | Uso das Listas 1 e 2 sem dados para a P-09 se a telemetria atrasar |
| 22 (08/02–21/02, Carnaval) | Listas 3–4 | US-08 | L3–L4 habilitadas; `.append()` na L2 mostra "permitido a partir da Lista 3" | Mapeamento de L3–L4 com casos novos; capacidade reduzida no Carnaval |
| 23 (22/02–07/03) | Listas 5–6, recursão obrigatória e registro do gerenciamento | US-06, US-27 | L5–L6 habilitadas; código sem recursão na L6 mostra R-68; R-02 ativa em todas as listas; quem aprovou, recusou, mudou o cargo, removeu ou reativou cada conta aparece para o desenvolvedor e os professores (REC-06) | Grafo de chamadas para recursão mútua (C-03) |
| 24 (08/03–21/03) | Regras por questão, governança e "esqueci minha senha" | US-04, US-12, US-13, US-14, US-26 | Overrides em `rulesets/2027.1/questions/` cadastrados por monitores e aprovados por monitor-chefe ou professor, por processo (Q-22 adiada; decidida em 09/10/2026: mantém o processo, opção A de 7.13.4); `ipc-rules validate` bloqueante na CI; nova senha definida por link de e-mail (Q-19 b); predicados num registro só | Monitores precisam aprender o fluxo de PR (template e guia em `RULES.md`) |
| 25 (22/03–04/04) | Endurecimento para o primeiro deploy | US-15, US-17, US-19 | Actions fixadas por SHA e Dependabot; deploy na ordem Render → Vercel, conferindo o commit; roteiro do primeiro deploy; limpeza diária do banco e expurgo de contas (Q-19 d); workers e prazos para 0,1 CPU; dados mascarados antes da IA | Depende das contas do autor para o ensaio real (região do banco, Q-20) |
| 26 (05/04–18/04) | Correção em lote e relatório | US-33, US-09, US-21 | "Próximo aluno", Ctrl+Enter e foco no resultado; cabeçalho que cabe no celular; relatório com resumo, agrupamento e clique que leva à linha; erros, prazos e sessão vencida iguais em todas as telas | Mudanças de tela pedem a revisão do guia da equipe |
| 27 (19/04–02/05) | Plágio por árvore | US-31 | ADR-07 implementada: cópias reordenadas ou reescritas em formas equivalentes dão ≥ 95%; contenção contra enchimento; comparação de uma solução contra a turma; trechos realçados nos dois códigos | Soluções independentes de exercícios curtos ficam mais parecidas (ameaça 20): o IDF da turma é obrigatório |
| 28 (03/05–16/05) | Carga, eficácia e passagem de bastão | US-20, US-22, US-23 | Relatório k6 no Render, já com login; consultas do relatório de eficácia (P-09, Q-15), com a adoção por lista do critério 2; runbook com rollback ensaiado, backup semanal, onboarding e CONTRIBUTING; blueprint dividido; releases com tag | O relatório final de eficácia só sai no fim de 2027.1 (P-10) |
| 29 (17/05–30/05) | Indícios de uso de IA | US-34 | ADR-08: painel com as múltiplas violações, a semelhança com soluções de referência geradas por IA e os marcadores de estilo, calibrado em soluções anteriores a 2023 | Risco de o painel ser lido como prova; a política com a coordenação precisa estar combinada antes de ligar |
| 30 (31/05–13/06) | Piloto verificado ponta a ponta | US-17, US-19, US-20, US-22, US-26, US-32, US-35 | "Deploy do piloto" verde com login e e2e no piloto; UptimeRobot com alerta ensaiado; backup cifrado restaurado e rollback em ≤ 5 min, com os tempos no runbook; P-12 (a) e P-15 confirmadas; supervisord sem `PermissionError` | Começa com a conta de verificação (ação do autor); capacidades do contêiner no Render (P-17) |
| 31 (14/06–27/06) | Decisões com a coordenação, auditoria bloqueante e troca de período sem código | US-11, US-13, US-15, US-23, US-32, US-34, US-36 | Política dos indícios, Q-16, Q-17 e Q-22 levadas com as opções de 7.13; Marco 2; gitleaks, pip-audit, npm audit e Semgrep bloqueantes no CI | Agenda da coordenação e do NTI |
| 32 (28/06–11/07) | Comparação com o gabarito | US-37, US-38 | Verificação com a análise comparativa com o gabarito da questão; plágio com A×gabarito, B×gabarito e o alerta de possível vazamento; nenhum texto do gabarito fora do servidor | Credencial só de leitura dos gabaritos no Render (autor); P95 da verificação com a comparação (NFR-01) |
| 33 (12/07–25/07) | Gabaritos, questões de 2027.1 e calibração | US-13, US-14, US-34 | Job dos gabaritos rodando; calibração com ≤ 5% de faixa alta; ruleset de 2027.1 com questões e referências | Dados externos (Q-14, soluções anteriores a 2023, documento de permissões de 2027.1) |
| 34 (26/07–08/08) | Prontidão para 2027.1 | US-12, US-19, US-22 | Plano do Render aplicado e medido; teste sintético diário; cenários do NFR-04 e do NFR-05; listas validadas habilitadas | Custo do Starter (decisão do autor); calendário da UFPE (P-10) |
| 35 (09/08–22/08) | Controles de qualidade e observabilidade | US-14, US-15, US-17, US-21 | pytest-benchmark, Lighthouse CI, cobertura por pasta, canário mensal e esquema do ruleset sem [PLANEJADO] | Variação de tempo dos runners; chave de API do Render para os logs |
| 36 (sob comando do autor) | Defeitos e documentos certos para a campanha de testes | US-06, US-08, US-11, US-20, US-22, US-31, US-33, US-37 | Turma com nomes repetidos e `###` no código corrigida; Tab e Shift+Tab no editor; recursão só na Lista 6 (Q-33); construções em português; tempo de 50 KB medido no piloto; guia e documentação fiéis ao motor | O separador novo muda um hábito da equipe |
| 37 (sob comando do autor) | Verificação mais clara | US-09, US-11, US-21, US-33 | Resumo por categoria e cartões; editor fixo e abas no celular; componentes comuns; identidade visual; tema, rascunho e atalhos | Mudança visual grande |
| 38 (sob comando do autor) | Explicar cada regra e exportar | US-02, US-08, US-10, US-12, US-22, US-32, US-33 | Porquê e alternativa em cada violação; feedback sem IA mais completo; exportar e carregar `.py`; feedback sem nova análise | Revisão dos textos por quem conhece o documento |
| 39 (sob comando do autor) | Qualidade interna, operação e documentação | US-14, US-15, US-20, US-35 | Arquivos menores; testes das páginas; CI mais rápida; backup agendado e restauração ensaiada; documentação reorganizada | Refatorar sem mudar comportamento |
| 40 (sob comando do autor) | A correção da turma inteira | US-16, US-31, US-33 | Correção em lote por upload com CSV; plágio todos contra todos com grupos; painel por lista | Carga concentrada no plano gratuito |
| 41 (a última da fila, P-24) | Fase 2 (bloqueada) | US-20, US-23 | GHCR por digest, deploy *pull-based* no CIn e staging | Só com a P-09 atingida, a Q-12 respondida e a validação com a equipe, a coordenação e a direção (P-24) |
| 42 (sob comando do autor) | Indícios de IA ligados no piloto | US-34 | Calibração na meta; evidência e confiança em cada indício; ligação primeiro para a chefia e depois para todos; guia e registro de casos | Leitura do painel como prova; base humana pequena (os gabaritos da equipe) |
| 43 (sob comando do autor) | Período na página e retenção por encerramento | US-37, US-39, US-40 | Período antes de Lista e Questão; o ativo e os 5 anteriores carregados; `retire-period` com simulação | `ruleset_version` por período nos painéis |
| 44 (sob comando do autor) | Feedback rastreável e o padrão do monitor | US-32, US-41, US-42 | Cada violação com linha e motivo no feedback sem IA; `estilo.yaml` revisado por PR | Texto mais longo para o Dikastis |
| 45 (sob comando do autor) | "Aprimorar com IA" com validação e crítica | US-32, US-43 | Nenhuma construção fora dos achados; nada de solução pronta nem de gabarito; uma rodada de crítica | Uma chamada a mais da cota gratuita |
| 46 (sob comando do autor) | Plágio calibrado | US-31, US-38, US-44 | Precisão e revocação medidas com plágio sintético; IDF de base por questão; matriz com trechos | Corpus pequeno até a P-21 |
| 47 (sob comando do autor) | Grupos de acompanhamento e histórico dos alunos | US-45, US-46, US-47 | Grupos com convite e aceite; histórico com o resultado resumido, sem código nem feedback; expurgo por período | Primeiro dado pessoal de alunos; aviso de privacidade aprovado pela coordenação antes da release |
| 48 (no fim da fila) | Entrada com o Google no piloto | US-25 | Cliente OAuth criado pelo autor; botão do Google no piloto; ensaio de domínio e de aprovação | Tela de consentimento publicada |
| Backlog (após o piloto) | Melhorias de experiência | US-10 | Tela de permissões da lista, editor com realce (CodeMirror) e análise do fluxo de controle no plágio (ADR-07, alternativa D, reavaliada com os números da Sprint 46); o upload de `.py` e a alternância de tema entraram nas Sprints 38 e 37 | Dependem da avaliação do piloto |

### 7.2 Onde está o detalhe de cada sprint

Desde a S39-05 (16/10/2026), o blueprint fica com os requisitos, a arquitetura, o roadmap, a DoD e
a integração; o detalhe de cada sprint mora num arquivo próprio. As seções antigas, citadas em
outros documentos, ficaram assim:

| Seção até 15/10/2026 | Onde está agora |
|---|---|
| 1.2 Falhas críticas corrigidas | [`historico/sprints-01-35.md`](historico/sprints-01-35.md) |
| 7.2 a 7.12 Tasks das Sprints 1 a 35 (inclusive 7.12.1, a base de testes de toda sprint) | [`historico/sprints-01-35.md`](historico/sprints-01-35.md) |
| 7.13 Decisões em aberto: opções para quem decide | [`decisoes.md`](decisoes.md), no fim |
| 7.14 Matriz de rastreabilidade das pendências | [`historico/sprints-01-35.md`](historico/sprints-01-35.md) |
| 7.15 e 7.16 Tasks das Sprints 36 a 48 | [`sprints/`](sprints/README.md), um arquivo por sprint |

## 8. Definition of Done (DoD)

Cada item é verificado como sim ou não. Uma task ou história só está pronta quando todos os itens aplicáveis estão marcados como "sim".

### Código

- [ ] A mudança entrou por PR. Na Fase 0 (desenvolvimento solo), o PR tem CI verde e o checklist de autorrevisão preenchido; PRs de regra seguem o `RULES.md`, e quem faz o merge confere a aprovação (sem CODEOWNERS nem check automático, porque o GitHub Free não os aplica em repositório privado; Q-22) do responsável pelo caminho alterado (professor em `rulesets/*/base.yaml`; monitor-chefe ou professor em `rulesets/*/questions/**`, sem autoaprovação; professor em override que libera R-05…R-14; mantenedor de segurança em `backend/**` e `deploy/**`).
- [ ] ruff, `mypy --strict`, ESLint e `tsc` passam com 0 erros (avisos do ESLint não reprovam a CI).
- [ ] O contrato do import-linter passa: o pacote `ipc_api` não importa `ast`, o motor não importa FastAPI e o `ipc_analyzer` não importa `asyncpg` nem `argon2` (desde a Sprint 13).
- [ ] As regras de segurança do ruff e a guarda de código (`backend/tests/test_code_guards.py`) não encontram `eval`, `exec`, `compile` (fora de `engine/parse.py`), `__import__`, `importlib`, `runpy`, `pickle` nem `subprocess` sobre dados de requisição.
- [ ] As dependências estão fixadas com hash em `uv.lock` e `package-lock.json`.
- [ ] Nenhuma regra de permissão foi codificada fora de `rulesets/**`. Todo `rule_id` usado em código ou teste existe no catálogo R-xx.

### Testes

- [ ] Os testes unitários e de integração passam na CI.
- [ ] A cobertura somada de `ipc_analyzer` e `ipc_api` é ≥ 90% (`--cov-fail-under=90`; NFR-16), com `ipc_analyzer/engine` ≥ 90% e cada outra pasta ≥ 80% (`backend/scripts/coverage_by_folder.py`, S35-03).
- [ ] Cada R-xx criado ou alterado tem pelo menos 3 casos golden (permitido na lista correta, proibido antes dela e evasão quando couber), com 0 FP e 0 FN (NFR-18).
- [ ] Os testes de contrato da API, gerados do OpenAPI, passam para todos os códigos de status documentados em 5.2.2.
- [ ] O benchmark do motor não regrediu mais de 20% e fica em P95 ≤ 50 ms nas entradas de até 5 KB (NFR-02, S35-01).
- [ ] O smoke e2e (Playwright) está verde: localmente na Fase 0 e no ambiente do piloto a partir da Sprint 11.
- [ ] Quando a entrega afeta o caminho de requisição (a partir da Sprint 28), o `deploy/load/run_load.py` no plano do piloto ou o workflow "Carga no piloto" mostra o P95 dentro do NFR-01; os cenários do NFR-04 e do NFR-05 estão no mesmo `run_load.py` desde a S34-03 (`--scenario nfr04` e `nfr05`), à mão.
- [ ] [PLANEJADO, a partir da Sprint 46] Uma mudança no plágio não baixa a precisão nem a revocação medidas pelo `ipc-rules calibrate-plagio` (FR-37).
- [ ] [PLANEJADO, a partir da Sprint 47] Toda rota dos grupos de acompanhamento tem a matriz cargo × ação × alvo testada por chamada direta, e o canário do NFR-11 cobre as tabelas da ADR-13.

### Segurança: submissões maliciosas contra o isolamento e o motor de regras

- [ ] 1. Código com 51.201 bytes retorna 413 `PAYLOAD_TOO_LARGE`, e um corpo acima de 128 KB é recusado antes de ser lido (pelo Caddy nas Fases 0 e 2; pela `api` na Fase 1).
- [ ] 2. Código com 1.001 linhas retorna 422 `INVALID_INPUT`.
- [ ] 3. Byte nulo, UTF-8 inválido e caracteres de controle retornam 422 `INVALID_INPUT`, sem 5xx.
- [ ] 4. 1.000 níveis de parênteses, colchetes ou `not` retornam 422 `ANALYSIS_LIMIT` em ≤ 2,5 s.
- [ ] 5. Cadeia `1+1+…+1` com 25 mil termos retorna 422 `ANALYSIS_LIMIT`, e a entrada mais larga que cabe em 50 KB (~53 mil nós) é analisada em menos de 2 s, sem `RecursionError` nos logs.
- [ ] 6. Literal de 50 KB e f-strings aninhadas respondem em < 2,5 s.
- [ ] 7. `while True: pass` e recursão infinita recebem resposta (violação ou sucesso) em < 100 ms, o que prova que nada foi executado.
- [ ] 8. As tentativas de RCE geram violações e o arquivo canário não é criado: `__import__("os").system("touch /tmp/canary")`, `open("/tmp/canary", "w")`, `eval`, `exec`, `compile`, `breakpoint()`, `getattr(__builtins__, "eval")` e `().__class__.__mro__[1].__subclasses__()`.
- [ ] 9. As tentativas de evasão do motor geram as violações esperadas:
  - `f = s.split; f()`, `getattr(s, "split")()` e `type("C", (), {})`;
  - `{*x}`, `[*a]`, `print(*a)` e `**kw`;
  - `lambda` antes da L5, `{}`/`dict()` antes da L5, `:=`, `match`, decoradores, `async def`/`async for`, `yield`, `assert`, `with`, `raise`, `nonlocal` e `global`;
  - um built-in sombreado por variável do aluno, que não deve gerar falso positivo.
- [ ] 10. Requisições concorrentes com marcadores distintos nunca recebem violações ou trechos umas das outras.
- [ ] 11. Isolamento do `analyzer` verificado na CI (contêiner próprio nas Fases 0 e 2):
  - conexão TCP e resolução DNS externas falham;
  - escrita no rootfs falha;
  - UID ≠ 0;
  - `env` sem segredos;
  - `cap_drop: ALL` e `no-new-privileges` ativos;
  - `pids_limit` e `mem_limit` aplicados.
  - na Fase 1 (Render): o processo do analisador roda com UID 10002, sem segredos no ambiente, não consegue ler o ambiente da `api`, e o seccomp dos workers bloqueia socket de rede e `execve`.
- [ ] 12. Depois dos itens 1 a 11, `/ready` = 200 e não há worker zumbi nem preso.
- [ ] 13. O teste canário de privacidade encontra 0 ocorrências do marcador em logs, no banco e no FS (NFR-11), inclusive nas rotas de plágio e de feedback (a partir das Sprints 17 e 18).
- [ ] 14. O job "Auditoria" do `ci.yml` (gitleaks, Semgrep, pip-audit e npm audit) está verde no PR, e a última rodada do workflow semanal `audit.yml` (os mesmos e o Trivy) não tem CVE crítica ou alta corrigível nem segredo sem triagem (NFR-09, NFR-13). Enquanto a cota do GitHub Actions estiver esgotada (P-19), vale o `scripts/ci-local.sh`, que roda os mesmos passos.
- [ ] 15. HSTS e CSP estão presentes, o TLS é ≥ 1.2 e o CORS segue o NFR-10: só a origem da SPA na Fase 1 e nenhum cabeçalho CORS nas Fases 0 e 2 (a partir da Sprint 11).
- [ ] 16. Sem sessão, todas as rotas do OpenAPI, exceto `/health`, `/ready` e `/api/v1/auth/*`, respondem 401 `UNAUTHENTICATED` e não retornam dados (a partir da Sprint 13).
- [ ] 17. A matriz de permissões do FR-27 é testada por chamada direta à API: monitor não aprova, não muda cargos nem remove contas; monitor-chefe não age sobre professor; só o desenvolvedor altera a conta do desenvolvedor; ninguém altera o próprio cargo (a partir da Sprint 15).
- [ ] 18. Domínios e Google: `x@xcin.ufpe.br`, `x@ee.ufpe.br` e `x@cin.ufpe.br.exemplo.com` são recusados nos dois métodos; maiúsculas são aceitas; Google com domínio fora ou `email_verified` falso é recusado mesmo com o `hd` adulterado; o registro pelo Google cai na fila de aprovação (a partir da Sprint 16).
- [ ] 19. Sessão: cookie `HttpOnly`, `Secure` e `SameSite=Lax`; identificador novo a cada login; sessões encerradas na troca de senha, na mudança de cargo e na remoção; rota que muda estado com `Origin` de outro site recebe 403 (a partir da Sprint 13).
- [ ] 20. Tokens e senhas: link de verificação expirado ou usado não funciona; senha que viola qualquer regra é recusada pelo backend; depois de 5 falhas de login em 15 min, a próxima tentativa espera; nenhuma senha, token ou cookie aparece em log (canário) (a partir da Sprint 14).
- [ ] 21. Feedback: a requisição ao provedor não contém o nome real do aluno; a apresentação e a frase obrigatória aparecem sempre; o texto é exibido como texto puro (a partir da Sprint 18).
- [ ] 22. Plágio: as entradas dos itens 1 a 8, em qualquer um dos dois códigos, recebem resposta controlada, sem 5xx e sem efeito colateral (a partir da Sprint 17).

### Documentação

- [ ] O OpenAPI foi regenerado e versionado, e os tipos do frontend foram regenerados a partir dele.
- [ ] `docs/mapping-R-xx.md` e o `CHANGELOG.md` (com a `ruleset_version` nova) foram atualizados quando alguma regra ou mapeamento mudou, com o "de acordo" do professor.
- [ ] Toda mudança de decisão arquitetural tem um ADR novo ou atualizado em `docs/adr/`.
- [ ] README, `RULES.md` e runbook foram atualizados quando o setup, a operação ou o processo de regras mudou.
- [ ] Toda premissa ou questão nova ou resolvida foi registrada em `docs/decisoes.md` (seção 1.3).
- [ ] O aviso de privacidade foi atualizado quando mudaram os dados pessoais guardados ou enviados a terceiros (a partir da Sprint 14).
- [ ] [PLANEJADO, a partir da Sprint 44] O `estilo.yaml` do feedback passa no esquema, e as mudanças de tom foram revisadas por um monitor-chefe, um professor ou o desenvolvedor (Q-31).

### Implantação

- [ ] As imagens são construídas na CI (jobs `security` e `e2e`) sobre imagens base fixadas por digest; o Render constrói a imagem do piloto a partir da `main`. Publicar no GHCR com tag = SHA e referenciar por digest é [PLANEJADO, Fase 2].
- [ ] Na Fase 0, `docker compose up --build` sobe o ambiente local, com `/ready` = 200. A partir da Sprint 11, o deploy no Render e na Vercel é disparado pelo pipeline depois da CI (não manualmente), com smoke e2e verde e `/ready` = 200.
- [ ] O `ENABLED_LISTS` de produção corresponde às listas cujo ruleset foi validado pelo professor.
- [ ] O rollback segue o `docs/runbook.md` e leva ≤ 5 min; o ensaio cronometrado fica registrado no runbook (a partir da Sprint 28).
- [ ] O UptimeRobot monitora `/ready`, `/health/slo` e a SPA a cada 5 min, com alerta por e-mail, configurado pelo autor conforme `deploy/piloto.md` e registrado no runbook.
- [ ] Toda migração de banco é reversível e foi testada antes de ir para o piloto (a partir da Sprint 13).
- [ ] [PLANEJADO, a partir da Sprint 47] Uma migração que cria tabelas com dados pessoais de alunos traz a função de expurgo e o teste dela (NFR-29).
- [ ] Os segredos novos (banco de contas, cliente OAuth, e-mail e LLM) existem só no ambiente da `api`, nunca no do `analyzer` nem no build da página (a partir da Sprint 13).

## 9. Integração com outros projetos da monitoria (possibilidade)

Existe a possibilidade, **não confirmada**, de o IP-Checker ser integrado a outros 2 projetos, mantidos por outros 2 monitores, cujos detalhes não são conhecidos (Q-23). Esta seção registra o que o IP-Checker oferece hoje, levantado do código em 07/10/2026, os pontos de integração candidatos e as lacunas, para que a conversa com esses monitores parta de fatos. Não há sprint de implementação: a decisão fica no ADR-09, com status Proposto.

### 9.1 Mapa da API pública

Levantado das rotas em `backend/src/ipc_api/routes/` e conferido com o `docs/openapi.json`, que é gerado do próprio app e conferido pelo CI (`tests/test_api_contract.py`). "Sessão" é o cookie `__Host-ipc_session` (`HttpOnly`, `Secure`, `SameSite=Lax`), criado pelo `POST /api/v1/auth/login` ou pelo Google; requisições que mudam estado com `Origin` de outro site recebem 403 `ORIGIN_MISMATCH`. Todo `/api/*` passa por um limite geral de 600 requisições por minuto por IP (6.000 nas faixas do campus); "Limitada" quer dizer que a rota também está em `LIMITED_ROUTES` (`backend/src/ipc_api/ratelimit.py`), com o limite por IP sem sessão (P-11).

| Método | Rota | Autenticação | Entrada | Saída | Códigos | Limite de taxa | Arquivo |
|---|---|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Nenhuma | `LoginRequest` (nome ou e-mail e senha) | `AccountResponse` e o cookie | 200, 401, 403, 422, 429, 503 | 30/min por IP sem sessão; bloqueio por falhas | `routes/auth.py` |
| GET | `/api/v1/auth/options` | Nenhuma | — | `AuthOptions` (`google`, `feedback_ai`, `ai_indicators`) | 200 | Geral | `routes/auth.py` |
| POST | `/api/v1/auth/logout` | Sessão (opcional) | — | — | 204, 403, 503 | Geral | `routes/auth.py` |
| GET | `/api/v1/auth/me` | Sessão | — | `AccountResponse` | 200, 401, 503 | Geral | `routes/auth.py` |
| POST | `/api/v1/auth/register` | Nenhuma | `RegisterRequest` | `RegisterResponse` | 201, 403, 409, 422, 429, 503 | Limitada | `routes/auth.py` |
| POST | `/api/v1/auth/verify` | Nenhuma | `VerifyRequest` (token do e-mail) | `VerifyResponse` | 200, 403, 422, 429, 503 | Limitada | `routes/auth.py` |
| POST | `/api/v1/auth/verify/resend` | Nenhuma | `ResendRequest` | — | 202, 403, 422, 429, 503 | Limitada; 1/min e 5/dia por conta | `routes/auth.py` |
| POST | `/api/v1/auth/password/forgot` | Nenhuma | `ForgotPasswordRequest` | — | 202, 403, 422, 429, 503 | Limitada | `routes/auth.py` |
| POST | `/api/v1/auth/password/reset` | Nenhuma | `ResetPasswordRequest` | — | 204, 403, 422, 429, 503 | Limitada | `routes/auth.py` |
| GET | `/api/v1/auth/google/start` | Nenhuma | — | Redireciona ao Google | 303, 429 | Limitada | `routes/google.py` |
| GET | `/api/v1/auth/google/callback` | Nenhuma | `code`, `state`, `error` (query) | Redireciona à página | 303, 422, 429 | Limitada | `routes/google.py` |
| GET | `/api/v1/auth/google/pending` | Cadastro pelo Google em andamento | — | `GooglePending` | 200, 422 | Geral | `routes/google.py` |
| POST | `/api/v1/auth/google/complete` | Cadastro pelo Google em andamento | `GoogleSignup` | `GoogleSignupResponse` | 201, 403, 409, 422, 429, 503 | Limitada | `routes/google.py` |
| PATCH | `/api/v1/profile` | Sessão | `ProfileUpdate` | `AccountResponse` | 200, 401, 403, 409, 422, 503 | Geral | `routes/profile.py` |
| POST | `/api/v1/profile/password` | Sessão | `PasswordChange` | — | 204, 401, 403, 422, 429, 503 | Limitada; 5 senhas atuais erradas em 15 min bloqueiam | `routes/profile.py` |
| GET | `/api/v1/lists` | Sessão | — | Listas habilitadas e questões | 200, 401, 503 | Geral | `routes/meta.py` |
| POST | `/api/v1/validate` | Sessão | `ValidateRequest` (`code`, `list_number`, `question_id`) | `ValidateResponse` (violações, avisos e, se ligados, `indicators`) | 200, 401, 403, 413, 422, 429, 503 | 30/min por conta | `routes/validate.py` |
| POST | `/api/v1/validate/batch` | Sessão | `ValidateBatchRequest` (`list_number`, `question_id` e de 1 a 20 `files`) | `ValidateBatchResponse` (uma linha por arquivo) | 200, 401, 403, 413, 422, 429, 503 | 30/min por conta, dividido com a verificação; o lote conta 1, e cada arquivo passa pela admissão | `routes/validate.py` |
| POST | `/api/v1/similarity` | Sessão | `SimilarityRequest` (`code_a`, `code_b`) | `SimilarityResponse` | 200, 401, 403, 413, 422, 429, 503 | 30/min por conta, dividido com a verificação | `routes/similarity.py` |
| POST | `/api/v1/similarity/batch` | Sessão | `SimilarityClassRequest` (até 100 soluções) | `SimilarityClassResponse` | 200, 401, 403, 413, 422, 429, 503 | idem | `routes/similarity.py` |
| POST | `/api/v1/similarity/class-matrix` | Sessão | `SimilarityMatrixRequest` (de 2 a 60 soluções) | `SimilarityMatrixResponse` (pares e grupos) | 200, 401, 403, 413, 422, 429, 503 | idem | `routes/similarity.py` |
| POST | `/api/v1/feedback` | Sessão | `FeedbackRequest` (`code`, `list_number`, `student_name`, `annotation`, `question_id`) | `FeedbackResponse` (`text`, `source`, `provider`) | 200, 401, 403, 413, 422, 429, 503 | idem, mais 60/dia por conta e 1.000/dia no servidor | `routes/feedback.py` |
| GET | `/api/v1/admin/requests` | Sessão de monitor-chefe, professor ou desenvolvedor | — | `RequestsResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/requests/{account_id}/approve` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/requests/{account_id}/reject` | idem | — | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| GET | `/api/v1/admin/members` | idem | — | `MembersResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| PATCH | `/api/v1/admin/members/{account_id}/role` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/members/{account_id}/remove` | idem | — | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/members/{account_id}/reactivate` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| GET | `/api/v1/admin/log` | Sessão de professor ou desenvolvedor (REC-06) | — | `ManagementLogResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| GET | `/api/v1/admin/list-panel` | Sessão de monitor-chefe, professor ou desenvolvedor | `list_number` e `semester` (query) | `ListPanelResponse` (só contagens anônimas) | 200, 401, 403, 422, 503 | Geral | `routes/admin.py` |
| GET | `/health` | Nenhuma | — | `HealthResponse` | 200 | Livre | `routes/meta.py` |
| GET | `/ready` | Nenhuma | — | `ReadyResponse` (versão do ruleset e `release`; consulta o banco) | 200, 503 | Livre | `routes/meta.py` |
| GET | `/health/service` | Nenhuma | — | `ReadyResponse` (sem o banco; health check do Render) | 200, 503 | Livre | `routes/meta.py` |
| GET | `/health/slo` | Nenhuma | — | `SloResponse` (P95 e 5xx dos últimos 5 min) | 200, 503 | Livre | `routes/meta.py` |

O analisador tem uma API interna (`/internal/analyze`, `/internal/feedback-input`, `/internal/similarity`, `/internal/similarity/class`, `/internal/similarity/matrix`, `/internal/ruleset/manifest` e `/internal/health`, em `backend/src/ipc_analyzer/service/app.py`), que escuta só em `127.0.0.1` (Render) ou na rede interna `analyzer_net` (compose) e não é ponto de integração (ADR-01).

### 9.2 Arquitetura atual, resumida para quem integra

- **Componentes:** a página (React, Vercel) fala só com a própria origem; a Vercel repassa `/api/*` à API (FastAPI, Render, UID 10001), que chama o analisador (UID 10002, seccomp, sem rede de saída) por `127.0.0.1` (ADR-01, ADR-03, ADR-04).
- **Dados:** contas, sessões, links de e-mail, registro de gerenciamento, cota de feedback e adoção por lista no esquema `app`, e telemetria anônima no esquema `telemetry`, no PostgreSQL do Supabase (us-east-1). O código do aluno nunca é guardado (NFR-11).
- **Autenticação:** sessão por cookie de conta aprovada da equipe; não há chave de API, token de serviço nem OAuth para outros sistemas.
- **Serviços externos:** Render (API), Vercel (página), Supabase (banco), Brevo (e-mail de verificação e de redefinição de senha), Google (entrada opcional, OIDC) e, se a Q-16 aprovar, um provedor de IA para o feedback.
- **Dados pessoais (LGPD):** da equipe, nome, e-mails institucionais, curso, tratamento, cargo, status, resumo Argon2id da senha, identificador Google, atividade e o registro de gerenciamento (12 meses); dos alunos, só o código, analisado e descartado, e o nome digitado no feedback, que nunca vai à IA (`[ALUNO]`). Os servidores ficam nos EUA (transferência internacional, a avaliar com a coordenação junto com a Q-16).

### 9.3 Pontos de integração candidatos e lacunas

| Ponto candidato | O que já existe | Lacuna para outro sistema usar |
|---|---|---|
| Verificar, comparar ou gerar feedback por outro sistema | `/api/v1/validate`, `/similarity`, `/similarity/batch` e `/feedback`, versionados em `/api/v1` e descritos no `docs/openapi.json` | Só sessão de pessoa (cookie); falta autenticação entre serviços (por exemplo, uma conta de serviço com token próprio e limite próprio); o limite de 30/min por conta não serve a lotes |
| Chamar a API de outro domínio pelo navegador | `IPC_CORS_ORIGINS` e `IPC_ALLOWED_ORIGINS` existem; no piloto o CORS está desligado (mesma origem) | Cada origem precisa ser liberada por configuração, e o cookie `SameSite=Lax` não vai em chamadas de outro site |
| Embutir a página em outro sistema | — | A CSP tem `frame-ancestors 'none'`: embutir em `iframe` exige mudar a política |
| Identidade compartilhada | Entrada pelo Google (OIDC), restrita aos domínios da UFPE | Nenhum SSO com outros sistemas; as contas e os cargos são só do IP-Checker |
| Regras das listas | `rulesets/` em YAML, com versão (`ruleset_version`) e SHA-256 no manifesto interno | O manifesto é interno; não há rota pública que exponha o ruleset |
| Dados agregados | Views anônimas em `telemetry` para o papel `ipc_reader` (FR-17, S28-02) | Acesso direto ao banco, sem API; outro sistema precisaria de um papel de leitura próprio |
| Eventos para outro sistema | — | Não há webhooks nem fila de eventos |
| Idempotência | `/validate`, `/similarity` e `/feedback` não guardam estado (o feedback gasta cota); as ações de gerenciamento recusam com 409 a transição já feita | Não há cabeçalho de idempotência; repetir um feedback gasta cota de novo |
| Isolamento de dados | Uma única disciplina, sem identificador de inquilino | Atender outra disciplina ou outro sistema com dados separados exigiria um modelo de inquilinos |

### 9.4 Perguntas aos outros 2 monitores

1. Qual é o objetivo de cada projeto, quem são os usuários (alunos, monitores, professores) e em que período ele entra em uso?
2. O projeto precisa **consumir** o IP-Checker (verificar, comparar, gerar feedback), **alimentá-lo** (enviar soluções, questões, regras, turmas) ou só **compartilhar** login e cargos?
3. As chamadas partem do navegador do usuário ou de um servidor? De qual domínio?
4. Qual o volume esperado por minuto e por dia, e em quais picos (véspera de prazo)?
5. Que dados pessoais o projeto trata (de alunos ou da equipe)? Onde ficam hospedados e quem é o responsável pelo tratamento (LGPD)?
6. Como o projeto autentica os usuários hoje? Usa o Google com contas `@cin.ufpe.br` ou `@ufpe.br`, outro provedor ou contas próprias?
7. Ele precisa receber eventos do IP-Checker (por exemplo, quando uma verificação termina), ou basta chamar e esperar a resposta?
8. Em que linguagem e plataforma está, e onde roda (Render, Vercel, servidor do CIn)?
9. Há contrato de API (OpenAPI) ou versionamento do lado dele?
10. Quem mantém cada projeto depois que o monitor sair, e quem aprova mudanças que afetem os dois lados?
11. O projeto executa código de aluno? Se sim, como o isola (o IP-Checker nunca executa, ADR-01)?
12. A coordenação já sabe da integração e a aprovou?

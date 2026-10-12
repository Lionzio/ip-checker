# IP-Checker — Blueprint Definitivo e Acionável

## 1. Visão Geral e Melhorias Aplicadas

### 1.1 Visão geral do IP-Checker

O IP-Checker é um verificador web de uso restrito à equipe da disciplina (desenvolvedor, professores, monitores-chefe e monitores), sem execução de código, que confere se uma solução em Python de um aluno de Introdução à Programação respeita as regras de permissão da lista e da questão selecionadas (catálogo R-01…R-68, seção 3.1). Ele apoia a correção feita pela equipe: aponta as proibições, compara duas soluções em busca de plágio e redige, com uma LLM, um feedback para o aluno a partir do resultado do motor, que continua sendo o único a decidir se houve violação. O acesso é restrito porque o uso frequente de proibições é um dos principais indícios de solução gerada por IA: com a ferramenta aberta, um aluno poderia gerar o código com IA, ver as proibições e pedir à IA que as removesse (P-13, decisão de 02/10/2026). Todas as funções exigem conta aprovada e ativa, com e-mail `@cin.ufpe.br` ou `@ufpe.br`, criada por e-mail e senha ou pelo Google e aprovada manualmente por monitor-chefe, professor ou pelo desenvolvedor (ADR-04). O código é analisado apenas pela sua árvore sintática (AST), dentro de um serviço analisador isolado, sem segredos, sem rede de saída e com limites de tamanho, tempo e memória (ADR-01); a comparação de plágio roda no mesmo analisador (ADR-05). As regras ficam em um ruleset versionado e declarativo, sob a responsabilidade do professor (regras das listas) e dos monitores (regras das questões, com aprovação de monitor-chefe ou professor). Assim, mudar uma lista não exige mudar o motor (ADR-02). Cada violação aparece com regra, linha, coluna e mensagem em PT-BR. A telemetria agregada e anônima não guarda código, IP nem identificador de pessoa. As Sprints 1 a 12 foram concluídas em 01/10/2026: o MVP (Sprint 9) entregou o fluxo ponta a ponta seguro para a Lista 1, rodando localmente. As Sprints 13 a 19 (contas, registro com verificação por e-mail, perfil, gerenciamento da equipe, Google, mesma origem no piloto, painel de plágio, a montagem do feedback, o feedback na página, o aviso de privacidade e o guia da equipe) foram concluídas em 02/10/2026; falta o primeiro deploy com login, que depende das contas do autor. A Sprint 20 habilitou a Lista 2, com o `zip` condicional (R-37) e a exigência do laço (R-02), e deixou pronta a validação com os gabaritos de períodos anteriores. A Sprint 21 ligou a telemetria anônima (views do FR-17 e expurgo de 12 meses) e os alertas de latência e de erro, a Sprint 22 habilitou as Listas 3 e 4, e a Sprint 23, as Listas 5 e 6, com a recursão obrigatória (R-68), e o registro das ações de gerenciamento (REC-06). O acesso restrito, o painel de plágio e o feedback entram nas Sprints 13 a 19, antes de qualquer exposição na internet; as Listas 2 a 6 e a telemetria vieram em seguida (Sprints 20 a 23); a Sprint 24 trouxe as regras por questão, o comando `ipc-rules` e o "esqueci minha senha"; as Sprints 25 a 28 trouxeram o endurecimento para o primeiro deploy, a correção em lote, o plágio por árvore e a passagem de bastão (carga com login, relatório de eficácia, runbook, backup, onboarding e releases), e o piloto subiu em 07/10/2026 (Render, Vercel e Supabase), faltando o primeiro deploy pelo pipeline com a conta de verificação, que confirma a P-15; a Sprint 29 trouxe os indícios de uso de IA (ADR-08, Q-21), desligados no piloto até a coordenação aprovar a política. As Sprints 30 a 36 (plano de 07/10/2026, seção 7.12) tratam as pendências restantes: o piloto verificado ponta a ponta, as decisões com a coordenação e o NTI, a comparação com o gabarito (ADR-11), os dados de calibração e de 2027.1, a prontidão para o período, os controles ainda [PLANEJADO] e a Fase 2; a integração com outros 2 projetos da monitoria é só uma possibilidade (seção 9, ADR-09). O piloto acontece em 2027.1, com a SPA na Vercel e o backend no Render, usado pela equipe na correção, e cada lista é habilitada antes de ser liberada aos alunos. O servidor do CIn só será adotado depois que os critérios de eficácia (P-09, em revisão na Q-15) forem atingidos (seção 7).

### 1.2 Falhas críticas corrigidas

| # | Problema | Evidência no rascunho | Impacto | Correção aplicada |
|---|---|---|---|---|
| 1 | O modelo de regras e o motor não conseguem representar o catálogo de permissões. | §12 (p.6–7): o esquema só tem `allowed_from_list` e `ast_nodes`, com IDs sintéticos como `Call_Attribute_split`. §11.3 e TASK-BE-002: "Verificar nome da classe do nó", com `visit_For`, `visit_Call`… escritos à mão. §12 mapeia `AsyncFor` como permitido a partir da Lista 2. | (a) R-37 (zip condicional), R-02/R-68 (exigências) e R-01 (precedência da questão) não podem ser expressos, então o veredito diverge do documento. (b) O *default deny* por classe de nó deixa passar `eval(...)`, `getattr(...)`, `__import__(...)` e métodos como `.title()`, porque `Call`, `Name` e `Attribute` são classes "permitidas". O resultado é um falso negativo e a questão anulada no Dikastis. (c) Cada regra nova exige código no Visitor, o que contraria a US-004 do rascunho. | Motor orientado a dados (ADR-02, 5.2.3). Ele usa um vocabulário de **fatos** (nó, operador, built-in, método/atributo, argumento nomeado, constante, contexto) e aplica o *default deny* a **cada fato**. Condições ficam em predicados declarativos, exigências em `requirements` e as regras da questão em `question_overrides`. Os IDs R-xx do catálogo são os IDs do ruleset, e o mapeamento foi validado em 01/10/2026 (Q-02). |
| 2 | O código do aluno é processado no mesmo processo da API, sem limite de tempo, e os controles de robustez ficam para depois da liberação aos usuários. | §8 e §10: parser, Rules Loader e cliente de telemetria (com credencial) na mesma aplicação FastAPI. §15: os únicos limites são tamanho e número de linhas. §11.3: `ast.NodeVisitor` recursivo. A captura de `SyntaxError` só vem na Sprint 6 (TASK-BE-010), o limite de profundidade e o rate limit na Sprint 9 (TASK-BE-012/013) e os logs seguros na Sprint 10 (TASK-BE-014). Enquanto isso, §25 libera o MVP 1.0 a testadores já na Sprint 4. | Uma entrada de até 50 KB com expressões encadeadas (ex.: `1+1+…`) gera uma AST mais profunda que o limite de recursão do Python, o que provoca `RecursionError` e HTTP 500. `ast.parse` roda em C e não pode ser interrompido por timeout em thread, então um único worker preso degrada todos os alunos no pico de entrega. Uma falha de memória do parser aconteceria num processo que guarda credencial do banco. Até a Sprint 6, todo erro de sintaxe vira 500. | ADR-01: serviço `analyzer` sem segredos e sem egress, com workers descartáveis, timeout de 2 s (kill) e `RLIMIT_AS`. A travessia é iterativa, com limite de profundidade e de nós. Limites, `SyntaxError` e logs sem código entram no MVP (7.2); rate limit e admissão entram antes de qualquer exposição à internet (Sprint 10). Todos fazem parte da DoD (seção 8). |
| 3 | O domínio está incompleto: a exigência do assunto de cada lista e a precedência da questão aparecem como opcionais. | Permissões p.1 §Introdução: "é obrigatória a implementação do assunto de cada lista" e "a prioridade será sempre o que está definido na questão". Rascunho §7.5 exige assunto só na Lista 6, e só auto-chamada direta. RF-012/TASK-BE-008 estão como "Medium / Recomendado" (§26), sem fonte de dados, formato ou responsável. §25: MVP 1.0 tem regras só das Listas 1–2, mas o seletor vai de 1 a 6 (RF-003). | A ferramenta aprova soluções que serão anuladas (ex.: Lista 2 sem laço) e acusa o que a questão permite. Isso contradiz o objetivo do §3 e mina a confiança na ferramenta. Com *default deny*, alunos das Listas 3–6 receberiam no MVP 1.0 violações para todo conteúdo permitido. | FR-10 e FR-11 passam a Must. R-02/R-68 entram no bloco `requirements`. Cada questão ganha um arquivo `questions/L<n>-Q<m>.yaml`, cadastrado por monitores e aprovado por monitor-chefe ou professor (aprovação conferida por quem faz o merge, Q-22, US-13, Q-08). O seletor passa a ser controlado por `ENABLED_LISTS`: L1 no MVP; as demais listas são habilitadas ao longo de 2027.1, antes de cada liberação (Sprints 20–23). Ver Q-04, Q-05, C-03 e Q-08. |

**Demais inconsistências encontradas (resumo):**

- **I-01** — A versão do Python se contradiz: §2 decide "3.12+" e, na mesma célula, diz "backend deve usar 3.11+"; §18 usa `python:3.12-slim` e TASK-DE-002 usa `python:3.11-slim`. Nenhuma das opções considera a versão do Dikastis. Correção: NFR-21 e Q-01.
- **I-02** — A imagem base também diverge: RNF-006 diz "Alpine-based (revisado para Debian-slim)" e o §31 diz "Alpine/Debian-slim". Correção: `python:3.13-slim` fixada por digest (5.3).
- **I-03** — O SLO de 99,9% (RNF-003) não é compatível com a hipótese de free tier com cold start (§2, linha "Render/Vercel"), nem com a ressalva "excluindo cold starts" (RNF-001). Correção: P-05, NFR-06 e ADR-03.
- **I-04** — As unidades de capacidade não batem: RNF-002 fala em "500 requests por minuto", mas o §25 (MVP 1.2) fala em "500 chamadas simultâneas". Correção: NFR-04 (vazão) separado de NFR-05 (concorrência).
- **I-05** — O rate limit de 10 req/IP/min (§2, TASK-BE-013) bloqueia laboratórios e Wi-Fi do campus atrás de NAT, e o limitador em memória não é compartilhado entre instâncias. Correção: P-04, FR-19 e ADR-03 (instância única).
- **I-06** — A precedência inclui um nível "Regra Geral" que não existe no documento de permissões (§7.4). Correção: C-02.
- **I-07** — `AsyncFor` está mapeado como permitido (§12). Correção: C-01.
- **I-08** — A detecção de métodos só olha `visit_Call` (§11.4; ADR-003 do rascunho), então não pega referências sem chamada (`f = s.split`). Correção: o fato `method:<nome>` é emitido para todo `Attribute` (5.2.3).
- **I-09** — A tabela `analytics_events` (§14) tem uma única coluna `rule_violated_id`. Ela não representa submissões com várias violações nem a questão, e não guarda `ruleset_version`. Correção: esquema `telemetry` (5.2.4).
- **I-10** — A frase "sofrer garbage collection imediatamente" (RNF-005) não pode ser verificada e o CPython não garante esse comportamento. Correção: teste canário (NFR-11).
- **I-11** — O §17 espera "400 ou 413" para "recursão infinita textual", mas entrada aninhada com até 50 KB é uma requisição bem formada. Correção: 422 `ANALYSIS_LIMIT` (5.2.2).
- **I-12** — Os KPIs não podem ser medidos: o §30.1 cita uma "base histórica" que não existe e o §3 quer "submissões inválidas… a quase zero" sem linha de base. Correção: NFR-18, P-08, Q-09 e REC-05.
- **I-13** — O §30.3 diz que `os.system("rm -rf /")` gera "bloqueio do Import". Sem `import`, porém, o nó é `Call(Attribute(Name))` e a violação correta é R-04 sobre `os`/`system`. Correção: corpus de evasão (DoD).
- **I-14** — Os RFs estão agrupados ou fora de sequência ("RF-006 a RF-010", "RF-019 e RF-026"), o que impede rastrear cada um. Correção: FR-01…FR-21 atômicos.
- **I-15** — O professor edita JSON por PR (§21), mas a validação e a documentação só chegam na Sprint 11 (TASK-DO-001). Correção: loader com validação e *fail-fast* no MVP (S1-02); FR-21 e US-14 na Sprint 24.
- **I-16** — A CI completa só vem na Sprint 8 (TASK-DE-003), enquanto a DoD do §27 exige CI desde a primeira task. Correção: S1-01.
- **I-17** — US-003 fala em "focar na lógica, não na sintaxe", mas a ferramenta verifica permissões, não lógica. Correção: US-11 reescrita.
- **I-18** — "Acessibilidade certificada" (§25) não indica norma nem método. Correção: NFR-19 (WCAG 2.1 AA, axe-core).
- **I-19** — O ADR-002 do rascunho diz que o servidor é "mais seguro" que o Pyodide. É o contrário: analisar no cliente elimina superfície de ataque no servidor. Os motivos válidos são consistência do ruleset, telemetria e custo de download. Correção: ADR-01, alternativa C.
- **I-20** — São 12 sprints sem duração, capacidade nem estimativa, e o aluno só recebe valor na Sprint 4. Correção: P-02, Q-13 e seção 7 (plano datado para um desenvolvedor, com MVP na Sprint 9 e piloto em 2027.1).
- **I-21** — O diagrama do §8 não mostra fronteiras de confiança, e o cliente de telemetria fica no mesmo processo do parser. Correção: 5.1.

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
- **FR-03** — Seleção obrigatória da lista. Só aparecem as listas habilitadas pela configuração `ENABLED_LISTS` (1 no MVP; as demais ao longo de 2027.1, antes da liberação de cada lista). A questão é opcional e é escolhida entre as cadastradas no ruleset do período ativo, já que a numeração reinicia a cada período (R-01, P-07). Origem: RF-003.
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
| NFR-01 | Desempenho | Latência do `POST /api/v1/validate` medida no servidor (borda → resposta) | P95 e P99 em janelas de 5 min | P95 ≤ 200 ms e P99 ≤ 500 ms, com 500 req/min e payload ≤ 5 KB | P95 do `/health/slo` em produção (memória da API, 5 min); k6 à mão: capacidade por plano com o `deploy/load/run_load.py` e o piloto de verdade com o workflow "Carga no piloto" (S28-01). k6 em staging e histograma Prometheus [PLANEJADO] |
| NFR-02 | Desempenho | Tempo de análise no worker (parse, fatos e política) | P95 por entrada do corpus | ≤ 50 ms para entradas ≤ 5 KB (as do NFR-01) e linear até 50 KB, com o limite de 2 s por análise como teto (Q-25, 11/10/2026; antes, ≤ 50 ms até 50 KB) | Benchmark do motor na CI desde a S35-01 (`tests/benchmark`, `IPC_BENCHMARK=1`): P95 ≤ 50 ms nas entradas de até 5 KB e regressão ≤ 20% sobre a linha de base em todas; a entrada de 50 KB leva cerca de 260 ms (Q-25) |
| NFR-03 | Desempenho | Carregamento da SPA | FCP e tamanho do JS inicial (gzip) | FCP ≤ 1,65 s no perfil móvel do Lighthouse ("Slow 4G"; Q-25, 11/10/2026; antes, < 1,5 s); JS inicial ≤ 350 KB gzip (Q-25) | Lighthouse CI e orçamento do JS na CI desde a S35-02 (`frontend/lighthouserc.json`, `scripts/js-budget.mjs`): JS inicial de 104,5 KB com gzip; FCP de 1,51 s no perfil móvel, com a CI falhando acima de 1,65 s, a meta desde a Q-25 |
| NFR-04 | Capacidade | Vazão sustentada no pico de entrega (P-01) | req/min, taxa de 5xx, taxa de timeout | 500 req/min por 15 min com 0% de 5xx e < 0,1% de timeouts | Cenário k6 `nfr04` do `deploy/load/run_load.py` (S34-03): 80% do tráfego de 4 IPs do campus (NAT, P-04) e o resto de IPs externos, com os limites por IP do piloto e o limite por conta aumentado só no teste; por release, à mão. No gratuito, não atingível (ADR-03, 11/10/2026) |
| NFR-05 | Concorrência | Degradação controlada sob sobrecarga | Respostas 500/502/504, tempo de emissão do 503, tempo de recuperação | A 1.500 req/min: 0 respostas 500/502/504; 503 com `Retry-After` em ≤ 100 ms quando a fila de admissão está cheia (quem já esperava uma vaga recebe o 503 em até 1 s, P-11); recuperação ≤ 60 s após a carga | Cenário k6 `nfr05` do `run_load.py` (S34-03), com a recuperação medida em 90 s a 20 por minuto; por release, à mão. A recusa rápida com `Retry-After` também é testada no pytest (S10). No gratuito, sem 500/502/504 e com recuperação em 5,7 s, mas o 503 leva segundos (ADR-03, 11/10/2026) |
| NFR-06 | Disponibilidade | Disponibilidade externa no período letivo, sem cold start | % mensal de checks OK; latência da 1ª verificação de usuário do dia | ≥ 99,5% (P-05); 1ª verificação do dia ≤ 300 ms | UptimeRobot a cada 5 min em `/ready`, que também mantém o plano gratuito do Render acordado (ADR-03), configurado pelo autor (`deploy/piloto.md`); teste sintético diário da 1ª verificação [PLANEJADO] |
| NFR-07 | Segurança | Isolamento do `analyzer` | % dos controles conferidos | Fases 0 e 2 (contêiner próprio): 100% de nenhum segredo no ambiente, nenhuma rota de egress, rootfs read-only, UID ≠ 0, `cap_drop: ALL`, `no-new-privileges`, `pids_limit` ≤ 64 e memória ≤ 512 MB. Fase 1 (processo no Render): 100% de UID próprio (10002), ambiente sem segredos, seccomp bloqueando sockets de rede e `execve`, `RLIMIT_FSIZE` = 0 | Fases 0 e 2: teste de configuração (`docker inspect`) e teste de egress na CI. Fase 1: teste automatizado na imagem do Render (abrir socket, executar programa, gravar em disco e ler o ambiente da `api` falham) |
| NFR-08 | Segurança | Limites por análise (P-04) | Limites aplicados; % do corpus malicioso tratado sem 5xx | Timeout de 2 s (kill), `RLIMIT_AS` de 256 MB, ≤ 60.000 nós, profundidade ≤ 200, ≤ 50 KB, ≤ 1.000 linhas; 100% do corpus | Suíte de segurança da DoD (seção 8) na CI |
| NFR-09 | Segurança | Código do aluno nunca executado nem importado | Usos proibidos no código-fonte do projeto | 0 usos de `eval`, `exec`, `compile` (fora de `engine/parse.py`), `__import__`, `importlib`, `runpy` ou `pickle` sobre a entrada | Regras de segurança do ruff (Bandit), guarda de código em pytest e Semgrep com regras próprias (`.semgrep/ip-checker.yml`, S31-04, P-20), bloqueantes em todo PR |
| NFR-10 | Segurança | Transporte, cabeçalhos e CORS | Versão de TLS, cabeçalhos presentes, origens aceitas, nota | TLS ≥ 1.2, HSTS e CSP sem `unsafe-inline` em scripts. Na Fase 1 (SPA na Vercel, API no Render), CORS aceita só a origem da SPA; nas Fases 0 e 2, mesma origem e nenhum cabeçalho CORS. SSL Labs ≥ A | Teste automatizado de cabeçalhos e CORS pós-deploy; SSL Labs por release |
| NFR-11 | Privacidade | O código não persiste em logs, banco ou disco | Ocorrências de um marcador canário | 0 ocorrências | Teste canário na CI (pytest, pelos logs, pelo banco e pela borda); a busca mensal em produção é [PLANEJADO] |
| NFR-12 | Privacidade | Minimização e retenção da telemetria | Colunas existentes; idade máxima dos registros | Só as colunas do esquema 5.2.4; nenhum registro com mais de 12 meses (P-06) | Teste de esquema na CI; verificação mensal do job de expurgo |
| NFR-13 | Segurança | Dependências e imagens | CVEs críticas ou altas corrigíveis | 0 | gitleaks, `pip-audit` e `npm audit` em todo PR (`ci.yml`, job "Auditoria") e, com o Trivy da imagem do piloto, no workflow semanal `audit.yml`; bloqueantes desde a S31-03 (09/10/2026), depois da primeira triagem (P-20) |
| NFR-14 | Observabilidade | Logs estruturados | % de requisições com os campos obrigatórios; campos proibidos | 100% com `request_id`, `route`, `status`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`; 0 campos com código ou IP | Teste de esquema de log na CI |
| NFR-15 | Observabilidade | Métricas e alertas | Tempo até o alerta | Alerta em ≤ 5 min se P95 > 200 ms ou 5xx > 1%; em ≤ 10 min se `/ready` falhar (2 checks de 5 min do UptimeRobot) | Exercício de disparo de alertas feito na S21-02 (compose); a cada release, [PLANEJADO] |
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
| NFR-30 | Desempenho | Plágio da turma inteira (S40-02, S46-03) [PLANEJADO] | Tempo no worker | Matriz de 100 soluções (120 KB no total) em ≤ 5 s | Teste de orçamento com a turma sintética |

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

- **C1 — SPA web (`frontend/`).** Editor próprio (`components/CodeEditor.tsx`: área de texto com numeração de linhas, Tab e marcação das linhas no gutter; CodeMirror 6 e a leitura de `.py` com `FileReader` (FR-02) ficaram no backlog), seletores de lista e questão alimentados por `GET /api/v1/lists`, que já traz as questões (FR-03), chamada a `/validate` com `AbortController` de 10 s, violações agrupadas com clique na linha (FR-13, S26-03) e renderização dos estados (FR-20). Gera um `X-Client-Id` (`crypto.randomUUID()` guardado em `sessionStorage`), usado só pelo rate limit. O código **não** é gravado em `localStorage`, para não ficar exposto em computadores compartilhados de laboratório. Na Fase 1, a SPA é servida pela Vercel e chama a API no Render com CORS restrito à sua origem. A partir da Sprint 13, a SPA ganha as telas Entrar, Registrar, verificação de e-mail, espera de aprovação, Perfil, Gerenciamento (FR-28) e Plágio (FR-29) e o botão Gerar feedback (FR-30), com roteamento no cliente; as chamadas usam o cookie de sessão da mesma origem (ADR-04), e o `X-Client-Id` deixa de ser necessário.
- **C2 — Borda (`caddy`).** TLS automático via ACME e HSTS (Fase 2), CSP sem `unsafe-inline` e os demais cabeçalhos de segurança, barreira anti-abuso de 128 KiB aplicada antes de ler o corpo (um `Content-Length` maior recebe 413 com `Connection: close`, e um corpo sem `Content-Length` recebe 411; o limite contratual de 50 KB fica na API), timeouts de leitura e escrita de 10 s, *reverse proxy* de `/api/*`, `/health` e `/ready` para `api:8000` e arquivos estáticos da SPA. O Caddy não tem log de acesso (a API registra cada requisição, sem IP), e o filtro dos demais logs remove IP, cabeçalhos e URL. Os erros da borda (411, 413 e API fora do ar) seguem o envelope do contrato. Na Fase 0, responde em HTTP só em `127.0.0.1:8180` (S9-02). A SPA e a API ficam na mesma origem, então não há cabeçalho CORS. Na Fase 1 não há Caddy: a borda é a do Render (TLS) e a da Vercel, e o limite de corpo é aplicado pela própria `api`.
- **C3 — `api` (FastAPI).** Cadeia de middlewares nesta ordem: `request_id`, guarda de tamanho (413), rate limit em memória (janela deslizante de 60 s, P-11: 10/min por `X-Client-Id`; por IP, 120/min para IPs externos e 1.000/min para as faixas do campus em `IPC_RATE_LIMIT_CAMPUS_CIDRS`; IPv6 pelo prefixo /64; IP e identificador só em RAM, como hash com sal do processo, e TTL de 2 min), validação Pydantic (FR-04), admissão (`asyncio.Semaphore` com capacidade = 2 × workers, fila de até 64 e espera máxima de 1 s, senão 503 `OVERLOADED`), cliente `httpx` para o analisador (timeout de 3 s), validação de esquema e tamanho (≤ 256 KB) da resposta do analisador, resposta ao cliente e enfileiramento da telemetria. Um contrato `import-linter` proíbe `import ast` no pacote `ipc_api`, de modo que a API nunca analisa código (NFR-09). O IP do cliente usado no rate limit é o da conexão ou, com `IPC_TRUSTED_PROXY_HOPS` = 1 (Caddy nas Fases 0 e 2, proxy do Render na Fase 1), o último endereço do `X-Forwarded-For`, escrito pelo proxy; o que o cliente manda nesse cabeçalho é ignorado. Com o acesso restrito (Sprint 13), uma dependência de sessão vem antes do limite de taxa, que passa a ser por conta. Desde a Sprint 25, um limite folgado por IP (600/min; 6.000/min no campus) vale para todo `/api/*` antes da sessão, o prazo do cliente do analisador vale para a chamada inteira e segue para o analisador em `X-IPC-Budget-Ms`, e uma exceção inesperada vira 500 `INTERNAL_ERROR` em JSON (S25-04).
- **C4 — `analyzer`.** FastAPI interno com 1 processo uvicorn e um `pebble.ProcessPool` (2 workers [PREMISSA P-04], contexto `forkserver`, `max_tasks=500`). O *initializer* de cada worker aplica `RLIMIT_AS` = 256 MB, `RLIMIT_FSIZE` = 0 e `RLIMIT_NOFILE` = 32. `RLIMIT_CPU` não é usado porque é cumulativo por processo; o limite de tempo é o timeout de parede de 2 s, com *kill* e substituição do worker. Endpoints internos: `POST /internal/analyze`, `GET /internal/ruleset/manifest`, `GET /internal/rulesets/effective`, `GET /internal/health`. Na Fase 1, o `analyzer` roda como processo separado dentro do serviço do Render: UID 10002, ambiente vazio, escuta só em `127.0.0.1` e workers com seccomp sem sockets de rede nem `execve` (biblioteca `pyseccomp`); são 2 workers de até 160 MB para caber nos 512 MB do plano (calibrado na S11-01: o pior caso de 50 KB é analisado dentro desse limite).
- **C5 — Motor de regras (`backend/src/ipc_analyzer/engine`).** Funções puras sem estado global mutável, detalhadas em 5.2.3.
- **C6 — Ruleset (`rulesets/`).** YAML validado pelo carregador do analisador e pelo `ipc-rules validate` na CI (S24-02). O analisador carrega o ruleset uma vez, como estrutura imutável (FR-15), e publica o `ruleset_sha256` no manifesto. Um JSON Schema e um `ipc-rules compile` são [PLANEJADO].
- **C7 — Telemetria (Sprint 21).** Fila `asyncio.Queue` limitada a 10.000 eventos, gravação em lote (100 eventos ou 2 s) via `asyncpg` com o papel `ipc_writer`. Se a fila transbordar, o evento é descartado e a métrica `telemetry_dropped_total` é incrementada; a resposta ao aluno nunca é bloqueada. **Implementado na Sprint 21** (`backend/src/ipc_api/telemetry.py`): o mesmo vale quando o banco falha; os contadores de gravados, descartados e lotes com falha aparecem em `GET /health/slo`, já que o `/metrics` ainda não existe.
- **C8 — Observabilidade.** Logs JSON em stdout (`structlog`), lidos no painel do Render; o P95 e a taxa de 5xx ficam na memória da API e saem em `/health/slo` (S21-02). Grafana Alloy, Grafana Cloud e métricas `/metrics` (`prometheus-client`) **não entram** (decisão do autor na S35-06, 11/10/2026: fica só o `/health/slo` com o UptimeRobot). Monitoramento externo pelo UptimeRobot (plano gratuito, intervalo de 5 min): um monitor em `/ready` do backend, que também impede o serviço gratuito do Render de dormir, e outro na SPA da Vercel, ambos com alerta por e-mail. **Sprint 21:** os alertas de latência e de erro do NFR-15 saem da própria API, sem outra conta externa: `GET /health/slo` responde 503 quando, nos últimos 5 minutos, o P95 do `POST /api/v1/validate` passa de 200 ms ou mais de 1% das respostas são 5xx (com pelo menos 20 requisições na janela), e um terceiro monitor do UptimeRobot manda o e-mail. Com o intervalo de 5 min do UptimeRobot, o alerta chega em até 10 min, e não em 5. O Grafana Cloud e o `/metrics` ficam opcionais.
- **C9 — CI/CD.** GitHub Actions com as actions fixadas por SHA; no piloto, o deploy sai da `main` depois da CI, pelos deploy hooks do Render e da Vercel (`deploy.yml`). Imagens no GHCR por digest, deploy por SSH com aprovação de *environment* e staging separado são [PLANEJADO, Fase 2].
- **C10 — Contas e sessão (`backend/src/ipc_api/auth/`, Sprints 13 a 16).** Rotas `/api/v1/auth/*` (registrar, confirmar e-mail, reenviar, entrar, sair, Google e perfil) e `/api/v1/admin/*` (fila, aprovar, recusar, cargo, remover e reativar); uma dependência FastAPI que carrega a sessão e a conta a cada requisição; e uma função pura de política, `can(ator, ação, alvo, cargo_novo)`, que implementa o FR-27, é usada por todas as rotas e é testada como matriz. Senhas com `argon2-cffi`, Google com Authlib e e-mails por um adaptador (`smtp`, `http` e, no desenvolvimento, o Mailpit do Compose), tudo configurado por variáveis `IPC_*`. Contas e sessões ficam no PostgreSQL (5.2.5), acessado com `asyncpg` pelo papel `ipc_app`; a API continua sem `import ast` (NFR-09).
- **C11 — Similaridade (`backend/src/ipc_analyzer/engine/similarity.py`, Sprint 17).** Função pura que recebe dois códigos e devolve a porcentagem e os componentes do *score* (ADR-05). Roda no worker isolado, pelo endpoint interno `POST /internal/similarity`, com os mesmos guards, limites e timeout da análise. A API expõe `POST /api/v1/similarity` e classifica o resultado pelas faixas do FR-29.
- **C12 — Feedback (`backend/src/ipc_api/feedback/`, Sprints 18 e 19).** Monta a apresentação, a abertura e a frase obrigatória; pede ao analisador o código sem comentários; troca o nome do aluno por `[ALUNO]`; chama o provedor configurado por um adaptador (`openai_compat` para OpenAI, Groq e DeepSeek, `gemini` e `fake` nos testes) com `httpx`; valida a saída e devolve o texto final (ADR-06). Tem limite por conta e teto diário de chamadas.

#### 5.2.2 Fluxo de uma submissão e contrato da API

1. A SPA envia `POST /api/v1/validate` com `{ "code": str, "list_number": 1..6, "question_id": "L3-Q2" | null }` e o cabeçalho `X-Client-Id`.
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
| `derived:recursion` | Grafo de chamadas entre `FunctionDef` do aluno, com detecção de ciclo por Tarjan (iterativo); as chamadas são pelo nome, como `call:user`, e um `lambda` não entra no grafo | Recursão direta ou mútua (C-03). Desde a Sprint 23 é um fato estrutural: só serve à exigência da R-68, porque o `def` e a chamada já são decididos pela R-59 |
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
| R-68 | `derived:recursion` (exigência da Lista 6) |

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
| Qualidade e segurança na CI | Na CI: ruff (com as regras do Bandit), `mypy --strict`, import-linter, pytest (com schemathesis para o contrato), Vitest com RTL e Playwright com axe-core; gitleaks, Semgrep, pip-audit e npm audit em todo PR e, com o Trivy, no workflow semanal (S31-03 e S31-04); à mão: k6. pytest-benchmark é [PLANEJADO] | Cada ferramenta verifica um NFR específico (NFR-02, 04, 05, 09, 13, 16, 18, 19) | Só linters e testes unitários (§18 do rascunho): não verificam isolamento, evasão nem carga |
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
| [ADR-03](adr/ADR-03-topologia-de-implantacao-por-fase.md) | Topologia de implantação por fase | Aceito em 01/10/2026 (Q-10); plano do Render revisto na S28-01 |
| [ADR-04](adr/ADR-04-autenticacao-sessao-e-autorizacao-da-equipe.md) | Autenticação, sessão e autorização da equipe | Implementado nas Sprints 13 a 16 |
| [ADR-05](adr/ADR-05-metodo-de-deteccao-de-plagio.md) | Método de detecção de plágio | Implementado na Sprint 17 |
| [ADR-06](adr/ADR-06-feedback-por-llm-com-moldura-deterministica.md) | Feedback por LLM com moldura determinística | Implementado na Sprint 18; revisão proposta nas Sprints 44 e 45 (7.16) |
| [ADR-07](adr/ADR-07-plagio-por-arvore-canonizada-insensivel-a.md) | Plágio por árvore canonizada, insensível à ordem | Implementado na Sprint 27; revisão proposta na Sprint 46 (7.16) |
| [ADR-08](adr/ADR-08-indicios-de-uso-de-ia-nunca.md) | Indícios de uso de IA, nunca veredito | Implementado na Sprint 29; desligado no piloto até a política (S29-04); ligação no piloto proposta na Sprint 42 (7.16) |
| [ADR-09](adr/ADR-09-integracao-com-outros-projetos-da-monitoria.md) | Integração com outros projetos da monitoria | Proposto em 07/10/2026 (Q-23); não confirmada |
| [ADR-10](adr/ADR-10-questoes-e-gabaritos-por-periodo.md) | Questões e gabaritos por período | Aceito em 08/10/2026 (Q-14); decisão 3 revista pela ADR-12 (proposta) |
| [ADR-11](adr/ADR-11-comparacao-com-o-gabarito.md) | Comparação com o gabarito na verificação, no plágio e nos indícios | Proposto em 09/10/2026 (Q-24); Sprint 32 |
| [ADR-12](adr/ADR-12-varios-periodos-e-retencao-por-encerramento.md) | Vários períodos carregados e retenção por encerramento | Proposto em 12/10/2026; Sprint 43 |
| [ADR-13](adr/ADR-13-grupos-de-acompanhamento-e-dados-de-alunos.md) | Grupos de acompanhamento e dados de alunos | Proposto em 12/10/2026; Q-26 a Q-29 decididas no mesmo dia; Sprint 47 |
| [ADR-14](adr/ADR-14-impressoes-digitais-persistentes.md) | Impressões digitais persistentes para plágio entre períodos e sinais com histórico | Rejeitado em 12/10/2026 (Q-27: só o resultado resumido é guardado) |

## 7. Roadmap de Sprints e Tasks do MVP

### 7.1 Roadmap

Cadência e capacidade conforme P-02 e Q-13: um único desenvolvedor, com 4 a 8 h por semana, em sprints de 2 semanas a partir de 05/10/2026. O plano usa 6 SP por sprint (1 SP ≈ 2 h de trabalho focado; premissa validada pelo autor em 12/10/2026) e metade disso nos recessos de fim de ano e de Carnaval. A meta é ter a equipe da disciplina usando a ferramenta em 2027.1 (Q-10, P-13), com início do período estimado em março de 2027 (P-10). As Sprints 1 a 12 foram concluídas em 01/10/2026, muito antes do calendário previsto. Em 02/10/2026, o roadmap foi refeito a partir da Sprint 13, com o acesso restrito, o plágio e o feedback antes das listas; as datas da Sprint 13 em diante foram re-estimadas a partir de 05/10/2026, com a mesma premissa de 6 SP por sprint, que serve de teto.

- **Fase 0 — MVP local (Sprints 1–9):** tudo roda com Docker Compose na máquina do desenvolvedor. O MVP (Marco 1) ficou pronto em 01/10/2026.
- **Fase 1a — Preparação do piloto (Sprints 10–12, concluídas):** rate limit, isolamento por processo no Render, pipeline de deploy na Vercel e no Render, exigência da Lista 1, teste de carga e material da apresentação.
- **Fase 1b — Acesso restrito e apoio à correção (Sprints 13–19):** login com aprovação, cargos e gerenciamento, Google, painel de plágio e feedback por LLM (P-13). Nada vai ao ar na internet antes do login completo (Sprint 16), e a apresentação a monitores-chefes e professores (Marco 2) passa para a Sprint 19.
- **Fase 1c — Listas e governança (Sprints 20–24), com o piloto em 2027.1:** cada lista é habilitada (`ENABLED_LISTS`) antes da data em que é liberada aos alunos; telemetria e regras por questão.
- **Fase 1d — Endurecimento, experiência e passagem de bastão (Sprints 25–29), criada em 06/10/2026 a partir da revisão de fim da Sprint 23:** primeiro deploy seguro, correção em lote, plágio por árvore, carga e eficácia, documentação para o próximo mantenedor e, se a Q-21 aprovar, os indícios de uso de IA. Como o ritmo real tem sido muito maior que 6 SP por sprint e não há calendário fixo (P-10), as datas da tabela são só a ordem prevista.
- **Fase 1e — Piloto verificado, decisões, dados e prontidão (Sprints 30–36), criada em 07/10/2026 a partir da lista de pendências depois da release da Sprint 29:** o pipeline do piloto sem passo pulado, com alerta, backup e rollback ensaiados (30); as decisões com a coordenação e o NTI e a auditoria bloqueante (31); a comparação com o gabarito na verificação, no plágio e nos indícios (32, ADR-11, incluída em 09/10/2026); os gabaritos, as questões de 2027.1 e a calibração dos indícios (33); a prontidão para 2027.1 (34); os controles ainda [PLANEJADO] (35); e a Fase 2, bloqueada pela P-09 e pela Q-12 (renumerada para 41 em 11/10/2026). As tasks estão em 7.12, as opções das decisões em 7.13 e a rastreabilidade em 7.14.
- **Fase 1f — Polimento (Sprints 36–40), criada em 11/10/2026:** até o fim do piloto, melhorar o que existe: os defeitos e os documentos da equipe (36), a tela de verificação (37), a explicação de cada regra e a exportação (38), a qualidade interna, a operação e a documentação (39) e a correção da turma inteira (40). As tasks estão em 7.15.
- **Fase 1g — Indícios, período, feedback, plágio, acompanhamento e Google (Sprints 42–48), proposta de 12/10/2026:** a partir da revisão das seis frentes ([`revisao-seis-frentes.md`](revisao-seis-frentes.md)): os indícios de IA ligados no piloto (42, a pedido do autor), o período na página e a retenção por encerramento (43), o feedback rastreável e o padrão do monitor (44), o "Aprimorar com IA" com validação e crítica (45), o plágio calibrado (46), os grupos de acompanhamento dos alunos (47) e a entrada com o Google no piloto (48, no fim da fila). As decisões sobre dados de alunos (Q-26 a Q-29) foram tomadas em 12/10/2026, e a 47 só vai ao piloto com o aviso de privacidade aprovado pela coordenação. As tasks estão em 7.16.
- **Fase 2 — Servidor do CIn (Sprint 41):** após 2027.1 e só se a P-09 for atingida. Adiada, junto com a Q-12, para depois do piloto.

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
| 24 (08/03–21/03) | Regras por questão, governança e "esqueci minha senha" | US-04, US-12, US-13, US-14, US-26 | Overrides em `rulesets/2027.1/questions/` cadastrados por monitores e aprovados por monitor-chefe ou professor, por processo (Q-22 adiada); `ipc-rules validate` bloqueante na CI; nova senha definida por link de e-mail (Q-19 b); predicados num registro só | Monitores precisam aprender o fluxo de PR (template e guia em `RULES.md`) |
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
| 41 (após 2027.1) | Fase 2 (bloqueada) | US-20, US-23 | GHCR por digest, deploy *pull-based* no CIn e staging | Só com a P-09 atingida e a Q-12 respondida |
| 42 (sob comando do autor) | Indícios de IA ligados no piloto | US-34 | Calibração na meta; evidência e confiança em cada indício; ligação primeiro para a chefia e depois para todos; guia e registro de casos | Leitura do painel como prova; base humana pequena (os gabaritos da equipe) |
| 43 (sob comando do autor) | Período na página e retenção por encerramento | US-37, US-39, US-40 | Período antes de Lista e Questão; o ativo e os 5 anteriores carregados; `retire-period` com simulação | `ruleset_version` por período nos painéis |
| 44 (sob comando do autor) | Feedback rastreável e o padrão do monitor | US-32, US-41, US-42 | Cada violação com linha e motivo no feedback sem IA; `estilo.yaml` revisado por PR | Texto mais longo para o Dikastis |
| 45 (sob comando do autor) | "Aprimorar com IA" com validação e crítica | US-32, US-43 | Nenhuma construção fora dos achados; nada de solução pronta nem de gabarito; uma rodada de crítica | Uma chamada a mais da cota gratuita |
| 46 (sob comando do autor) | Plágio calibrado | US-31, US-38, US-44 | Precisão e revocação medidas com plágio sintético; IDF de base por questão; matriz com trechos | Corpus pequeno até a P-21 |
| 47 (sob comando do autor) | Grupos de acompanhamento e histórico dos alunos | US-45, US-46, US-47 | Grupos com convite e aceite; histórico com o resultado resumido, sem código nem feedback; expurgo por período | Primeiro dado pessoal de alunos; aviso de privacidade aprovado pela coordenação antes da release |
| 48 (no fim da fila) | Entrada com o Google no piloto | US-25 | Cliente OAuth criado pelo autor; botão do Google no piloto; ensaio de domínio e de aprovação | Tela de consentimento publicada |
| Backlog (após o piloto) | Melhorias de experiência | US-10 | Tela de permissões da lista, editor com realce (CodeMirror) e análise do fluxo de controle no plágio (ADR-07, alternativa D, reavaliada com os números da Sprint 46); o upload de `.py` e a alternância de tema entraram nas Sprints 38 e 37 | Dependem da avaliação do piloto |

### 7.2 Tasks do MVP (Sprints 1 a 9)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S1-01 | US-15 | Criar o monorepo com `pyproject.toml` (ruff com regras de segurança, `mypy --strict`, pytest), a guarda de código do NFR-09 e o workflow `ci.yml` (lint, type, test). O import-linter entra com a `ipc_api` (Sprint 8) e a governança das regras por processo, na Sprint 24 (sem CODEOWNERS; Q-22) | Repositório `ip-checker/` (`backend/`, `frontend/`, `rulesets/`, `docs/`) e `.github/workflows/ci.yml` | 2 | — | Um PR com erro de lint ou de tipo é bloqueado pela CI |
| S1-02 | US-05 | Criar o modelo Pydantic do ruleset v2 e o loader imutável (`MappingProxyType` com índice `fato → regras`, *fail-fast*). Codificar R-03…R-36 em `base.yaml` (proibições gerais, Lista 1 e Lista 2 sem o `zip`, que depende de predicado), com mensagens em PT-BR e citação da fonte | `backend/src/ipc_analyzer/engine/ruleset.py`, `rulesets/2026.2/base.yaml`, `docs/mapping-R-xx.md` | 3 | S1-01 | Ruleset inválido impede o analisador de ficar pronto. A matriz registra as decisões Q-02 a Q-07 aplicáveis. Cobertura ≥ 90% |
| S2-01 | US-03, US-15 | Implementar os guards (UTF-8, até 51.200 bytes, até 1.000 linhas, sem NUL), o `parse` com a gramática do Python 3.13 e a tradução de `SyntaxError` para PT-BR, mais a medição iterativa de profundidade (≤ 200) e de nós (≤ 60.000, calibrado na S5-01) | `backend/src/ipc_analyzer/engine/guards.py`, `engine/parse.py` (único ponto com `ast.parse`) | 3 | S1-01 | Os testes dos limites passam. Uma cadeia `1+1+…` com 25 mil termos retorna `ANALYSIS_LIMIT` sem `RecursionError` |
| S2-02 | US-01, US-03 | Montar a SPA mínima contra o contrato de 5.2.2, com respostas simuladas: área de código com numeração de linhas, seletor de lista, painel com os estados do MVP e hook `useValidateCode.ts` com `AbortController` de 10 s | `frontend/src/components/*`, `frontend/src/hooks/useValidateCode.ts`, `frontend/src/types/api.ts` | 3 | S1-01 | Os testes Vitest/RTL dos estados válido, com violações, erro de sintaxe, entrada rejeitada e falha de rede passam |
| S3-01 | US-05 | Implementar a coleta de nomes ligados pelo aluno e o extrator iterativo de fatos (`node`, `op`, `cmp`, `builtin`, `method`, `kwarg`, `const`, `param`, `target:for_unpack`) | `backend/src/ipc_analyzer/engine/symbols.py`, `engine/facts.py` | 5 | S2-01 | `f = s.split` produz `method:split`. Uma variável do aluno chamada `len` não produz `builtin:len`. Cobertura ≥ 90% |
| S4-01 | US-05 | Implementar o avaliador de política v1: *default deny*, cumulatividade, proibições gerais e "fora da lista", com categorias, deduplicação e truncamento. Predicados e exigências entram nas Sprints 12 e 20 a 23; overrides de questão, na Sprint 24 | `backend/src/ipc_analyzer/engine/policy.py`, `engine/models.py` (`Violation`, `AnalysisResult`) | 3 | S1-02, S3-01 | Os testes de precedência passam. `type("C", (), {})` gera R-09 e `eval(...)` gera R-04 |
| S4-02 | US-05, US-15 | Montar o corpus golden das R-03…R-36 (≥ 3 casos por regra) e o corpus de evasão (`getattr`, `eval`, `__import__`, dunders, alias, sombreamento), escritos pelo monitor-desenvolvedor (P-08) | `backend/tests/golden/*.yaml` e `backend/tests/test_golden.py` | 3 | S4-01 | 0 FP e 0 FN, com job de CI bloqueante |
| S5-01 | US-15 | Implementar o pool Pebble (`forkserver`, 2 workers, `max_tasks` 500, *initializer* com `RLIMIT_AS`, `RLIMIT_FSIZE` e `RLIMIT_NOFILE`, timeout de 2 s) e o serviço interno | `backend/src/ipc_analyzer/runtime/pool.py`, `backend/src/ipc_analyzer/service/app.py`: `POST /internal/analyze`, `GET /internal/health` | 5 | S4-01 | Timeout mata e substitui o worker. `MemoryError` vira `ANALYSIS_LIMIT`. A memória base do worker é medida e registrada em P-04 |
| S6-01 | US-15 | Escrever o Dockerfile do analyzer (`python:3.13-slim` por digest, UID 10001, sem segredos) e o compose com `read_only`, `cap_drop: [ALL]`, `security_opt: no-new-privileges`, `pids_limit: 64`, `mem_limit: 512m` e rede `analyzer_net` com `internal: true`. Só `/tmp` (socket do `forkserver`) e `/dev/shm` (semáforos do pool) são graváveis, em memória, com 16 MB e `noexec` | `backend/Dockerfile`, `deploy/compose.yaml`, `backend/tests/test_container.py` (desde a S7, `backend/tests/security/test_isolation.py`), job `container` no `ci.yml` (desde a S7, `security`) | 2 | S5-01 | O teste de configuração (`docker inspect`) passa em 100% dos itens do NFR-07 |
| S7-01 | US-15 | Escrever a suíte de segurança contra o endpoint interno do analisador (itens 2 a 12 da seção 8) e os testes de isolamento do contêiner, como job de integração na CI | `backend/tests/security/test_malicious_submissions.py`, `backend/tests/security/test_isolation.py`, job `security` no `ci.yml` | 3 | S6-01 | 100% da suíte passa, nenhum 5xx genérico ocorre e `/internal/health` responde ao final |
| S8-01 | US-01, US-03 | Implementar o endpoint de validação com modelos Pydantic, `ENABLED_LISTS=1`, cliente `httpx` (timeout 3 s), mapeamento de erros (413, 422, 503), validação da resposta do analyzer, `GET /api/v1/lists`, `/health` e `/ready`, e o contrato import-linter que proíbe `ast` na API | `backend/src/ipc_api/routes/validate.py`, `routes/meta.py`, `schemas.py`, `clients/analyzer.py`; `POST /api/v1/validate`; `docs/openapi.json` e `backend/tests/test_api_contract.py` (schemathesis) | 5 | S6-01 | Os testes de contrato OpenAPI passam. A L2 retorna 422 `LIST_NOT_ENABLED`. Com o analyzer parado, retorna 503 `ANALYZER_UNAVAILABLE` |
| S9-01 | US-01 | Configurar logs JSON (`structlog`) com `request_id`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`, um filtro que rejeita campos de código e IP, e o teste canário | `backend/src/ipc_api/logging.py`, `backend/src/ipc_analyzer/logging.py`, `backend/tests/test_log_contract.py` | 2 | S8-01 | O esquema do log é validado e o marcador canário aparece 0 vezes nos logs da suíte |
| S9-02 | US-01, US-03 | Integrar a SPA à API real (tipos gerados do OpenAPI) e escrever o smoke e2e local com Playwright | `frontend/src/services/api.ts`, `frontend/e2e/smoke.spec.ts` | 2 | S2-02, S8-01 | Código válido na L1 mostra sucesso; `for` na L1 mostra R-34 na linha 2; erro de sintaxe mostra linha e coluna |
| S9-03 | US-15 | Estender a suíte de segurança à API pública (itens 1, 3, 4 e 13 da seção 8 via `POST /api/v1/validate`) | `backend/tests/security/test_api_limits.py` | 1 | S7-01, S8-01 | 100% passa, sem 5xx genérico, e `/ready` = 200 ao final |

Total do MVP: 42 SP em 9 sprints, distribuídos conforme a capacidade de cada sprint (5, 6, 5, 6, 5, 2, 3, 5 e 5 SP).

### 7.3 Tasks da Sprint 10 (proteção para exposição pública)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S10-01 | US-17 | Implementar o limite de taxa em memória (janela deslizante de 60 s: 10/min por `X-Client-Id`, 120/min por IP externo e 1.000/min para `IPC_RATE_LIMIT_CAMPUS_CIDRS`; IPv6 por /64; IP lido do `X-Forwarded-For` conforme `IPC_TRUSTED_PROXY_HOPS`) e o controle de admissão (4 análises simultâneas, até 64 em espera por no máximo 1 s) | `backend/src/ipc_api/ratelimit.py`, `admission.py`; 429 `RATE_LIMITED` e 503 `OVERLOADED` em `POST /api/v1/validate` | 3 | S8-01, S9-01 | A 11ª verificação em 1 min do mesmo cliente recebe 429 com `Retry-After`. 60 clientes atrás de um IP do campus, com 5 verificações cada, não recebem 429. Sob saturação, 503 com `Retry-After` sem esperar a análise em curso. Nenhum IP ou `X-Client-Id` nos logs |
| S10-02 | US-18 | Gerar o `X-Client-Id` por sessão e mostrar estados distintos para limite de taxa, sobrecarga, serviço indisponível e código acima de 50 KB, com contagem regressiva da espera | `frontend/src/services/clientId.ts`, `components/ResultPanel.tsx`, `e2e/smoke.spec.ts` | 2 | S9-02, S10-01 | No navegador, a 11ª verificação da mesma aba mostra o limite e o tempo de espera vindo do servidor; o botão de nova tentativa só é liberado ao final |
| S10-03 | US-15, US-17 | Estender a suíte de segurança ao limite de taxa pela borda: 11ª requisição da sessão, `X-Forwarded-For` forjado e rajada de um único IP | `backend/tests/security/test_api_rate_limit_edge.py` | 1 | S9-03, S10-01 | 100% passa. Forjar o `X-Forwarded-For` não cria identidades novas nem rende o limite do campus. Um IP externo não passa de 120 verificações por minuto |

### 7.4 Tasks da Sprint 11 (deploy do piloto)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S11-01 | US-15 | Imagem do piloto: API (UID 10001) e analisador (UID 10002, `env -i`, só em `127.0.0.1`) sob o `supervisord`; filtro seccomp nos workers (`socket`, `socketpair`, `execve`, `execveat`) com modos `off`, `optional` e `required` (fail-closed); 160 MiB por worker; Blueprint do Render sem deploy automático | `deploy/render/Dockerfile`, `deploy/render/supervisord.conf`, `backend/src/ipc_analyzer/runtime/sandbox.py`, `render.yaml`, `backend/tests/security/test_pilot_isolation.py` | 3 | S10-01 | Na imagem do piloto: UIDs separados, ambiente do analisador sem o segredo, ambiente da API ilegível para o UID 10002, worker com um filtro seccomp a mais, socket, `execve` e escrita em disco falhando, só a API fora do loopback e o pior caso de 50 KB dentro de 160 MiB |
| S11-02 | US-17 | CORS só para a origem da página (`IPC_CORS_ORIGINS`, inclusive nos erros), HSTS e `nosniff` na API, versão implantada em `/ready`; página com `VITE_API_BASE_URL` e build da Vercel (Build Output API v3) com CSP apontando só para a API, HSTS e `version.json` | `backend/src/ipc_api/edge.py`, `frontend/scripts/vercel-build.mjs`, `frontend/scripts/vercel-config.mjs`, `frontend/vercel.json` | 2 | S11-01 | Preflight da página aceito e de outra origem recusado; 429 e 413 legíveis pela página; sem nenhum cabeçalho CORS nas Fases 0 e 2; smoke e2e verde entre origens |
| S11-03 | US-17, US-19 | Deploy disparado depois da CI na `main` (deploy hooks), espera da versão nova na API e na página, verificação do piloto no ar (cabeçalhos, CORS, TLS ≥ 1.2, nada além da API exposto) e smoke e2e; UptimeRobot e contas configurados pelo autor do projeto (passo a passo em `deploy/README.md`) | `.github/workflows/deploy.yml`, `backend/tests/pilot/test_deployed_pilot.py` | 1 | S11-02 | Uma release na `main` vai ao ar sem passo manual, com as verificações e o smoke verdes e `/ready` = 200; sem a configuração, o pipeline só avisa |

### 7.5 Tasks da Sprint 12 (liberação do piloto, Marco 2)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S12-01 | US-06 (Lista 1), US-11 | Avaliar as exigências do ruleset (passo 6 do algoritmo) e ativar a R-02 da Lista 1 (`if` ou ternário, Q-05) como dado; mostrar a exigência como da solução inteira e avisar, antes da verificação, que as regras de questão ainda não valem | `backend/src/ipc_analyzer/engine/policy.py`, `rulesets/2026.2/base.yaml` (`requirements`), `backend/tests/golden/requirements.yaml`, `frontend/src/components/ResultPanel.tsx` | 2 | S11-02 | Código da Lista 1 sem `if` nem ternário recebe R-02 `EXIGENCIA`; `if` em string ou comentário não conta; 0 FP e 0 FN no corpus golden |
| S12-02 | US-22 | Teste de carga curto com o k6 contra a imagem do piloto, emulando os planos do Render, para decidir entre o plano gratuito e o Starter antes do primeiro prazo | `deploy/load/pilot-load.js`, `deploy/load/run_load.py` | 1 | S11-01 | Relatório com P95, P99 e falhas a 500/min nos dois planos e a recomendação registrada (ADR-03) |
| S12-03 | US-11 | Guia de uso para monitores e alunos no piloto (o que a ferramenta faz e não faz, leitura do relatório, limites) e roteiro da apresentação do Marco 2 | `docs/guia-do-piloto.md` (substituído por `docs/guia-da-equipe.md` na S19-02) | 1 | S12-01 | Guia revisado pelo autor do projeto antes da liberação |

### 7.6 Tasks das Sprints 13 a 19 (acesso restrito, plágio e feedback)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S13-01 | US-30 | Banco de contas: contêiner `postgres` no Compose (rede interna, sem porta no host, volume próprio), migrações SQL reversíveis com o esquema `app` (5.2.5), papel `ipc_app`, pool `asyncpg` na API (`IPC_DATABASE_URL`) e *seed* idempotente da conta do desenvolvedor (dois e-mails; senha de `IPC_DEV_INITIAL_PASSWORD` só na criação) | `database/migrations/`, `deploy/compose.yaml`, `backend/src/ipc_api/accounts/` | 2 | — | A migração aplica e reverte; o *seed* roda duas vezes sem duplicar; o `/ready` confere o banco; nenhum segredo aparece em log |
| S13-02 | US-26 | Sessão e login por senha: Argon2id, `POST /api/v1/auth/login` (nome ou e-mail), `logout`, `GET /api/v1/auth/me`, cookie de sessão (NFR-22), dependência que exige conta `ativo` em todas as rotas exceto `/health`, `/ready` e `/api/v1/auth/*`, limite de taxa por conta (recalibrar o 10/min, C-04), limite de tentativas por conta e por IP e mensagens do FR-25 | `backend/src/ipc_api/auth/`, `deps.py`, `ratelimit.py`, `docs/openapi.json` | 3 | S13-01 | Sem sessão, todas as rotas do OpenAPI respondem 401; credencial inválida tem mensagem única; o status só aparece com a senha correta; depois de 5 falhas em 15 min, a próxima tentativa espera |
| S13-03 | US-26 | Telas inicial (só Registrar e Entrar sem sessão) e Entrar, roteamento com guarda, cliente da API com o cookie da mesma origem e fim do `X-Client-Id` | `frontend/src/` (React Router), `frontend/e2e/auth.spec.ts` | 1 | S13-02 | E2E: sem login só aparecem Registrar e Entrar; o desenvolvedor entra e verifica um código |
| S14-01 | US-24 | Registro por e-mail e senha: campos obrigatórios, domínio exato (`cin.ufpe.br` e `ufpe.br`), política de senha compartilhada entre frontend e backend, nome e e-mail únicos sem diferenciar maiúsculas, e-mails do desenvolvedor reservados e status `aguardando_verificacao` | `backend/src/ipc_api/auth/accounts.py`, `frontend/src/pages/Register.tsx` | 2 | S13-02 | `x@xcin.ufpe.br`, `x@ee.ufpe.br` e senha fraca são recusados pelo backend; nome repetido com outra caixa é recusado |
| S14-02 | US-24 | E-mail de verificação: adaptador (`smtp` e `brevo`, por HTTPS; Mailpit no Compose, em `127.0.0.1` e com porta conferida contra os outros projetos da máquina), token de 256 bits guardado como hash, válido por 24 h e de uso único, reenvio limitado, link montado a partir de `IPC_PUBLIC_BASE_URL` para uma página que confirma por `POST`; depois da confirmação, `aguardando_aprovacao` | `backend/src/ipc_api/mail.py`, `frontend/src/pages/Verify.tsx`, `deploy/compose.yaml` | 2 | S14-01 | Link expirado ou usado não funciona; um `GET` no link não gasta o token; `Host` forjado não muda o link |
| S14-03 | US-29 | Perfil: editar nome, curso, tratamento e senha (com a senha atual), ou definir a senha numa conta do Google; nenhuma rota altera o próprio cargo; o tratamento só sai nas respostas ao próprio titular | `PATCH /api/v1/profile`, `POST /api/v1/profile/password`, `frontend/src/pages/Profile.tsx` | 2 | S13-02 | Nenhuma resposta sobre outra pessoa traz o tratamento (teste de contrato); trocar a senha encerra as outras sessões |
| S15-01 | US-27, US-28 | Política de cargos: função pura `can()` com a tabela do FR-27, proteção da conta do desenvolvedor, `ja_foi_monitor_chefe` permanente, remoção para Ex-monitor, Conselheiro ou inativo, reativação e encerramento das sessões do alvo | `backend/src/ipc_api/auth/policy.py`, `backend/tests/test_role_policy.py` | 2 | S13-01 | Matriz completa (4 cargos × ações × cargos-alvo) testada; remover quem já foi monitor-chefe resulta em Conselheiro, e quem nunca foi, em Ex-monitor |
| S15-02 | US-27, US-28 | API de gerenciamento: fila, aprovar com cargo, recusar, membros, alterar cargo, remover e reativar, cada item com as ações permitidas para quem consulta | `backend/src/ipc_api/routes/admin.py`, `backend/src/ipc_api/auth/management.py` | 2 | S15-01 | Monitor recebe 403 em todas as rotas de gerenciamento por chamada direta; monitor-chefe não age sobre professor; ninguém além do desenvolvedor altera a conta dele |
| S15-03 | US-27, US-28 | Tela de gerenciamento: fila (nome, e-mail, curso, método e data), membros com etiquetas coloridas e com o nome do cargo, ex-monitores e conselheiros, só os botões permitidos e confirmação antes de remover | `frontend/src/pages/Admin.tsx` | 2 | S15-02 | E2E de aprovação e remoção; axe sem violações graves |
| S16-01 | US-25 | Google com Authlib: `state`, `nonce`, PKCE e ID token validado; `hd` só como dica; `email_verified` e domínio exato conferidos no backend; vínculo por e-mail, com descarte da senha de conta não verificada; formulário complementar; Entrar com o Google sem conta leva ao registro | `backend/src/ipc_api/auth/google.py`, `backend/src/ipc_api/auth/google_accounts.py`, `backend/src/ipc_api/routes/google.py`, `frontend/src/pages/GoogleComplete.tsx` | 3 | S14-01 | Com um provedor OIDC falso nos testes: domínio fora, `hd` adulterado e `email_verified` falso são recusados; o mesmo e-mail com senha e com Google dá a mesma conta |
| S16-02 | US-25 | Mesma origem no piloto: *rewrite* de `/api/*` na Vercel, cookie na origem da página, CORS desligado, `IPC_TRUSTED_PROXY_HOPS` conferido e retorno do Google na origem da página; verificações do piloto passam a usar login | `frontend/scripts/vercel-config.mjs`, `render.yaml`, `.github/workflows/deploy.yml`, `backend/tests/pilot/` | 1 | S16-01 | O piloto no ar só responde com login; a P-15 é confirmada ou a alternativa fica registrada |
| S16-03 | US-15 | Suíte de segurança da autenticação: força bruta, CSRF (`Origin`), fixação e atributos do cookie, matriz de autorização por chamada direta, tokens vencidos e reusados, domínios parecidos, `hd` e `email_verified`, pré-sequestro de conta e nenhuma senha em log (canário) | `backend/tests/security/test_auth.py` | 2 | S15-02, S16-01 | Itens 16 a 20 da seção 8 verdes na CI |
| S17-01 | US-31 | Motor de similaridade (ADR-05): normalização por `tokenize`, nomes do aluno em marcadores (`symbols.py`), *winnowing* em tokens e em nós da AST, *score* ponderado com pesos documentados e limiares em constantes | `backend/src/ipc_analyzer/engine/similarity.py`, `backend/tests/similarity/` | 3 | — | Corpus de pares (NFR-25) verde; a cópia com variáveis renomeadas dá ≥ 99% |
| S17-02 | US-31 | `POST /internal/similarity` no analisador (worker isolado, mesmos guards e timeout) e `POST /api/v1/similarity` com sessão, classificação pelas faixas e contrato OpenAPI | `backend/src/ipc_analyzer/service/app.py`, `backend/src/ipc_api/routes/similarity.py` | 1 | S17-01, S13-02 | Valores exatos de 99, 95, 90 e 80% caem na faixa certa; entradas maliciosas não geram 5xx (seção 8, item 22) |
| S17-03 | US-31 | Painel de plágio: duas áreas lado a lado (empilhadas no celular), Verificar, porcentagem e classificação com cor e texto, aviso de indício e de código curto | `frontend/src/pages/Plagiarism.tsx` | 2 | S17-02 | E2E com cópia renomeada mostra "Plágio"; axe sem violações graves |
| S18-01 | US-32 | Camada de provedores (ADR-06): interface `generate`, adaptadores `openai_compat` (OpenAI, Groq e DeepSeek) e `gemini`, provedor `fake`, configuração por variáveis, IA principal e de reserva (`IPC_LLM_*` e `IPC_LLM_FALLBACK_*`), 12 s por tentativa e prazo total de 28 s; sem IA, o feedback é montado por modelos (ADR-06, item 6) | `backend/src/ipc_api/feedback/providers.py`, `backend/src/ipc_api/feedback/service.py` | 2 | S13-02 | Adaptadores testados contra respostas gravadas; a chave nunca aparece em log nem em resposta |
| S18-02 | US-32 | Montagem e validação: apresentação pela tabela do FR-30, abertura e frase obrigatória pelo backend, proibições pelos nomes do `display.py`, `[ALUNO]` em todo o prompt, comentários removidos pelo analisador, dados delimitados, saída validada, com a IA de reserva e, sem texto válido, o feedback montado por modelos, limite por conta e teto diário, e `POST /api/v1/feedback` | `backend/src/ipc_api/feedback/compose.py`, `backend/src/ipc_api/routes/feedback.py`, `backend/src/ipc_analyzer/engine/feedback.py`, `backend/src/ipc_analyzer/service/app.py` | 3 | S18-01 | NFR-26 atendido com o provedor falso (respostas boas e adversariais); a requisição ao provedor não traz o nome real |
| S19-01 | US-32 | Feedback na página: Nome do aluno (obrigatório), Anotação (opcional), Gerar feedback, campo editável e Copiar; o texto é exibido como texto puro | `frontend/src/components/FeedbackPanel.tsx`, `frontend/src/pages/Checker.tsx`, `frontend/e2e/feedback.spec.ts` | 2 | S18-02 | E2E com o provedor falso nos três tratamentos |
| S19-02 | US-11, US-24…US-32 | Liberação para a equipe: guia da equipe (substitui o guia do piloto), aviso de privacidade no registro (Q-19), passo a passo das contas externas (Supabase, cliente OAuth do Google, e-mail e provedor de LLM) em `deploy/README.md`, deploy e verificações do piloto com login e apresentação do Marco 2 revista | `docs/guia-da-equipe.md`, `frontend/src/pages/Privacy.tsx`, `frontend/src/components/PrivacyNotice.tsx`, `deploy/README.md` | 3 | S16-02, S19-01 | Piloto no ar com login; guia revisado pelo autor; apresentação marcada |

Total: 40 SP em 7 sprints (6, 6, 6, 6, 6, 5 e 5 SP). As Sprints 18 e 19 caem no recesso; ver a sensibilidade em 7.1. As tasks das Sprints 20 a 29 são detalhadas no início de cada uma, como nas Sprints 10 a 12 (7.7 em diante).

Situação: as Sprints 13 a 19 foram concluídas em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

### 7.7 Tasks da Sprint 20 (Lista 2 e gabaritos)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S20-01 | US-07, US-06 | R-37 com o predicado `zip_in_for_header` desenhado em 5.2.3 e no FR-09: o extrator marca o `zip()` built-in que é o iterável do comando `for` e o alvo desse `for` com o número de sequências; `builtin:zip` e `target:for_unpack` só são permitidos com 2 ou mais (Q-02 d, Q-04), nas Listas 2 a 4. Exigência R-02 da Lista 2 (`for` ou `while`, Q-05). Lista 2 habilitada (`IPC_ENABLED_LISTS=1,2`) e ruleset `2026.2.1` | `backend/src/ipc_analyzer/engine/facts.py`, `engine/conditions.py`, `rulesets/2026.2/base.yaml`, `backend/tests/golden/list2.yaml` | 3 | S12-01 | Os três cenários da US-07 (o da Lista 5 depende da R-64, Sprint 23); pelo menos 3 casos golden por regra; e2e da Lista 2 |
| S20-02 | US-07 | Gabaritos de períodos anteriores com zero violação na sua lista (Q-14): harness que lê `IPC_GABARITOS_DIR` (`<período>/lista-<n>/*.py` e `excecoes.yaml` para o que só o enunciado libera, até a Sprint 24) e job "Gabaritos" na CI, que baixa o repositório privado com token só de leitura quando `GABARITOS_REPO` e `GABARITOS_TOKEN` estão definidos | `backend/tests/official_answers/`, `.github/workflows/ci.yml`, `rulesets/README.md` | 2 | S20-01 | Harness testado com soluções sintéticas; saída sem código; gabaritos reais rodando na CI depois que o autor criar o repositório privado |

Situação: a Sprint 20 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

### 7.8 Tasks da Sprint 21 (telemetria e alertas)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S21-01 | US-16 | Telemetria anônima (FR-16, C7): migração `0002` com o esquema `telemetry` de 5.2.4, papéis `ipc_writer` e `ipc_reader`, as views do FR-17 (`v_top_rules_by_list`, `v_syntax_error_rate` e `v_weekly_volume`) e o expurgo de 12 meses (P-06); fila limitada na API com gravação em lote, fora do caminho da resposta; evento por verificação, inclusive as recusas de código e de limite de análise | `database/migrations/0002_telemetria.up.sql`, `backend/src/ipc_api/telemetry.py`, `backend/src/ipc_api/routes/validate.py` | 3 | S13-01 | O usuário da API insere e expurga, mas não lê; o `ipc_reader` lê só as views; nenhuma coluna identifica alguém (US-16, NFR-12); banco fora não afeta a verificação |
| S21-02 | US-19 | Alertas do NFR-15: `GET /health/slo` com o P95 do `/validate` e a taxa de 5xx dos últimos 5 minutos, 503 fora da meta; terceiro monitor do UptimeRobot; exercício de falha documentado e feito no compose | `backend/src/ipc_api/slo.py`, `backend/src/ipc_api/routes/meta.py`, `deploy/README.md` | 2 | S11-03 | Exercício local: com o limite apertado, `/health/slo` vira 503 e volta a 200 ao restaurar; o exercício no piloto depende das contas do autor |

Situação: a Sprint 21 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

### 7.9 Tasks da Sprint 22 (Listas 3 e 4)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S22-01 | US-08 | Regras R-38 a R-58 (Lista 3) e R-59 e R-60 (Lista 4) no ruleset pelo mapeamento de 5.2.3; exigência R-02 das Listas 3 (lista ou tupla) e 4 (`def`), pela Q-05; fato `derived:nested_function` para a função aninhada da Q-02 (f); ruleset `2026.2.2` | `rulesets/2026.2/base.yaml`, `backend/src/ipc_analyzer/engine/facts.py`, `backend/tests/golden/list3.yaml`, `backend/tests/golden/list4.yaml` | 3 | S20-01 | Pelo menos 3 casos golden por regra; `.append()` na L2 mostra "a partir da Lista 3"; os casos em aberto do mapeamento ficam como estão, registrados |
| S22-02 | US-08 | Listas 3 e 4 habilitadas (API, compose, Render e página simulada) e e2e das duas | `backend/src/ipc_api/settings.py`, `deploy/compose.yaml`, `render.yaml`, `frontend/e2e/smoke.spec.ts` | 1 | S22-01 | E2E: lista com `append` passa na L3, `append` na L2 é "Fora da lista", função passa na L4 e função aninhada é R-04 |

Situação: a Sprint 22 foi concluída em 02/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

### 7.10 Tasks da Sprint 23 (Listas 5 e 6, recursão e registro do gerenciamento)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S23-01 | US-06 | Regras R-61 a R-67 (Lista 5) pelo mapeamento de 5.2.3, com a R-64 liberando o `zip` (Q-04); predicados `enumerate_in_for_header` e `items_in_for_header` para vários nomes no alvo do `for`; fato `derived:recursion` pelo grafo de chamadas (Tarjan iterativo) e exigências R-02 da Lista 5 (dicionário) e R-68 da Lista 6 (recursão direta ou mútua, C-03); ruleset `2026.2.3` | `rulesets/2026.2/base.yaml`, `backend/src/ipc_analyzer/engine/facts.py`, `engine/conditions.py`, `engine/ruleset.py`, `backend/tests/golden/list5.yaml`, `list6.yaml` | 3 | S22-01 | Pelo menos 3 casos golden por regra; código sem recursão na L6 mostra R-68; recursão mútua passa; um ciclo de 400 funções é analisado sem recursão do Python |
| S23-02 | US-06 | Listas 5 e 6 habilitadas (API, compose, Render e página simulada) e e2e das duas | `backend/src/ipc_api/settings.py`, `deploy/compose.yaml`, `render.yaml`, `frontend/e2e/smoke.spec.ts` | 1 | S23-01 | E2E: dicionário com `.items()` no `for` passa na L5, dicionário na L4 é "a partir da Lista 5", recursão passa na L6 e código sem recursão mostra a R-68 |
| S23-03 | US-27 | Registro das ações de gerenciamento (REC-06): migração `0003` com `app.management_log` só de inserção para a API, gravado na mesma transação da ação, com nomes e cargos do momento; expurgo de 12 meses por função `SECURITY DEFINER`; `GET /api/v1/admin/log` e `can_view_log` na conta; seção "Registro de ações" na tela de gerenciamento | `database/migrations/0003_registro_gerenciamento.up.sql`, `backend/src/ipc_api/auth/management.py`, `accounts/store.py`, `accounts/postgres.py`, `routes/admin.py`, `frontend/src/pages/Admin.tsx` | 2 | S15-02 | Cada ação aplicada entra no registro, e as recusadas (403, 409) não; o monitor-chefe e o monitor recebem 403; o usuário da API não altera nem apaga um registro; e2e de aprovação, remoção e reativação confere o registro |

Situação: a Sprint 23 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

### 7.11 Tasks das Sprints 24 a 29 (plano de 06/10/2026)

Origem: o roadmap de 7.1 e a revisão de fim da Sprint 23 (técnica, visual, de CI e de documentação), que o autor pediu para incluir inteira em 06/10/2026. As estimativas seguem a P-02; os detalhes de cada task são refinados no início da sprint, como nas anteriores.

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S24-01 | US-04, US-13 | Overrides por questão (R-01): `rulesets/<período>/questions/L<n>-Q<m>.yaml` com `allow`, `allow_facts`, `deny` e `source`; precedência C-02; `question_id` na API e seletor de questão na página; `QUESTION_RULES_NOT_APPLIED` sem questão; as exceções dos gabaritos (`excecoes.yaml`) migram para os overrides | `engine/policy.py`, `engine/ruleset.py`, `routes/validate.py`, `frontend/src/pages/Checker.tsx` | 3 | S23-01 | Cenários da US-04; override que libera R-05…R-14 marcado como "exige professor" |
| S24-02 | US-12, US-14 | `ipc-rules validate` (CLI) bloqueante na CI e registro único dos predicados (`engine/predicates.py`), importado pelo loader e pelas condições; `facts.py` dividido em extrator, cabeçalho do `for` e grafo de chamadas | `backend/src/ipc_analyzer/cli.py`, `engine/predicates.py`, `engine/facts/` | 2 | S24-01 | Ruleset inválido sai com código ≠ 0 e o caminho do campo; nenhum predicado declarado em dois lugares |
| S24-03 | US-13 | Governança por processo (Q-22 adiada para depois da release): `RULES.md` com o passo a passo do cadastro de uma questão e template de PR para regras; a aprovação de monitor-chefe ou professor é conferida por quem faz o merge, sem fork nem check automático | `RULES.md`, `.github/PULL_REQUEST_TEMPLATE/regras.md` | 1 | S24-01 | Um monitor cadastra uma questão seguindo só o `RULES.md` |
| S24-04 | US-26 | "Esqueci minha senha" (Q-19 b): token de uso único por e-mail, como o da verificação, resposta sempre 202 e limite por conta | `auth/accounts.py`, `frontend/src/pages/ResetPassword.tsx` | 1 | S14-02 | Link vencido ou usado não funciona; definir a senha encerra as outras sessões |
| S25-01 | US-15 | Cadeia de suprimentos da CI: actions fixadas por SHA, `persist-credentials: false`, versão do `uv` fixada, `UV_IMAGE` com digest, `openapi-typescript` no `package.json`; Dependabot mensal para a `develop` (actions, Docker, npm, uv); segredos fora dos passos de instalação no deploy; job `audit` (gitleaks, pip-audit, npm audit, trivy) semanal e ainda não bloqueante | `.github/`, `deploy.yml`, `frontend/package.json` | 2 | — | Nenhum `uses:` por tag; nenhum passo de instalação com segredo no ambiente |
| S25-02 | US-17, US-19 | Deploy seguro e primeiro deploy: `workflow_dispatch` só para a `main` com CI verde; Render primeiro, Vercel depois do `/ready` com a versão certa; conferência de que a ponta da `main` é o commit testado; prazo no lugar do laço; `engines` do Node 24; roteiro do primeiro deploy (migração manual antes do Render, lista de conferência com a P-15); Data API do Supabase desligada ou tabela de migrações fora do `public`; health do Render em `/health`; `docs/runbook.md` com o rollback | `deploy.yml`, `deploy/README.md`, `render.yaml`, `docs/runbook.md` | 2 | S25-01 | Uma segunda release durante o deploy não publica um commit sem CI; o roteiro leva do zero ao piloto sem passo implícito |
| S25-03 | US-30 | Limpeza diária do banco: função `app.housekeeping()` (`SECURITY DEFINER`) que apaga sessões vencidas, tokens usados ou vencidos, contas não verificadas com mais de 48 h (o nome volta a ficar livre) e o registro de gerenciamento com mais de 12 meses; expurgo das contas fora do status `ativo` com 365 dias sem atividade (Q-19 d), com `last_activity_at`; roda ao subir e uma vez por dia, com as contagens em `/health/slo` | `database/migrations/0004_*.sql`, `accounts/postgres.py`, `slo.py` | 2 | S23-03 | A conta do desenvolvedor nunca é apagada; o registro de gerenciamento mantém os nomes depois do expurgo |
| S25-04 | US-15, US-22 | Robustez no plano gratuito: no Render, 1 worker e admissão igual ao número de workers; prazo da API derivado do prazo do pool, com o analisador descartando pedidos vencidos; pool do banco com `timeout` e prazo no `acquire`; sessão em uma consulta; limite por IP folgado em todo `/api/*` antes da sessão; a API não sobe com `IPC_PUBLIC_BASE_URL` sem `https://` quando o cookie é seguro; seccomp e rlimits ampliados (`io_uring_*`, `ptrace`, `process_vm_*`, `bpf`, `userfaultfd`, `unshare`, `RLIMIT_NPROC`, `RLIMIT_CORE`); um handler central de erros com 500 em JSON e `request_id` | `runtime/`, `admission.py`, `accounts/postgres.py`, `auth/middleware.py`, `app.py` | 3 | S25-02 | Nenhuma análise continua depois que a API desistiu; tokens aleatórios não chegam ao banco acima do limite |
| S25-05 | US-32 | Privacidade do feedback: docstrings removidas e matrículas (8 ou mais dígitos), e-mails e CPFs mascarados no código enviado à IA; cota diária persistida e cobrada só depois da análise | `engine/feedback.py`, `feedback/service.py` | 1 | — | Teste com cada dado mascarado; a cota não zera num deploy |
| S26-01 | US-33 | Cabeçalho e navegação no celular: nome curto, menu compacto, subtítulo só em telas maiores, alvos de 44 px; `<title>` por tela, `<nav>` com `aria-current`, `<h2>` na verificação; contraste AA no modo escuro; escala única de títulos e espaçamentos; componentes `Button`, `TextLink`, `ErrorText` e rótulos num `labels.ts` | `frontend/src/components/AppHeader.tsx`, `ui.ts`, `labels.ts` | 2 | — | Nenhuma tela passa de 375 px; axe sem violações graves nos dois temas |
| S26-02 | US-33 | Fluxo em lote: "Próximo aluno", Ctrl+Enter, foco e rolagem até o resultado, foco em Copiar depois de gerar, última lista lembrada, aviso quando o código mudou e o nome não; rascunho em memória que sobrevive à navegação e ao novo login; editor com tabulação de 4, Tab que insere espaços, altura ajustável, Limpar e Colar | `pages/Checker.tsx`, `components/CodeEditor.tsx`, `components/FeedbackPanel.tsx` | 2 | S26-01 | E2E: três alunos seguidos em até 4 ações cada, sem o nome do anterior no feedback |
| S26-03 | US-33, US-09 | Relatório: resumo por categoria, ordem por gravidade, uma linha por regra com as linhas afetadas, cores distintas para anulação e fora da lista, aviso das regras de questão uma vez só; clique na violação seleciona o trecho no editor e marca a linha; trecho do código no cartão; faixa "o código mudou desde a verificação" | `components/ResultPanel.tsx`, `components/CodeEditor.tsx` | 2 | S26-02 | E2E: clicar numa violação seleciona a linha certa |
| S26-04 | US-33, US-21 | Erros iguais em todas as telas: `useApiCall` com prazo, cancelamento e sessão vencida central; foco que não se perde ao enviar; anúncio só do resumo ao leitor de tela; listas com "Tentar novamente"; gerenciamento com busca, filtro por cargo, "Mostrar mais" no registro e ocupado por linha; o simulado exige sessão e cobre `truncated`, `ANALYSIS_LIMIT` e o texto da IA | `frontend/src/hooks/useApiCall.ts`, `pages/*`, `services/mockClient.ts` | 2 | S26-01 | Plágio e feedback têm prazo e cancelamento; sessão vencida leva a Entrar em todas as telas |
| S27-01 | US-31 | Representação canônica (ADR-07): canonização da AST, reordenação por dependência, padrões de laço e multiconjunto de subárvores com Dice e contenção, no analisador; corpus de pares ampliado com cada reescrita da ADR-07 e com soluções independentes | `engine/similarity_tree.py`, `tests/similarity/` | 3 | — | Reescritas da ADR-07 ≥ 95%; soluções independentes < 80% no corpus; 50 KB em menos de 1 s |
| S27-02 | US-31 | Uma contra várias: comparar uma solução com até 100 da turma, em memória, com o peso das subárvores pelo inverso da frequência na turma; aviso de código curto mantido | `POST /api/v1/similarity/batch`, `pages/Plagiarism.tsx` | 2 | S27-01 | Uma linha óbvia que toda a turma escreve não eleva a similaridade |
| S27-03 | US-31 | Trechos realçados: a API devolve os pares de intervalos de linhas que coincidem; o painel realça os dois códigos com rolagem sincronizada; "Trocar A e B" e "Limpar" | `routes/similarity.py`, `pages/Plagiarism.tsx` | 1 | S27-01 | E2E: a cópia reordenada mostra os trechos correspondentes nos dois lados |
| S28-01 | US-22 | Teste de carga com o k6 no Render, já com login, medindo a região do banco (Q-20), e a decisão entre o gratuito e o Starter | `deploy/load/` | 1 | S25-04 | Relatório com P95, P99 e falhas; recomendação registrada na ADR-03 |
| S28-02 | US-23 | Relatório de eficácia (P-09, Q-15): adoção por lista do critério 2 (um registro por conta, período e lista, apagado com a conta), consultas dos critérios 1 e 5 e o formulário da pesquisa do critério 4; a telemetria deixa de contar as verificações da conta de verificação do deploy | `database/migrations/`, `telemetry.py` | 2 | S25-03 | A view só devolve porcentagens por lista |
| S28-03 | US-20 | Passagem de bastão: `docs/onboarding.md` (do zero ao compose verde em 30 min), `CONTRIBUTING.md`, `SECURITY.md`, `docs/README.md` como mapa; runbook completo com o rollback cronometrado (DoD: 5 min ou menos); backup semanal criptografado dos esquemas `app` e `telemetry`; `deploy/README.md` dividido | `docs/`, `.github/workflows/backup.yml` | 2 | S25-02 | Um mantenedor novo sobe o ambiente seguindo só o onboarding |
| S28-04 | US-20 | Documentação e processo: blueprint dividido (ADRs em `docs/adr/`, situação das sprints num `CHANGELOG.md`, decisões em `docs/decisoes.md`); afirmações sobre controles que não existem corrigidas ou marcadas "[PLANEJADO]"; `scripts/release.sh` com tag e GitHub Release; template de PR ampliado; checksum das migrações aplicadas; e2e com uma conta por projeto (sai a pausa de 61 s); CI pesada pulada na `main` e na documentação | `docs/`, `scripts/`, `.github/` | 2 | S28-03 | A `main` recebe uma tag por sprint; nenhum controle descrito como ativo sem existir |
| S29-01 | US-34 | Sinal de múltiplas violações (Q-21): a partir das violações do motor, variedade de proibições gerais, repetição da mesma proibição, salto de lista (quantidade e distância) e construções fora do documento ou incomuns para o nível; faixas iniciais da ADR-08, item 1; só para a equipe, nunca no feedback ao aluno | `engine/indicators.py`, `routes/validate.py` | 2 | S24-01 | `break`, `pass` e `continue` juntos, vários `pass` e construções da Lista 6 na Lista 3 dão indício com as linhas; uma solução limpa não mostra nada |
| S29-02 | US-34 | Soluções de referência por IA: geradas pela equipe a partir só do enunciado, num repositório privado como os gabaritos; comparação pelo motor da ADR-07 | `backend/tests/official_answers/`, `routes/similarity.py` | 2 | S27-01 | Nenhum dado do aluno sai do servidor |
| S29-03 | US-34 | Painel de indícios: as múltiplas violações, a semelhança com as referências e os marcadores de estilo, cada um com motivo e trecho; texto de indício, nunca de prova; 2 ou 3 perguntas sugeridas para a conversa com o aluno | `pages/Checker.tsx`, `components/IndicatorsPanel.tsx` | 2 | S29-01, S29-02 | Falsos positivos "altos" em até 5% das soluções anteriores a 2023 |
| S29-04 | US-34 | Política e calibração: texto combinado com a coordenação (inclusive o que é dito aos alunos), definição de quem gera as referências e calibração das faixas nas soluções anteriores a 2023 e nos casos confirmados ou descartados | `docs/guia-da-equipe.md`, `docs/indicios-de-ia.md` | 1 | S29-03 | Política aprovada pela coordenação antes de o painel ser ligado no piloto |

Situação: a Sprint 24 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

Situação: a Sprint 25 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

Situação: a Sprint 26 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

Situação: a Sprint 27 foi concluída em 06/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md).

Situação: a Sprint 28 foi concluída em 07/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md); ficam para depois da conta de verificação do deploy a carga no piloto de verdade (S28-01) e o primeiro ensaio cronometrado do rollback (S28-03).

Situação: a Sprint 29 foi concluída em 07/10/2026. O que foi entregue e as decisões de implementação estão no [CHANGELOG](../CHANGELOG.md); os indícios ficam desligados no piloto até a coordenação aprovar a política e a calibração com soluções anteriores a 2023 ficar na meta (S29-04, `docs/indicios-de-ia.md`).

### 7.12 Tasks das Sprints 30 a 35 (plano de 07/10/2026)

A Sprint 36 deste plano (Fase 2) passou a ser a Sprint 41, em 7.15 (11/10/2026).

Origem: a lista de pendências de 07/10/2026, depois da release da Sprint 29 (tag `sprint-29`, commit `03e3256`, no ar no piloto), que reúne as pendências do piloto adiadas pelo autor, as decisões em aberto, as premissas a confirmar, os critérios de sprints que ficaram abertos e os controles marcados como [PLANEJADO]. A ordem segue a prioridade definida pelo autor: (1) o piloto verificado ponta a ponta; (2) as decisões com a coordenação e o NTI; (3) os dados (gabaritos, questões de 2027.1 e calibração); (4) a prontidão para 2027.1; depois, os controles [PLANEJADO] e a Fase 2. O backlog posterior ao piloto (seção 7.1, "Backlog") não vira task.

Cada task tem um **tipo**: **Engenharia** (executável pelo desenvolvedor no repositório), **Externa** (depende de outra pessoa ou de uma conta externa; a task acompanha a entrada esperada e o critério de desbloqueio, e nunca é dada como concluída sem a ação) ou **Decisão** (escolha do autor, da coordenação, do NTI ou do suporte de TI; as opções estão em 7.13). Responsáveis: **Autor** (o desenvolvedor), **Coordenação**, **NTI**, **Equipe** (monitores e monitores-chefe), **Professor**, **TI do CIn**. As estimativas seguem a P-02 (1 SP ≈ 2 h); tasks externas e de decisão não têm SP de engenharia. Nada aqui foi executado: o estado de cada pendência está na matriz de 7.14.

#### 7.12.1 Base de testes de toda sprint

Vale para as Sprints 30 a 36 e não se repete nelas; cada sprint lista só os testes que acrescenta. Sem *branch protection* (GitHub Free, P-02), "bloqueante" quer dizer: o PR só é mergeado na `develop` com o CI verde, conferido por quem faz o merge (`CONTRIBUTING.md`), e a `main` só avança com o CI verde da `develop` (`scripts/release.sh`).

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Lint e tipos do backend | ruff, `mypy --strict`, import-linter | `ci.yml`, job "Backend" (`uv run ruff check .`, `uv run mypy`, `uv run lint-imports`) | PR e push na `develop` (pulado na `main` e em mudança só de `.md`, S28-04) | 0 erros; 4 contratos do import-linter mantidos |
| Unitários e integração do backend | pytest, com PostgreSQL de serviço | `ci.yml`, job "Backend" (`uv run pytest`) | idem | Todos passam; cobertura ≥ 90% (`--cov-fail-under=90`, `backend/pyproject.toml`) |
| Regras e regressão do motor | `ipc-rules validate` e casos golden | `uv run ipc-rules validate ../rulesets --golden tests/golden` (o período de `rulesets/ATIVO`, S31-09) | idem | 0 FP e 0 FN; hoje 296 de 296 casos |
| Contrato da API | pytest com schemathesis | `tests/test_api_contract.py` e `docs/openapi.json` em dia | idem | Contrato em dia e todos os status documentados conferidos |
| Unitários do frontend | Vitest com RTL | `ci.yml`, job "Frontend" (`npm test`) | idem | Todos passam (hoje 229) |
| Lint, tipos e builds do frontend | ESLint, `tsc`, Vite | `npm run lint`, `npm run typecheck`, `npm run build`, `npm run build:vercel` | idem | 0 erros; tipos gerados do OpenAPI em dia |
| Segurança e isolamento | pytest pela borda do compose e imagem do piloto | `ci.yml`, job "Segurança" (`IPC_SECURITY_TESTS=1 uv run pytest tests/security`) | idem | Itens 1 a 22 da seção 8 verdes |
| e2e no compose | Playwright com axe-core | `ci.yml`, job "Smoke e2e" (`npm run e2e`) | idem | Todos passam (hoje 51), sem violação grave no axe |
| Verificação pós-deploy | pytest contra o piloto | `deploy.yml`, passo "Conferir o piloto" (`tests/pilot`) | `workflow_run` do CI na `main` e `workflow_dispatch` | `/ready` e `/version.json` com o commit, cabeçalhos da Vercel, repasse `/api/*`, TLS ≥ 1.2, CORS desligado e `ai_indicators` como esperado |
| e2e no piloto | Playwright (`E2E_TARGET=pilot`) | `deploy.yml`, passo "Smoke e2e no piloto" | idem, só com a conta de verificação (`HAS_CHECK_ACCOUNT`) | `smoke` e `auth` verdes pela página da Vercel |
| Auditoria | gitleaks, pip-audit, npm audit, Trivy | `audit.yml` | segunda-feira 09:00 UTC e manual | Bloqueante desde a S31-03 (09/10/2026); gitleaks, pip-audit e npm audit também em todo PR, com o Semgrep (`ci.yml`, job "Auditoria") |

#### Sprint 30 — Piloto verificado ponta a ponta

**Situação (08/10/2026):** concluída. O rollback foi ensaiado (S30-08), o RPO foi decidido (S30-12:
backup diário), e a API passou a atender `/api/*` só pela página, com o segredo do middleware da
Vercel (S30-03). Falta só conferir, em 09/10/2026, os 24 h verdes do UptimeRobot (critério 4). O que cada task entregou está no [CHANGELOG](../CHANGELOG.md).

**Objetivo:** o "Deploy do piloto" fecha verde sem nenhum passo pulado (login e e2e no piloto), com alerta, backup e rollback ensaiados e medidos, e com a P-12 (a) e a P-15 confirmadas ou corrigidas por evidência registrada.

**Premissas:** confirma a P-12 (a) e a P-15 (a) e (b); mede a Q-20; usa a P-16 (UptimeRobot gratuito) e investiga a P-17 (capacidades do contêiner no Render), registradas em `docs/decisoes.md`. A P-12 (b), (c) e (d) e o repasse `/api/*` da P-15 (a) já foram confirmados no primeiro deploy (07/10/2026).

**Histórias:** US-17, US-19, US-20, US-22, US-26, US-32 e US-35 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S30-01 | US-17 | Externa | Criar a conta de verificação no piloto (registro com outro e-mail institucional, confirmação, aprovação como monitor) e gravar os secrets `PILOT_CHECK_LOGIN`, `PILOT_CHECK_PASSWORD` e `PILOT_CHECK_NAME` com `gh secret set` | `deploy/piloto.md` (passo 8), `docs/runbook.md` ("Conta de verificação") | Autor | — | — | Entrada: conta ativa como monitor. Desbloqueio: `gh secret list` mostra os três nomes, e o passo de migração do "Deploy do piloto" mostra "conta de verificação: marcada" |
| S30-02 | US-26, US-32 | Engenharia | Primeiro deploy com login: "Deploy do piloto" por `workflow_dispatch` na `main`, com o login pela página e o smoke e2e no piloto; acrescentar a `tests/pilot` uma verificação do feedback pela origem da página (`POST /api/v1/feedback`, modelos de texto) com prazo de 30 s, que fecha a P-15 (a) | `backend/tests/pilot/test_deployed_pilot.py`, `.github/workflows/deploy.yml` | Autor | 1 | S30-01 | Os passos "Conferir o piloto" e "Smoke e2e no piloto" verdes, sem o aviso de conta ausente; o teste do feedback responde 200 em ≤ 30 s pela Vercel |
| S30-03 | US-17 | Engenharia | Confirmar a P-12 (a) e a P-15 (b): uma verificação em `tests/pilot` que manda, de um mesmo cliente, logins sem sessão com valores forjados diferentes no início do `X-Forwarded-For` e confere que o limite por IP (30 por minuto sem sessão) conta todos como um só cliente; se falhar, corrigir `IPC_TRUSTED_PROXY_HOPS` no `render.yaml`. Registrar o resultado na P-12 e na P-15 | `backend/tests/pilot/test_deployed_pilot.py`, `backend/src/ipc_api/ratelimit.py` (`client_ip`), `render.yaml` | Autor | 1 | S30-01 | A 31ª tentativa em 60 s recebe 429 com `X-Forwarded-For` forjado; P-12 (a) e P-15 (b) marcadas como confirmadas, com a data e o run do workflow |
| S30-04 | US-19 | Externa | Criar no UptimeRobot os três monitores HTTP(S), de 5 em 5 minutos, com alerta por e-mail: `<Render>/ready`, `<Render>/health/slo` e `<Vercel>/` | Painel do UptimeRobot; `deploy/piloto.md` (passo 9) | Autor | — | — | Entrada: os três monitores ativos. Desbloqueio: os três verdes por 24 h e o Render sem dormência (`/ready` abaixo de 1 s na primeira chamada do dia) |
| S30-05 | US-19 | Engenharia | Exercício de alerta no piloto (pendente desde a S21): baixar `IPC_SLO_P95_MS` no Render por 10 min, gerar tráfego com o workflow "Carga no piloto" (20 por minuto) até o `/health/slo` responder 503, medir o tempo até o e-mail do UptimeRobot e voltar o valor | Painel do Render, `.github/workflows/load.yml`, `docs/runbook.md` ("Latência ou erros acima da meta") | Autor | 0,5 | S30-01, S30-04 | Alerta recebido em ≤ 5 min (NFR-15), valor restaurado, registro com data e tempos no runbook |
| S30-06 | US-20, US-35 | Externa | Gerar a chave com `age-keygen`, guardar a privada fora do GitHub e gravar a pública na variável `BACKUP_AGE_RECIPIENT` | `docs/runbook.md` ("Backup") | Autor | — | — | Desbloqueio: `gh variable list` mostra `BACKUP_AGE_RECIPIENT` |
| S30-07 | US-35 | Engenharia | Rodar o "Backup do banco do piloto" à mão e fazer o primeiro ensaio de restauração num PostgreSQL descartável, cronometrado | `.github/workflows/backup.yml`, `docs/runbook.md` ("Restaurar um backup") | Autor | 1 | S30-06 | Artefato `ipc-piloto-AAAA-MM-DD` com o `.sha256` conferido; contagens de `app.account` e `telemetry.validation_event` iguais às do piloto no momento do backup; RTO medido e registrado na tabela do runbook (NFR-20: RTO ≤ 30 min) |
| S30-08 | US-35 | Engenharia | Primeiro ensaio cronometrado do rollback (pendente da S28-03): voltar a API (Render, **Rollback**) e a página (Vercel, **Instant Rollback**) para a release anterior e depois para a atual | `docs/runbook.md` ("Voltar para a versão anterior") | Autor | 0,5 | S30-02 | Do passo 1 ao passo 3 conferido em ≤ 5 min, com `/ready` e `/version.json` no commit anterior; registro na tabela do runbook |
| S30-09 | US-22 | Engenharia | Carga no piloto de verdade (pendente da S28-01): workflow "Carga no piloto" com 20 por minuto por 5 min; registrar o P95 do servidor (`/health/slo`), o P95 do k6 e a diferença entre `sessao_ms` e `sem_banco_ms` (Q-20) | `.github/workflows/load.yml`, `deploy/load/pilot-load.js`, `docs/adr/ADR-03-topologia-de-implantacao-por-fase.md`, `docs/decisoes.md` (Q-20) | Autor | 1 | S30-01 | Resumo do workflow com os três números; ADR-03 e Q-20 atualizadas com a medição e a data |
| S30-10 | US-17 | Engenharia | Corrigir o `PermissionError` do supervisord no desligamento (ver o diagnóstico abaixo): registrar as capacidades no boot, reproduzir com `docker run --cap-drop KILL`, aplicar a correção escolhida e cobri-la com um teste na suíte do piloto | `deploy/render/supervisord.conf`, `deploy/render/Dockerfile`, `backend/tests/security/test_pilot_isolation.py` | Autor | 2 | — | Na imagem com `--cap-drop KILL`, `docker stop` encerra os dois serviços em ≤ 15 s (`stopwaitsecs`) sem a linha `CRIT unknown problem killing`; no Render, um deploy e uma dormência sem essa linha nos logs; isolamento da suíte do piloto inalterado |
| S30-11 | US-22 | Decisão | Plano do Render (ADR-03): gratuito ou Starter (cerca de US$ 7 por mês), com a medição da S30-09 (opções em 7.13.6) | `render.yaml` (`plan`), painel do Render | Autor | — | S30-09 | Decisão registrada no ADR-03; se Starter, `plan: starter` por PR e nova rodada da S30-09 com P95 do servidor ≤ 200 ms |
| S30-12 | US-35 | Decisão | RPO do banco do piloto: o backup semanal dá RPO de até 7 dias, acima da meta de 24 h da NFR-20; escolher entre o backup diário (só o `cron` do `backup.yml` muda) e revisar a NFR-20 para o piloto (opções em 7.13.8) | `.github/workflows/backup.yml`, NFR-20 | Autor | — | S30-07 | Desbloqueio: decisão registrada na NFR-20; se diário, o `cron` alterado por PR e uma semana de artefatos diários |

*Diagnóstico da S30-10 (confirmado em 08/10/2026, P-17).* O `supervisord` roda como root (`user=root`) e encerra cada programa com `stopasgroup=true` e `killasgroup=true`, ou seja, manda o sinal ao grupo de processos de `ipc-api` (UID 10001) e de `ipc-analyzer` (UID 10002). Um processo root só sinaliza processos de outro usuário com a capacidade `CAP_KILL`; a hipótese (P-17) é que o Render roda o contêiner sem ela, e o `kill()` devolve `EPERM`, que o supervisord registra como `PermissionError`. Os processos acabam encerrados quando o Render destrói o contêiner, por isso nada quebra. Opções a avaliar na task: (a) um intermediário root por programa, que inicia o serviço com `setpriv --reuid ... --pdeathsig TERM` e apenas sai ao receber o sinal, para o kernel entregar o `SIGTERM` ao filho, sem precisar de `CAP_KILL` (resolvido na S30-10; ver a P-17); (b) cada serviço encerrar-se sozinho quando o pai morre, configurando o `PR_SET_PDEATHSIG` no início do processo; (c) aceitar o registro e documentá-lo no runbook (só se (a) e (b) enfraquecerem o isolamento). A correção não pode dar ao analisador o mesmo UID da API nem rodar algum serviço como root.
*Resultado (08/10/2026):* a P-17 se confirmou no Render, e as opções (a) e (b) não servem: o kernel
entrega o `PR_SET_PDEATHSIG` com a mesma checagem de permissão do `kill()`. Foi aplicada uma quarta
opção, sem sinal entre usuários: um lançador root por serviço fecha um pipe ao receber o `SIGTERM`, e
um guardião com o usuário do serviço o encerra (`deploy/render/run_as.py`; P-17 em
`docs/decisoes.md`).

**ADRs:** atualiza o ADR-03 (medição da S30-09 e a decisão da S30-11). Sem ADR novo.

**Critérios de aceite:**
1. O run do "Deploy do piloto" na `main` termina verde com os passos "Conferir o piloto" e "Smoke e2e no piloto" executados, nenhum pulado e nenhum aviso de conta ausente.
2. O feedback pela página responde em ≤ 30 s, e o login cria o cookie `__Host-ipc_session` com `HttpOnly`, `Secure` e `SameSite=Lax` pela origem da Vercel.
3. A 31ª tentativa de login sem sessão em 60 s recebe 429, mesmo com `X-Forwarded-For` forjado.
4. Os três monitores do UptimeRobot ficam verdes por 24 h, e o alerta de latência chega em ≤ 5 min no exercício.
5. A restauração de um backup cifrado reproduz as contagens do banco, com o RTO registrado no runbook.
6. O rollback dos dois serviços leva ≤ 5 min, com o tempo registrado no runbook.
7. O ADR-03 tem o P95 do servidor medido no piloto, com login, e a decisão do plano.
8. Os logs do Render não mostram `CRIT unknown problem killing` num deploy nem numa dormência.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Login com cookie pela página | pytest | `tests/pilot::test_login_validation_and_logout_through_the_page` | `deploy.yml` | 200 no login, cookie `__Host-` com os atributos, 200 na verificação, 204 na saída e 401 depois |
| Feedback em até 30 s pela página (novo) | pytest | `tests/pilot` (S30-02) | `deploy.yml` | 200 em ≤ 30 s, `source` = `template` sem IA configurada |
| `X-Forwarded-For` e `IPC_TRUSTED_PROXY_HOPS` (novo) | pytest | `tests/pilot` (S30-03) | `deploy.yml`, depois só à mão (gasta o limite por IP do runner) | 429 na 31ª tentativa com o valor forjado |
| e2e no piloto | Playwright | `deploy.yml`, "Smoke e2e no piloto" | `deploy.yml` com a conta | `smoke.spec.ts` e `auth.spec.ts` verdes |
| Carga no piloto | k6 | `load.yml` (20 por minuto, 5 min) | à mão | Sem 5xx; P95 do servidor registrado; ≤ 200 ms no plano escolhido para o prazo |
| Encerramento sem `CAP_KILL` (novo) | pytest pela imagem do piloto | `tests/security/test_pilot_isolation.py` | job "Segurança" do CI | `docker stop` em ≤ 15 s, sem `CRIT` no log, isolamento por UID e seccomp mantidos |
| Exercício de alerta | UptimeRobot | Runbook, S30-05 | à mão, uma vez | E-mail em ≤ 5 min |
| Restauração do backup | age, `pg_restore` | Runbook, "Restaurar um backup" | à mão, uma vez por semestre | Contagens iguais; RTO registrado |
| Rollback cronometrado | Painéis do Render e da Vercel | Runbook, "Voltar para a versão anterior" | à mão, uma vez por período | ≤ 5 min do passo 1 ao 3 |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, mais: os registros de ensaio do runbook preenchidos com data, responsável e tempo; a P-12 e a P-15 atualizadas em `docs/decisoes.md` com a evidência (run do workflow); nenhum secret ou URL de hook em arquivo, log ou PR.

**Riscos e bloqueios:** S30-02, S30-03, S30-05, S30-08 e S30-09 esperam a S30-01 (ação do autor, cerca de 10 min). O e-mail de verificação da conta nova pode cair no spam (remetente Gmail pelo Brevo, Q-17). A S30-03 gasta o limite de login por IP do runner por 1 min. Se a correção da S30-10 exigir capacidades que o Render não dá, vale a opção (c), com o motivo no runbook. O backup semanal não atende o RPO de 24 h da NFR-20 (S30-12).

#### Avisos de pendência das Sprints 11 a 29 (revisão de 08/10/2026)

A coluna "Situação" do README ainda trazia avisos de quando cada sprint fechou. Revistos em
08/10/2026, depois da Sprint 30:

| Sprint | Aviso | Situação em 08/10/2026 | Onde fica |
|---|---|---|---|
| 11 | Falta a configuração das contas | Resolvido: contas configuradas em 07/10/2026 e a conta de verificação em 08/10/2026 | S30-01 |
| 19 | Falta o primeiro deploy com login | Resolvido em 08/10/2026 (run 37754224989) | S30-02 |
| 20 | Falta o repositório privado dos gabaritos | Em parte: repositório e chave da CI criados hoje (H-02); faltam os gabaritos do Notion | S33-01 |
| 21 | Falta o terceiro monitor do UptimeRobot | Resolvido em 08/10/2026 | S30-04 |
| 22 | Os casos em aberto do mapeamento seguem para o Marco 2 | Resolvido: decididos pelo autor em 09/10/2026 (ruleset `2026.2.5`); Marco 2 em 19/10/2026 | S31-05, S31-12 |
| 24 | Nenhuma questão real cadastrada ainda | Ensaio feito em 09/10/2026 (L3-Q9, `docs/ensaio-cadastro.md`); falta o cadastro de 2027.1 pela equipe, com a troca de período sem código | S31-09, S31-10, S31-13, S33-04 |
| 25 | Falta o primeiro deploy | Resolvido em 07/10/2026 | S25-02 |
| 28 | Faltam o ensaio do rollback e a carga no piloto | Resolvido em 08/10/2026 | S30-08, S30-09 |
| 29 | Desligada no piloto até a política e a calibração | Planejado | S31-01, S33-02, S33-03, S33-06 |

**Feito em 08/10/2026, antes da Sprint 31:**

| ID | O que | Resultado |
|---|---|---|
| H-01 | Avisos desatualizados do README corrigidos (Sprints 11, 19, 21, 25 e 28) | README com a situação acima |
| H-02 | Repositório privado `Lionzio/ip-checker-gabaritos` criado, com as pastas de 2026.2 e um README para a equipe; chave de implantação só de leitura nele e a parte privada no segredo `GABARITOS_SSH_KEY`; o job "Gabaritos" do `ci.yml` passa a usar a chave (ADR-10) | Falta só copiar os gabaritos e gravar `GABARITOS_REPO` (S33-01) |
| H-03 | Pauta do Marco 2 em `docs/marco-2.md`: os 9 casos do mapeamento, a política dos indícios, Q-16, Q-17, Q-22, questões e gabaritos e o piloto | Usada na S31-05 e na S31-12 |
| H-04 | Plano: US-36, FR-31, NFR-27, ADR-10 e as tasks S31-09 a S31-13 | Esta seção e a Sprint 31 |

#### Sprint 31 — Decisões com a coordenação e auditoria bloqueante

**Objetivo:** levar à coordenação, ao NTI e ao autor as decisões em aberto com as opções de 7.13, entregar o Marco 2 e tornar a auditoria de segurança bloqueante, com os achados triados.

**Missão, persona e execução:** a missão é sair da Sprint 31 com as decisões da coordenação registradas (ou formalmente aguardando), a auditoria bloqueante e o período pronto para trocar sem mudar código. A persona é o Tech Lead e monitor-mantenedor (US-36), com o autor como quem apresenta o Marco 2. Execução: primeiro a engenharia sem dependência externa, em PRs pequenos (S31-03, S31-04, S31-09, S31-10 e S31-11); em paralelo, o Marco 2 com a pauta de `docs/marco-2.md` (S31-05 e S31-12) e as decisões S31-01, S31-02, S31-07 e S31-08; por fim, o ensaio de cadastro de questões reais de 2026.2 pela equipe (S31-13).

**Premissas:** Q-16, Q-17, Q-22 e ADR-08 (S29-04) seguem abertas até a decisão registrada; a NFR-13 passa a ser medida a cada PR; o período ativo é 2026.2 até a S33-04.

**Histórias:** US-11, US-13, US-23, US-32, US-34, US-15 e US-36 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S31-01 | US-34 | Decisão | Levar à coordenação a política dos indícios de IA (S29-04, ADR-08): o texto aos alunos e quem gera as referências (opções em 7.13.1) | `docs/indicios-de-ia.md` | Coordenação | — | — | Entrada: aprovação ou pedido de mudança, por escrito. Desbloqueio: a decisão registrada na Q-21 e no ADR-08, com a data |
| S31-02 | US-32 | Decisão | Q-16: provedor de IA do feedback (opções em 7.13.2); se aprovado, o autor grava `IPC_LLM_*` no Render | `docs/decisoes.md` (Q-16), `deploy/compose.md` ("Feedback por IA") | Autor e Coordenação | — | — | Desbloqueio: Q-16 decidida; se houver provedor, um feedback no piloto com `source` = `llm` e o nome do aluno ausente do pedido ao provedor |
| S31-03 | US-15 | Engenharia | Triar a auditoria semanal (S25-01) e torná-la bloqueante: corrigir ou justificar cada achado alto ou crítico corrigível, tirar o `continue-on-error` do `audit.yml` e rodar gitleaks, pip-audit e npm audit também no `ci.yml`, em todo PR (Trivy fica no semanal, por demorar) | `.github/workflows/audit.yml`, `.github/workflows/ci.yml` | Autor | 2 | — | Uma rodada do `audit.yml` sem achado aberto; PR com uma dependência vulnerável de teste falha no CI; NFR-13 e item 14 da seção 8 sem a ressalva "ainda não bloqueante" |
| S31-04 | US-15 | Engenharia | Semgrep no CI (NFR-09): imagem fixada por digest, regras para Python e TypeScript, achados novos bloqueiam o PR | `.github/workflows/ci.yml`, `.semgrep.yml` (novo; o conjunto de regras foi decidido na P-20) | Autor | 1 | — | Job verde na `develop`; um PR com `eval` sobre dado de requisição falha; NFR-09 sem [PLANEJADO] |
| S31-05 | US-11 | Externa | Marco 2: revisar o guia da equipe e marcar a data da apresentação a monitores-chefes e professores | `docs/guia-da-equipe.md`; arquivo da apresentação [A CONFIRMAR: não está no repositório] | Autor | — | — | Entrada: data marcada e guia revisado. Desbloqueio: apresentação feita, com as decisões registradas em `docs/decisoes.md` |
| S31-06 | US-23 | Externa | Criar o formulário da pesquisa de satisfação e a planilha do critério 3, como especificados (S28-02) | `docs/eficacia.md` (seções 3 e 4) | Equipe | — | — | Entrada: formulário anônimo e planilha sem dados de aluno. Desbloqueio: os dois links registrados em `docs/eficacia.md` |
| S31-07 | US-11 | Decisão | Q-17: remetente definitivo dos e-mails e, se for `@cin.ufpe.br`, SPF, DKIM e DMARC conferidos com o NTI (opções em 7.13.3) | `docs/decisoes.md` (Q-17), `deploy/compose.md` ("Registro e e-mails"), `IPC_EMAIL_FROM` no Render | Autor e NTI | — | — | Desbloqueio: um e-mail de verificação entregue na caixa de entrada de um `@cin.ufpe.br` e de um `@ufpe.br`, fora do spam |
| S31-08 | US-13 | Decisão | Q-22: governança das regras por fork e check de aprovação (opções em 7.13.4) | `RULES.md`, `.github/PULL_REQUEST_TEMPLATE/regras.md` | Autor | — | — | Desbloqueio: Q-22 decidida; se a opção B, uma task de implementação entra na sprint seguinte |
| S31-09 | US-36 | Engenharia | Período ativo num só lugar: o analisador, o compose, o `render.yaml`/supervisord e a CI leem o período de um único arquivo, e nenhum outro arquivo cita `2026.2` como período ativo | `rulesets/` (arquivo do período ativo, novo), `backend/src/ipc_analyzer/` (configuração), `deploy/render/supervisord.conf`, `backend/Dockerfile`, `.github/workflows/ci.yml` | Autor | 2 | — | Trocar de período muda uma linha; um teste falha se outro arquivo citar o período ativo; `/ready` mostra a `ruleset_version` do período do arquivo |
| S31-10 | US-36 | Engenharia | `ipc-rules new-period <novo> --from <anterior>`: copia o `base.yaml` com o período e a `ruleset_version` novos e cria `questions/` e `referencias/` vazias; recusa período existente ou fora do formato `AAAA.N` | `backend/src/ipc_analyzer/cli.py`, `RULES.md` | Autor | 1 | — | `ipc-rules new-period 2027.1 --from 2026.2` cria a pasta, e `ipc-rules validate ../rulesets/2027.1 --golden tests/golden` sai com 0 |
| S31-11 | US-36 | Engenharia | Gabaritos com as questões do próprio período: o harness usa `rulesets/<período do gabarito>/questions/` quando a pasta existe; o `excecoes.yaml` fica para períodos sem questões cadastradas | `backend/tests/official_answers/harness.py`, `test_harness.py` | Autor | 1 | — | Teste: um gabarito de 2026.2 com o período ativo 2027.1 é analisado com a questão de 2026.2 |
| S31-12 | US-11 | Externa | Levar ao Marco 2 a pauta de `docs/marco-2.md` e registrar as decisões: os 9 casos do mapeamento (aviso da Sprint 22), os indícios de IA, Q-16, Q-17, Q-22, questões e gabaritos e o piloto; cada caso liberado vira uma task de regra na sprint seguinte | `docs/marco-2.md`, `docs/mapping-R-xx.md`, `docs/decisoes.md` | Autor, monitores-chefes e professores | — | S31-05 | Desbloqueio: a tabela "Registro" preenchida e cada decisão em `docs/decisoes.md`, com a data e quem decidiu |
| S31-13 | US-13 | Externa | Ensaiar o cadastro de questões reais em 2026.2 (aviso da Sprint 24): pelo menos uma questão de cada lista já aplicada, pelo `RULES.md`, para validar o fluxo antes de 2027.1 | `rulesets/2026.2/questions/` | Equipe e Professor | — | — | Desbloqueio: `ipc-rules validate ../rulesets/2026.2` mostra as questões, com o PR aprovado por um monitor-chefe ou professor |

**ADRs:** ADR-10 (questões e gabaritos por período, aceito em 08/10/2026); se a Q-16 escolher um provedor, o ADR-06 recebe a decisão.

**Critérios de aceite:**
1. As decisões S31-01, S31-02, S31-07 e S31-08 estão registradas em `docs/decisoes.md`, com a data e quem decidiu, ou a sprint fecha com cada uma marcada "aguardando", com a entrada pendente.
2. O `audit.yml` roda sem `continue-on-error`, e a última rodada não tem achado alto ou crítico corrigível aberto.
3. Um PR de teste com um segredo falso, uma dependência vulnerável ou um `eval` sobre dado de requisição falha no CI (o PR é descartado depois).
4. Os links do formulário e da planilha estão em `docs/eficacia.md`.
5. Trocar o período ativo muda uma linha de um arquivo, e `ipc-rules new-period 2027.1 --from 2026.2` gera um período válido (S31-09, S31-10).
6. Um gabarito de um período anterior é conferido com as questões do próprio período (S31-11).
7. A pauta do Marco 2 sai com cada um dos 9 casos do mapeamento decidido ou adiado com o motivo, e o caso 10 (expressão geradora, aplicado de forma provisória em 09/10/2026) ratificado ou revertido (S31-12).

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Segredos | gitleaks | `ci.yml` (novo) e `audit.yml` | PR, push e segunda-feira | 0 achados; o PR de teste com segredo falso falha |
| Dependências Python | pip-audit 2.9.0 | `ci.yml` (novo) e `audit.yml` | idem | 0 vulnerabilidades corrigíveis |
| Dependências npm | `npm audit --audit-level=high` | `ci.yml` (novo) e `audit.yml` | idem | 0 altas ou críticas |
| Imagem do piloto | Trivy (`--severity HIGH,CRITICAL --ignore-unfixed`) | `audit.yml` | segunda-feira e manual | 0 achados |
| Análise estática | Semgrep | `ci.yml` (novo) | PR e push | 0 achados novos; o PR de teste com `eval` falha |
| Feedback com IA (se a Q-16 aprovar) | pytest com o provedor gravado | `tests/feedback` e uma verificação manual no piloto | depois da configuração | `source` = `llm`, nome do aluno trocado por `[ALUNO]`, texto validado |
| Entrega de e-mail (Q-17) | registro real | runbook, roteiro do primeiro deploy | depois da decisão | E-mail na caixa de entrada em ≤ 5 min |
| Período ativo num só lugar (novo) | pytest | `tests/test_ruleset_loader.py` e um teste que procura o período em `deploy/` e `backend/Dockerfile` | PR e `develop` | Só o arquivo do período ativo cita o período; `/ready` com a `ruleset_version` dele |
| Período novo (novo) | pytest e `ipc-rules` | `tests/test_cli.py`; `uv run ipc-rules new-period 2027.1 --from 2026.2` numa pasta temporária | PR | Pasta criada e validada; período repetido ou inválido recusado |
| Gabaritos por período (novo) | pytest | `tests/official_answers/test_harness.py` | PR | A questão do período do gabarito é usada |
| Gabaritos reais | pytest no job "Gabaritos" | `ci.yml`, com `GABARITOS_REPO` gravada (S33-01) | PR e `develop` | Zero violação em todos os gabaritos de listas habilitadas |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com o item 14 sem a ressalva de "ainda não bloqueante".

**Riscos e bloqueios:** as decisões dependem da agenda da coordenação e do NTI; a sprint não espera por elas e as mantém como "aguardando". A triagem pode revelar uma vulnerabilidade sem correção: ela é registrada com a justificativa e revista a cada rodada.

#### Sprint 32 — Comparação com o gabarito (incluída em 09/10/2026)

**Objetivo:** a verificação mostra, junto com as violações, a semelhança do código do aluno com o gabarito oficial da questão; o plágio compara A e B também com o gabarito e alerta um possível vazamento; os indícios ganham o sinal do gabarito; nenhum texto do gabarito sai do servidor (ADR-11). Incluído em 09/10/2026 (Q-16): o feedback passa a ser sem IA por padrão, com o botão "Aprimorar com IA" usando uma cadeia de provedores gratuitos com fallback (S32-11 a S32-14).

**Missão, persona e execução:** a missão é dar à equipe, na hora da correção, a distância entre o código do aluno e a solução oficial, e um sinal de que o gabarito pode estar circulando, sem guardar nada e sem expor o gabarito. A persona é quem corrige (monitor, monitor-chefe ou professor; US-37 e US-38), com o Tech Lead cuidando da confidencialidade (NFR-27). Execução: a credencial do autor primeiro (S32-01); depois, em PRs pequenos, o carregamento na API (S32-02), a comparação no analisador (S32-03), as rotas (S32-04, S32-05), as telas (S32-06, S32-07), o sinal dos indícios (S32-08), os testes de confidencialidade e desempenho (S32-09) e a documentação (S32-10). O carregamento entra numa release sem migração (P-18).

**Premissas:** Q-24 decidida pelo autor (1B 2B 3A 4B 5A 6B); a troca de período sem código (S31-09, S31-10) já está pronta; o limiar do alerta (95%) e o tamanho mínimo (60 tokens) foram validados pelo autor em 12/10/2026; a credencial só de leitura é criada pelo autor [A CONFIRMAR: a validade máxima que o GitHub aceita para ela, que define a troca no runbook].

**Histórias:** US-37 e US-38 (seção 4); FR-32; NFR-27 (revisto) e NFR-28; US-32, FR-30 e NFR-26 para o "Aprimorar com IA" (Q-16).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S32-01 | US-37 | Externa | Criar a credencial só de leitura do `Lionzio/ip-checker-gabaritos` (*fine-grained token*, Contents: Read-only, só esse repositório) e gravá-la no Render (`IPC_GABARITOS_TOKEN`), com o passo a passo do runbook | Painel do GitHub e do Render; `docs/runbook.md` | Autor | — | — | Desbloqueio: o diagnóstico da API mostra "gabaritos carregados: N" no piloto, sem expor nada |
| S32-02 | US-37 | Engenharia | Carregamento na API: ao subir, baixar o repositório dos gabaritos (API do GitHub, HTTPS), só os `<período>/lista-<n>/L<n>-Q<m>.py`, com limite por arquivo e no total; índice em memória por período e questão; nunca em disco nem em log; falha → comparação desligada com aviso, `/ready` intacto; `IPC_GABARITOS_REPO` e `IPC_GABARITOS_TOKEN` (`sync: false`) no `render.yaml` | `backend/src/ipc_api/` (módulo novo), `settings.py`, `render.yaml` | Autor | 2 | S32-01 (só para o piloto) | Testes com repositório falso: carrega, ignora o que não é gabarito, respeita os limites, nada no disco nem no log (canário), falha sem derrubar a API |
| S32-03 | US-37, US-38 | Engenharia | Comparação no analisador: rota interna que recebe o código e o gabarito, prepara com cache por hash e devolve a semelhança (ADR-07), as construções em comum, só no aluno e só no gabarito (fatos do motor) e as linhas do aluno que coincidem — nunca o texto do gabarito | `backend/src/ipc_analyzer/` (similaridade e serviço) | Autor | 2 | — | Testes com gabaritos sintéticos: idêntico = 100%; renomeado ≥ 99%; independente < 80%; a resposta não contém nenhuma linha do gabarito |
| S32-04 | US-37 | Engenharia | API da verificação: `question_id` do seletor, campo `gabarito` opcional no `POST /api/v1/validate` (faixa, porcentagem, construções e linhas do aluno) e a rota que lista as questões do período ativo com gabarito (só os IDs); OpenAPI e tipos gerados | `routes/validate.py`, `routes/meta.py`, `schemas.py`, `docs/openapi.json`, `frontend/src/types/openapi.ts` | Autor | 2 | S32-02, S32-03 | Contrato atualizado; sem gabarito, `gabarito` vem nulo com o aviso; P95 local sem regressão |
| S32-05 | US-38 | Engenharia | API do plágio: com a questão, A×gabarito e B×gabarito e o alerta de possível vazamento pelas regras da ADR-11 (limiar e mínimo configuráveis) | `routes/similarity.py`, `schemas.py`, OpenAPI | Autor | 1 | S32-03 | Testes: alerta com A, B e o gabarito idênticos e grandes; sem alerta com códigos curtos ou com só um aluno parecido |
| S32-06 | US-37 | Engenharia | Tela de verificação: seletores de período, lista e questão (questões com gabarito), o bloco "Comparação com o gabarito" (faixa com cor e nome, construções, linhas do aluno destacadas no editor) e os avisos | `frontend/src/` (verificação) | Autor | 2 | S32-04 | Vitest e e2e; axe sem violações graves; cabe em 375 px |
| S32-07 | US-38 | Engenharia | Tela de plágio: o seletor da questão, os dois resultados com o gabarito e o alerta de possível vazamento, com o aviso de que é um indício | `frontend/src/` (plágio) | Autor | 1 | S32-05 | Vitest e e2e; axe; 375 px |
| S32-08 | US-34 | Engenharia | Indícios de IA: a semelhança com o gabarito como sinal novo, nas faixas de referência, só com `IPC_AI_INDICATORS` | `engine/indicators.py`, painel de indícios | Autor | 1 | S32-03 | Testes do sinal; desligado no piloto (S31-01) |
| S32-09 | US-37, US-38 | Engenharia | Confidencialidade e desempenho: testes canário (um gabarito sintético com marcador nunca aparece nas respostas, nos logs, na telemetria nem no disco), a imagem do piloto sem gabaritos, isolamento do analisador inalterado e a carga com a comparação (NFR-28) | `tests/security/`, `tests/test_log_contract.py`, `deploy/load/` | Autor | 1 | S32-04, S32-05 | Todos os canários com 0 ocorrência; P95 ≤ 200 ms local; suíte do piloto verde |
| S32-10 | US-37, US-38 | Engenharia | Documentação: guia da equipe (como ler a comparação e o alerta), runbook (credencial, troca, "gabaritos indisponíveis"), ADR-11 como Aceito, CHANGELOG e README | `docs/`, `README.md`, `CHANGELOG.md` | Autor | 0,5 | S32-02 a S32-09 | Revisados no PR |
| S32-11 | US-32 | Externa | Criar as contas gratuitas e as chaves dos provedores da cadeia do "Aprimorar com IA" (Q-16): pelo menos Gemini e Groq, e outros gratuitos que o autor escolher; gravar no Render só pelos nomes (`IPC_LLM_CHAIN` e `IPC_LLM_<PROVEDOR>_*`, `sync: false`), com o passo a passo do runbook | Painéis dos provedores e do Render; `docs/runbook.md` | Autor | — | — | Desbloqueio: o diagnóstico do feedback mostra os provedores configurados (só os nomes), e um "Aprimorar com IA" no piloto responde |
| S32-12 | US-32 | Engenharia | Feedback sem IA como padrão e o "Aprimorar com IA" no backend (Q-16, A e C): o **Gerar feedback** devolve sempre a versão determinística (`compose.template_text`), sem chamar IA; uma rota nova recebe a versão determinística e o mesmo contexto já enviado hoje (código sem comentários nem docstrings, anotação e resultado, nome trocado por `[ALUNO]`, dados pessoais mascarados) e pede à IA para detalhar, expandir, exemplificar e melhorar, mantendo a abertura e a frase obrigatória. Cadeia de N provedores (`IPC_LLM_CHAIN`, em ordem), com fallback por erro, prazo, cota esgotada (429) ou resposta reprovada na validação (NFR-26), e uma pausa por provedor depois de 429; tudo falhando, devolve a versão determinística com o aviso. A cota diária por conta e o teto do servidor valem para o aprimoramento | `backend/src/ipc_api/feedback/` (`providers.py`, `service.py`), `routes/feedback.py`, `settings.py`, `render.yaml`, OpenAPI | Autor | 2 | — | Testes com provedores falsos: ordem da cadeia, fallback em cada tipo de falha, pausa depois de 429, partes fixas preservadas, nada inventado sobre violações, chave nunca em log nem em resposta |
| S32-13 | US-32 | Engenharia | Tela do feedback: o botão **Aprimorar com IA** ao lado do texto determinístico, com a espera, o aviso quando nenhuma IA responde, o rótulo "aprimorado por IA" e **Desfazer** (volta ao texto determinístico); continua editável e com Copiar | `frontend/src/` (feedback) | Autor | 1 | S32-12 | Vitest e e2e com o provedor falso; axe sem violações graves; cabe em 375 px |
| S32-14 | US-32 | Engenharia | Privacidade e documentação do aprimoramento: o aviso de privacidade diz que o "Aprimorar com IA" envia o código (sem nome nem dados pessoais) a provedores gratuitos que podem usá-lo para treino; FR-30 e ADR-06 revistos; runbook (chaves, cotas, troca de provedor); guia da equipe | `frontend/src/` (aviso), `docs/blueprint.md`, `docs/adr/ADR-06-*.md`, `docs/runbook.md`, `docs/guia-da-equipe.md` | Autor | 0,5 | S32-12 | Revisados no PR; o aviso aparece antes do primeiro aprimoramento |

**ADRs:** ADR-11 (Proposto → Aceito no fim da sprint); ADR-10 e NFR-27 revistos pela ADR-11.

**Critérios de aceite:**
1. Com a L1-Q1 de 2026.2 escolhida, a verificação mostra a porcentagem e a faixa da semelhança com o gabarito, as construções em comum, só no aluno e só no gabarito e as linhas do aluno que coincidem.
2. Nenhuma resposta da API, linha de log, evento de telemetria ou arquivo em disco contém texto do gabarito (canário com 0 ocorrência), e a imagem do piloto não tem nenhum gabarito.
3. No plágio, A×gabarito e B×gabarito aparecem com a questão escolhida; o alerta aparece com os três acima do limiar e os códigos acima do tamanho mínimo, e não aparece nos pares independentes do corpus de `tests/similarity` (0 alerta falso).
4. Sem a credencial ou com o download falho, a verificação e o plágio funcionam como antes, com o aviso, e o `/ready` responde 200.
5. P95 do `/validate` com a comparação ≤ 200 ms (NFR-28), medido localmente e, com a cota do Actions de volta, pelo "Carga no piloto".
6. O **Gerar feedback** devolve o texto determinístico sem chamar nenhuma IA; o **Aprimorar com IA** passa pela cadeia na ordem configurada e, com o primeiro provedor fora do ar ou sem cota, responde pelo seguinte; com todos falhando, volta o texto determinístico com o aviso (S32-12, S32-13).
7. O texto aprimorado mantém a abertura e a frase obrigatória, não cita violação que o motor não achou (NFR-26) e não leva o nome do aluno ao provedor; o aviso de privacidade fala do envio a provedores gratuitos (S32-14).

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Carregamento dos gabaritos | pytest com repositório falso | `tests/test_gabaritos_loader.py` (novo) | PR | Carrega, filtra, limita, falha sem derrubar a API |
| Comparação no analisador | pytest | `tests/similarity/` | PR | Faixas esperadas nos pares sintéticos; nada do gabarito na saída |
| Contrato da API | pytest e `gen:api` | `tests/test_api_contract.py`, tipos em dia | PR | Verde |
| Confidencialidade (canário) | pytest | `tests/security/`, `tests/test_log_contract.py` | PR | 0 ocorrência do marcador |
| Telas | Vitest e Playwright | `npm test`, `npm run e2e` | PR | Verde; axe sem violações graves; 375 px |
| Desempenho | pytest e k6 | orçamento da similaridade; "Carga no piloto" | PR; à mão | NFR-28 |
| Gabaritos reais | harness | `tests/official_answers` | PR | Zero violação, como antes |
| Cadeia do "Aprimorar com IA" | pytest com provedores falsos | `tests/feedback/` | PR | Ordem, fallback por erro, prazo, 429 e validação; partes fixas preservadas; nenhuma chave em log |
| Feedback na tela | Vitest e Playwright (provedor falso) | `npm test`, `npm run e2e` | PR | Determinístico por padrão; Aprimorar e Desfazer; axe; 375 px |
| Regressão | `scripts/ci-local.sh --e2e` (P-19) | — | PR | Verde |

**Definition of Done:** a da seção 8, mais: nenhum texto do gabarito fora do servidor (critério 2); a credencial só no Render e no runbook pelo nome; o ADR-11 como Aceito.

**Riscos e bloqueios:** os provedores gratuitos mudam limites e termos sem aviso e podem usar os dados para treino (risco aceito pelo autor, Q-16), e as chaves dependem do autor (S32-11); a credencial depende do autor (S32-01) e vence (troca no runbook); o limiar do alerta é premissa até a S33-02 e a S33-03; a comparação aumenta o tempo da verificação (NFR-28); sem a cota do Actions até 01/11 (P-19), a evidência vem da CI local.


#### Sprint 33 — Dados: gabaritos, questões de 2027.1 e calibração dos indícios

**Objetivo:** rodar os gabaritos de períodos anteriores no CI, calibrar os indícios de IA com soluções humanas (meta da ADR-08: no máximo 5% de faixa alta), cadastrar as questões de 2027.1 com as referências e, só com a política aprovada, ligar os indícios no piloto.

**Missão, persona e execução:** a missão é pôr dados reais no motor: os gabaritos protegendo contra falsos positivos, as questões de 2027.1 cadastradas e os indícios calibrados. As personas são o monitor-chefe e o professor que cadastram e aprovam questões (US-13) e o monitor-mantenedor que calibra (US-34, US-36). Execução: o autor copia os gabaritos e liga o job (S33-01); a equipe cria 2027.1 com `ipc-rules new-period` e cadastra as questões (S33-04); com as soluções da S33-02, a calibração (S33-03); com a política aprovada, as referências e os indícios ligados (S33-05, S33-06).

**Premissas:** Q-14 (gabaritos fora do repositório); ADR-08 (faixas iniciais a calibrar); P-07 (numeração das questões por período).

**Histórias:** US-13, US-14 e US-34 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S33-01 | US-14 | Externa | Copiar os gabaritos do Notion para o repositório privado já criado (`Lionzio/ip-checker-gabaritos`, H-02), em `<período>/lista-<n>/L<n>-Q<m>.py`, dar acesso à equipe (colaboradores) e, depois do primeiro gabarito, gravar a variável `GABARITOS_REPO` | `rulesets/README.md` ("Gabaritos"), README do repositório dos gabaritos, `backend/tests/official_answers/` | Autor e Equipe | — | — | Desbloqueio: o job "Gabaritos (zero violação, Q-14)" do `ci.yml` roda (não fica "skipped") e passa |
| S33-02 | US-34 | Externa | **Descartada pelo autor em 12/10/2026.** Obter as soluções humanas de períodos anteriores a 2023 para a calibração, no mesmo formato, fora do repositório [A CONFIRMAR: se os gabaritos da Q-14 trazem soluções de alunos ou só as respostas oficiais; se forem só oficiais, a fonte das soluções é a coordenação] | Pasta local fora do repositório | Autor e Coordenação | — | — | Entrada: pelo menos 200 soluções [PREMISSA] distribuídas pelas 6 listas. Desbloqueio: pasta disponível ao autor, sem dado de aluno no repositório |
| S33-03 | US-34 | Engenharia | Calibrar os indícios: rodar `ipc-rules calibrate` nas soluções da S33-02, ajustar as faixas de `engine/indicators.py` por PR até a faixa alta ficar em ≤ 5%, e registrar a distribuição no ADR-08 | `backend/src/ipc_analyzer/cli.py`, `backend/src/ipc_analyzer/engine/indicators.py`, `docs/adr/ADR-08-indicios-de-uso-de-ia-nunca.md` | Autor | 2 | S33-02 | `uv run ipc-rules calibrate ../rulesets/2026.2 <pasta> --max-alto 5` sai com 0; os testes de `test_indicators.py` atualizados para as faixas novas |
| S33-04 | US-13 | Externa | Criar o período 2027.1 com `ipc-rules new-period 2027.1 --from 2026.2` (S31-10), ajustar o `base.yaml` ao documento de permissões validado pelo professor, trocar o período ativo (S31-09) e cadastrar as questões das listas liberadas (R-01) pelo `RULES.md` | `rulesets/2027.1/base.yaml` e `questions/` (novos) | Professor e Equipe | — | Documento de permissões de 2027.1; S31-09, S31-10 | Desbloqueio: `ipc-rules validate ../rulesets/2027.1 --golden tests/golden` verde, com pelo menos uma questão por lista habilitada |
| S33-05 | US-34 | Externa | Gerar as referências por IA das questões cadastradas (S29-02), conforme a decisão da S31-01 sobre quem gera | `rulesets/2027.1/referencias/<questão>/*.py` (novos), `RULES.md` (passo 5) | Equipe (a decidir na S31-01) | — | S31-01, S33-04 | Desbloqueio: `ipc-rules validate` mostra "referências de IA: N em M questões", com M igual ao número de questões cadastradas |
| S33-06 | US-34 | Engenharia | Ligar os indícios no piloto: `IPC_AI_INDICATORS` = `"1"` no `render.yaml`, o teste correspondente atualizado e a variável `PILOT_AI_INDICATORS` = `1` | `render.yaml`, `backend/tests/test_indicators_api.py`, `.github/workflows/deploy.yml` | Autor | 0,5 | S31-01 (aprovada), S33-03 | Deploy verde com `ai_indicators: true` no `/api/v1/auth/options` da Vercel e o painel visível numa verificação de teste com a conta de verificação |

**ADRs:** atualiza o ADR-08 (faixas calibradas e, se for o caso, o status "ligado no piloto"). Sem ADR novo.

**Critérios de aceite:**
1. O job dos gabaritos roda no CI e passa com zero violação.
2. A calibração mostra no máximo 5% de faixa alta nas soluções anteriores a 2023, e o ADR-08 registra a distribuição.
3. O ruleset de 2027.1 é válido, com as questões e as referências das listas liberadas.
4. Os indícios só ficam ligados no piloto se a S31-01 estiver aprovada e o critério 2 for cumprido; senão, a S33-06 continua bloqueada.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Gabaritos | pytest (`tests/official_answers`) | `ci.yml`, job "Gabaritos" | PR e push, com `GABARITOS_REPO` definido | Zero violação em cada gabarito |
| Calibração dos indícios | `ipc-rules calibrate` | comando da S33-03 | à mão, a cada período | Sai com 0 (≤ 5% de faixa alta); a saída nunca mostra código |
| Regras R-01 de 2027.1 | `ipc-rules validate` e casos golden | `uv run ipc-rules validate ../rulesets/2027.1 --golden tests/golden` | PR de regras | 0 FP e 0 FN; referências válidas |
| Indícios no piloto (S33-06) | pytest | `tests/pilot::test_ai_indicators_are_on_only_when_expected` com `PILOT_AI_INDICATORS=1` | `deploy.yml` | `ai_indicators` igual ao esperado |
| Caso de uso dos indícios | Playwright | `frontend/e2e/indicators.spec.ts` | CI (compose) | Faixa alta com `break`, `continue` e `pass`; nada numa solução limpa |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Tasks acrescentadas em 11/10/2026 (início da sprint):**

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S33-07 | US-38 | Engenharia | `ipc-rules calibrate-gabarito`: em soluções humanas independentes, a distribuição de semelhança com o gabarito nas faixas do FR-29 e os alarmes falsos do alerta de vazamento (ADR-11), com limiar e tamanho mínimo ajustáveis; saída só com contagens e caminhos | `backend/src/ipc_analyzer/gabarito_calibration.py`, `cli.py` | Autor | 1 | — | Testes com soluções sintéticas: cópias do gabarito geram o alarme, soluções diferentes não; nenhum código na saída |
| S33-08 | US-14 | Engenharia | `ipc-rules import-gabaritos`: lê uma exportação do Notion em Markdown e grava `<período>/lista-<n>/L<n>-Q<m>.py` no repositório privado, nunca neste; questão pelo título, pela página ou pelas pastas; conflitos e blocos sem questão ficam para decisão manual | `backend/src/ipc_analyzer/gabarito_import.py`, `cli.py`, `rulesets/README.md` | Autor | 1 | — | Testes com uma exportação sintética; o destino neste repositório é recusado (NFR-27) |
| S33-09 | US-34 | Engenharia | (Opcional, a decidir pelo autor) gerar as referências por IA a partir do enunciado, pela cadeia do Aprimorar com IA, para quem cadastra revisar | a definir | Autor | 1 | S33-04 | Aguardando a decisão |
| S33-10 | US-15 | Externa | Volta da cota do Actions (01/11/2026): CI com o job "Gabaritos", "Deploy do piloto", backup e auditoria rodando no Actions (runbook, "Sem GitHub Actions") | `.github/workflows/` | Autor | — | 01/11/2026 | Os quatro workflows verdes |

**Situação (11/10/2026):** S33-07 e S33-08 entregues. S33-03 em parte: a medição preliminar nos 23 gabaritos de 2026.2 deu 0% na faixa alta (ADR-08), sem valor de calibração. Aguardando, com as premissas da P-21: S33-01 (períodos anteriores e Listas 4 a 6 de 2026.2), S33-02, S33-04, S33-05, S33-06 (depois da S33-02), S33-09 (decisão do autor) e S33-10 (01/11/2026). **Proposta de 12/10/2026:** as S33-03, S33-05, S33-06 e S33-09 passam para a Sprint 42 (7.16), que liga os indícios no piloto. **Decisões do autor (12/10/2026):** a S33-02 foi descartada, porque as soluções anteriores a 2023 não existem e não serão buscadas; a S33-09 foi aprovada; as questões de 2027.1 (S33-04) ficam prontas perto de março de 2027, até uma semana antes de cada lista.

**Definition of Done:** a da seção 8; nenhum gabarito ou solução de aluno no repositório (Q-14, NFR-11).

**Riscos e bloqueios:** a sprint inteira depende de dados externos (S33-01, S33-02 e S33-04). Sem as soluções anteriores a 2023, a calibração não sai, e os indícios continuam desligados no piloto. O documento de permissões de 2027.1 tem data incerta (P-10).

#### Sprint 34 — Prontidão para 2027.1

**Objetivo:** antes da primeira lista de 2027.1, ter o plano do Render decidido e aplicado, o monitoramento estável, um teste sintético diário da primeira verificação, os cenários de carga do NFR-04 e do NFR-05 e as listas habilitadas conforme o professor validar.

**Missão, persona e execução:** a missão é chegar ao primeiro prazo de 2027.1 sabendo como o piloto se comporta no pico, no plano gratuito (S30-11). A persona é o monitor-mantenedor que opera o piloto (US-19, US-22). Execução: medir o pico no gratuito (S34-01) e os cenários do NFR-04 e do NFR-05 (S34-03), o teste sintético diário (S34-02), o alerta a cada release (S34-04), as listas habilitadas (S34-05) e 7 dias de monitores verdes (S34-06).

**Premissas:** P-01 (pico de 500 por minuto), P-04 (NAT do campus), P-05 (disponibilidade), P-10 (calendário), ADR-03.

**Histórias:** US-19, US-22 e US-12 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S34-01 | US-22 | Engenharia | Medir o pico no plano gratuito (S30-11, troca aceita pelo autor em 08/10/2026): "Carga no piloto" em degraus até o `OVERLOADED` aparecer, com a taxa máxima sem recusa e a porcentagem de recusas a 500 por minuto registradas no ADR-03 | `.github/workflows/load.yml`, `docs/adr/ADR-03-topologia-de-implantacao-por-fase.md` | Autor | 0,5 | S30-11 | Taxa máxima sem `OVERLOADED` e recusas a 500 por minuto no ADR-03; nenhum 500/502/504 |
| S34-02 | US-19 | Engenharia | Teste sintético diário da primeira verificação (NFR-06): workflow agendado que entra com a conta de verificação, verifica uma solução da Lista 1 e mede o tempo | `.github/workflows/synthetic.yml` (novo), `backend/tests/pilot/` | Autor | 1 | S30-01 | Roda todo dia útil às 07:00 (horário de Brasília), falha se a verificação passar de 300 ms no servidor (medido pelo `Server-Timing`; ver a situação da Sprint 34) ou se der erro |
| S34-03 | US-22 | Engenharia | Cenários de carga por release: o NFR-04 (500 por minuto por 15 min, 80% de 4 IPs) e o NFR-05 (1.500 por minuto, recusa com `Retry-After` em ≤ 100 ms e recuperação em ≤ 60 s), na emulação local, com `X-Forwarded-For` simulado e `IPC_TRUSTED_PROXY_HOPS` = 1 só no contêiner de teste | `deploy/load/run_load.py`, `deploy/load/pilot-load.js` | Autor | 2 | — | Relatório dos dois cenários no plano escolhido: 0 respostas 500, 502 ou 504; 503 com `Retry-After`; recuperação ≤ 60 s |
| S34-04 | US-19 | Engenharia | Exercício de alertas a cada release (NFR-15): o roteiro da S30-05 entra no checklist da release e no runbook, com uma linha por release | `docs/runbook.md`, `scripts/release.sh` (mensagem final) | Autor | 0,5 | S30-05 | Tabela do runbook com uma linha por release desde a Sprint 34 |
| S34-05 | US-12 | Externa | Habilitar as listas no piloto conforme o professor validar o ruleset de 2027.1 (`IPC_ENABLED_LISTS`) | `render.yaml` | Professor e Autor | — | S33-04 | Desbloqueio: `/api/v1/lists` do piloto mostra só as listas validadas, antes da data de liberação de cada uma |
| S34-06 | US-19 | Externa | Conferir os monitores no início do período: UptimeRobot verde nos 7 dias anteriores à primeira lista, e os contatos de alerta atualizados | Painel do UptimeRobot | Autor | — | S30-04 | Disponibilidade ≥ 99,5% nos 7 dias (P-05, NFR-06) |

**ADRs:** atualiza o ADR-03 com a medição da S34-01.

**Situação (11/10/2026):** S34-02 e S34-04 entregues (#71): o `Server-Timing` da verificação, o
workflow "Sintético diário", que começa a rodar com a volta da cota em 01/11/2026, os scripts
`sintetico-local.sh` e `carga-piloto.sh` e o exercício de alerta a cada release. S34-01 e S34-03
medidos na emulação do gratuito (ADR-03, "Pico no plano gratuito"): no máximo 100 verificações por
minuto sem recusa; sob sobrecarga, nenhum 500, 502 ou 504, todo 503 com `Retry-After` e
recuperação em 5,7 s, mas o NFR-04 e o tempo do 503 no NFR-05 não são atingíveis com 0,1 CPU (a
consequência aceita na S30-11). Achado para a Sprint 35: sob sobrecarga, o pool do banco esgotado
vira `DATABASE_UNAVAILABLE` em vez de `OVERLOADED`. O [A CONFIRMAR] da S34-02 foi resolvido pelo
`Server-Timing`, em vez do log ou do `/health/slo`. Aguardando: S34-05 (documento de 2027.1,
S33-04) e S34-06 (datas de 2027.1, P-10); os "7 dias seguidos" do sintético contam a partir de
01/11/2026.

**Critérios de aceite:**
1. O plano do Render está aplicado e medido.
2. O teste sintético roda há pelo menos 7 dias seguidos, sem falha.
3. Os relatórios do NFR-04 e do NFR-05 estão anexados ao ADR-03.
4. Só as listas validadas pelo professor estão habilitadas no piloto.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Sintético diário (novo) | pytest ou k6 contra o piloto | `synthetic.yml` | `schedule`, dias úteis | Verificação ≤ 300 ms e sem erro |
| Capacidade (NFR-04) | k6 | `python deploy/load/run_load.py --plan <plano> --rate 500 --duration 15m` | antes de cada release | 0% de 5xx e < 0,1% de timeouts |
| Estresse (NFR-05) | k6 | `run_load.py` com 1.500 por minuto | antes de cada release | 0 respostas 500, 502 ou 504; `Retry-After` em ≤ 100 ms; recuperação ≤ 60 s |
| Carga no piloto | k6 | `load.yml` | depois da mudança de plano | P95 do servidor ≤ 200 ms |
| Exercício de alerta | UptimeRobot | runbook | a cada release | E-mail em ≤ 5 min |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com o item do UptimeRobot cumprido.

**Riscos e bloqueios:** o custo do Starter é decisão do autor (S30-11); sem ele, o NFR-01 não é atendido com login (ADR-03, S28-01). O calendário de 2027.1 depende da UFPE (P-10).

#### Sprint 35 — Controles de qualidade e observabilidade

**Objetivo:** tirar do estado [PLANEJADO] os controles de qualidade que não dependem da Fase 2: benchmark do motor, Lighthouse, cobertura por pasta, canário em produção e esquema do ruleset; a observabilidade com Prometheus e Grafana entra só se o autor decidir.

**Missão, persona e execução:** a missão é tirar do estado [PLANEJADO] os controles de qualidade. A persona é o Tech Lead que cuida da qualidade (US-14, US-15, US-17, US-21). Execução: um controle por PR (S35-01 a S35-05), cada um entrando no CI só depois de verde na `develop`, e a decisão do `/metrics` (S35-06).

**Premissas:** NFR-02, NFR-03, NFR-11 e NFR-16, com as metas da seção 3.3.

**Histórias:** US-14, US-15, US-17 e US-21 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S35-01 | US-15 | Engenharia | `pytest-benchmark` no CI (NFR-02: P95 ≤ 50 ms por entrada de até 50 KB): corpus fixo de entradas, linha de base versionada, e o CI falha se o P95 regredir mais de 20% | `backend/pyproject.toml` (dependência de dev), `backend/tests/benchmark/` (novo), `.github/workflows/ci.yml` | Autor | 2 | — | Um PR que deixa o motor 30% mais lento falha; o item do benchmark da seção 8 sem [PLANEJADO] |
| S35-02 | US-21 | Engenharia | Lighthouse CI nos PRs do `frontend/` (NFR-03): perfil móvel ("Slow 4G") sobre o build de produção | `.github/workflows/ci.yml`, `frontend/lighthouserc.json` (novo) | Autor | 1 | — | FCP < 1,5 s e JS inicial ≤ 350 KB gzip (NFR-03); um PR que estoura a meta falha |
| S35-03 | US-15 | Engenharia | Cobertura com limite por pasta (NFR-16): ≥ 90% em `ipc_analyzer/engine` e ≥ 80% no restante, além do total | `backend/pyproject.toml`, `.github/workflows/ci.yml` | Autor | 0,5 | — | O CI falha se a pasta do motor cair abaixo de 90% |
| S35-04 | US-17 | Engenharia | Busca mensal do canário em produção (NFR-11): um workflow agendado verifica, com a conta de verificação, um código com um marcador e procura o marcador no banco (com a credencial de administrador) e nos logs do Render **Decidido pelo autor em 11/10/2026:** sem chave de API do Render (ela não tem escopo e daria acesso total ao serviço); o workflow procura no banco, e os logs são conferidos pelo painel com a marca que ele mostra (runbook, "Canário mensal") | `.github/workflows/canary.yml` (novo) | Autor | 2 | S30-01 | 0 ocorrências no banco e nos logs; o workflow falha com uma ocorrência plantada num teste |
| S35-05 | US-14 | Engenharia | JSON Schema do ruleset e `ipc-rules compile` (C6): esquema gerado do modelo do carregador, para editores e para o CI, e um compilado com o SHA-256 | `rulesets/schema/ruleset.schema.json` (novo), `backend/src/ipc_analyzer/cli.py` | Autor | 2 | — | O esquema valida os rulesets de 2026.2 e 2027.1; o compilado tem o mesmo `ruleset_sha256` do manifesto; o item da C6 sem [PLANEJADO] |
| S35-06 | US-17 | Decisão | Métricas `/metrics`, Grafana e Prometheus (opcionais, C8): manter o `/health/slo` com o UptimeRobot ou acrescentar o Grafana Cloud gratuito (opções em 7.13.7) | `docs/blueprint.md` (C8) | Autor | — | — | Desbloqueio: decisão registrada na C8; se aprovada, uma task de implementação entra na sprint seguinte |

**ADRs:** nenhum; a decisão da S35-06, se positiva, atualiza a C8 da seção 5.2.1.

**Tasks acrescentadas em 11/10/2026 (início da sprint), dos achados das Sprints 34 e do roteiro de
testes manuais:**

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S35-07 | US-08 | Engenharia | Plágio resistente a linhas inseridas dentro de um bloco copiado (cenários P-11 e P-12 do roteiro): comparar também os comandos de cada bloco, além das subárvores inteiras (ADR-07) | `backend/src/ipc_analyzer/engine/similarity_tree.py`, `docs/adr/ADR-07-*.md` | Autor | 3 | — | P-11 ≥ 95% e P-12 ≥ 90%; as soluções independentes do roteiro (P-09) e o corpus de pares continuam baixos |
| S35-08 | US-22 | Engenharia | Sob sobrecarga, o pool do banco esgotado responde `OVERLOADED` com `Retry-After`, e não `DATABASE_UNAVAILABLE` (achado da S34-03, ADR-03) | `backend/src/ipc_api/accounts/postgres.py`, `backend/src/ipc_api/errors.py` | Autor | 1 | — | Teste com o pool esgotado; a medição do NFR-05 no gratuito sem `DATABASE_UNAVAILABLE` |
| S35-09 | US-12 | Engenharia | Período 2027.1 criado como cópia do 2026.2 (P-22), inativo até a troca do `rulesets/ATIVO` | `rulesets/2027.1/` | Autor | 0,5 | — | Todo período do repositório carrega; 2027.1 com as permissões de 2026.2 |
| S35-10 | US-14 | Externa | Campanha de testes manuais pela equipe com o `docs/testes-manuais.md`; cada falha confirmada vira um teste automático | `docs/testes-manuais.md` | Equipe | — | — | Fichas de falha respondidas |

**Decisão da S35-06 (11/10/2026, autor):** manter só o `/health/slo` com o UptimeRobot, sem Grafana
nem `/metrics` (C8 atualizada).

**Situação (11/10/2026):** engenharia concluída. S35-01, S35-02 e S35-03 na CI (#84), com as metas
do NFR-02 e do NFR-03 medidas pela primeira vez e abertas na Q-25 (a CI usa as proteções descritas
lá até a decisão); S35-04 (canário só no banco, logs pelo painel); S35-05 (#83); S35-07 (#82);
S35-08 (#81); S35-09 (#80); S35-06 decidida. Aguardando: Q-25 (autor), S35-10 (equipe) e o primeiro
canário mensal no piloto.

**Critérios de aceite:**
1. O CI falha num PR que regride o motor mais de 20%, ou que estoura a meta do Lighthouse, ou que baixa a cobertura do motor abaixo de 90%.
2. O canário mensal roda e acha 0 ocorrências.
3. O esquema e o compilado do ruleset existem e conferem com o manifesto.

**Testes (além da base de 7.12.1):**

| Teste | Ferramenta | Comando ou workflow | Gatilho | Critério de aprovação |
|---|---|---|---|---|
| Desempenho do motor | pytest-benchmark | `ci.yml` (novo) | PR e push | P95 ≤ 50 ms por entrada e regressão ≤ 20% sobre a linha de base |
| Desempenho da página | Lighthouse CI | `ci.yml` (novo) | PR que muda `frontend/` | FCP < 1,5 s (móvel) e JS inicial ≤ 350 KB gzip |
| Cobertura por pasta | pytest-cov | `ci.yml` | PR e push | ≥ 90% no motor, ≥ 80% no resto |
| Canário em produção | pytest ou script, banco e logs | `canary.yml` (novo) | `schedule`, mensal | 0 ocorrências |
| Esquema do ruleset | JSON Schema | `ipc-rules validate` e o esquema | PR de regras | Válido |
| Regressão | base de 7.12.1 | `ci.yml` | PR e `develop` | Verde |

**Definition of Done:** a da seção 8, com os itens de benchmark e de cobertura sem [PLANEJADO].

**Riscos e bloqueios:** a variação de tempo dos runners do GitHub pode gerar falsos alarmes no benchmark (mitigação: comparar mediana de 5 rodadas). O canário nos logs depende de uma chave de API do Render, que é um secret novo, gravado pelo autor.

### 7.13 Decisões em aberto: opções para quem decide

Estas decisões não pertencem ao desenvolvedor sozinho; nada aqui as toma. Cada opção traz prós, contras e impacto no plano.

#### 7.13.1 Política dos indícios de IA (S29-04, ADR-08) — Coordenação

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Aprovar `docs/indicios-de-ia.md` como está | Liga os indícios na S33-06, depois da calibração | Exige combinar o texto aos alunos já em 2027.1 | S33-06 executável |
| B. Aprovar com mudanças no texto aos alunos ou em quem gera as referências | Ajusta à política da disciplina | Uma rodada a mais de revisão | S33-06 depois da revisão |
| C. Não ligar no piloto | Nenhum risco de leitura como prova | Perde os indícios em 2027.1 | S33-05 e S33-06 saem do plano; o código fica desligado |

**Decidido (09/10/2026):** opção A, a política aprovada como está (Q-21).

#### 7.13.2 Provedor de IA do feedback (Q-16) — Autor e Coordenação

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Sem IA (como hoje) | Nenhum dado sai do servidor; custo zero | Texto menos personalizado | Nenhuma task |
| B. Plano pago com termos de não retenção | Texto melhor, dentro da política proposta na Q-16 | Custo mensal; transferência internacional (LGPD, art. 33) a avaliar pela coordenação | S31-02 grava `IPC_LLM_*`; aviso de privacidade revisto |
| C. Plano gratuito | Sem custo | Pode usar os dados para treino; contraria a proposta da Q-16 | Não recomendado pela Q-16 |

**Decidido (09/10/2026, autor):** A e C combinadas. O feedback sem IA é o padrão; o botão "Aprimorar com IA"
manda a versão determinística a provedores gratuitos (Gemini, Groq e outros), em cadeia com fallback,
para detalhar, expandir e exemplificar. Risco aceito pelo autor e levado ao Marco 2 (Q-16). A
implementação entra na Sprint 32 (S32-11 a S32-14).

#### 7.13.3 Remetente dos e-mails (Q-17) — Autor e NTI

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Manter o Brevo com o remetente Gmail verificado | Funciona hoje, sem DNS | Risco de spam; remetente pessoal | Nenhuma mudança de código |
| B. Brevo com remetente `@cin.ufpe.br` | Remetente institucional | Exige SPF, DKIM e DMARC com o NTI | S31-07 com o NTI; `IPC_EMAIL_FROM` no Render |
| C. SMTP institucional | Sem terceiro | O plano gratuito do Render bloqueia SMTP de saída (25, 465 e 587) | Só com o Starter ou na Fase 2 |

**Decidido (09/10/2026, autor):** opção A.

#### 7.13.4 Governança das regras (Q-22) — Autor

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Manter o processo atual (merge confere a aprovação) | Simples; funciona com poucos monitores | Depende de quem faz o merge; quem tem escrita vê os workflows com segredos | Nenhuma task |
| B. Monitores com papel Read, PR por fork e um check de aprovação no CI | Fork não recebe os segredos; aprovação conferida por máquina | Mais atrito para monitores; a Q-22 pede confirmar que o GitHub permite fork de repositório pessoal privado com papel Read | Uma task de implementação depois da decisão (cerca de 3 SP) |

**Decidido (09/10/2026, autor):** opção A.

#### 7.13.5 Servidor do CIn (Q-12) — Suporte de TI do CIn

Adiada até a P-09. As perguntas estão na Q-12; a resposta desbloqueia a Sprint 41.

#### 7.13.6 Plano do Render (ADR-03) — Autor

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Ficar no gratuito | Custo zero | Com login, P95 acima de 200 ms mesmo a 30 por minuto (S28-01); o `/health/slo` vai alertar com uso | NFR-01 não atendido; risco aceito no ADR-03 |
| B. Starter (cerca de US$ 7 por mês) antes do primeiro prazo | Atende 500 por minuto com P95 de 28 ms na emulação (S28-01) | Custo mensal | S34-01 aplica e mede |
| C. Starter só nos períodos de prazo | Custo menor | Troca manual de plano e risco de esquecer | Runbook com o roteiro de troca |

**Decidido (08/10/2026, autor):** opção A, plano gratuito, sem orçamento para o Starter. A S30-09 mediu
no Render P95 do servidor abaixo de 200 ms a 20 por minuto; o pico segue com a degradação do NFR-05
(ADR-03, "Medição da S30-09 e decisão do plano").

#### 7.13.7 Observabilidade (C8) — Autor

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. `/health/slo` e UptimeRobot (como hoje) | Sem conta nova | Só a janela de 5 min; sem histórico | Nenhuma task |
| B. `/metrics` com `prometheus-client` e Grafana Cloud gratuito | Histórico e painéis | Conta nova; o `/metrics` precisa ficar fora da internet | Uma task de implementação (cerca de 3 SP) |

**Decidido (11/10/2026, autor, S35-06):** opção A: só o `/health/slo` com o UptimeRobot, sem Grafana nem `/metrics`.

#### 7.13.8 RPO do banco do piloto (NFR-20) — Autor

| Opção | Prós | Contras | Impacto |
|---|---|---|---|
| A. Backup diário | Atende o RPO de 24 h | 7 vezes mais artefatos (90 dias de retenção) e mais minutos do Actions | `cron` do `backup.yml` muda por PR |
| B. Manter semanal e revisar a NFR-20 para o piloto | Menos custo | Até 7 dias de dados de contas perdidos num desastre | NFR-20 revista, com o motivo |

**Decidido (08/10/2026, autor):** opção A, backup diário; a NFR-20 fica como está (RPO ≤ 24 h).

### 7.14 Matriz de rastreabilidade das pendências (07/10/2026, atualizada em 12/10/2026)

Criada em 07/10/2026 e atualizada em 12/10/2026 pelo CHANGELOG e pelas decisões do autor. A última coluna diz o que já foi resolvido; quando uma task fechar, o item é marcado aqui e na origem.

| Pendência original | Seção da lista de 07/10/2026 | Sprint/Task | Tipo | Situação em 12/10/2026 |
|---|---|---|---|---|
| Conta de verificação e `PILOT_CHECK_*` | 2 | S30-01 | Externa | Feito (08/10/2026) |
| Primeiro deploy com login (S11, S16, S19, S25; P-15) | 2 e 5 | S30-02 | Engenharia | Feito (08/10/2026) |
| UptimeRobot, três monitores (S11, S21) | 2 e 5 | S30-04, S34-06 | Externa | Feito (08/10/2026); a conferência para 2027.1 (S34-06) espera as datas |
| Exercício de alerta no piloto (S21; NFR-15) | 5 e 6 | S30-05, S34-04 | Engenharia | Feito; repetido a cada release (runbook) |
| Chave do backup e `BACKUP_AGE_RECIPIENT` (S28-03) | 2 | S30-06 | Externa | Feito (08/10/2026) |
| Ensaio de restauração do backup (S28-03; NFR-20) | 5 | S30-07 | Engenharia | Feito (S30-07) |
| Ensaio cronometrado do rollback (S28-03) | 2 e 5 | S30-08 | Engenharia | Feito (08/10/2026) |
| Carga no piloto de verdade (S28-01) e latência até o Supabase (Q-20) | 2, 4 e 5 | S30-09 | Engenharia | Feito (S30-09) |
| Plano Starter (ADR-03) | 2 e 3 | S30-11 (decisão), S34-01 (aplicação) | Decisão | Decidido: plano gratuito (08/10/2026); medido na S34-01 |
| P-12 (a): `X-Forwarded-For` | 4 | S30-03 | Engenharia | Resolvido (08/10/2026) |
| P-15 (a): login com cookie e feedback em até 30 s | 4 | S30-02 | Engenharia | Resolvido (08/10/2026) |
| P-15 (b): IP do cliente como penúltimo endereço | 4 | S30-03 | Engenharia | Resolvido (08/10/2026) |
| `PermissionError` do supervisord | Dívida técnica | S30-10 | Engenharia | Resolvido (08/10/2026, P-17) |
| Política dos indícios (S29-04, ADR-08) | 3 | S31-01 | Decisão | Decidido: aprovada (09/10/2026, Q-21) |
| Q-16: provedor de IA | 3 | S31-02 | Decisão | Decidido (09/10/2026) |
| Q-17: remetente dos e-mails | 3 | S31-07 | Decisão | Decidido (09/10/2026) |
| Q-22: governança das regras | 3 | S31-08 | Decisão | Decidido (09/10/2026) |
| Q-12: servidor do CIn | 3 | S41-02 | Externa | Adiada até a P-09 |
| Auditoria bloqueante (S25-01; NFR-13) | 5 e 6 | S31-03 | Engenharia | Feito (09/10/2026) |
| Semgrep (NFR-09) | 6 | S31-04 | Engenharia | Feito (09/10/2026, P-20) |
| Marco 2: guia e apresentação | 5 | S31-05 | Externa | Pendente: apresentação em 19/10/2026 |
| Formulário e planilha do critério 3 (S28-02) | 5 | S31-06 | Externa | Descartado pelo autor; a satisfação será medida com os feedbacks coletados pelo autor (Q-36, 12/10/2026) |
| Gabaritos de períodos anteriores (S20, Q-14) | 5 | S33-01 | Externa | Em parte: Listas 1 a 4 de 2026.2 carregadas; faltam as Listas 5 e 6 e os períodos anteriores |
| Calibração dos indícios (S29-03/04) e faixas (ADR-08) | 4 e 5 | S33-02 (dados), S33-03; S42-01 e S42-02 (12/10/2026) | Externa e Engenharia | Soluções anteriores a 2023 descartadas (12/10/2026); critérios e base aprovados (Q-35, 12/10/2026); calibração na S42-02 |
| Questões reais de 2027.1 (S24, R-01) | 5 | S33-04 | Externa | Perto de março de 2027, até uma semana antes de cada lista |
| Referências reais por IA (S29-02) | 5 | S33-05; S42-04 (12/10/2026) | Externa | Gerador aprovado (S33-09, 12/10/2026); na Sprint 42 |
| Ligar os indícios no piloto | 3 | S33-06; S42-05 e S42-06 (12/10/2026) | Engenharia | Sprint 42 (critérios aprovados em 12/10/2026) |
| Listas habilitadas conforme o professor | Prioridade 4 | S34-05 | Externa | Espera as datas de 2027.1 |
| Teste sintético diário (NFR-06) | 6 | S34-02 | Engenharia | Feito (11/10/2026) |
| k6 por release: NFR-04 e NFR-05 | 6 | S34-03 | Engenharia | Feito (11/10/2026) |
| Membros ativos sem o desenvolvedor (S28-02) | 4 | Premissa mantida; revista com a coordenação na S31-05 | Decisão | Premissa mantida; revisão no Marco 2 |
| Backup do Supabase gratuito (premissa) | 4 | Premissa mantida; o `backup.yml` já cobre (S30-07 ensaia) | Engenharia | Resolvido: o `backup.yml` cobre, ensaiado na S30-07 |
| RPO de 24 h da NFR-20 com backup semanal (achado de 07/10/2026) | — | S30-12 | Decisão | Decidido: backup diário (08/10/2026) |
| `pytest-benchmark` (NFR-02) | 6 | S35-01 | Engenharia | Feito (11/10/2026) |
| Lighthouse CI (NFR-03) | 6 | S35-02 | Engenharia | Feito (11/10/2026) |
| Cobertura por pasta (NFR-16) | 6 | S35-03 | Engenharia | Feito (11/10/2026) |
| Canário mensal em produção (NFR-11) | 6 | S35-04 | Engenharia | Feito (11/10/2026): só no banco, com os logs pelo painel |
| JSON Schema e `ipc-rules compile` (C6) | 6 | S35-05 | Engenharia | Feito (11/10/2026) |
| `/metrics`, Grafana e Prometheus (C8, opcionais) | 6 | S35-06 | Decisão | Decidido: só o `/health/slo` com o UptimeRobot (11/10/2026) |
| GHCR por digest, deploy por SSH e staging (Fase 2) | 6 | S41-03, S41-04 | Engenharia (bloqueada) | Bloqueado (Sprint 41) |
| Backlog de experiência e REC fora do escopo | 7 | Seção 7.1, "Backlog"; sem task | — | — |
| Comparação com o gabarito na verificação, no plágio e nos indícios (pedido do autor, 09/10/2026) | Q-24 | S32-01 a S32-10 | Externa e Engenharia | Feito (Sprint 32; 23 gabaritos no piloto em 10/10/2026) |
| Aviso da Sprint 20: repositório privado dos gabaritos | Revisão de 08/10/2026 | H-02, S33-01 | Engenharia e Externa | Feito (08/10/2026) |
| Aviso da Sprint 22: casos em aberto do mapeamento | Revisão de 08/10/2026 | H-03, S31-05, S31-12 | Externa | Casos decididos (ruleset 2026.2.5, 09/10/2026); a revisão do guia fica para o Marco 2 |
| Aviso da Sprint 24: nenhuma questão real cadastrada | Revisão de 08/10/2026 | S31-09, S31-10, S31-11, S31-13, S33-04 | Engenharia e Externa | Em parte: 3 questões em 2026.2; as de 2027.1 perto de março de 2027 |
| Aviso da Sprint 29: indícios desligados no piloto | Revisão de 08/10/2026 | S31-01, S33-02, S33-03, S33-06; Sprint 42 (12/10/2026) | Decisão, Externa e Engenharia | Sprint 42 (critérios aprovados em 12/10/2026) |
| Avisos das Sprints 11, 19, 21, 25 e 28 | Revisão de 08/10/2026 | Resolvidos (S30); README corrigido (H-01) | — | Resolvidos (S30) |

### 7.15 Tasks das Sprints 36 a 41 (plano de polimento de 11/10/2026)

Plano criado em 11/10/2026, depois da Sprint 35. A Fase 2 depende do fim do piloto: a decisão da
coordenação vem do relatório de eficácia de 2027.1 (P-09), e o servidor depende da Q-12. Por isso o
autor decidiu usar as sprints até lá para **melhorar o que existe**: rever e melhorar
funcionalidades, acrescentar o que falta e corrigir defeitos. A antiga Sprint 36 (Fase 2) passa a ser a
**Sprint 41**, com as tasks S41-01 a S41-04, como na renumeração da Q-24.

As tasks vêm da análise de 11/10/2026: revisão dos documentos, revisão do código, um tour da
interface com 41 capturas de tela (fora do repositório, em `prints-2026-10-11/`) e os achados das
Sprints 34 e 35. A ordem segue o valor e o risco:

1. **Sprint 36:** os defeitos que levam a uma conclusão errada e os documentos que a equipe usa,
   antes da campanha de testes manuais.
2. **Sprint 37:** a tela de verificação, a mais usada.
3. **Sprint 38:** explicar cada regra e exportar o resultado.
4. **Sprint 39:** qualidade interna, operação e documentação.
5. **Sprint 40:** a correção da turma inteira.

A campanha de testes manuais (S35-10) corre em paralelo. Cada falha confirmada vira uma task da
sprint seguinte, com um teste automático.

**Base comum (como em 7.12.1):**
- **Evidência de cada PR:** `scripts/ci-local.sh --e2e` até a cota do Actions voltar (P-19), e o Actions depois.
- **Release:** `scripts/release.sh NN`, com `--ci-local` enquanto durar a P-19.
- **Depois do deploy:**
  - o sintético (`scripts/sintetico-local.sh` ou o workflow);
  - o exercício de alerta (runbook);
  - uma linha nova na tabela de exercícios.
- **Vercel:** deploy só quando a página muda.
- **Render:** Manual Deploy quando o servidor muda; publica sozinho quando muda o `render.yaml`.
- **Migração:** nunca junto com uma mudança do `render.yaml` (P-18).
- **Início:** cada sprint só começa com o comando do autor.

#### Sprint 36 — Defeitos e documentos certos para a campanha de testes

**Objetivo:** corrigir os defeitos que podem levar a uma conclusão errada e deixar o guia da equipe e
a documentação fiéis ao que a ferramenta faz.

**Missão:** que a equipe comece a campanha de testes manuais sem nenhum defeito conhecido e com um
guia que diz o mesmo que o motor.

**Personas:** o monitor que corrige e compara soluções (US-11, US-31, US-37) e o monitor-mantenedor
que cuida da documentação (US-20).

**Execução:**
1. Os defeitos do plágio da turma (S36-01 e S36-02), num PR com os testes.
2. O editor (S36-03).
3. A tela de verificação (S36-04 e S36-05).
4. A medição no piloto (S36-06), que depende do deploy da release anterior.
5. A recursão só na Lista 6 (S36-09), num PR de regras.
6. Por último, a documentação (S36-07), num PR só de `.md`.

**Histórias:** US-06, US-08, US-11, US-20, US-22, US-31, US-33 e US-37.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S36-01 | US-31 | Engenharia | No "Contra a turma", identificar cada solução pela posição, e não pelo nome: com dois alunos de mesmo nome, o segundo apagava o primeiro, e "Comparar lado a lado" abria o código errado. Nomes repetidos ganham um aviso e um sufixo ("Ana (2)") | `frontend/src/pages/Plagiarism.tsx`, `frontend/src/plagiarismClass.ts` | Autor | 0,5 | — | Teste com duas "Ana": cada uma abre o próprio código lado a lado |
| S36-02 | US-31 | Engenharia | Um separador de soluções que não colide com comentários. Hoje `### calcula a média` ou `#####` dentro do código parte a solução. O separador novo é `=== nome`, que não é Python válido e nunca aparece num código. O `### nome` continua aceito numa turma sem nenhum `===`, com um aviso | `frontend/src/plagiarismClass.ts`, texto de ajuda, `docs/guia-da-equipe.md` | Autor | 1 | — | Testes com `###` e `#####` dentro do código; a ajuda e o guia mostram o formato novo |
| S36-03 | US-33 | Engenharia | No editor, Tab e Shift+Tab indentam e desindentam as linhas selecionadas. Hoje o Tab troca a seleção por 4 espaços. O componente ganha testes unitários | `frontend/src/components/CodeEditor.tsx` (+ teste) | Autor | 1 | — | Testes: Tab com 3 linhas selecionadas indenta as 3; Shift+Tab desfaz; Esc e Tab continuam saindo do editor |
| S36-04 | US-37 | Engenharia | Na comparação com o gabarito, os nomes das construções em português ("atribuição", "comparação", "conta aritmética", "laço"), com o termo técnico na dica. Hoje aparecem "Assign", "Compare" e "BinOp" | `backend/src/ipc_analyzer/engine/gabarito.py` ou um mapa no frontend, `frontend/src/components/` | Autor | 0,5 | — | Nenhum nome de nó do `ast` na tela; teste com o mapa completo |
| S36-05 | US-11 | Engenharia | O Verificar mostra "Verificando…" e um Cancelar, como o Plágio e o Feedback. O seletor de Questão deixa de cortar o texto: rótulo curto no seletor e a descrição abaixo dele | `frontend/src/pages/Checker.tsx` | Autor | 0,5 | — | Teste do estado de espera e do cancelamento; o seletor cabe na largura do computador e do celular |
| S36-06 | US-22 | Engenharia | Medir no piloto (0,1 CPU) a análise da entrada de 50 KB do benchmark, pela conta de verificação e pelo `Server-Timing`. Se passar de 1 s, subir o `IPC_TIMEOUT_S` do analisador no `render.yaml`, com folga até o prazo da API, ou limitar o tamanho no piloto | ADR-03, `render.yaml` se preciso | Autor | 0,5 | Deploy da release anterior | Tempo registrado no ADR-03; nenhum 422 por prazo para entradas legítimas de até 50 KB |
| S36-07 | US-20 | Engenharia | Documentação fiel ao que existe. Ver a lista logo abaixo da tabela | `docs/`, `deploy/piloto.md`, `README.md` | Autor | 1,5 | — | Os achados da revisão de 11/10/2026 resolvidos; o guia diz o mesmo que o motor nos cenários do roteiro |
| S36-08 | US-11 | Externa | Campanha de testes manuais pela equipe, com `docs/testes-manuais.md` (continua a S35-10). Cada falha confirmada vira task, com teste | Fichas de falha | Equipe | — | S36-07 | Fichas respondidas; falhas viram tasks na Sprint 37 |
| S36-09 | US-06, US-08 | Engenharia | Recursão só na Lista 6 (Q-33, decisão do autor de 12/10/2026): uma função que chama a si mesma, direta ou mutuamente (C-03), passa a ser "Fora da lista" nas Listas 4 e 5, liberada a partir da 6; as outras formas de função continuam permitidas desde a 4. O `derived:recursion` sai dos fatos estruturais e passa a ser permitido a partir da Lista 6 pela regra da recursão (de preferência com o ID da R-68, sem criar ID fora do catálogo); o comentário da R-59, a seção 5.2.3 e a matriz de mapeamento acompanham. Rulesets de 2026.2 e de 2027.1 numa versão nova, com o de acordo do professor (DoD) | `rulesets/*/base.yaml`, `engine/policy.py` (se preciso), `backend/tests/golden/`, `docs/mapping-R-xx.md` | Autor | 1 | — | Pelo menos 3 casos golden (recursão na Lista 6 permitida, recursão direta na Lista 4 e mútua na Lista 5 "Fora da lista"), com 0 FP e 0 FN; os gabaritos das Listas 4 e 5 de 2026.2 seguem sem violação, ou o caso vai ao autor |

**O que a S36-07 corrige:**
- **Guia da equipe:**
  - o `split()` comprova a Lista 3;
  - vários nomes no `for` valem com qualquer sequência a partir da Lista 3;
  - entram os casos do Marco 2 (expressão geradora, `if __name__`, argumentos nomeados, `start=` e `dict(a=1)`), a política dos indícios aprovada e o "montado sem IA" como padrão.
- **`deploy/piloto.md`:**
  - o proxy com 4 saltos e o cabeçalho `Forwarded`;
  - o plano gratuito e o backup diário;
  - as variáveis novas: `IPC_LLM_CHAIN`, `IPC_EDGE_SECRET` e `IPC_GABARITOS_TOKEN`.
- **Roteiro de testes:** a release `sprint-35`.
- **Blueprint:**
  - o status dos ADRs 04, 08 e 11;
  - os restos da Q-25 e das listas "só a 1";
  - os caminhos que não existem mais;
  - os marcadores [PLANEJADO] e [A CONFIRMAR] já resolvidos.
- **`RULES.md`:** a Q-22 decidida.
- **Benchmark:** o docstring com a meta nova do NFR-02.

**ADRs:** atualiza o ADR-03 (S36-06); corrige o status dos ADRs 04, 08 e 11 (S36-07).

**Critérios de aceite:**
1. "Contra a turma" abre sempre a solução certa e não parte código com `###`.
2. O editor indenta e desindenta blocos.
3. Nenhum termo técnico em inglês na comparação com o gabarito.
4. O tempo de 50 KB no piloto está medido.
5. O guia e a documentação passam na conferência da revisão.
6. Uma função recursiva na Lista 4 ou na 5 aparece como "Fora da lista", liberada na Lista 6 (Q-33).

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Turma com nomes repetidos e com `###` no código | Vitest (`plagiarismClass`, `Plagiarism`) e e2e `plagiarism-tree.spec.ts` | PR | Cada nome abre a própria solução; nenhuma solução partida |
| Tab e Shift+Tab | Vitest (`CodeEditor`) | PR | Indenta e desindenta as linhas selecionadas |
| Nomes das construções | pytest ou Vitest | PR | Mapa completo, sem termo do `ast` na tela |
| Verificando e Cancelar | Vitest (`Checker`) | PR | Estado de espera e cancelamento |
| Tempo de 50 KB no piloto | `Server-Timing` pela conta de verificação | Depois do deploy | Registrado no ADR-03 |
| Recursão só na Lista 6 | pytest golden e `official_answers` | PR | 0 FP e 0 FN; gabaritos sem violação |
| Regressão | base de 7.12.1 (27 etapas) | PR e `develop` | Verde |

**Deploy:** release `sprint-36`.
- **Vercel:** sim, porque a página muda (S36-01 a S36-05), com **Create Deployment > main**.
- **Render:** Manual Deploy, porque o ruleset muda (S36-09) e talvez o analisador (S36-04); publica sozinho se a S36-06 mudar o `render.yaml`. Sem migração.
- **Depois:** sintético e exercício de alerta.

**Riscos:** o separador novo muda um hábito da equipe; por isso o `### nome` continua aceito, com aviso.

#### Sprint 37 — Verificação mais clara

**Objetivo:** tornar a tela de verificação mais rápida de ler e de usar, no computador e no celular, e
dar à ferramenta uma identidade visual simples.

**Missão:** que o monitor, corrigindo dezenas de soluções seguidas, entenda o resultado num olhar,
sem rolar a página e sem perder o código de vista.

**Personas:** o monitor em correção em lote (US-33), no computador e no celular (US-21).

**Execução:**
1. O resumo e os cartões (S37-01) e os componentes comuns (S37-03), que o resto usa.
2. O editor fixo e as abas do celular (S37-02).
3. A tela inicial e o cabeçalho (S37-04).
4. As preferências (S37-05).
5. As capturas de antes e depois vão no PR (o roteiro de capturas entra em `scripts/`).

**Histórias:** US-09, US-11, US-21 e US-33.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S37-01 | US-09 | Engenharia | Resumo do resultado por categoria, com contadores clicáveis que filtram os cartões. Cada regra num cartão que abre e fecha, aberto por padrão até 5 regras. O trecho de código com a linha destacada | `frontend/src/components/ResultPanel.tsx` | Autor | 1,5 | — | Sete violações cabem numa tela de 900 px com os cartões fechados; teste dos filtros |
| S37-02 | US-33, US-21 | Engenharia | No computador, o editor fica fixo na tela (`position: sticky`) enquanto o resultado rola, e clicar numa linha continua selecionando o trecho. No celular, abas "Resultado", "Indícios" e "Feedback" e um botão "Voltar ao código" | `frontend/src/pages/Checker.tsx` | Autor | 1,5 | S37-01 | No celular, o resultado das 7 violações cabe em até 2 telas; e2e de layout verde com o axe |
| S37-03 | US-21 | Engenharia | Componentes comuns (`Button`, `Card`, `LineChip`, `SyntaxErrorBox`) no lugar das cópias de `ResultPanel`, `Plagiarism`, `IndicatorsPanel` e `FeedbackPanel`. No Gerenciar, os botões com foco visível e alvo de 44 px, e as tabelas que rolam no celular | `frontend/src/components/`, `frontend/src/pages/Admin.tsx` | Autor | 1 | — | Nenhuma classe de botão repetida; axe sem violações no Gerenciar |
| S37-04 | US-11 | Engenharia | Identidade visual simples: um logotipo em SVG e a cor da marca. A tela inicial explica Verificar, Plágio e Feedback em três blocos. O cabeçalho mostra o primeiro nome, com um menu da conta (Perfil e Sair). A área "Soluções da turma" ganha numeração de linhas | `frontend/src/pages/Landing.tsx`, `frontend/src/components/AppHeader.tsx`, `frontend/public/` | Autor | 1 | — | Capturas aprovadas pelo autor; nada novo no JS inicial além do SVG |
| S37-05 | US-33 | Engenharia | Preferências e atalhos. Tema claro, escuro ou do sistema, salvo neste navegador. O rascunho do editor sobrevive ao F5 (`sessionStorage`; o Sair continua apagando). Alt+N para "Próximo aluno" e Ctrl+Shift+C para copiar o feedback, com uma ajuda dos atalhos | `frontend/src/`, `docs/guia-da-equipe.md` | Autor | 1 | — | Testes do tema, do rascunho e dos atalhos; o guia atualizado |

**ADRs:** nenhum.

**Critérios de aceite:**
1. O resultado de 7 violações cabe numa tela no computador e em 2 no celular.
2. O código fica à vista enquanto o resultado rola.
3. Nenhuma violação do axe.
4. Lighthouse dentro da meta (FCP ≤ 1,65 s; Q-25), e o JS inicial ≤ 350 KB com gzip.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Resumo, filtros e cartões | Vitest | PR | Contadores e filtros corretos |
| Layout no celular e no computador | Playwright `layout.spec.ts` com o axe | PR | Sem rolagem lateral e sem violação |
| Tema, rascunho e atalhos | Vitest | PR | Preferência salva; rascunho volta depois do F5 e some no Sair |
| Desempenho da página | Lighthouse e `js-budget.mjs` | PR | FCP ≤ 1,65 s; JS ≤ 350 KB |
| Capturas de antes e depois | Roteiro de capturas | PR | Anexadas ao PR |

**Deploy:** release `sprint-37`.
- **Vercel:** sim, só a página muda.
- **Render:** não precisa.
- **Depois:** sintético e exercício de alerta.

**Riscos:** mudança visual grande; mitigada pelas capturas de antes e depois e pela aprovação do autor.

#### Sprint 38 — Explicar cada regra e exportar o resultado

**Objetivo:** cada violação passa a dizer por que a construção é proibida e o que usar no lugar, o
feedback sem IA aproveita isso, e o resultado pode ser exportado e o código carregado de um arquivo.

**Missão:** que o monitor explique a violação ao aluno sem reler o documento de permissões, e que o
feedback sem IA seja bom o bastante para dispensar o "Aprimorar com IA" na maioria dos casos.

**Personas:** o monitor que dá o feedback (US-32) e o professor que mantém as regras (US-12).

**Execução:**
1. Os campos novos do ruleset (S38-01), com os textos revisados por um monitor-chefe ou professor.
2. O feedback (S38-02).
3. Exportar e carregar arquivo (S38-03).
4. O feedback sem nova análise (S38-04) e o desempenho da extração de fatos (S38-05).

**Histórias:** US-02, US-08, US-10, US-12, US-22, US-32 e US-33.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S38-01 | US-10, US-08 | Engenharia | Explicação de cada regra: campos `explicacao` (por que é proibida) e `alternativa` (o que usar nesta lista) no `base.yaml`, mostrados no cartão da violação. Os textos saem do documento de permissões, sem inventar regra; quem revisa é um monitor-chefe, um professor ou o desenvolvedor (Q-31). Rulesets `2026.2.6` e `2027.1.1` | `rulesets/*/base.yaml`, `engine/ruleset.py`, esquema JSON (S35-05), `ResultPanel.tsx` | Autor e revisor | 2 | — | Todas as regras com os dois campos; esquema e golden verdes; revisão registrada no PR |
| S38-02 | US-32 | Engenharia | O feedback sem IA usa a explicação e a alternativa de cada regra violada | `engine/feedback.py` | Autor | 1 | S38-01 | Testes do texto montado; a frase obrigatória e o `[ALUNO]` inalterados |
| S38-03 | US-02, US-33 | Engenharia | Carregar um `.py` no editor (botão e arrastar; UTF-8 de até 50 KB). Exportar o relatório: copiar como texto e baixar um `.txt` com a lista, a questão, as regras e as linhas. Nada é guardado | `frontend/src/pages/Checker.tsx`, `ResultPanel.tsx` | Autor | 1 | — | Testes de arquivo grande demais, de encoding errado e do texto exportado |
| S38-04 | US-32, US-22 | Engenharia | O feedback deixa de reanalisar o código: a API guarda em memória, por 10 min, só o resultado (nunca o código), pela chave do hash do código, da lista e da questão. "Gerar" e "Aprimorar" reaproveitam o resultado; sem ele, a API analisa como hoje | `ipc_api/routes/feedback.py`, um cache com limite de itens | Autor | 1,5 | — | Teste: o segundo "Gerar" não chama o analisador; nenhum código no cache |
| S38-05 | US-22 | Engenharia | Desempenho da extração de fatos: o `SourceMap.column` deixa de converter a linha a cada fato (atalho para linha ASCII e tabela por linha). A linha de base do benchmark é regravada | `engine/facts/model.py`, `tests/benchmark` | Autor | 0,5 | — | O benchmark mostra o ganho; nenhuma coluna diferente no golden |

**ADRs:** nenhum; o FR-30 (feedback) ganha a explicação da regra.

**Critérios de aceite:**
1. Toda violação mostra o porquê e a alternativa.
2. O feedback sem IA usa esses textos.
3. Dá para exportar o relatório e carregar um `.py`.
4. "Gerar" e "Aprimorar" não reanalisam o código.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Campos novos do ruleset | `ipc-rules validate`, esquema JSON e golden | PR | Todas as regras com os dois campos |
| Texto do feedback | pytest (`test_feedback_engine.py`) | PR | Usa a explicação; frase obrigatória e `[ALUNO]` mantidos |
| Exportar e carregar | Vitest e e2e | PR | Texto exportado correto; limites do arquivo |
| Cache do feedback | pytest | PR | O segundo pedido não chama o analisador; o cache não guarda código |
| Desempenho | benchmark (S35-01) | PR | Ganho registrado; linha de base nova |

**Deploy:** release `sprint-38`, com o ruleset novo.
- **Render:** Manual Deploy (o analisador e a API mudam).
- **Vercel:** Create Deployment (a página muda). Sem migração.
- **Depois:** sintético e exercício de alerta.

**Riscos:** os textos de explicação precisam de revisão de quem conhece o documento de permissões; sem
ela, a task fica aguardando, e o resto da sprint segue.

#### Sprint 39 — Qualidade interna, operação e documentação

**Objetivo:** reduzir o custo de manter o projeto: arquivos menores, testes mais rápidos e completos,
backup automático e restauração ensaiada, e a documentação reorganizada para quem chega.

**Missão:** que o próximo monitor-mantenedor assuma o projeto sem depender do autor.

**Persona:** o monitor-mantenedor (US-20, US-35).

**Execução:**
1. Os testes que faltam (S39-03), antes das refatorações.
2. As refatorações do frontend e do backend (S39-01 e S39-02), cada uma num PR, sem mudar comportamento.
3. A operação (S39-04).
4. A documentação (S39-05), num PR só de `.md`.

**Histórias:** US-14, US-15, US-20 e US-35.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S39-01 | US-20 | Engenharia | Frontend em arquivos menores. `Plagiarism.tsx` (511 linhas) vira os modos "Dois códigos" e "Contra a turma" e os resultados em arquivos próprios. `Admin.tsx` (420) ganha as tabelas em componentes. O `parseClass` da turma deixa de rodar a cada tecla (`useMemo`) | `frontend/src/pages/` | Autor | 1,5 | S39-03 | Nenhum arquivo de página com mais de 300 linhas; os mesmos testes verdes |
| S39-02 | US-14, US-20 | Engenharia | Backend em módulos menores. As listas de palavras dos indícios (cerca de 180 linhas de `indicators.py`) vão para um arquivo de dados. O `ruleset.py` se divide em esquema, compilação e carga. Os DTOs saem do `service/app.py` para `service/schemas.py` | `backend/src/ipc_analyzer/` | Autor | 1,5 | S39-03 | Import-linter e testes verdes; nenhum módulo com mais de 500 linhas |
| S39-03 | US-15, US-20 | Engenharia | Os testes que faltam: `Login`, `Register`, `Profile`, `Verify`, `ForgotPassword` e `Landing` no Vitest. Os testes lentos ganham o marcador `slow`, e as esperas reais viram eventos ou relógio injetado. `pytest-xdist` nos testes sem banco | `frontend/src/pages/*.test.tsx`, `backend/tests/`, `backend/pyproject.toml` | Autor | 1,5 | — | Cobertura das páginas ≥ 80%; a etapa de pytest da CI local ≥ 30% mais rápida |
| S39-04 | US-35 | Engenharia | Operação. O `scripts/backup-local.sh` agendado no Agendador de Tarefas do Windows (o backup do Actions volta com a cota). Um ensaio de restauração completo num PostgreSQL descartável, comparando as contagens. A troca do token dos gabaritos agendada antes de vencer | `scripts/`, `docs/runbook.md` | Autor | 0,5 | — | Restauração ensaiada com o tempo no runbook; tarefa agendada documentada |
| S39-05 | US-20 | Engenharia | Documentação reorganizada. Ver a lista logo abaixo da tabela | `docs/` | Autor | 1 | S36-07 | O blueprint com menos de 1.000 linhas; os documentos novos no mapa (`docs/README.md`) |

**O que a S39-05 reorganiza:**
- O histórico das tasks das Sprints 1 a 35 sai do blueprint para `docs/historico/`.
- O `decisoes.md` ganha uma tabela-resumo (ID, situação, data e uma frase) e uma seção por ID.
- Documentos novos:
  - um glossário (R-xx, P/C/Q/REC, Snn-mm, FR/NFR/US, fato, faixa, contenção);
  - uma página única de estado e pendências;
  - um FAQ do mantenedor (habilitar lista, trocar de período, gabarito novo e reinício do Render);
  - a agenda das rotinas (backup, sintético, canário, auditoria, rollback, restauração, vencimento do token);
  - quem cuida de cada conta (Render, Vercel, Supabase, Brevo, UptimeRobot, gabaritos, chaves das IAs).
- O índice de sintomas do runbook ganha os gabaritos indisponíveis, o "Aprimorar com IA" sem cota e a falha do sintético ou do canário.

**ADRs:** nenhum.

**Critérios de aceite:**
1. Nenhum arquivo de página com mais de 300 linhas e nenhum módulo do backend com mais de 500.
2. As páginas sem teste agora têm teste.
3. A CI local mais rápida.
4. Backup agendado e restauração ensaiada.
5. Documentação reorganizada e no mapa.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Testes novos das páginas | Vitest | PR | Verdes; cobertura das páginas ≥ 80% |
| Refatorações | toda a base de 7.12.1 | PR | Nada muda de comportamento |
| Restauração | `pg_restore` num PostgreSQL descartável e `contagens.sql` | Uma vez | Contagens iguais; tempo no runbook |
| Tempo da CI | `ci-local.sh` | PR | Etapa de pytest ≥ 30% mais rápida |

**Deploy:** release `sprint-39`.
- **Render:** Manual Deploy (o backend é refatorado, sem mudar comportamento).
- **Vercel:** Create Deployment (a página é refatorada). Sem migração.
- **Depois:** sintético, exercício de alerta e o roteiro de testes manuais na parte do plágio e do gerenciamento.

**Riscos:** refatorar sem mudar comportamento exige os testes primeiro (S39-03), por isso eles vêm antes.

#### Sprint 40 — A correção da turma inteira

**Objetivo:** corrigir e comparar uma turma inteira de uma vez, sem colar solução por solução.

**Missão:** que o monitor receba as soluções de uma lista (do Dikastis ou de uma pasta) e veja, numa
tabela, o status de cada aluno e os grupos de soluções parecidas.

**Personas:** o monitor em correção em lote (US-33) e o professor que acompanha a lista (US-16).

**Execução:**
1. Correção em lote por upload (S40-01), com os limites de tamanho e de quantidade primeiro.
2. Plágio todos contra todos (S40-02), reaproveitando o `compare_class`.
3. O painel por lista para os professores (S40-03), a partir da telemetria anônima.

**Histórias:** US-16, US-31 e US-33.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S40-01 | US-33 | Engenharia | Correção em lote por upload: vários `.py` ou um `.zip` (até 100 arquivos, 50 KB cada e 2 MB no total, com proteção contra zip bomb). Uma tabela com aluno (nome do arquivo), status, violações por categoria e semelhança com o gabarito, e exportação em CSV. Nada é guardado, e cada análise passa pelos mesmos limites e pela admissão | Rota nova `POST /api/v1/validate/batch`, `frontend/src/pages/` (tela nova), OpenAPI | Autor | 3 | S38-03 | Testes de limites e de zip malicioso; e2e com 10 arquivos; contrato OpenAPI atualizado |
| S40-02 | US-31 | Engenharia | Plágio todos contra todos: os pares ordenados pela semelhança e grupos de soluções parecidas (componentes acima da faixa "Requer atenção"), com o peso pela raridade (IDF) da turma | `engine/similarity.py`, rota `POST /api/v1/similarity/class-matrix`, `Plagiarism.tsx` | Autor | 2 | — | Testes com uma turma sintética de 30 soluções (dois grupos de cópias e o resto independente); o tempo dentro do orçamento |
| S40-03 | US-16 | Engenharia | Painel por lista para professores e monitores-chefes: as regras mais violadas por lista e período, a partir das views anônimas da telemetria (`v_top_rules_by_list`), sem dado de aluno | Rota de leitura, tela no Gerenciar | Autor | 1 | — | Só professores, monitores-chefes e o desenvolvedor veem; nenhum dado pessoal |

**ADRs:** atualiza o ADR-07 (todos contra todos) e o ADR-04 (rota nova de lote, com os limites).

**Critérios de aceite:**
1. Uma turma de 100 soluções é corrigida e exportada em CSV.
2. O todos contra todos acha os dois grupos de cópias da turma sintética.
3. O painel por lista mostra só dados anônimos.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Limites do lote | pytest e suíte de segurança | PR | Zip bomb, arquivo grande, encoding errado e quantidade acima do limite recusados |
| Tabela e CSV | Vitest e e2e | PR | CSV correto, sem código dentro |
| Todos contra todos | pytest com a turma sintética | PR | Dois grupos achados; tempo no orçamento |
| Painel por lista | pytest e e2e | PR | Só os cargos certos; sem dado pessoal |
| Carga | `run_load.py` com o lote | Uma vez | Admissão funciona, sem 500 |

**Deploy:** release `sprint-40`.
- **Render:** Manual Deploy (rotas novas e analisador).
- **Vercel:** Create Deployment (tela nova). Sem migração, se as views existentes bastarem.
- **Depois:** sintético e exercício de alerta.

**Riscos:**
- O lote concentra muita análise de uma vez no plano gratuito (0,1 CPU); a admissão e os limites protegem o serviço, e a tela mostra o progresso.
- Uma lista grande pode levar minutos; a tela permite cancelar.

#### Sprint 41 — Fase 2: imagens no GHCR, deploy pelo servidor do CIn e staging (bloqueada)

Era a Sprint 36 do plano de 07/10/2026, renumerada em 11/10/2026 (as tasks S36-01 a S36-04 passaram a S41-01 a S41-04).

**Objetivo:** preparar a Fase 2 da ADR-03, só se a P-09 for atingida e a Q-12 for respondida pelo suporte de TI do CIn: imagens publicadas no GHCR por digest, deploy *pull-based* no servidor do CIn e um ambiente de staging.

**Missão, persona e execução:** a missão é preparar a Fase 2 no servidor do CIn, só se a P-09 for atingida e a Q-12 respondida. As personas são o monitor-mantenedor e o suporte de TI do CIn (US-20, US-23). Execução: as decisões S41-01 e S41-02 primeiro; só então o GHCR e o deploy (S41-03, S41-04).

**Premissas:** P-09 (critérios de eficácia), Q-12 (requisitos do CIn), ADR-03 (Fase 2).

**Histórias:** US-20 e US-23 (seção 4).

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S41-01 | US-23 | Decisão | Migrar ou não para o servidor do CIn, com o relatório de eficácia de 2027.1 (P-09, `docs/eficacia.md`) | `docs/eficacia.md`, ADR-03 | Coordenação | — | Fim de 2027.1 | Desbloqueio: decisão registrada na P-09 |
| S41-02 | US-20 | Externa | Q-12: o suporte de TI do CIn responde Docker, porta 443, subdomínio e TLS, saída para o PostgreSQL gerenciado e quem administra o sistema | `docs/decisoes.md` (Q-12) | TI do CIn | — | S41-01 | Desbloqueio: Q-12 respondida por escrito |
| S41-03 | US-20 | Engenharia | Publicar as imagens no GHCR com a tag igual ao SHA e referenciá-las por digest no compose | `.github/workflows/ci.yml`, `deploy/compose.yaml` | Autor | 2 | S41-01 | `docker compose pull` com digests; o item do GHCR da seção 8 sem [PLANEJADO] |
| S41-04 | US-20 | Engenharia | Deploy *pull-based* no servidor do CIn e ambiente de staging, com o mesmo `/ready` e as verificações de `tests/pilot` apontadas para lá | `deploy/` (novo roteiro), `.github/workflows/deploy.yml` | Autor | 3 | S41-02, S41-03 | Staging e produção verdes nas verificações; rollback ≤ 5 min ensaiado no servidor |

**ADRs:** atualiza o ADR-03 (Fase 2).

**Critérios de aceite:**
1. As imagens são publicadas por digest.
2. Staging e produção passam nas mesmas verificações do piloto.
3. O rollback no servidor leva ≤ 5 min.

**Testes:** a base de 7.12.1; as verificações de `tests/pilot` apontadas para o staging e a produção; o ensaio de rollback e a restauração do backup no servidor; a suíte de isolamento do NFR-07 no compose do servidor.

**Definition of Done:** a da seção 8, com os itens de implantação da Fase 2 sem [PLANEJADO].

**Riscos e bloqueios:** a sprint inteira está bloqueada pela P-09 e pela Q-12 e só é detalhada depois do piloto.

### 7.16 Tasks das Sprints 42 a 48 (proposta de 12/10/2026: indícios de IA, período, feedback, plágio, acompanhamento e Google)

Proposta criada em 12/10/2026 a partir da revisão técnica das seis frentes pedidas pelo autor
([`revisao-seis-frentes.md`](revisao-seis-frentes.md)): o período da turma, a qualidade do
feedback, os indícios de uso de IA, o plágio, os alunos sob responsabilidade de cada monitor e os
grupos de monitores. A revisão mapeou o código atual com `caminho:linha`; esta seção traz só o
plano. A Sprint 42, a ligação dos indícios de IA no piloto, entrou a pedido do autor no mesmo
dia. Nenhuma destas sprints começa sem o comando do autor.

**Por que é uma fase nova (Fase 1g):** até aqui o IP-Checker não guarda nada sobre alunos (NFR-11,
REC-07). As Sprints 42 a 46 continuam sem guardar dados de alunos. A 47 cria a primeira
persistência de dados pessoais de alunos, só com o resultado resumido de cada verificação (Q-26 a
Q-29, decididas em 12/10/2026), e só vai ao piloto com o aviso de privacidade aprovado pela
coordenação. A 48, a entrada com o Google no piloto, fica no fim da fila (decisão de 12/10/2026).

**Ordem sugerida, intercalada com o plano de polimento (7.15):** 36 → 37 → 38 → **42** → **43** → **44** →
39 → 40 → **46** → **45** → **47** → **48**, com a 41 (Fase 2) quando a P-09 e a Q-12 permitirem.
A 42 começa assim que houver o corpus de calibração ou a resposta da Q-35 e pode correr em
paralelo com as outras, porque toca poucos arquivos. A 43 vem antes da 39 para que a refatoração de `Checker.tsx` e `Plagiarism.tsx` já inclua o
seletor de período; a 44 depende da S38-01 e da S38-02; a 46 depende da S40-02.

**Base comum:** a mesma de 7.15 (evidência por `ci-local.sh --e2e` enquanto durar a P-19, release
por `scripts/release.sh NN`, sintético e exercício de alerta depois do deploy, migração nunca junto
com o `render.yaml`, P-18).

**Decisões do plano:** respostas do autor em 12/10/2026, registradas em [`decisoes.md`](decisoes.md).

| Decisão | Resposta | Sprints |
|---|---|---|
| Q-26: identificador do aluno | O nome de exibição e, opcionalmente, o login do Dikastis; nunca CPF, e-mail ou matrícula | 47 |
| Q-27: o que guardar | Só o resultado resumido, como "L3-Q1 anulada por Laços de repetição" ou "L4-Q2 validada"; nada do código (a ADR-14 foi rejeitada) | 47 |
| Q-28: feedback no histórico | Não | 47 |
| Q-29: retenção | Ao encerrar o período ou 12 meses depois do fim dele, o que vier primeiro | 43 e 47 |
| Q-30: regra no feedback | Só o nome da regra | 44 |
| Q-31: quem revisa o estilo e os textos das regras | Um monitor-chefe, um professor ou o desenvolvedor | 38 e 44 |
| Q-32: metas do plágio | Revocação ≥ 95% na faixa de 90%; precisão de 100% na de 95% e ≥ 90% na de 90% | 46 |
| Q-33: leituras do documento de permissões | Recursão só na Lista 6; só o literal `None` anula; `in`, `pop()` e `copy()` em tuplas e dicionários seguem as listas desses tipos | 36 (S36-09) |
| Q-34: janela de períodos | O ativo e os 5 anteriores | 43 |
| Q-35: critérios dos indícios de IA | Os critérios propostos, com a repetição no máximo média, dois marcadores novos e a calibração pelos gabaritos e por soluções novas geradas por IA | 42 |
| Q-36: satisfação sem o formulário | O autor mede no futuro, com os feedbacks da equipe coletados manualmente | Eficácia (P-09) |
| S33-09: gerador de referências por IA | Aprovado, com revisão de quem cadastra | 42 |

#### Sprint 42 — Indícios de IA ligados no piloto (incluída a pedido do autor em 12/10/2026)

**Objetivo:** que a equipe veja os indícios de uso de IA no piloto, calibrados, com a política já
aprovada (Q-21, 7.13.1, opção A).

**Missão:** que o monitor decida com quem conversar a partir de evidências ancoradas no documento
de permissões, sem que o painel possa ser lido como prova.

**Personas:** o membro da equipe que corrige e conversa com o aluno (US-34), a coordenação, dona da
política, e o monitor-mantenedor que calibra.

**Por que agora e o que a bloqueia:** o código está pronto desde a Sprint 29 e a política foi
aprovada em 09/10/2026. A política pedia a calibração com soluções humanas anteriores a 2023
(S33-02), mas o autor a descartou em 12/10/2026: essas soluções não existem e não serão buscadas.
Esta sprint reúne o que faltava da Sprint 33 (S33-03, S33-05, S33-06 e o gerador da S33-09,
aprovado em 12/10/2026) e acrescenta uma ligação gradual por cargo. Os critérios dos indícios e a
nova base de calibração foram aprovados pelo autor em 12/10/2026 (Q-35).

**Execução:**
1. Os critérios e a base de calibração validados pelo autor (S42-01, Q-35).
2. A calibração (S42-02) e, em paralelo, a evidência e a confiança em cada indício (S42-03).
3. As referências por IA das questões cadastradas (S42-04), que não bloqueiam a ligação: sem elas,
   o sinal de referência fica inerte e os outros funcionam.
4. A ligação gradual (S42-05): primeiro a chefia (desenvolvedor, professores e monitores-chefes),
   por uma lista; depois a equipe toda (S42-06).
5. O guia, o registro de casos e o runbook (S42-07).

**Histórias:** US-34.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S42-01 | US-34 | Decisão | Validar os critérios dos indícios e a base de calibração sem as soluções anteriores a 2023 (Q-35): os gabaritos da equipe para os alarmes falsos e soluções novas geradas por IA, diferentes das referências, para os acertos | `docs/indicios-de-ia.md`, ADR-08 | Autor | — | Q-35 | Feito em 12/10/2026 (Q-35): critérios e metas aprovados e registrados em `docs/indicios-de-ia.md`; pelo menos 200 soluções no total, entre gabaritos e soluções geradas por IA (premissa validada pelo autor em 12/10/2026) |
| S42-02 | US-34 | Engenharia | Calibração (era a S33-03): `ipc-rules calibrate` na base da S42-01, em cada período carregado; faixas de `engine/indicators.py` ajustadas por PR até as metas; a distribuição registrada no ADR-08 | `cli.py`, `engine/indicators.py`, ADR-08 | Autor | 2 | S42-01 | Nenhum gabarito na faixa alta e as metas de acerto da S42-01 cumpridas; `test_indicators.py` com as faixas novas |
| S42-03 | US-34 | Engenharia | Os critérios aprovados na Q-35: a repetição da mesma proibição passa a ir no máximo à faixa média, e entram dois marcadores sem faixa (texto dentro do `input()` e validação de entrada que o enunciado não pede). Cada indício passa a trazer a evidência (regra, linhas e um trecho de até 120 caracteres) e a confiança (baixa, média ou alta); o painel ganha um teste de vocabulário que recusa "prova", "veredito", "plagiou" e "usou IA" como afirmação | `engine/indicators.py`, `IndicatorsPanel.tsx`, OpenAPI | Autor | 2 | — | pytest e Vitest; contrato atualizado |
| S42-04 | US-34 | Engenharia e equipe | Referências por IA das questões cadastradas (era a S33-05), geradas a partir do enunciado pela cadeia do "Aprimorar com IA" (gerador da S33-09, aprovado em 12/10/2026) e revisadas por quem cadastra; as de 2027.1 saem com as questões, perto de março de 2027 | `cli.py`, `rulesets/<período>/referencias/` | Autor e equipe | 1 | S33-04 | `ipc-rules validate` mostra as referências em todas as questões cadastradas |
| S42-05 | US-34 | Engenharia | Ligação gradual: `IPC_AI_INDICATORS` aceita `0` (desligado), `chefia` (desenvolvedor, professores e monitores-chefes) e `1` (toda a equipe); a API só calcula e devolve o painel para os cargos ligados, e `/api/v1/auth/options` informa a cada conta se ela o vê | `settings.py`, `routes/validate.py`, `routes/auth.py`, `test_indicators_api.py` | Autor | 1 | — | Matriz cargo × valor testada por chamada direta; o feedback continua sem indícios |
| S42-06 | US-34 | Engenharia | Ligar no piloto (era a S33-06): um PR com `IPC_AI_INDICATORS: chefia` no `render.yaml`, a variável `PILOT_AI_INDICATORS` e o teste do piloto; depois de uma lista com o registro de casos, outro PR com `1` | `render.yaml`, `.github/workflows/deploy.yml`, `backend/tests/pilot/` | Autor | 0,5 | S42-02, S42-05 | Painel visível numa verificação com a conta de verificação; o sintético e o exercício de alerta depois de cada deploy |
| S42-07 | US-34 | Documentação | Guia da equipe (como ler o painel e conduzir a conversa, com as perguntas sugeridas), como a chefia registra, sem nome nem matrícula, os casos confirmados e descartados (sem a planilha, descartada em 12/10/2026), o runbook (desligar pela variável no Render, sem deploy de código) e o status da ADR-08 e de `docs/indicios-de-ia.md` | docs | Autor | 1 | — | Revisão pela coordenação |

**ADRs:** ADR-08 (status: ligado no piloto, com a calibração registrada).

**Critérios de aceite:**
1. Nenhum gabarito da equipe fica na faixa alta, e as metas de acerto validadas na Q-35 são cumpridas.
2. Com `chefia`, um monitor não recebe o painel, e um monitor-chefe recebe.
3. Com `1`, toda a equipe recebe o painel, e o feedback nunca leva os indícios.
4. Cada indício mostra a regra, as linhas, o trecho e a confiança, com o aviso de que não é prova.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Calibração | `ipc-rules calibrate` | À mão, a cada período | Sai com 0; a saída nunca mostra código |
| Ligação por cargo | pytest (matriz) | PR | `0`, `chefia` e `1` com o painel certo para cada cargo |
| Evidência e vocabulário | pytest e Vitest | PR | Todo indício com evidência; nenhum termo de veredito |
| Piloto | `tests/pilot` com `PILOT_AI_INDICATORS` | Depois do deploy | `ai_indicators` igual ao esperado |

**Deploy:** release `sprint-42`. A mudança do `render.yaml` publica sozinha no Render (sem migração
junto, P-18); a Vercel só se o painel mudar. Depois, o sintético e o exercício de alerta.

**Riscos:**
- O painel ser lido como prova: o texto, o guia e a ligação primeiro para a chefia reduzem o risco.
- A base humana é pequena (os gabaritos da equipe): as metas são revistas a cada lista, com o uso
  pela chefia.
- Desligar é imediato: a variável no Render volta a `0` sem deploy de código.

#### Sprint 43 — Período na interface e retenção por encerramento

**Objetivo:** corrigir uma lista atrasada com as regras do período certo e manter só os períodos
recentes carregados.

**Missão:** que o monitor escolha Período → Lista → Questão, com o período ativo já escolhido, e que
o mantenedor encerre períodos antigos sem perder nada do Git.

**Personas:** o monitor que corrige uma lista de outro período (US-39) e o monitor-mantenedor
(US-40).

**Execução:**
1. O analisador carrega o ativo e os 5 anteriores (S43-01), e a API aceita o período (S43-02).
2. O seletor na página (S43-03).
3. O encerramento por CLI com simulação (S43-04) e os documentos (S43-05).

**Histórias:** US-37, US-39 e US-40.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S43-01 | US-39 | Engenharia | `load_rulesets(root)` carrega o período do `ATIVO` e os 5 anteriores presentes em `rulesets/` (ignora `rulesets/encerrados/`); o manifesto passa a listar `periods` (período, ativo, `ruleset_version`, questões); cache de preparação por (período, hash) | `engine/ruleset.py`, `service/app.py`, `/internal/ruleset/manifest` | Autor | 2 | — | Testes com 7 períodos em `tmp_path` (6 carregados); hash por período; subida até +2 s em relação a um período (premissa validada pelo autor em 12/10/2026) |
| S43-02 | US-39 | Engenharia | `period` opcional em `/validate`, `/similarity`, `/similarity/batch` e `/feedback` (padrão: o ativo); `GET /api/v1/periods`; 422 `UNKNOWN_PERIOD`; `questions.py` resolve por (período, questão); a telemetria e a adoção gravam o período da requisição | `ipc_api/schemas.py`, `routes/*`, `questions.py`, `telemetry.py`, `adoption.py`, OpenAPI | Autor | 1 | S43-01 | Contrato OpenAPI; teste com `L3-Q9` de 2026.2 e o ativo em 2027.1 |
| S43-03 | US-39 | Engenharia | `PeriodSelector` antes de `ListSelector` no verificador e no plágio, com "(ativo)" no rótulo; o rascunho (S37-05) guarda o período; "Próximo aluno" mantém o período | `frontend/src/components/`, `Checker.tsx`, `Plagiarism.tsx` | Autor | 1 | S43-02 | Vitest e e2e da lista atrasada |
| S43-04 | US-40 | Engenharia | `ipc-rules retire-period <período> [--dry-run]` move a pasta para `rulesets/encerrados/` e recusa o ativo e os períodos da janela; o índice de gabaritos ignora `encerrados/`; aviso em `/health/slo` quando o `ATIVO` parece defasado em relação à data (só aviso, nunca troca automática) | `cli.py`, `gabaritos.py`, `routes/meta.py` | Autor | 1 | S43-01 | `--dry-run` não toca no disco; recusas testadas |
| S43-05 | US-40 | Documentação | ADR-12; revisão da ADR-10 (decisão 3); `rulesets/README.md` ("Encerrar um período"); README dos gabaritos (`encerrados/`); FR-32 e US-37 sem a nota de "até a Sprint 43"; `new-period` deixa de copiar a lista de questões do `LEIA-ME.md` (hoje `rulesets/2027.1/questions/LEIA-ME.md` cita questões que não existem) | docs, `cli.py` | Autor | 1 | — | Revisão |

**ADRs:** ADR-12 (novo) e ADR-10 (revisão).

**Critérios de aceite:**
1. Com o `ATIVO` em 2027.1, o monitor escolhe 2026.2, a Lista 3 e a L3-Q9, e a resposta traz a `ruleset_version` de 2026.2.
2. Sem período na requisição, tudo funciona como hoje.
3. O `retire-period --dry-run` mostra o que sairia, e o ativo nunca é encerrado.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Carregamento de vários períodos | pytest | PR | 6 carregados, `encerrados/` ignorado, hash por período |
| Período na API | pytest e contrato OpenAPI | PR | Padrão = ativo; 422 para período desconhecido |
| Seletor | Vitest e e2e | PR | Lista atrasada verificada com as regras do período |
| Encerramento | pytest com `tmp_path` | PR | Simulação sem efeito; recusas |

**Deploy:** release `sprint-43`. Render (analisador e API) e Vercel; sem migração.

**Riscos:** as views que agrupam por `ruleset_version` passam a misturar períodos na mesma semana
(conferir `v_top_rules_by_list`); mais memória no analisador (dezenas de KB por período).

#### Sprint 44 — Feedback rastreável e o padrão do monitor

**Objetivo:** que cada violação citada no feedback traga a linha e o motivo, e que o tom da equipe
fique num arquivo revisável.

**Missão:** o aluno sabe onde e por que a questão foi anulada, e o monitor-chefe ajusta o tom sem
programar.

**Personas:** o monitor que manda o feedback (US-41) e o monitor-chefe (US-42).

**Execução:**
1. Os itens do feedback com regra, linhas, explicação e alternativa (S44-01), sobre a S38-01 e a S38-02.
2. O `estilo.yaml` com o esquema (S44-02).
3. A tela destaca as linhas citadas (S44-03) e os documentos (S44-04).

**Histórias:** US-32, US-41 e US-42.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S44-01 | US-41 | Engenharia | `FeedbackItem` ganha `rule_id`, `lines`, `explanation` e `alternative` (do ruleset); o trecho sem IA cita cada item na ordem do motor, com o nome da regra (Q-30), a linha, o porquê e um caminho, sem a solução; a frase obrigatória não muda (NFR-26) | `engine/feedback.py`, `feedback/compose.py` | Autor | 2 | S38-01, S38-02 | Casos T1 a T3 da revisão; NFR-26 intacto |
| S44-02 | US-42 | Engenharia | `backend/src/ipc_api/feedback/estilo.yaml` (tom, dicas, fechamentos e 3 a 5 exemplos com `[ALUNO]`) com esquema JSON validado na CI; os prompts usam o tom e os exemplos | `feedback/estilo.yaml`, `estilo.schema.json`, `compose.py` | Autor | 1 | — | Arquivo inválido falha na CI; a mudança aparece no próximo feedback |
| S44-03 | US-41 | Engenharia | `FeedbackResponse.items`; a página destaca no editor a linha de cada item citado | `schemas.py`, `FeedbackPanel.tsx`, OpenAPI | Autor | 1 | S44-01 | Vitest |
| S44-04 | US-42 | Documentação | `docs/estilo-do-feedback.md` (como editar e quem revisa, Q-31); FR-34 e FR-35; revisão da ADR-06; guia da equipe | docs | Autor | 1 | — | Revisão |

**ADRs:** ADR-06 (revisão).

**Critérios de aceite:**
1. Para `for` e `range()` na Lista 1, o feedback sem IA cita as duas construções com a linha e diz que são liberadas na Lista 2.
2. Um `estilo.yaml` inválido não passa na CI.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Itens rastreáveis | pytest (`test_compose.py`, `test_feedback_engine.py`) | PR | Linha e motivo em todo item; ordem do motor |
| Esquema do estilo | pytest | PR | Arquivo inválido recusado |
| Destaque na página | Vitest e e2e | PR | A linha citada é marcada no editor |

**Deploy:** release `sprint-44`. Render e Vercel.

**Riscos:** um texto mais longo pode passar do que cabe no Dikastis (**hipótese**; medir com a equipe
na campanha de testes).

#### Sprint 45 — Aprimorar com IA: validação rastreável e crítica

**Objetivo:** nenhum erro inventado pela IA chega ao aluno.

**Missão:** que o texto da IA só fale do que o verificador achou, não entregue a solução nem o
gabarito, e seja reescrito uma vez antes de cair no texto sem IA.

**Personas:** o membro da equipe que usa o "Aprimorar com IA" (US-43).

**Execução:**
1. Os validadores novos (S45-01).
2. Uma rodada de crítica e reescrita dentro do prazo atual de 28 s (S45-02).
3. A avaliação com a rubrica (S45-03).

**Histórias:** US-32 e US-43.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S45-01 | US-43 | Engenharia | Validação da saída além dos filtros atuais: (a) toda construção citada (vocabulário de `display.py`) está entre os itens do motor; (b) nenhum bloco com 3 ou mais linhas de código; (c) nenhum trecho com 6 ou mais tokens seguidos iguais ao gabarito, conferido na API, sem enviar o gabarito ao provedor; (d) ao menos uma frase de encorajamento do estilo; (e) até 6 frases e 900 caracteres | `feedback/compose.py`, `feedback/service.py` | Autor | 2 | S44-01, S44-02 | Casos T4 a T6 da revisão; 0 texto de gabarito nos logs (canário) |
| S45-02 | US-43 | Engenharia | Uma rodada de crítica: com a lista de problemas da validação, uma chamada de reescrita, só se sobrarem pelo menos 10 s; depois, o texto sem IA (`NO_ANSWER`) | `feedback/service.py` | Autor | 1 | S45-01 | Caso T8 (fallback em até 28 s); `test_service.py` |
| S45-03 | US-43 | Avaliação | 20 casos revisados pela equipe com a rubrica de 5 critérios (achado com linha; nada sem achado; caminho sem solução; tom; forma), de 0 a 2 cada; resultado em `docs/eficacia.md` | docs | Autor e equipe | 1 | S45-02 | Média de pelo menos 9 em 10 |

**ADRs:** ADR-06 (revisão: etapas de validação e crítica). O NFR-26 ganha "0 construções citadas
fora dos achados do motor e 0 trechos de 6 ou mais tokens iguais ao gabarito".

**Critérios de aceite:**
1. Um texto da IA que cita `while` num código sem `while` nunca é exibido.
2. Sem resposta válida em 28 s, aparece o texto sem IA, como hoje.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Validadores | pytest com o provedor falso | PR | Os casos adversariais novos são recusados |
| Crítica e prazo | pytest | PR | Uma rodada só; fallback no prazo |
| Gabarito fora dos logs | canário do NFR-11 e do NFR-27 | PR | 0 ocorrências |
| Rubrica | revisão humana | Uma vez | Média ≥ 9/10 |

**Deploy:** release `sprint-45`. Render.

**Riscos:** a crítica gasta uma chamada a mais da cota gratuita (60 por conta e 1.000 por dia); com a
cota no fim, a crítica é pulada.

#### Sprint 46 — Plágio calibrado

**Objetivo:** limiares medidos, código comum descontado e a matriz da turma com trechos.

**Missão:** que a equipe saiba quanto o detector acerta (precisão e revocação) e que soluções curtas
e naturais da mesma questão não pareçam cópia.

**Personas:** o membro da equipe que compara a turma (US-44).

**Execução:**
1. O gerador de plágio sintético e a medição (S46-01).
2. O peso de base por questão e a parte explicada pelo gabarito (S46-02).
3. A matriz com grupos e trechos (S46-03), sobre a S40-02, e os documentos (S46-04).

**Histórias:** US-31, US-38 e US-44.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S46-01 | US-44 | Engenharia | Gerador de plágio sintético (variáveis renomeadas, blocos reordenados, `for` trocado por `while`, linha inerte e a combinação) sobre o corpus de `pares.yaml`, as referências e, só com `IPC_GABARITOS_DIR` na CI local, os gabaritos; `ipc-rules calibrate-plagio` imprime precisão e revocação por faixa e falha abaixo das metas (Q-32) | `backend/tests/similarity/sintetico.py`, `cli.py` | Autor | 2 | — | Relatório por faixa; gate na CI local |
| S46-02 | US-31, US-38 | Engenharia | IDF de base por questão (gabarito, referências e soluções independentes) combinado com o IDF da turma; o par mostra a parte da semelhança explicada pelo gabarito, sem descontá-la (descontar esconderia uma cópia do gabarito) | `engine/similarity_tree.py`, `routes/similarity.py`, `Plagiarism.tsx` | Autor | 2 | S46-01 | Pares independentes curtos abaixo de 80% |
| S46-03 | US-44 | Engenharia | Na matriz da S40-02, os trechos de cada par sob demanda e os grupos acima de 90% | `engine/similarity.py`, `Plagiarism.tsx` | Autor | 1 | S40-02 | Turma de 100 soluções (120 KB) em até 5 s no worker (NFR-30) |
| S46-04 | US-44 | Documentação | NFR-25 com os valores medidos; revisão da ADR-07 (IDF de base; alternativa D reavaliada com os números); seção "Plágio" em `docs/eficacia.md` | docs | Autor | 1 | S46-01 | Revisão |

**ADRs:** ADR-07 (revisão).

**Critérios de aceite:**
1. A medição mostra revocação ≥ 95% na faixa de 90% para as três transformações e precisão de 100% na faixa de 95% (Q-32).
2. A turma sintética de 30 soluções tem os dois grupos achados e nenhum independente acima de 90%.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Precisão e revocação | `ipc-rules calibrate-plagio` | PR que toca o plágio | Metas da Q-32 |
| Peso de base | pytest | PR | Independentes curtos abaixo de 80% |
| Matriz e orçamento | pytest | PR | 100 soluções em até 5 s |

**Deploy:** release `sprint-46`. Render e Vercel.

**Riscos:** o corpus de independentes é pequeno até chegarem as soluções anteriores a 2023 (P-21);
os números da primeira medição são provisórios.

#### Sprint 47 — Grupos de acompanhamento e histórico dos alunos (vai ao piloto com o aviso de privacidade aprovado)

**Objetivo:** cada monitor cadastra os alunos pelos quais é responsável e acompanha o histórico
deles, sozinho, em dupla ou em trio.

**Missão:** que um grupo de acompanhamento (N monitores e M alunos, por período) compartilhe as
verificações, os indícios e os alertas de plágio como resultados resumidos, sem o feedback (Q-28) e
sem nada do código do aluno (Q-27).

**Personas:** o monitor (US-45, US-46) e o monitor-chefe e o professor que supervisionam (US-47).

**Execução:**
1. A migração com as tabelas, o expurgo e os papéis (S47-01).
2. A política de acesso e as rotas (S47-02).
3. A gravação assíncrona do registro (S47-03).
4. As telas (S47-04) e a privacidade (S47-05).

**Histórias:** US-45, US-46 e US-47.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S47-01 | US-45 | Engenharia | Migração `0007_acompanhamento`: `app.student` (período, nome de exibição e, opcionalmente, o login do Dikastis, Q-26; nunca CPF, e-mail ou matrícula), `app.follow_group`, `app.group_member` (convite e aceite), `app.group_student`, `app.check_record` (só inserção; o resultado resumido, como "L3-Q1 anulada por Laços de repetição" ou "L4-Q2 validada", com as regras, a faixa dos indícios de IA e a do alerta de plágio quando houver e quem executou; sem código, hash, linhas, trechos ou feedback, Q-27 e Q-28) e `app.group_log`; `app.purge_semester()` `SECURITY DEFINER`; o `ipc_app` sem `DELETE` direto | `database/migrations/0007_*` | Autor | 2 | — | Ida e volta testadas (`test_migrations.py`) |
| S47-02 | US-45, US-47 | Engenharia | Política cargo × ação × alvo em `auth/policy.py` (membro vê e edita o próprio grupo; monitor-chefe, professor e desenvolvedor leem todos os grupos do período); rotas `groups`, `invites`, `students` e `history` | `auth/policy.py`, `routes/groups.py`, OpenAPI | Autor | 2 | S47-01 | Matriz testada por chamada direta (NFR-23) |
| S47-03 | US-46 | Engenharia | `student_id` e `group_id` opcionais em `/validate`, `/feedback` e `/similarity`; o registro é gravado em segundo plano e descartado sob `StoreBusy`, como a telemetria | `routes/*`, `telemetry.py` (padrão) | Autor | 1 | S47-02 | A resposta não muda com o banco ocupado |
| S47-04 | US-45, US-46, US-47 | Engenharia | Telas "Meus alunos" (grupos, convites, alunos), campo "Aluno" no verificador e no plágio, "Histórico do aluno" (linha do tempo com quem executou) e a leitura no Gerenciar | `frontend/src/pages/` | Autor | 3 | S47-02 | e2e: criar grupo, convidar, aceitar, adicionar aluno fictício, verificar e ver no histórico |
| S47-05 | US-45 | Documentação | Aviso de privacidade, seção 9.2, NFR-29, ADR-13, runbook (expurgo por período), guia da equipe | docs, `Privacy.tsx` | Autor e coordenação | 1 | — | Aprovação da coordenação |

**ADRs:** ADR-13 (novo) e ADR-04 (rotas novas na matriz de autorização).

**Critérios de aceite:**
1. Um aluno em dois grupos aparece nos dois; sair de um grupo não apaga os registros.
2. Nenhuma coluna guarda código (canário do NFR-11 estendido às tabelas novas).
3. O expurgo de um período remove alunos, grupos e registros daquele período.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Migração e expurgo | pytest com PostgreSQL | PR | Ida e volta; `purge_semester` |
| Autorização | pytest (matriz) | PR | 403 fora do grupo; leitura pela chefia |
| Sem código guardado | canário do NFR-11 | PR | 0 ocorrências |
| Fluxo completo | e2e | PR | Criar, convidar, aceitar, verificar e ver no histórico |
| Carga | `run_load.py` | Uma vez | Sem 500; registros descartados sob carga |

**Deploy:** release `sprint-47`, só depois da aprovação do aviso de privacidade (S47-05). Migração antes da release e nunca junto com o `render.yaml` (P-18);
depois, Render e Vercel.

**Riscos:** dado pessoal novo de terceiros (os alunos não usam a ferramenta, P-13); a base legal e o
aviso dependem da coordenação. Mais escritas no banco do plano gratuito (`POOL_SIZE=5`).

#### Sprint 48 — Entrada com o Google no piloto (no fim da fila, decisão de 12/10/2026)

**Objetivo:** que a equipe entre no piloto também com a conta Google da UFPE, além da senha.

**Missão:** ligar no piloto a entrada pelo Google que existe desde a Sprint 16, sem afrouxar as regras
de domínio e de aprovação.

**Personas:** o membro da equipe que prefere não guardar outra senha (US-25).

**Contexto:** o código, os testes e a recusa de domínios fora da UFPE e de e-mail não verificado
existem desde a Sprint 16 (US-25, `auth/google.py`). No piloto, o botão não aparece porque faltam o
cliente OAuth e as variáveis `IPC_GOOGLE_CLIENT_ID` e `IPC_GOOGLE_CLIENT_SECRET` (`deploy/piloto.md`,
passo 6). A antiga Sprint 48 (impressões digitais, ADR-14) saiu do plano com a Q-27; a integração
com outros projetos da monitoria (Q-23) fica para depois, sem sprint por enquanto.

**Execução:**
1. O autor cria o cliente OAuth e grava as variáveis no painel do Render (S48-01).
2. A verificação no piloto e o ensaio de entrada (S48-02).
3. Os documentos (S48-03).

**Histórias:** US-25.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S48-01 | US-25 | Externa | Criar no Google Cloud o cliente OAuth do tipo aplicativo da Web, com a URI de retorno `<endereço da Vercel>/api/v1/auth/google/callback`, só os escopos `openid`, `email` e `profile` e a tela de consentimento publicada; gravar `IPC_GOOGLE_CLIENT_ID` e `IPC_GOOGLE_CLIENT_SECRET` no painel do Render, nunca no repositório | Google Cloud, painel do Render | Autor | — | — | `/api/v1/auth/options` responde com o Google ligado no piloto |
| S48-02 | US-25 | Engenharia | O teste do piloto confere o Google ligado; ensaio com uma conta `@cin.ufpe.br` nova (entra na fila de aprovação), uma já existente (chega à mesma conta) e uma de outro domínio (recusada) | `backend/tests/pilot/`, `docs/runbook.md` | Autor | 1 | S48-01 | Os três casos registrados no runbook |
| S48-03 | US-25 | Documentação | Guia da equipe (entrar com o Google), aviso de privacidade (o Google como provedor de identidade), runbook (troca do segredo) e README | docs, `Privacy.tsx` | Autor | 0,5 | — | Revisão |

**ADRs:** nenhum novo; o ADR-04 já cobre a entrada pelo Google.

**Critérios de aceite:**
1. O botão de entrar com o Google aparece no piloto.
2. Uma conta Google fora de `cin.ufpe.br` e `ufpe.br` é recusada, mesmo com o parâmetro `hd` alterado (US-25).
3. Uma conta nova pelo Google só tem acesso depois da aprovação.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Domínio e aprovação | pytest (os testes da Sprint 16) | PR | Verdes |
| Google ligado no piloto | `tests/pilot` | Depois do deploy | O Google aparece ligado |
| Ensaio de entrada | Roteiro do runbook | Uma vez | Os três casos |

**Deploy:** release `sprint-48` (teste do piloto e documentos). As variáveis do Google valem no
Render depois de um Manual Deploy; a Vercel não muda. Depois, o sintético.

**Riscos:**
- Em modo de teste, a tela de consentimento só aceita os usuários listados; ela precisa estar
  publicada. Com só os escopos básicos, o Google não deve exigir a revisão do aplicativo
  [A CONFIRMAR no console].
- Um segredo a mais para trocar (runbook).

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
- [ ] A cobertura somada de `ipc_analyzer` e `ipc_api` é ≥ 90% (`--cov-fail-under=90`; NFR-16). Um limite separado por pasta é [PLANEJADO].
- [ ] Cada R-xx criado ou alterado tem pelo menos 3 casos golden (permitido na lista correta, proibido antes dela e evasão quando couber), com 0 FP e 0 FN (NFR-18).
- [ ] Os testes de contrato da API, gerados do OpenAPI, passam para todos os códigos de status documentados em 5.2.2.
- [ ] [PLANEJADO] O benchmark do motor não regrediu mais de 20% (NFR-02).
- [ ] O smoke e2e (Playwright) está verde: localmente na Fase 0 e no ambiente do piloto a partir da Sprint 11.
- [ ] Quando a entrega afeta o caminho de requisição (a partir da Sprint 28), o `deploy/load/run_load.py` no plano do piloto ou o workflow "Carga no piloto" mostra o P95 dentro do NFR-01; os cenários do NFR-04 e do NFR-05 são [PLANEJADO].
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
| POST | `/api/v1/similarity` | Sessão | `SimilarityRequest` (`code_a`, `code_b`) | `SimilarityResponse` | 200, 401, 403, 413, 422, 429, 503 | 30/min por conta, dividido com a verificação | `routes/similarity.py` |
| POST | `/api/v1/similarity/batch` | Sessão | `SimilarityClassRequest` (até 100 soluções) | `SimilarityClassResponse` | 200, 401, 403, 413, 422, 429, 503 | idem | `routes/similarity.py` |
| POST | `/api/v1/feedback` | Sessão | `FeedbackRequest` (`code`, `list_number`, `student_name`, `annotation`, `question_id`) | `FeedbackResponse` (`text`, `source`, `provider`) | 200, 401, 403, 413, 422, 429, 503 | idem, mais 60/dia por conta e 1.000/dia no servidor | `routes/feedback.py` |
| GET | `/api/v1/admin/requests` | Sessão de monitor-chefe, professor ou desenvolvedor | — | `RequestsResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/requests/{account_id}/approve` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/requests/{account_id}/reject` | idem | — | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| GET | `/api/v1/admin/members` | idem | — | `MembersResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| PATCH | `/api/v1/admin/members/{account_id}/role` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/members/{account_id}/remove` | idem | — | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| POST | `/api/v1/admin/members/{account_id}/reactivate` | idem | `RoleChoice` | — | 204, 401, 403, 404, 409, 422, 503 | Geral | `routes/admin.py` |
| GET | `/api/v1/admin/log` | Sessão de professor ou desenvolvedor (REC-06) | — | `ManagementLogResponse` | 200, 401, 403, 503 | Geral | `routes/admin.py` |
| GET | `/health` | Nenhuma | — | `HealthResponse` | 200 | Livre | `routes/meta.py` |
| GET | `/ready` | Nenhuma | — | `ReadyResponse` (versão do ruleset e `release`; consulta o banco) | 200, 503 | Livre | `routes/meta.py` |
| GET | `/health/service` | Nenhuma | — | `ReadyResponse` (sem o banco; health check do Render) | 200, 503 | Livre | `routes/meta.py` |
| GET | `/health/slo` | Nenhuma | — | `SloResponse` (P95 e 5xx dos últimos 5 min) | 200, 503 | Livre | `routes/meta.py` |

O analisador tem uma API interna (`/internal/analyze`, `/internal/feedback-input`, `/internal/similarity`, `/internal/similarity/class`, `/internal/ruleset/manifest` e `/internal/health`, em `backend/src/ipc_analyzer/service/app.py`), que escuta só em `127.0.0.1` (Render) ou na rede interna `analyzer_net` (compose) e não é ponto de integração (ADR-01).

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

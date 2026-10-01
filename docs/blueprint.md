# IP-Checker — Blueprint Definitivo e Acionável

## 1. Visão Geral e Melhorias Aplicadas

### 1.1 Visão geral do IP-Checker

O IP-Checker é um verificador web, anônimo e sem execução de código, que confere se uma solução em Python de um aluno de Introdução à Programação respeita as regras de permissão da lista e da questão selecionadas (catálogo R-01…R-68, seção 3.1), antes do envio ao juiz Dikastis. O código é analisado apenas pela sua árvore sintática (AST), dentro de um serviço analisador isolado, sem segredos, sem rede de saída e com limites de tamanho, tempo e memória (ADR-01). As regras ficam em um ruleset versionado e declarativo, sob a responsabilidade do professor (regras das listas) e dos monitores (regras das questões, com aprovação de monitor-chefe ou professor). Assim, mudar uma lista não exige mudar o motor (ADR-02). Cada violação aparece com regra, linha, coluna e mensagem em PT-BR. A telemetria agregada e anônima não guarda código, IP nem identificador do aluno. O MVP (Sprint 9, fevereiro de 2027) entrega o fluxo ponta a ponta seguro para a Lista 1, rodando localmente. O piloto acontece em 2027.1, com a SPA na Vercel e o backend no Render: começa pela Lista 1 depois da apresentação a monitores-chefes e professores, e cada lista seguinte é habilitada antes de ser liberada aos alunos. O servidor do CIn só será adotado depois que os critérios de eficácia (P-09) forem atingidos (seção 7).

### 1.2 Falhas críticas corrigidas

| # | Problema | Evidência no rascunho | Impacto | Correção aplicada |
|---|---|---|---|---|
| 1 | O modelo de regras e o motor não conseguem representar o catálogo de permissões. | §12 (p.6–7): o esquema só tem `allowed_from_list` e `ast_nodes`, com IDs sintéticos como `Call_Attribute_split`. §11.3 e TASK-BE-002: "Verificar nome da classe do nó", com `visit_For`, `visit_Call`… escritos à mão. §12 mapeia `AsyncFor` como permitido a partir da Lista 2. | (a) R-37 (zip condicional), R-02/R-68 (exigências) e R-01 (precedência da questão) não podem ser expressos, então o veredito diverge do documento. (b) O *default deny* por classe de nó deixa passar `eval(...)`, `getattr(...)`, `__import__(...)` e métodos como `.title()`, porque `Call`, `Name` e `Attribute` são classes "permitidas". O resultado é um falso negativo e a questão anulada no Dikastis. (c) Cada regra nova exige código no Visitor, o que contraria a US-004 do rascunho. | Motor orientado a dados (ADR-02, 5.2.3). Ele usa um vocabulário de **fatos** (nó, operador, built-in, método/atributo, argumento nomeado, constante, contexto) e aplica o *default deny* a **cada fato**. Condições ficam em predicados declarativos, exigências em `requirements` e as regras da questão em `question_overrides`. Os IDs R-xx do catálogo são os IDs do ruleset, e o mapeamento foi validado em 01/10/2026 (Q-02). |
| 2 | O código do aluno é processado no mesmo processo da API, sem limite de tempo, e os controles de robustez ficam para depois da liberação aos usuários. | §8 e §10: parser, Rules Loader e cliente de telemetria (com credencial) na mesma aplicação FastAPI. §15: os únicos limites são tamanho e número de linhas. §11.3: `ast.NodeVisitor` recursivo. A captura de `SyntaxError` só vem na Sprint 6 (TASK-BE-010), o limite de profundidade e o rate limit na Sprint 9 (TASK-BE-012/013) e os logs seguros na Sprint 10 (TASK-BE-014). Enquanto isso, §25 libera o MVP 1.0 a testadores já na Sprint 4. | Uma entrada de até 50 KB com expressões encadeadas (ex.: `1+1+…`) gera uma AST mais profunda que o limite de recursão do Python, o que provoca `RecursionError` e HTTP 500. `ast.parse` roda em C e não pode ser interrompido por timeout em thread, então um único worker preso degrada todos os alunos no pico de entrega. Uma falha de memória do parser aconteceria num processo que guarda credencial do banco. Até a Sprint 6, todo erro de sintaxe vira 500. | ADR-01: serviço `analyzer` sem segredos e sem egress, com workers descartáveis, timeout de 2 s (kill) e `RLIMIT_AS`. A travessia é iterativa, com limite de profundidade e de nós. Limites, `SyntaxError` e logs sem código entram no MVP (7.2); rate limit e admissão entram antes de qualquer exposição à internet (Sprint 10). Todos fazem parte da DoD (seção 8). |
| 3 | O domínio está incompleto: a exigência do assunto de cada lista e a precedência da questão aparecem como opcionais. | Permissões p.1 §Introdução: "é obrigatória a implementação do assunto de cada lista" e "a prioridade será sempre o que está definido na questão". Rascunho §7.5 exige assunto só na Lista 6, e só auto-chamada direta. RF-012/TASK-BE-008 estão como "Medium / Recomendado" (§26), sem fonte de dados, formato ou responsável. §25: MVP 1.0 tem regras só das Listas 1–2, mas o seletor vai de 1 a 6 (RF-003). | A ferramenta aprova soluções que serão anuladas (ex.: Lista 2 sem laço) e acusa o que a questão permite. Isso contradiz o objetivo do §3 e mina a confiança na ferramenta. Com *default deny*, alunos das Listas 3–6 receberiam no MVP 1.0 violações para todo conteúdo permitido. | FR-10 e FR-11 passam a Must. R-02/R-68 entram no bloco `requirements`. Cada questão ganha um arquivo `questions/L<n>-Q<m>.yaml`, cadastrado por monitores e aprovado por monitor-chefe ou professor (CODEOWNERS, US-13, Q-08). O seletor passa a ser controlado por `ENABLED_LISTS`: L1 no MVP; as demais listas são habilitadas ao longo de 2027.1, antes de cada liberação (Sprints 13–16). Ver Q-04, Q-05, C-03 e Q-08. |

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
- **I-15** — O professor edita JSON por PR (§21), mas a validação e a documentação só chegam na Sprint 11 (TASK-DO-001). Correção: loader com validação e *fail-fast* no MVP (S1-02); FR-21 e US-14 na Sprint 17.
- **I-16** — A CI completa só vem na Sprint 8 (TASK-DE-003), enquanto a DoD do §27 exige CI desde a primeira task. Correção: S1-01.
- **I-17** — US-003 fala em "focar na lógica, não na sintaxe", mas a ferramenta verifica permissões, não lógica. Correção: US-11 reescrita.
- **I-18** — "Acessibilidade certificada" (§25) não indica norma nem método. Correção: NFR-19 (WCAG 2.1 AA, axe-core).
- **I-19** — O ADR-002 do rascunho diz que o servidor é "mais seguro" que o Pyodide. É o contrário: analisar no cliente elimina superfície de ataque no servidor. Os motivos válidos são consistência do ruleset, telemetria e custo de download. Correção: ADR-01, alternativa C.
- **I-20** — São 12 sprints sem duração, capacidade nem estimativa, e o aluno só recebe valor na Sprint 4. Correção: P-02, Q-13 e seção 7 (plano datado para um desenvolvedor, com MVP na Sprint 9 e piloto em 2027.1).
- **I-21** — O diagrama do §8 não mostra fronteiras de confiança, e o cliente de telemetria fica no mesmo processo do parser. Correção: 5.1.

### 1.3 Premissas, conflitos, questões em aberto e recomendações

Fontes: os quatro arquivos foram lidos integralmente. As versões .docx e .pdf de cada documento têm conteúdo equivalente, e a comparação automatizada só encontrou diferenças de diagramação (hifenização em células de tabela, marcadores de lista, espaços de largura zero). Cada documento é tratado como fonte única: "Permissões" (3 páginas) e "Rascunho" (31 seções, 25 páginas). Não há [CONFLITO] entre os formatos. Em 01/10/2026, o autor do projeto respondeu C-01…C-03, Q-01…Q-09, Q-11 e as premissas P-01…P-09. As decisões sobre a interpretação das regras serão ratificadas por monitores-chefes e professores na apresentação (Marco 2, seção 7). Também foram respondidas Q-10, Q-13 e Q-14, e a Q-12 foi adiada para depois do piloto. Falta apenas confirmar o calendário de 2027.1 (P-10).

| ID | Tipo | Descrição | Impacto | Quem valida |
|---|---|---|---|---|
| P-01 | [PREMISSA] | **Resolvido (01/10/2026):** 4 turmas e cerca de 200 alunos regulares, sem contar quem refaz a disciplina, alunos de outros centros (eletiva) e de especialização. O dimensionamento usa 500 alunos para ter margem. O pico de 500 verificações/min (RNF-002 do rascunho) equivale a uma verificação por aluno por minuto, com folga para essa população. | Dimensionamento (NFR-04, NFR-05) | Validado em 01/10/2026 |
| P-02 | [PREMISSA] | **Resolvido (01/10/2026):** o projeto é conduzido por uma única pessoa, Vinícius Leôncio (Lionzio), monitor e desenvolvedor, que coordena as sprints e apresenta o resultado a monitores-chefes e professores. Disponibilidade de 4 a 8 h por semana (Q-13), sprints de 2 semanas e 6 SP por sprint (1 SP ≈ 2 h de trabalho focado [PREMISSA]), com metade da capacidade nos recessos; recalibrar ao fim de cada sprint. Até o piloto, o autor é PO e único revisor; a revisão por CODEOWNERS passa a valer na Sprint 17. | Escopo e datas de cada sprint (seção 7) | Validado em 01/10/2026 |
| P-03 | [PREMISSA] | **Resolvido (01/10/2026):** Fase 0: Docker Compose local, sem custo. Fase 1 (piloto em 2027.1): SPA na Vercel e backend no plano gratuito do Render, por serem mais acessíveis (Q-10), mantido acordado pelo UptimeRobot a cada 5 min (ADR-03). Fase 2: servidor do CIn, só depois da comprovação da eficácia (P-09). PostgreSQL gerenciado (Supabase, §2 do rascunho) para a telemetria. | Custo e topologia (ADR-03) | Validado em 01/10/2026 |
| P-04 | [PREMISSA] | **Resolvido (01/10/2026):** o Wi-Fi do CIn (`CINUFPE`) dá IP privado a cada dispositivo e sai para a internet por NAT, num conjunto de IPs públicos da UFPE na borda com a RNP; logo, centenas de alunos compartilham poucos IPs. Decisão: o limite que protege cada aluno é o do cliente anônimo (10 req/min, valor do rascunho). O limite por IP serve contra abuso: 120 req/min para IPs externos e 1.000 req/min [PREMISSA: 2× o pico de P-01] para as faixas do campus configuradas em `RATE_LIMIT_CAMPUS_CIDRS` (Q-11). A admissão global (NFR-05) protege a capacidade. Limites por análise calibrados na S5-01, com medição em Linux: timeout de 2 s; `RLIMIT_AS` de 256 MB por worker (o worker usa ~50 MB em repouso e ~74 MB no pior caso de 50 KB); até 60.000 nós (50 KB geram no máximo ~53 mil, e um programa legítimo de 1.000 linhas densas já passa de 20 mil, o valor inicial); profundidade até 200; até 200 violações por resposta. O pior caso de 50 KB é analisado em 0,46 s. | Equilíbrio entre segurança e bloqueio indevido | Validado em 01/10/2026 (faixas em Q-11; limites de análise calibrados na Sprint 5) |
| P-05 | [PREMISSA] | **Resolvido (01/10/2026):** disponibilidade de 99,5% ao mês no período letivo (até cerca de 3,6 h fora do ar), no lugar dos 99,9% do RNF-003. | NFR-06 | Validado em 01/10/2026 |
| P-06 | [PREMISSA] | **Resolvido (01/10/2026):** a telemetria é retida por 12 meses e depois expurgada. Como é anônima e não permite reidentificar alunos, fica fora da definição de dado pessoal da LGPD (art. 12); mesmo assim, o projeto segue os princípios de finalidade, minimização e prazo de retenção. | NFR-12 | Validado em 01/10/2026 |
| P-07 | [PREMISSA] | **Resolvido (01/10/2026):** existe numeração oficial no formato `L<lista>-Q<número>` (ex.: `L3-Q2`), que reinicia a cada período: a `L3-Q2` de 2026.2 é diferente da `L3-Q2` de 2026.1 e da de 2025.2. Por isso a identidade de uma questão é o par (período, `question_id`): os overrides ficam em `rulesets/<período>/questions/`, a API só aceita questões do período do ruleset ativo e a telemetria grava o período (5.2.4). | FR-03, FR-11, FR-17 | Validado em 01/10/2026 |
| P-08 | [PREMISSA] | **Resolvido (01/10/2026):** os casos golden são escritos pelos monitores (na Fase 0, pelo autor do projeto): 3 casos por R-xx e mais 30 casos de evasão. O banco de test cases com saídas esperadas de cada questão continua no Dikastis e não é usado pelo IP-Checker, que não executa código (ADR-01). Ver Q-14. | NFR-18 | Validado em 01/10/2026 |
| P-09 | [PREMISSA] | **Aprovado (01/10/2026):** critérios de eficácia do piloto, que decidem a migração para o servidor do CIn. O piloto é o período 2027.1, depois da aprovação na apresentação (Marco 2), e é comparado com a linha de base coletada pela REC-05 no semestre atual, sem a ferramenta. Critérios: (1) precisão: 100% no corpus golden e nenhum falso positivo confirmado pela monitoria sem correção em até 2 dias úteis; (2) uso: média ≥ 3 verificações por aluno matriculado por lista (telemetria do FR-17 dividida pelo número de matrículas); (3) resultado: redução ≥ 50% das anulações por recurso proibido em relação à linha de base; (4) satisfação: ≥ 70% de alunos e monitores avaliam a ferramenta como útil ou muito útil em pesquisa de fim de piloto; (5) operação: NFR-01 e NFR-06 atendidos e nenhum incidente de segurança. Justificativa: P-03 condiciona a migração à "comprovação da eficácia", que os documentos não definem. | Decisão de migração (US-23, após 2027.1) | Validado em 01/10/2026 |
| P-10 | [PREMISSA] | O período 2027.1 começa em março de 2027 e a Lista 1 é liberada cerca de 2 semanas depois; as listas seguintes saem em intervalos de 2 a 4 semanas. Justificativa: o roadmap precisa de datas, e o calendário acadêmico e o das listas não foram informados. | Datas das Sprints 12–18 (7.1) | Autor do projeto (calendário da UFPE e das listas) |
| C-01 | [CONFLITO] | **Resolvido (01/10/2026):** o §12 do rascunho mapeava `AsyncFor` na regra do `for`. `async for` é uma construção distinta do `for` da R-34: só existe dentro de `async def` e percorre iteradores assíncronos. `AsyncFor`, `AsyncFunctionDef`, `AsyncWith` e `Await` geram violação R-04; para laços e iteração vale apenas o `for` comum. | Falso negativo eliminado | Validado em 01/10/2026 |
| C-02 | [CONFLITO] | **Resolvido (01/10/2026):** dois níveis, com o override da questão (R-01) acima da base (R-03 a R-68), inclusive das proibições gerais R-05…R-14. Uma questão pode liberar uma proibição geral, embora isso nunca tenha ocorrido na disciplina; por ser excepcional, a CI exige aprovação de professor para esse tipo de override (FR-21). Substitui a hierarquia de 4 níveis do §7.4 do rascunho. | Ordem de avaliação do motor | Validado em 01/10/2026 |
| C-03 | [CONFLITO] | **Resolvido (01/10/2026):** a exigência da R-68 é atendida por recursão direta ou mútua (ciclo no grafo de chamadas entre funções do aluno), e não só pela auto-chamada direta prevista no rascunho (§7.5, §28). | Falso positivo na L6 eliminado | Validado em 01/10/2026 |
| Q-01 | [QUESTÃO] | **Resolvido (01/10/2026):** Python 3.13+ (o primeiro rascunho previa 3.12+). O analisador usa a imagem `python:3.13-slim`. Quando o Dikastis mudar de versão minor, a imagem do analisador acompanha no mesmo semestre, validada pelo corpus do NFR-21. | Gramática do parser | Validado em 01/10/2026 |
| Q-02 | [QUESTÃO] | **Resolvido (01/10/2026):** (a) `format()` como função e como método `str.format`: permitidos desde a L1 (R-28); (b) `not in` e `is not`: permitidos com R-30 e R-17; (c) `sep=`, `reverse=` e `key=`: proibidos (R-04), pois só `end=` consta na R-32; (d) desempacotamento `a, b = …` antes da L3: proibido (R-04), exceto no alvo de `for` com `zip` na L2 (R-37); (e) expressões geradoras e *dict comprehension*: proibidas (R-04); (f) valores padrão de parâmetros e funções aninhadas: proibidos (R-04); (g) `else` em laços: proibido (R-04); (h) `*`/`**` em chamadas: R-10 (anulação). | Matriz de mapeamento (5.2.3) | Validado em 01/10/2026 |
| Q-03 | [QUESTÃO] | **Resolvido (01/10/2026):** a R-14 proíbe apenas a instrução `global`. Ler, dentro de uma função, uma variável criada no módulo não gera violação. | Mapeamento da R-14 | Validado em 01/10/2026 |
| Q-04 | [QUESTÃO] | **Resolvido (01/10/2026):** a condição da R-37 vale nas Listas 2–4; a partir da L5, `zip()` fica liberado sem restrição (R-64). | Veredito de `zip` na L5–L6 | Validado em 01/10/2026 |
| Q-05 | [QUESTÃO] | **Resolvido (01/10/2026):** a exigência da R-02 vale para toda questão da lista e é comprovada por: L1 `if` (com ou sem `elif`/`else`) ou operador ternário; L2 `for`/`while`; L3 lista ou tupla (literal, `list()`, `tuple()` ou *list comprehension*); L4 `def`; L5 dicionário (literal ou `dict()`); L6 recursão (R-68, C-03). | Exigências (FR-10) | Validado em 01/10/2026 |
| Q-06 | [QUESTÃO] | **Resolvido (01/10/2026):** todo `import` e `from … import`, inclusive da biblioteca padrão (ex.: `math`), é R-05, com anulação imediata. | Severidade e mensagem | Validado em 01/10/2026 |
| Q-07 | [QUESTÃO] | **Resolvido (01/10/2026):** `type()` com 3 argumentos é R-09 (Classes, anulação); com 1 argumento continua permitido pela R-33. | Evasão de R-09 | Validado em 01/10/2026 |
| Q-08 | [QUESTÃO] | **Resolvido (01/10/2026):** as regras por questão são cadastradas por monitores (na maioria dos casos), monitores-chefe ou professores, por PR em `rulesets/<semestre>/questions/`. Governança adotada: ninguém aprova o próprio PR; a aprovação vem de monitor-chefe ou professor (CODEOWNERS), e overrides que liberam R-05…R-14 exigem professor (C-02). O campo `source` registra o trecho do enunciado. | FR-11, FR-21, US-13 | Validado em 01/10/2026 |
| Q-09 | [QUESTÃO] | **Resolvido (01/10/2026):** não existem dados de anulação por lista. O objetivo do §3 do rascunho fica sem linha de base até a coleta da REC-05; até lá, o sucesso é medido pela precisão (NFR-18) e pela telemetria de uso (FR-17). | Medição de sucesso | Validado em 01/10/2026 |
| Q-10 | [QUESTÃO] | **Resolvido (01/10/2026):** o piloto é o período 2027.1, com monitores e alunos usando a ferramenta. Hospedagem: SPA na Vercel e backend no Render, por serem mais acessíveis; depois, servidor do CIn. O plano gratuito do Render dorme após 15 min sem tráfego; para evitar isso, o UptimeRobot acessa o backend a cada 5 min (decisão de 01/10/2026). O gratuito continua com só 0,1 CPU: se o teste de carga da Sprint 12 ou o P95 numa véspera de prazo passar de 200 ms, o backend migra para o plano Starter (cerca de US$ 7 por mês). Se o plano de "pouco mais de R$ 40" encontrado for anual, provavelmente é hospedagem compartilhada, que não roda contêiner Docker nem serviço Python contínuo; confirmar antes de contratar. | Topologia do piloto (ADR-03) | Validado em 01/10/2026 |
| Q-11 | [QUESTÃO] | **Resolvido (01/10/2026):** a UFPE usa o bloco `150.161.0.0/16` (AS1916, RNP), e o CIn está dentro dele (ex.: `150.161.2.0/24`, `150.161.6.0/24`, `150.161.70.0/24`). Configuração: `RATE_LIMIT_CAMPUS_CIDRS=150.161.0.0/16`, que cobre o CIn e também os alunos de outros centros (P-01). Tráfego IPv6, se houver, é limitado por prefixo /64, e o prefixo IPv6 da UFPE entra na mesma lista quando for conhecido. | Rate limit no campus (FR-19, Sprint 10) | Validado em 01/10/2026 (fonte: registro BGP do bloco) |
| Q-12 | [QUESTÃO] | **Adiada (01/10/2026):** só será tratada depois do piloto, se a P-09 for atingida. Já se sabe que o acesso aos servidores do CIn exige vínculo ativo, login CIn (LDAP) e, de fora da universidade, VPN IKEv2; por isso, na Fase 2 o deploy será *pull-based* (o servidor busca a imagem no GHCR). Ficam para depois: Docker, porta 443 aberta para a internet, subdomínio e TLS, saída para o PostgreSQL gerenciado e administração do sistema. | Migração (após 2027.1) | Suporte de TI do CIn |
| Q-13 | [QUESTÃO] | **Resolvido (01/10/2026):** 4 a 8 h por semana. O roadmap usa 6 SP por sprint e mostra o efeito dos extremos (7.1): com 8 h sobra folga, com 4 h o piloto só começaria a partir da Lista 2 ou 3. A apresentação precisa ocorrer antes da liberação da Lista 1 em 2027.1. | Datas da seção 7 | Validado em 01/10/2026 |
| Q-14 | [QUESTÃO] | **Resolvido (01/10/2026):** as questões ficam no Dikastis e os gabaritos no Notion. Os gabaritos de períodos anteriores entram no corpus golden como casos que devem ter zero violação na sua lista (Sprint 13). Por serem respostas oficiais, ficam num repositório privado separado, nunca no repositório principal; a CI os lê com um token somente leitura. | Precisão (NFR-18) | Validado em 01/10/2026 |
| REC-01 | [RECOMENDAÇÃO] | Fora do escopo: colocar um proxy de CDN com mitigação de DDoS (plano gratuito) na frente do Caddy, se o NFR-05 for violado em produção. | Risco residual de DDoS (5.4) | Coordenação e mantenedores |
| REC-02 | [RECOMENDAÇÃO] | Fora do escopo: coletar, com consentimento, uma amostra anonimizada de soluções históricas para ampliar o corpus golden. | Precisão (NFR-18) | Coordenação/comitê de ética |
| REC-03 | [RECOMENDAÇÃO] | Fora do escopo: congelar e publicar o ruleset da lista N pelo menos 48 h antes de liberá-la. | Fidelidade no dia da liberação | Professor |
| REC-04 | [RECOMENDAÇÃO] | Ficam fora deste blueprint, como no §22 do rascunho: dashboard público para professores, CLI `pip install ip-checker` e webhook com o Dikastis. | Contenção de escopo | Coordenação |
| REC-05 | [RECOMENDAÇÃO] | Fora do sistema: a coordenação passa a registrar, por lista e por semestre, quantas questões foram anuladas por uso de recurso proibido (planilha simples), a partir de 2026.2, para criar a linha de base que hoje não existe (Q-09). | Mensurabilidade do objetivo do §3 do rascunho | Coordenação |

## 2. Mapa de Personas

| Persona | Objetivo | Necessidades | Dores | Interação com o sistema |
|---|---|---|---|---|
| Aluno de IP (rascunho §3 "Público"; US-001, US-002 e US-005 do rascunho; Permissões p.1 "anulação imediata da questão") | Submeter ao Dikastis soluções que respeitem as permissões da lista e da questão, sem perder pontos. | Saber antes do envio se usou algo proibido, com a linha exata. Entender a partir de qual lista um recurso é liberado. Saber se a questão tem regra própria (R-01) e se cumpriu o assunto obrigatório (R-02). | Perde pontos por usar comandos não ensinados (rascunho §3 "Problema"). As regras cumulativas (R-03), as proibições gerais (R-05…R-14) e as exceções por questão são difíceis de memorizar. | SPA web anônima: cola ou envia `.py`, escolhe lista e questão, lê o relatório e navega até a linha. Não há login. |
| Monitor e monitor-chefe (rascunho §3; US-003 do rascunho; resposta à Q-08) | Concentrar o atendimento na lógica do aluno, não em dúvidas de permissão, e manter atualizadas as regras específicas das questões. | Verificar em segundos o código de um aluno, sem configuração, vendo o mesmo relatório que o aluno vê. Cadastrar as permissões e proibições explícitas de cada questão sem programar. O monitor-chefe revisa e aprova o cadastro feito pelos monitores. | Monitoria sobrecarregada por dúvidas de permissão (rascunho §3 "Problema"). Risco de cadastrar uma regra de questão diferente do enunciado. | Usa a mesma SPA que o aluno, sem login. Cadastra regras de questão por PR em `questions/*.yaml`; o monitor-chefe aprova como CODEOWNER. |
| Professor/Coordenação (rascunho §3; US-004 do rascunho; §16; §30.1 "a confirmar com a coordenação"; resposta à Q-08) | Garantir que a ferramenta aplica exatamente o documento de permissões e as regras de cada questão, e acompanhar onde os alunos mais erram. | Alterar as regras das listas sem reprogramar a ferramenta. Aprovar overrides de questão, obrigatoriamente os que liberam proibições gerais (C-02). Consultar violações agregadas por lista. Decidir a migração para o servidor do CIn com base nos critérios de eficácia (P-09). | No rascunho, editar o JSON exige PR sem validação nem documentação até a Sprint 11 (I-15). Não havia fonte nem responsável para as regras de questão (1.2 #3). | Edita o ruleset base (YAML) por PR e aprova como CODEOWNER. Consulta views SQL somente leitura. |
| Monitor-mantenedor, equipe técnica futura (rascunho §1 "manutenção por futuras equipes de monitores"; §21; §31 "handover") | Manter e evoluir a ferramenta apesar da rotatividade semestral. | Motor desacoplado das regras. Testes golden e de segurança na CI. Runbook e guia de onboarding. Observabilidade. | Conhecimento se perde a cada troca de equipe. Risco de quebrar regras ao mexer no código. Incidentes em véspera de prazo. | Repositório GitHub, CI/CD, CLI `ipc-rules`, painéis e alertas. |

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
| R-41 | 3 → 6 | List comprehension | permitido | List comprehension. | Perm. p.2 §Lista 3 |
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
- **FR-16** — Telemetria anônima e assíncrona por validação: lista, questão, versão do ruleset, resultado, `rule_id`s e tempo de análise. Nunca registra código, IP ou identificador de cliente. Origem: RF-019 e RF-026.
- **FR-17** — Consultas agregadas pré-definidas (views SQL somente leitura) para professores: regras mais violadas por lista, questão e período, taxa de erro de sintaxe e volume de verificações por lista e por semana, usado na avaliação de eficácia do piloto (P-09). Origem: §16.
- **FR-18** — Endpoints `GET /health` (o processo está vivo) e `GET /ready` (o analisador responde e o ruleset está carregado). Origem: RF-020.
- **FR-19** — Rate limit por cliente anônimo (10 req/min) e por IP (120 req/min para IPs externos; 1.000 req/min para as faixas do campus em `RATE_LIMIT_CAMPUS_CIDRS`), mais controle de admissão. Respostas 429 ou 503 sempre trazem `Retry-After`. Origem: RF-022 e P-04.
- **FR-20** — Interface web responsiva (≥ 360 px) com os estados: válido, com violações, erro de sintaxe, entrada rejeitada, limite de taxa, sobrecarga e falha de rede (com opção de nova tentativa). Origem: RF-017.
- **FR-21** — Ferramenta de validação do ruleset: o comando `ipc-rules validate` e o mesmo job na CI verificam schema, existência dos R-xx referenciados, consistência de `since_list`/`until_list` e os testes golden. Também sinaliza overrides de questão que liberam R-05…R-14, que só podem entrar com aprovação de professor (C-02). Origem: US-004 do rascunho e §21.

### 3.3 Requisitos Não Funcionais

| ID | Categoria | Requisito | Métrica | Valor-alvo | Método de verificação |
|---|---|---|---|---|---|
| NFR-01 | Desempenho | Latência do `POST /api/v1/validate` medida no servidor (borda → resposta) | P95 e P99 em janelas de 5 min | P95 ≤ 200 ms e P99 ≤ 500 ms, com 500 req/min e payload ≤ 5 KB | k6 em staging antes de cada release; histograma Prometheus em produção |
| NFR-02 | Desempenho | Tempo de análise no worker (parse, fatos e política) | P95 por entrada do corpus | ≤ 50 ms para entradas ≤ 50 KB | `pytest-benchmark` na CI; falha se regredir mais de 20% |
| NFR-03 | Desempenho | Carregamento da SPA | FCP e tamanho do JS inicial (gzip) | FCP < 1,5 s (perfil mobile "Slow 4G"); JS inicial ≤ 350 KB gzip [PREMISSA] | Lighthouse CI em todo PR do `frontend/` |
| NFR-04 | Capacidade | Vazão sustentada no pico de entrega (P-01) | req/min, taxa de 5xx, taxa de timeout | 500 req/min por 15 min com 0% de 5xx e < 0,1% de timeouts | Cenário k6 "véspera de prazo" por release, com 80% do tráfego vindo de 4 IPs (NAT do campus, P-04) e 20% de IPs distintos |
| NFR-05 | Concorrência | Degradação controlada sob sobrecarga | Respostas 500/502/504, tempo de emissão do 503, tempo de recuperação | A 1.500 req/min: 0 respostas 500/502/504; 503 com `Retry-After` em ≤ 100 ms; recuperação ≤ 60 s após a carga | Teste de stress k6 por release |
| NFR-06 | Disponibilidade | Disponibilidade externa no período letivo, sem cold start | % mensal de checks OK; latência da 1ª verificação de usuário do dia | ≥ 99,5% (P-05); 1ª verificação do dia ≤ 300 ms | UptimeRobot a cada 5 min em `/ready`, que também mantém o plano gratuito do Render acordado (ADR-03); teste sintético diário da 1ª verificação |
| NFR-07 | Segurança | Isolamento do `analyzer` | % dos controles conferidos | Fases 0 e 2 (contêiner próprio): 100% de nenhum segredo no ambiente, nenhuma rota de egress, rootfs read-only, UID ≠ 0, `cap_drop: ALL`, `no-new-privileges`, `pids_limit` ≤ 64 e memória ≤ 512 MB. Fase 1 (processo no Render): 100% de UID próprio (10002), ambiente sem segredos, seccomp bloqueando sockets de rede e `execve`, `RLIMIT_FSIZE` = 0 | Fases 0 e 2: teste de configuração (`docker inspect`) e teste de egress na CI. Fase 1: teste automatizado na imagem do Render (abrir socket, executar programa, gravar em disco e ler o ambiente da `api` falham) |
| NFR-08 | Segurança | Limites por análise (P-04) | Limites aplicados; % do corpus malicioso tratado sem 5xx | Timeout de 2 s (kill), `RLIMIT_AS` de 256 MB, ≤ 60.000 nós, profundidade ≤ 200, ≤ 50 KB, ≤ 1.000 linhas; 100% do corpus | Suíte de segurança da DoD (seção 8) na CI |
| NFR-09 | Segurança | Código do aluno nunca executado nem importado | Usos proibidos no código-fonte do projeto | 0 usos de `eval`, `exec`, `compile` (fora de `engine/parse.py`), `__import__`, `importlib`, `runpy` ou `pickle` sobre a entrada | Regras de segurança do ruff (Bandit) e guarda de código em pytest, bloqueantes na CI; Semgrep e revisão por CODEOWNERS a partir do piloto |
| NFR-10 | Segurança | Transporte, cabeçalhos e CORS | Versão de TLS, cabeçalhos presentes, origens aceitas, nota | TLS ≥ 1.2, HSTS e CSP sem `unsafe-inline` em scripts. Na Fase 1 (SPA na Vercel, API no Render), CORS aceita só a origem da SPA; nas Fases 0 e 2, mesma origem e nenhum cabeçalho CORS. SSL Labs ≥ A | Teste automatizado de cabeçalhos e CORS pós-deploy; SSL Labs por release |
| NFR-11 | Privacidade | O código não persiste em logs, banco ou disco | Ocorrências de um marcador canário | 0 ocorrências | Teste canário e2e na CI e mensal em produção (busca em logs e tabelas) |
| NFR-12 | Privacidade | Minimização e retenção da telemetria | Colunas existentes; idade máxima dos registros | Só as colunas do esquema 5.2.4; nenhum registro com mais de 12 meses (P-06) | Teste de esquema na CI; verificação mensal do job de expurgo |
| NFR-13 | Segurança | Dependências e imagens | CVEs críticas ou altas corrigíveis | 0 | Trivy, `pip-audit` e `npm audit` bloqueantes na CI; varredura semanal agendada |
| NFR-14 | Observabilidade | Logs estruturados | % de requisições com os campos obrigatórios; campos proibidos | 100% com `request_id`, `route`, `status`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`; 0 campos com código ou IP | Teste de esquema de log na CI |
| NFR-15 | Observabilidade | Métricas e alertas | Tempo até o alerta | Alerta em ≤ 5 min se P95 > 200 ms ou 5xx > 1%; em ≤ 10 min se `/ready` falhar (2 checks de 5 min do UptimeRobot) | Exercício de disparo de alertas a cada release |
| NFR-16 | Manutenibilidade | Qualidade estática e cobertura | % de cobertura; erros de lint/tipo | ≥ 90% em `ipc_analyzer/engine` (valor do rascunho) e ≥ 80% no restante; 0 erros de ruff, `mypy --strict`, ESLint e `tsc` | Gate na CI |
| NFR-17 | Manutenibilidade | Evolução de regras sem tocar no código | % de PRs de regra que alteram só dados | 100% dos PRs com label `rules` alteram apenas `rulesets/**` e `backend/tests/golden/**` | Job de CI que verifica os caminhos alterados |
| NFR-18 | Correção | Precisão do motor | Falsos positivos e falsos negativos no corpus golden | 0 FP e 0 FN, com ≥ 3 casos por R-xx (P-08) | `pytest` golden na CI |
| NFR-19 | Acessibilidade | Conformidade com WCAG 2.1 AA | Violações axe *critical/serious*; fluxo por teclado | 0 violações; fluxo completo operável só pelo teclado | Playwright com axe-core na CI e checklist manual por release |
| NFR-20 | Portabilidade e recuperação | Implantação reproduzível | RTO; RPO da telemetria | RTO ≤ 30 min (VM limpa + `docker compose up`); RPO ≤ 24 h | Ensaio de restauração uma vez por semestre |
| NFR-21 | Compatibilidade | Gramática alinhada à do Dikastis, Python 3.13+ (Q-01) | Divergências no corpus de sintaxe específica de versão | 0 | Testes de corpus por versão na CI |

## 4. Backlog de User Stories

Toda história segue o formato "Como <persona>, quero <ação>, para <valor>". A tabela traz apenas a ação e o valor.

### Épico E1 — Submissão e verificação

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-01 | Aluno | colar meu código no editor, escolher a lista e pedir a verificação | saber, antes de enviar ao Dikastis, se usei algo não permitido | Dado um código sem violações e a Lista 1, Quando clico em "Verificar", Então vejo "Nenhuma violação encontrada" e a `ruleset_version`; Dado um código com `for` e a Lista 1, Quando verifico, Então vejo a violação R-34 com a linha e a coluna do `for`; Dado que nenhuma lista foi escolhida, Quando vejo o botão "Verificar", Então ele está desabilitado | Must | FR-01, FR-03, FR-04, FR-06, FR-12 |
| US-02 | Aluno | enviar um arquivo `.py` | não precisar copiar e colar à mão | Dado um `.py` UTF-8 de até 50 KB, Quando o seleciono ou arrasto, Então o conteúdo aparece no editor sem nenhum envio ao servidor; Dado um arquivo de mais de 50 KB ou com outra extensão, Quando o seleciono, Então vejo uma mensagem de rejeição e nada é enviado | Should | FR-02, FR-04 |
| US-03 | Aluno | ver o erro de sintaxe com linha e coluna | corrigir o código antes da verificação de permissões | Dado um código com parêntese não fechado na linha 5, Quando verifico, Então recebo `syntax_error` com linha 5, coluna e mensagem em PT-BR e nenhuma violação de regra; Dado um código com byte nulo, Quando verifico, Então recebo 422 `INVALID_INPUT` | Must | FR-04, FR-05, FR-12 |
| US-04 | Aluno | selecionar a questão que estou resolvendo | que as permissões e proibições explícitas da questão prevaleçam (R-01) | Dado a questão `L3-Q2` cadastrada com `allow` para um construto, Quando verifico um código que o usa com essa questão selecionada, Então não aparece violação desse construto; Dado o mesmo código sem questão selecionada, Quando verifico, Então a violação aparece com o aviso `QUESTION_RULES_NOT_APPLIED`; Dado uma lista sem questões cadastradas, Quando abro o seletor, Então vejo "Nenhuma questão com regra específica cadastrada" | Must | FR-03, FR-11, FR-12 |

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
| US-11 | Monitor | verificar o código de um aluno durante o atendimento, sem login | dedicar o atendimento à lógica, não às permissões | Dado o código colado e a lista do aluno, Quando verifico, Então obtenho exatamente o relatório que o aluno obteria; Dado o fim da verificação, Quando procuro o canário em logs e no banco, Então não há cópia do código (NFR-11) | Should | FR-01, FR-12 |

### Épico E4 — Governança do ruleset

| ID | Persona | Ação | Valor Esperado | Critérios de Aceite | Prioridade (MoSCoW) | FRs atendidos |
|---|---|---|---|---|---|---|
| US-12 | Professor/Coordenação | alterar as regras das listas editando o ruleset, sem mexer no código | manter a ferramenta fiel ao documento de permissões | Dado um PR que altera só `rulesets/`, Quando a CI roda, Então schema e golden são validados e o merge exige minha aprovação (CODEOWNERS); Dado o merge na `main`, Quando o deploy termina, Então a nova `ruleset_version` aparece nas respostas; Dado um ruleset inválido em produção, Quando o analisador inicia, Então ele não fica pronto e a versão anterior continua atendendo | Must | FR-15, FR-21 |
| US-13 | Monitor | cadastrar as permissões e proibições explícitas de uma questão | que a ferramenta reflita o enunciado (R-01) | Dado `questions/L3-Q2.yaml` com `allow`/`deny` de R-xx ou de fatos e o campo `source`, Quando o PR passa na CI, é aprovado e publicado, Então a questão aparece no seletor; Dado um PR aberto por mim, Quando tento fazer o merge, Então ele exige a aprovação de um monitor-chefe ou professor, e não a minha; Dado um override que libera uma proibição geral (R-05…R-14), Quando a CI roda, Então o PR exige aprovação de professor; Dado um override que cita um R-xx inexistente, Quando a CI roda, Então o PR falha com o caminho do erro | Must | FR-11, FR-15, FR-21 |
| US-14 | Monitor-mantenedor | validar o ruleset com um comando, localmente e na CI | impedir que uma regra inválida chegue à produção | Dado um ruleset válido, Quando executo `ipc-rules validate rulesets/2026.2`, Então o comando sai com código 0; Dado um ruleset inválido, Quando executo, Então recebo erros com o caminho do campo e código ≠ 0; Dado um PR, Quando a CI roda, Então o mesmo comando é bloqueante | Must | FR-15, FR-21 |

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

## 5. Arquitetura do Sistema e Stack

### 5.1 Diagrama conceitual

Topologia de referência, usada localmente na Fase 0 e no servidor do CIn na Fase 2:

```
 ZONA NÃO CONFIÁVEL (Internet)
 +--------------------------------------------+
 | Navegador do Aluno / Monitor               |
 | SPA React + CodeMirror (código só em RAM)  |
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

 TB-5 CADEIA DE ENTREGA: rulesets/*.yaml + código (GitHub, CODEOWNERS) -> GitHub Actions
 (lint, testes, golden, segurança, Trivy) -> GHCR (imagem por digest) -> deploy SSH -> compose
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
                | (4) assíncrono, TLS (a partir da Sprint 14)
================|============ TB-4: Render -> banco =============================================
 +--------------v---------------+
 | Supabase (PostgreSQL): papel |
 | ipc_writer, só INSERT        |
 +------------------------------+
```

### 5.2 Descrição dos componentes e do fluxo

#### 5.2.1 Componentes

- **C1 — SPA web (`frontend/`).** Editor CodeMirror 6, leitura local de `.py` com `FileReader` (FR-02), seletores de lista e questão alimentados por `GET /api/v1/lists` e `GET /api/v1/questions` (FR-03), chamada a `/validate` com `AbortController` de 10 s, diagnósticos com `@codemirror/lint` (FR-13) e renderização dos estados (FR-20). Gera um `X-Client-Id` (`crypto.randomUUID()` guardado em `sessionStorage`), usado só pelo rate limit. O código **não** é gravado em `localStorage`, para não ficar exposto em computadores compartilhados de laboratório. Na Fase 1, a SPA é servida pela Vercel e chama a API no Render com CORS restrito à sua origem.
- **C2 — Borda (`caddy`).** TLS automático via ACME, HSTS, CSP, `request_body max_size 128KB` como barreira anti-abuso (o limite contratual de 50 KB fica na API), timeouts de leitura e escrita de 10 s, *reverse proxy* de `/api/*` para `api:8000` e arquivos estáticos da SPA. O access log tem filtro que remove `remote_ip`. A SPA e a API ficam na mesma origem, então não há cabeçalho CORS. Na Fase 1 não há Caddy: a borda é a do Render (TLS) e a da Vercel, e o limite de corpo é aplicado pela própria `api`.
- **C3 — `api` (FastAPI).** Cadeia de middlewares nesta ordem: `request_id`, guarda de tamanho (413), rate limit em memória (*token bucket*: 10/min por `X-Client-Id`; por IP, 120/min para IPs externos e 1.000/min para as faixas do campus em `RATE_LIMIT_CAMPUS_CIDRS`; IP só em RAM e TTL de 2 min), admissão (`asyncio.Semaphore` com capacidade = 2 × workers e espera máxima de 1 s, senão 503), validação Pydantic (FR-04), cliente `httpx` para o analisador (timeout de 3 s), validação de esquema e tamanho (≤ 256 KB) da resposta do analisador, resposta ao cliente e enfileiramento da telemetria. Um contrato `import-linter` proíbe `import ast` no pacote `ipc_api`, de modo que a API nunca analisa código (NFR-09). Na Fase 1, o IP do cliente usado no rate limit é o último endereço inserido pelo proxy do Render no `X-Forwarded-For`.
- **C4 — `analyzer`.** FastAPI interno com 1 processo uvicorn e um `pebble.ProcessPool` (2 workers [PREMISSA P-04], contexto `forkserver`, `max_tasks=500`). O *initializer* de cada worker aplica `RLIMIT_AS` = 256 MB, `RLIMIT_FSIZE` = 0 e `RLIMIT_NOFILE` = 32. `RLIMIT_CPU` não é usado porque é cumulativo por processo; o limite de tempo é o timeout de parede de 2 s, com *kill* e substituição do worker. Endpoints internos: `POST /internal/analyze`, `GET /internal/ruleset/manifest`, `GET /internal/rulesets/effective`, `GET /internal/health`. Na Fase 1, o `analyzer` roda como processo separado dentro do serviço do Render: UID 10002, ambiente vazio, escuta só em `127.0.0.1` e workers com seccomp sem sockets de rede nem `execve` (biblioteca `pyseccomp`); são 2 workers de até 160 MB para caber nos 512 MB do plano [PREMISSA].
- **C5 — Motor de regras (`backend/src/ipc_analyzer/engine`).** Funções puras sem estado global mutável, detalhadas em 5.2.3.
- **C6 — Ruleset (`rulesets/`).** YAML, mais `rulesets/schema/ruleset.schema.json`. Na construção da imagem, `ipc-rules compile` gera `ruleset.compiled.json` com SHA-256. O analisador carrega esse arquivo uma vez, como estrutura imutável (FR-15).
- **C7 — Telemetria (Sprint 14).** Fila `asyncio.Queue` limitada a 10.000 eventos, gravação em lote (100 eventos ou 2 s) via `asyncpg` com o papel `ipc_writer`. Se a fila transbordar, o evento é descartado e a métrica `telemetry_dropped_total` é incrementada; a resposta ao aluno nunca é bloqueada.
- **C8 — Observabilidade.** Logs JSON em stdout (`structlog`), coletados pelo Grafana Alloy e enviados ao Grafana Cloud [PREMISSA: plano gratuito]. Métricas `/metrics` (`prometheus-client`) expostas só na rede interna. Monitoramento externo pelo UptimeRobot (plano gratuito, intervalo de 5 min): um monitor em `/ready` do backend, que também impede o serviço gratuito do Render de dormir, e outro na SPA da Vercel, ambos com alerta por e-mail.
- **C9 — CI/CD.** GitHub Actions, imagens no GHCR referenciadas por digest e deploy por SSH com aprovação de *environment*. Staging e produção rodam como projetos Compose separados na mesma VM [PREMISSA].

#### 5.2.2 Fluxo de uma submissão e contrato da API

1. A SPA envia `POST /api/v1/validate` com `{ "code": str, "list_number": 1..6, "question_id": "L3-Q2" | null }` e o cabeçalho `X-Client-Id`.
2. A borda aplica TLS e repassa à `api`: o Caddy nas Fases 0 e 2, com limite de corpo de 128 KB (413), e o Render na Fase 1, quando o limite de corpo fica na `api`.
3. A `api` aplica, nesta ordem: limite de taxa (429), admissão (503) e validação. A validação recusa lista fora de `ENABLED_LISTS`, questão inexistente no período do ruleset ativo (P-07), UTF-8 inválido, byte nulo, código acima de 51.200 bytes ou acima de 1.000 linhas, com 413 ou 422.
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
  "syntax_error": null,
  "violations": [ { "rule_id": "R-46", "category": "FORA_DA_LISTA", "line": 4, "col": 2,
    "end_line": 4, "end_col": 15, "construct": "method:append", "allowed_from_list": 3,
    "message": "O método append() só é permitido a partir da Lista 3." } ] }
```

Códigos de erro: 413 `PAYLOAD_TOO_LARGE`, 422 `INVALID_INPUT` / `LIST_NOT_ENABLED` / `UNKNOWN_QUESTION` / `ANALYSIS_LIMIT`, 429 `RATE_LIMITED`, 503 `OVERLOADED` / `ANALYZER_UNAVAILABLE`, sempre no formato `{ "error": { "code", "message", "retry_after_s" } }`.

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
| `derived:recursion` | Grafo de chamadas entre `FunctionDef` do aluno, com detecção de ciclo por Tarjan | Recursão direta ou mútua (C-03) |

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

Formato de override por questão em `rulesets/2026.2/questions/<question_id>.yaml`; a pasta do período resolve a reinicialização da numeração a cada período (P-07). Os campos são `question_id`, `list`, `source` (referência ao enunciado), `allow` (R-xx), `allow_facts` (fatos fora do catálogo que o enunciado permita explicitamente) e `deny` (R-xx ou fatos). **Nenhuma questão real está cadastrada. O conteúdo vem do enunciado e é cadastrado por monitores, monitores-chefe ou professores, com aprovação de monitor-chefe ou professor (US-13, Q-08).**

**Algoritmo de avaliação.** Para a lista *n* e a questão *q*:

1. Os guards de entrada (FR-04) e o `ast.parse` (FR-05) são executados.
2. Os limites de AST são verificados: profundidade até 200 e no máximo 60.000 nós.
3. As ligações de nomes do aluno são coletadas.
4. Os fatos são extraídos.
5. Cada ocorrência de fato *f* é classificada pela primeira condição verdadeira:
   1. *f* é estrutural: aceito.
   2. *f* está em `q.deny`: `PROIBIDO_NA_QUESTAO`.
   3. *f* está em `q.allow` ou `q.allow_facts`: aceito (R-01).
   4. *f* casa com uma regra `deny` geral: `ANULACAO`.
   5. *f* casa com uma regra `allow` em que `since_list ≤ n ≤ until_list` e o predicado `when` é verdadeiro: aceito (R-03).
   6. *f* casa com uma regra `allow` cujo predicado é falso: violação com o ID dessa regra (ex.: R-37).
   7. *f* casa com uma regra `allow` em que `since_list > n`: `FORA_DA_LISTA`, com `allowed_from_list`.
   8. Nenhuma das anteriores: R-04, `NAO_CONSTA`.
6. Cada `requirement` com `list = n` exige pelo menos um fato de `require_any`; se faltar, gera `EXIGENCIA`.
7. As violações são deduplicadas por (`rule_id`, `line`, `col`), ordenadas e truncadas em 200.

O índice `fato → regras` é um dicionário montado na carga, com busca O(1) por fato.

**Fronteira de extensibilidade.** Criar, alterar ou remover regras, mudar listas, condições que usam predicados existentes, exigências e overrides de questão são mudanças **só de dados** (NFR-17). Criar um **novo tipo de fato** ou um **novo predicado** exige código no motor, com ADR e testes, e é o único ponto de extensão programática.

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
| R-61…R-67 | `node:Dict`; `builtin:dict`, `enumerate`, `zip` (R-64); `method:keys`, `values`, `items`, `get`, `update`; `node:Lambda` |
| R-68 | `derived:recursion` (exigência) |

#### 5.2.4 Modelo de dados (telemetria, Sprint 14)

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
-- papéis: ipc_writer (INSERT nas 2 tabelas); ipc_reader (SELECT só nas views v_*)
-- views agrupam por (semester, question_id): v_top_rules_by_list, v_syntax_error_rate
-- expurgo diário de registros com mais de 12 meses (pg_cron, P-06)
```

### 5.3 Tabela de tecnologias

| Camada | Tecnologia | Justificativa técnica | Alternativa descartada e motivo |
|---|---|---|---|
| Parser do analisador | Python 3.13, a mesma versão do Dikastis (Q-01), com o módulo `ast` da stdlib | A gramática é idêntica à do interpretador que corrige (NFR-21), sem dependência externa no caminho crítico, e `ast.parse` não executa código | tree-sitter-python: tolera erros e serve a várias linguagens, mas tem gramática própria que pode divergir do CPython e não reproduz o `SyntaxError` do Dikastis |
| Isolamento de processo | Pebble 5.x (`ProcessPool` com timeout por tarefa e `max_tasks`) e `resource.setrlimit` | Mata o worker em timeout, o que não é possível com threads. A reciclagem limita vazamento de memória. É uma biblioteca pequena e madura | `concurrent.futures.ProcessPoolExecutor`: não cancela uma tarefa em execução, e um worker travado fica preso |
| API e serviço interno | FastAPI, Uvicorn e Pydantic v2 | Mesmo ecossistema do motor, o que significa uma única linguagem para uma equipe rotativa. Contrato validado de forma declarativa e OpenAPI gerado automaticamente. Modelo async adequado ao I/O com o analisador e a telemetria | Node.js/Express: segunda linguagem para a equipe e modelos de contrato duplicados. Django REST: ORM e admin desnecessários num caminho sem estado |
| Ruleset | YAML, mais JSON Schema 2020-12 validado com `jsonschema`, compilado para JSON na build | O YAML aceita comentários, onde o professor cita a fonte de cada regra. O schema aponta o caminho do campo com erro. A compilação evita o parse de YAML em produção | JSON puro (§12 do rascunho): não aceita comentários. Banco de dados com UI de administração: exige autenticação e UI fora do escopo e perde a revisão por PR |
| Frontend | React 18, Vite, TypeScript e Tailwind CSS (§9 do rascunho) | Tipos gerados do OpenAPI (`openapi-typescript`), build rápido e ecossistema maduro | Vanilla JS: difícil de manter com os estados exigidos pelo FR-20 |
| Editor | CodeMirror 6 com `@codemirror/lang-python` e `@codemirror/lint` | Diagnósticos por intervalo de forma nativa (FR-13), operável por teclado, bundle bem menor que o do Monaco | Monaco: alguns MB a mais, o que compromete o NFR-03 em rede móvel |
| Borda | Caddy 2 nas Fases 0 e 2; na Fase 1, a borda gerenciada do Render e da Vercel | TLS automático via ACME, limite de corpo e filtro de log nativos, configuração curta | Nginx com certbot: renovação de certificado e configuração manuais, mais passos para uma equipe rotativa |
| Hospedagem | Fase 0: Docker Compose local. Fase 1 (piloto em 2027.1): SPA na Vercel e backend em 1 serviço Docker no Render (plano Starter recomendado). Fase 2: Docker Compose no servidor do CIn (ADR-03) | No piloto, custo baixo e nenhum servidor para administrar (decisão do projeto, Q-10). Nas Fases 0 e 2, redes `internal: true`, `read_only`, `cap_drop`, `pids_limit` e `mem_limit` testáveis (NFR-07) | VM de nuvem com Compose já no piloto: isolamento completo, mas exige administrar o sistema operacional com 4 a 8 h por semana. Kubernetes: custo operacional desproporcional |
| Isolamento por processo (Fase 1) | `supervisord`, UIDs distintos para `api` e `analyzer` e `pyseccomp` (libseccomp) nos workers | Compensa a falta de rede interna e de flags de contêiner no Render: o analisador não lê o ambiente da API, não abre sockets de rede e não executa programas | nsjail ou bubblewrap: dependem de *user namespaces*, em geral indisponíveis em PaaS |
| Imagem base | `python:3.13-slim` (Debian), fixada por digest | glibc instala wheels binárias sem compilação, a superfície é reduzida e há atualizações de segurança do Debian | Alpine: o musl força compilar wheels e tem diferenças de comportamento. Distroless: depuração mais difícil para a equipe (reavaliar após o MVP) |
| Telemetria/BD | PostgreSQL gerenciado (Supabase, §2 do rascunho) com `asyncpg` e o papel `ipc_writer`, que só faz INSERT | Backup gerenciado, SQL para as views do FR-17 e menor privilégio via conexão Postgres direta | supabase-py/REST com chave de serviço: credencial com privilégio amplo. SQLite: perde dados a cada deploy (§19 do rascunho) |
| Observabilidade | structlog (JSON), prometheus-client, Grafana Alloy e Grafana Cloud [PREMISSA: plano gratuito], mais o UptimeRobot (linha seguinte) | Logs, métricas e alertas (NFR-14, NFR-15) sem servidor próprio | Prometheus, Grafana e Loki auto-hospedados: três serviços a mais para operar na VM |
| Keep-alive e monitoramento externo (Fase 1) | UptimeRobot, plano gratuito, checagem de `/ready` a cada 5 min e da SPA | O serviço gratuito do Render dorme após 15 min sem tráfego; uma checagem a cada 5 min o mantém acordado e ainda mede a disponibilidade (NFR-06) e alerta por e-mail (US-19). Um único serviço acordado o mês todo cabe nas 750 h/mês do plano gratuito | Cron do GitHub Actions: o intervalo mínimo é de 5 min e as execuções costumam atrasar, o que deixaria o serviço dormir. Render Starter: elimina a dormência, mas custa cerca de US$ 7/mês |
| Repositório e CI/CD | Monorepo no GitHub, GitHub Actions e GHCR | Ruleset, motor e contrato mudam no mesmo PR, com CODEOWNERS por pasta e registro de imagens integrado | Dois repositórios (§20–21 do rascunho): contrato e ruleset ficam dessincronizados entre front e back |
| Qualidade e segurança na CI | ruff, `mypy --strict`, import-linter, pytest (com hypothesis e pytest-benchmark), Vitest com RTL, Playwright com axe-core, k6, Semgrep, Bandit, pip-audit, npm audit, Trivy e gitleaks | Cada ferramenta verifica um NFR específico (NFR-02, 04, 05, 09, 13, 16, 18, 19) | Só linters e testes unitários (§18 do rascunho): não verificam isolamento, evasão nem carga |

### 5.4 Modelo de ameaças

Premissa operacional (Zero Trust): todo código submetido e toda requisição anônima são não confiáveis, e a resposta do `analyzer` também é tratada como não confiável pela `api`. Cada componente roda com o menor privilégio possível. A segurança não é absoluta, e o risco residual de cada ameaça está declarado abaixo.

| Ameaça | Vetor | Controle | Como é verificado | Risco residual |
|---|---|---|---|---|
| 1. Execução remota de código (RCE) no servidor | O código chega a `eval`/`exec`/`compile`/`import`/`pickle` por erro de implementação, ou um payload como `__import__("os").system(...)` é enviado | Nenhum caminho de execução: a entrada só passa por `ast.parse`, num único ponto (`engine/parse.py`). O import-linter proíbe `ast` na `api`. A análise roda só no `analyzer`, sem segredos, sem root e com FS read-only, além de `RLIMIT_FSIZE` = 0 | Semgrep e Bandit bloqueantes (NFR-09); corpus de RCE com canário (`/tmp/canary`), cuja ausência é verificada após a suíte | Baixo: depende de uma regressão humana, barrada pela CI e por CODEOWNERS |
| 2. RCE por vulnerabilidade do parser do CPython | Entrada artesanal que explora um bug de memória em `ast.parse` (código C) | Versão do Python suportada e atualizada. O parse só ocorre no worker isolado: sem segredos, sem egress, sem escrita, sem root, com `cap_drop: ALL`, `no-new-privileges` e o seccomp padrão do Docker. O worker é reciclado | Teste de configuração (NFR-07), fuzzing com hypothesis na CI, varredura semanal com Trivy | Baixo: exige um 0-day, e o impacto fica contido num contêiner sem dados e sem rede Na Fase 1, o worker divide o contêiner com a API e a contenção depende de UID separado e seccomp: risco Médio-baixo durante o piloto. |
| 3. Esgotamento por arquivo enorme | Corpo com vários MB, ou 50 KB com milhares de linhas | Caddy recusa acima de 128 KB (413). A `api` recusa acima de 51.200 bytes ou 1.000 linhas (413/422) antes de chegar ao analisador. A SPA bloqueia arquivos acima de 50 KB | Testes de segurança 1 e 2 (seção 8) | Muito baixo |
| 4. Esgotamento por código que trava o analisador | Aninhamento profundo (`((((…`), cadeia `1+1+…` com 25 mil termos, f-strings aninhadas, literais gigantes | Travessia iterativa, sem `RecursionError`. Profundidade até 200 e no máximo 60.000 nós. Timeout de parede de 2 s com kill. `RLIMIT_AS` de 256 MB. A admissão limita a concorrência | Testes 4 a 6 (seção 8), fuzzing com hypothesis, `/ready` = 200 após a suíte | Baixo: cada requisição de ataque consome no máximo 2 s de um dos 2 workers, e o rate limit limita a taxa |
| 5. Laço infinito | `while True:` ou recursão infinita no código do aluno | O código nunca é executado. O custo do motor é proporcional ao número de nós, que já é limitado | Teste 7: `while True: pass` responde em menos de 100 ms | Nulo para o código do aluno; um bug do próprio motor é contido pelo timeout |
| 6. Acesso indevido à rede e ao sistema de arquivos | Um worker comprometido tenta exfiltrar dados ou ler e escrever arquivos | `analyzer_net` com `internal: true` (sem rota externa), rootfs read-only, nenhum volume, `RLIMIT_FSIZE` = 0, UID 10001, nenhum segredo no ambiente ou no FS | Teste 11 na CI: conexões TCP e DNS externas falham, a escrita falha, `env` não tem segredos | Baixo: só é possível ler o código da imagem, que é público Na Fase 1, sem rede interna no Render, o bloqueio de rede é feito por seccomp no worker; se o Render não permitir seccomp, o risco sobe para Médio durante o piloto e fica registrado. |
| 7. Vazamento de dados de outros alunos | Mistura de estado entre requisições, código em logs ou telemetria, computador de laboratório compartilhado | Motor puro, sem estado global mutável. Worker reciclado. Código nunca logado nem persistido. Telemetria sem código e sem IP. A SPA não grava código em `localStorage` | Teste de concorrência com marcadores distintos (eles nunca se cruzam), teste canário (NFR-11), esquema de log (NFR-14) | Baixo: resta o próprio aluno deixar o código visível na aba aberta |
| 8. Evasão das regras por construções indiretas ou dinâmicas | `getattr(s, "split")()`, `f = s.split`, `eval("…")`, `__import__`, `globals()`, `__builtins__`, `type("C", (), {})`, sombreamento de built-ins, `{*x}` | *Default deny* por fato (5.2.3): built-ins fora do catálogo, todo `Attribute` e todo dunder geram violação. Nomes ligados pelo aluno são distinguidos de built-ins. `type` com 3 argumentos cai em R-09 (Q-07) | Corpus golden de evasão com ≥ 30 casos (NFR-18) e matriz de mapeamento revisada pelo professor (Q-02) | Médio-baixo: o tipo do receptor não é inferido (`x.count()` em string ou lista; `in` em string ou lista). Isso é mitigado porque listas, tuplas e dicionários só podem ser criados a partir das listas que os liberam. Aceito e documentado |
| 9. Abuso volumétrico (DoS) | Rajadas na véspera do prazo, scripts, botnets | Rate limit por cliente e por IP (com limite próprio para os IPs de NAT do campus, P-04), admissão com 503 rápido, timeouts na borda | Teste de stress do NFR-05, com tráfego concentrado em poucos IPs | Médio: um DDoS distribuído supera a VM única (ver REC-01). Um usuário mal-intencionado dentro do campus pode trocar de `X-Client-Id` e usar até 1.000 req/min do IP compartilhado; nesse caso, a admissão devolve 503 aos demais até o limite do campus ser reduzido |
| 10. Adulteração do ruleset ou da cadeia de suprimentos | PR malicioso liberando construções, dependência comprometida, imagem trocada | CODEOWNERS em `rulesets/**` (professor no ruleset base; monitor-chefe ou professor nas questões, sem autoaprovação; professor para overrides que liberam R-05…R-14), *branch protection*, golden obrigatório, lockfiles com hash, imagens referenciadas por digest, Trivy | CI bloqueante e auditoria de PR | Baixo |
| 11. XSS na SPA | Código ou mensagem contendo `<script>` renderizado na página | O CodeMirror renderiza texto puro. As mensagens são exibidas como texto, sem `dangerouslySetInnerHTML`. CSP estrita | Teste e2e com payload de XSS e regra de lint React | Baixo |
| 12. Vazamento da credencial do banco | Leitura das variáveis de ambiente da `api` | A credencial existe só na `api` (Docker secret), com papel que só faz INSERT. O `analyzer` não tem nenhum segredo | Teste de configuração (NFR-07) e gitleaks | Baixo: a credencial vazada só permite inserir eventos falsos Na Fase 1, a credencial existe só no ambiente do processo da API (UID 10001), que o UID 10002 do analisador não consegue ler. |

## 6. ADRs (Architecture Decision Records)

### ADR-01 — Modelo de análise e isolamento do código do aluno

**Título:** Análise exclusivamente estática, por AST, num serviço analisador isolado com workers descartáveis e limitados.

**Status:** Aceito. Versão alvo confirmada: Python 3.13+ (Q-01), com suporte de segurança até outubro de 2029.

**Contexto:** As regras do catálogo (R-01…R-68) são sintáticas: descrevem construções da linguagem, não comportamento. O rascunho define a verificação como estática (§1, §3, §15.1) e deixa a execução de testes fora do escopo (§3), já que o Dikastis executa as soluções. Pelo rascunho, o parse aconteceria no mesmo processo da API, que guarda a credencial de telemetria, sem limite de tempo e com visitor recursivo (1.2 #2). A restrição do projeto proíbe executar ou importar o código no processo da API e exige limites de tamanho e de tempo também na análise estática. As duas hipóteses de verificação, estática e dinâmica, foram avaliadas.

**Decisão:**
1. Não há execução do código: só `ast.parse` com a gramática alvo, extração de fatos e avaliação de política (5.2.3).
2. A `api` nunca faz parse. Isso é garantido pelo import-linter (NFR-09).
3. O parse e o motor rodam no serviço `analyzer`, que não tem segredos, não tem egress (`internal: true`), usa rootfs read-only, UID 10001, `cap_drop: ALL` e `no-new-privileges`, e tem `pids_limit` de 64 e memória de 512 MB. Na Fase 1 (Render), sem controle de rede nem de flags do contêiner, o isolamento é por processo: UID 10002, ambiente vazio e workers com seccomp sem sockets de rede nem `execve` (ADR-03).
4. Dentro do `analyzer`, cada análise roda num worker do pool Pebble, com timeout de parede de 2 s e *kill*, `RLIMIT_AS` de 256 MB, `RLIMIT_FSIZE` = 0 e reciclagem a cada 500 tarefas.
5. A travessia é iterativa, com profundidade máxima de 200 e no máximo 60.000 nós.
6. A `api` trata a resposta do `analyzer` como não confiável e valida esquema e tamanho.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: AST num `analyzer` isolado, com pool limitado | O tempo é limitado de fato (kill de processo). Uma falha do parser fica contida sem segredos e sem rede. As fronteiras de confiança são verificáveis por teste (NFR-07) | Mais um serviço e um salto HTTP interno (cerca de 1–3 ms). O pool exige calibração de `RLIMIT_AS` (P-04) |
| B. AST no próprio processo da API (§8 e §10 do rascunho) | Mais simples e com a menor latência | `ast.parse` roda em C e não pode ser interrompido por timeout em thread. `RecursionError`/`MemoryError` derrubam o worker que atende todos os alunos. O parser divide o processo com a credencial do banco |
| C. AST no navegador via Pyodide (WebAssembly) | Nenhum código chega ao servidor e a escala é gratuita | Download de vários MB na primeira visita, o que viola o NFR-03. Lento em dispositivos modestos. A versão do Python do Pyodide pode não coincidir com a do Dikastis (NFR-21). Ruleset e telemetria continuam exigindo servidor |
| D. Hipótese dinâmica: executar a solução em sandbox (nsjail, gVisor ou Firecracker) com casos de teste | Detectaria comportamento em tempo de execução | Não acrescenta nada à verificação das regras, que são sintáticas. Está fora do escopo (§3 do rascunho), duplica o papel do Dikastis e amplia muito a superfície de RCE. Se um dia for adotada, exige um serviço separado em sandbox descartável, sem rede, sem privilégios e com limites de CPU, memória, tempo e processos, e um ADR novo |

**Consequências positivas:** o código nunca é executado. Uma entrada maliciosa custa no máximo 2 s de um worker e não derruba o serviço. Uma eventual exploração do parser não alcança dados nem credenciais. Cada controle é verificado automaticamente (seção 8).

**Consequências negativas:** a operação fica mais complexa (dois serviços Python e uma rede interna). A análise estática não infere tipos, o que deixa risco residual na ameaça 8 da seção 5.4. Os limites de recursos precisam ser recalibrados a cada mudança de versão do Python.

### ADR-02 — Motor de regras declarativo baseado em fatos

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
- CODEOWNERS exige aprovação de professor no ruleset base e de monitor-chefe ou professor nos arquivos de questão, sem autoaprovação; overrides que liberam R-05…R-14 exigem professor (C-02, Q-08).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida: ruleset declarativo sobre fatos | Representa todos os mecanismos do catálogo. Mudar regras não exige código (NFR-17). O *default deny* granular fecha a evasão dinâmica. É auditável por PR | Depende da matriz de mapeamento (validada nas decisões Q-02 a Q-07). Um fato ou predicado novo exige código e um ADR |
| B. Esquema do rascunho com métodos `visit_*` por regra | Simples de começar | Não expressa R-01, R-02, R-37 nem R-68. Deixa passar built-ins e métodos não catalogados. Toda regra nova é código |
| C. Motor de terceiros (regras Semgrep ou OPA/Rego) | Linguagem de regras madura e com ferramentas | O Semgrep foi feito para lista de bloqueio, não para lista de permissão cumulativa, e seu runtime custa centenas de ms por chamada. O OPA acrescenta uma linguagem e um runtime a mais para a equipe |
| D. Regras em banco de dados, com UI de administração | O professor edita sem Git | Exige autenticação, autorização e UI, que estão fora do escopo. Perde a revisão por PR e o gate de testes golden |

**Consequências positivas:** o veredito pode ser rastreado até o R-xx e a página do documento. Adicionar uma lista ou uma questão é um PR só de dados. O corpus golden funciona como especificação executável do documento.

**Consequências negativas:** a semântica depende da qualidade da matriz de mapeamento. Casos ambíguos novos, não cobertos pelas decisões Q-02 a Q-07, exigem decisão registrada antes de entrar no ruleset. Há uma curva de aprendizado do vocabulário de fatos para os mantenedores.

### ADR-03 — Topologia de implantação por fase

**Por que está entre as três mais críticas:** é nas vésperas de prazo que os alunos mais precisam da ferramenta, e a hospedagem define latência, disponibilidade, custo e quanto do isolamento do ADR-01 pode ser aplicado.

**Título:** Implantação em três fases: Docker Compose local, Vercel + Render no piloto de 2027.1 e Docker Compose no servidor do CIn.

**Status:** Aceito em 01/10/2026 (Q-10). A Fase 2 depende dos critérios de eficácia (P-09) e dos requisitos em Q-12, adiada para depois do piloto.

**Contexto:** O projeto tem um único desenvolvedor com 4 a 8 h por semana (P-02, Q-13) e pouco orçamento. O servidor do CIn só será usado depois de comprovada a eficácia (P-03). O pico de referência é de 500 req/min (P-01), com P95 ≤ 200 ms. O `analyzer` precisa ficar separado de dados e credenciais (ADR-01). O rate limit em memória só é consistente com uma única instância da `api`, o que vale em todas as fases.

**Decisão:**
- **Fase 0 (desenvolvimento, até fevereiro de 2027):** Docker Compose local com `caddy`, `api` e `analyzer`, redes `edge_net` e `analyzer_net` (`internal: true`), sem custo.
- **Fase 1 (piloto em 2027.1):** SPA estática na Vercel (plano Hobby) e backend em 1 serviço Docker no Render, com dois processos sob `supervisord`. A `api` roda com UID 10001 e é a única com a credencial da telemetria. O `analyzer` roda com UID 10002, ambiente vazio, escuta só em `127.0.0.1` e seus workers aplicam seccomp sem sockets de rede nem `execve`. O CORS aceita só a origem da SPA, e o deploy é disparado por *deploy hook* depois que a CI passa.
- **Plano do Render:** começa no gratuito, que dorme após 15 min sem tráfego. Para evitar o cold start, o UptimeRobot acessa `/ready` a cada 5 min, o que mantém o serviço acordado e ainda mede a disponibilidade. Um serviço acordado o mês inteiro usa até 744 h, dentro das 750 h/mês do plano gratuito; por isso não pode haver um segundo serviço gratuito sempre ativo. O gratuito tem só 0,1 CPU: se o teste de carga da Sprint 12 ou o P95 numa véspera de prazo passar de 200 ms, o backend migra para o Starter (cerca de US$ 7 por mês, 0,5 CPU). Com 512 MB, o analisador usa 2 workers de até 160 MB [PREMISSA, calibrar no deploy].
- **Fase 2 (servidor do CIn, após o piloto):** o mesmo Compose da Fase 0, com Caddy e redes segregadas; deploy *pull-based*, porque o acesso externo ao CIn exige VPN (Q-12).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Escolhida para as Fases 0 e 2: Docker Compose numa máquina própria | Isolamento de rede declarativo e testável (NFR-07), sem cold start, ambiente reproduzível (NFR-20) | Exige administrar o sistema operacional, o que no piloto pesaria sobre um único desenvolvedor com 4 a 8 h por semana |
| B. Escolhida para a Fase 1: Vercel + Render (decisão do projeto, Q-10) | Custo baixo, TLS e deploy gerenciados, nenhum servidor para administrar | Sem rede interna nem flags de contêiner, então o isolamento passa a ser por processo (UID, ambiente vazio, seccomp). Exige CORS. No plano gratuito, a dormência é contornada pelo UptimeRobot, mas a CPU continua limitada (0,1 CPU) |
| C. Cloud Run com `min-instances=1` e sandbox gVisor | Isolamento gVisor gerenciado e escala automática | Conta e faturamento GCP, IAM e VPC complexos para um único desenvolvedor, custo variável |

**Consequências positivas:** o piloto começa em 2027.1 sem servidor próprio para administrar. A migração para o CIn reaproveita as imagens e o Compose da Fase 0.

**Consequências negativas:** na Fase 1, o isolamento é mais fraco que nas Fases 0 e 2 (risco residual em 5.4, ameaças 2, 6 e 12) e depende de o Render permitir seccomp. No plano gratuito, 0,1 CPU pode não atender o NFR-01 no pico (gatilho para migrar ao Starter), e o keep-alive depende de os termos do plano gratuito do Render continuarem permitindo pings de monitoramento, o que precisa ser confirmado. Reinícios e deploys ainda causam alguns segundos de indisponibilidade. O plano Hobby da Vercel é para uso não comercial, o que precisa ser confirmado para o projeto. Há um único ponto de falha em todas as fases, e um DDoS distribuído excede a capacidade (REC-01).
## 7. Roadmap de Sprints e Tasks do MVP

### 7.1 Roadmap

Cadência e capacidade conforme P-02 e Q-13: um único desenvolvedor, com 4 a 8 h por semana, em sprints de 2 semanas a partir de 05/10/2026. O plano usa 6 SP por sprint (1 SP ≈ 2 h de trabalho focado [PREMISSA]) e metade disso nos recessos de fim de ano e de Carnaval. A meta é ter monitores e alunos usando a ferramenta em 2027.1 (Q-10), com início do período estimado em março de 2027 (P-10).

- **Fase 0 — MVP local (Sprints 1–9):** tudo roda com Docker Compose na máquina do desenvolvedor. O MVP (Marco 1) fica pronto em 07/02/2027.
- **Fase 1a — Preparação do piloto (Sprints 10–12):** rate limit, isolamento por processo no Render, deploy na Vercel e no Render e apresentação a monitores-chefes e professores (Marco 2), com liberação do piloto na Lista 1.
- **Fase 1b — Piloto em 2027.1 (Sprints 13–18):** cada lista é habilitada (`ENABLED_LISTS`) antes da data em que é liberada aos alunos.
- **Fase 2 — Servidor do CIn:** após 2027.1 e só se a P-09 for atingida. Adiada, junto com a Q-12, para depois do piloto.

Sensibilidade ao ritmo: com 8 h/semana, a preparação termina por volta de 24/01/2027 e sobra cerca de 1 mês de folga. Com 6 h/semana, termina na primeira semana de março, sem folga. Com 4 h/semana, só termina por volta de maio de 2027, e o piloto começaria a partir da Lista 2 ou 3.

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
| 12 (08/03–21/03, Marco 2) | Apresentação e liberação do piloto com a Lista 1 | US-06 (Lista 1), US-11 | Apresentação a monitores-chefes e professores; exigência R-02 da L1 ativa; aviso de que regras específicas de questão ainda não são consideradas; monitores e alunos usando a Lista 1; teste de carga curto (k6) no plano gratuito decide se o backend precisa do Starter antes do primeiro prazo | Data de liberação da Lista 1 ainda estimada (P-10). Se o teste indicar o Starter, há custo a partir de março (cerca de US$ 7/mês) |
| 13 (22/03–04/04) | Lista 2 e validação com gabaritos | US-07 | `zip` condicional e R-02 da L2 ativos; gabaritos de períodos anteriores sem violação (corpus privado, Q-14); L2 habilitada | Gabaritos que usam permissões de questão aparecem como violação até a Sprint 17 |
| 14 (05/04–18/04) | Telemetria mínima e alertas | US-16, US-19 | Eventos anônimos no Supabase; `v_top_rules_by_list` consultável; alertas do UptimeRobot (ativos desde a Sprint 11) revisados num exercício de falha | As Listas 1–2 ficam sem dados de uso para a P-09 |
| 15 (19/04–02/05) | Listas 3–4 | US-08 | L3–L4 habilitadas; `.append()` na L2 mostra "permitido a partir da Lista 3" | Mapeamento de L3–L4 com casos novos |
| 16 (03/05–16/05) | Listas 5–6 e recursão obrigatória | US-06 | L5–L6 habilitadas; código sem recursão na L6 mostra R-68; R-02 ativa em todas as listas | Grafo de chamadas para recursão mútua (C-03) |
| 17 (17/05–30/05) | Regras por questão e governança | US-04, US-12, US-13, US-14 | Overrides em `rulesets/2027.1/questions/` cadastrados por monitores e aprovados por monitor-chefe ou professor; `ipc-rules validate` bloqueante na CI | Monitores precisam aprender o fluxo de PR (template e guia em `RULES.md`) |
| 18 (31/05–13/06) | Carga, eficácia e handover | US-20, US-22, US-23 | Relatório k6 no Render; consultas do relatório de eficácia (P-09) prontas; runbook e guia de onboarding | Fim do período 2027.1 ainda estimado (P-10) |
| Backlog (após o piloto) | Melhorias de experiência | US-02, US-09, US-10, US-21 | Upload de `.py`, clique na violação leva à linha, tela de permissões, acessibilidade WCAG AA | Dependem da avaliação do piloto |

### 7.2 Tasks do MVP (Sprints 1 a 9)

| ID | História | Descrição técnica | Componente/API/Esquema | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|
| S1-01 | US-15 | Criar o monorepo com `pyproject.toml` (ruff com regras de segurança, `mypy --strict`, pytest), a guarda de código do NFR-09 e o workflow `ci.yml` (lint, type, test). O import-linter entra com a `ipc_api` (Sprint 8) e o `CODEOWNERS`, na Sprint 17 | Repositório `ip-checker/` (`backend/`, `frontend/`, `rulesets/`, `docs/`) e `.github/workflows/ci.yml` | 2 | — | Um PR com erro de lint ou de tipo é bloqueado pela CI |
| S1-02 | US-05 | Criar o modelo Pydantic do ruleset v2 e o loader imutável (`MappingProxyType` com índice `fato → regras`, *fail-fast*). Codificar R-03…R-36 em `base.yaml` (proibições gerais, Lista 1 e Lista 2 sem o `zip`, que depende de predicado), com mensagens em PT-BR e citação da fonte | `backend/src/ipc_analyzer/engine/ruleset.py`, `rulesets/2026.2/base.yaml`, `docs/mapping-R-xx.md` | 3 | S1-01 | Ruleset inválido impede o analisador de ficar pronto. A matriz registra as decisões Q-02 a Q-07 aplicáveis. Cobertura ≥ 90% |
| S2-01 | US-03, US-15 | Implementar os guards (UTF-8, até 51.200 bytes, até 1.000 linhas, sem NUL), o `parse` com a gramática do Python 3.13 e a tradução de `SyntaxError` para PT-BR, mais a medição iterativa de profundidade (≤ 200) e de nós (≤ 60.000, calibrado na S5-01) | `backend/src/ipc_analyzer/engine/guards.py`, `engine/parse.py` (único ponto com `ast.parse`) | 3 | S1-01 | Os testes dos limites passam. Uma cadeia `1+1+…` com 25 mil termos retorna `ANALYSIS_LIMIT` sem `RecursionError` |
| S2-02 | US-01, US-03 | Montar a SPA mínima contra o contrato de 5.2.2, com respostas simuladas: área de código com numeração de linhas, seletor de lista, painel com os estados do MVP e hook `useValidateCode.ts` com `AbortController` de 10 s | `frontend/src/components/*`, `frontend/src/hooks/useValidateCode.ts`, `frontend/src/types/api.ts` | 3 | S1-01 | Os testes Vitest/RTL dos estados válido, com violações, erro de sintaxe, entrada rejeitada e falha de rede passam |
| S3-01 | US-05 | Implementar a coleta de nomes ligados pelo aluno e o extrator iterativo de fatos (`node`, `op`, `cmp`, `builtin`, `method`, `kwarg`, `const`, `param`, `target:for_unpack`) | `backend/src/ipc_analyzer/engine/symbols.py`, `engine/facts.py` | 5 | S2-01 | `f = s.split` produz `method:split`. Uma variável do aluno chamada `len` não produz `builtin:len`. Cobertura ≥ 90% |
| S4-01 | US-05 | Implementar o avaliador de política v1: *default deny*, cumulatividade, proibições gerais e "fora da lista", com categorias, deduplicação e truncamento. Predicados e exigências entram nas Sprints 12–16; overrides de questão, na Sprint 17 | `backend/src/ipc_analyzer/engine/policy.py`, `engine/models.py` (`Violation`, `AnalysisResult`) | 3 | S1-02, S3-01 | Os testes de precedência passam. `type("C", (), {})` gera R-09 e `eval(...)` gera R-04 |
| S4-02 | US-05, US-15 | Montar o corpus golden das R-03…R-36 (≥ 3 casos por regra) e o corpus de evasão (`getattr`, `eval`, `__import__`, dunders, alias, sombreamento), escritos pelo monitor-desenvolvedor (P-08) | `backend/tests/golden/*.yaml` e `backend/tests/test_golden.py` | 3 | S4-01 | 0 FP e 0 FN, com job de CI bloqueante |
| S5-01 | US-15 | Implementar o pool Pebble (`forkserver`, 2 workers, `max_tasks` 500, *initializer* com `RLIMIT_AS`, `RLIMIT_FSIZE` e `RLIMIT_NOFILE`, timeout de 2 s) e o serviço interno | `backend/src/ipc_analyzer/runtime/pool.py`, `backend/src/ipc_analyzer/service/app.py`: `POST /internal/analyze`, `GET /internal/health` | 5 | S4-01 | Timeout mata e substitui o worker. `MemoryError` vira `ANALYSIS_LIMIT`. A memória base do worker é medida e registrada em P-04 |
| S6-01 | US-15 | Escrever o Dockerfile do analyzer (`python:3.13-slim` por digest, UID 10001, sem segredos) e o compose com `read_only`, `cap_drop: [ALL]`, `security_opt: no-new-privileges`, `pids_limit: 64`, `mem_limit: 512m` e rede `analyzer_net` com `internal: true` | `backend/Dockerfile`, `deploy/compose.yaml` | 2 | S5-01 | O teste de configuração (`docker inspect`) passa em 100% dos itens do NFR-07 |
| S7-01 | US-15 | Escrever a suíte de segurança contra o endpoint interno do analisador (itens 2 a 12 da seção 8) e os testes de isolamento do contêiner, como job de integração na CI | `backend/tests/security/test_malicious_submissions.py`, `backend/tests/security/test_isolation.py`, job `security` no `ci.yml` | 3 | S6-01 | 100% da suíte passa, nenhum 5xx genérico ocorre e `/internal/health` responde ao final |
| S8-01 | US-01, US-03 | Implementar o endpoint de validação com modelos Pydantic, `ENABLED_LISTS=1`, cliente `httpx` (timeout 3 s), mapeamento de erros (413, 422, 503), validação da resposta do analyzer, `GET /api/v1/lists`, `/health` e `/ready`, e o contrato import-linter que proíbe `ast` na API | `backend/src/ipc_api/routes/validate.py`, `routes/meta.py`, `schemas.py`, `clients/analyzer.py`; `POST /api/v1/validate` | 5 | S6-01 | Os testes de contrato OpenAPI passam. A L2 retorna 422 `LIST_NOT_ENABLED`. Com o analyzer parado, retorna 503 `ANALYZER_UNAVAILABLE` |
| S9-01 | US-01 | Configurar logs JSON (`structlog`) com `request_id`, `latency_ms`, `payload_bytes`, `ruleset_version` e `outcome`, um filtro que rejeita campos de código e IP, e o teste canário | `backend/src/ipc_api/logging.py`, `backend/src/ipc_analyzer/logging.py`, `backend/tests/test_log_contract.py` | 2 | S8-01 | O esquema do log é validado e o marcador canário aparece 0 vezes nos logs da suíte |
| S9-02 | US-01, US-03 | Integrar a SPA à API real (tipos gerados do OpenAPI) e escrever o smoke e2e local com Playwright | `frontend/src/services/api.ts`, `frontend/e2e/smoke.spec.ts` | 2 | S2-02, S8-01 | Código válido na L1 mostra sucesso; `for` na L1 mostra R-34 na linha 2; erro de sintaxe mostra linha e coluna |
| S9-03 | US-15 | Estender a suíte de segurança à API pública (itens 1, 3, 4 e 13 da seção 8 via `POST /api/v1/validate`) | `backend/tests/security/test_api_limits.py` | 1 | S7-01, S8-01 | 100% passa, sem 5xx genérico, e `/ready` = 200 ao final |

Total do MVP: 42 SP em 9 sprints, distribuídos conforme a capacidade de cada sprint (5, 6, 5, 6, 5, 2, 3, 5 e 5 SP).

## 8. Definition of Done (DoD)

Cada item é verificado como sim ou não. Uma task ou história só está pronta quando todos os itens aplicáveis estão marcados como "sim".

### Código

- [ ] A mudança entrou por PR. Na Fase 0 (desenvolvimento solo), o PR tem CI verde e o checklist de autorrevisão preenchido; a partir do piloto, exige a aprovação do CODEOWNER do caminho alterado (professor em `rulesets/*/base.yaml`; monitor-chefe ou professor em `rulesets/*/questions/**`, sem autoaprovação; professor em override que libera R-05…R-14; mantenedor de segurança em `backend/**` e `deploy/**`).
- [ ] ruff, `mypy --strict`, ESLint e `tsc` passam com 0 erros e 0 avisos.
- [ ] O contrato do import-linter passa: o pacote `ipc_api` não importa `ast` e o motor não importa FastAPI.
- [ ] As regras de segurança do ruff e a guarda de código (`backend/tests/test_code_guards.py`) não encontram `eval`, `exec`, `compile` (fora de `engine/parse.py`), `__import__`, `importlib`, `runpy`, `pickle` nem `subprocess` sobre dados de requisição.
- [ ] As dependências estão fixadas com hash em `uv.lock` e `package-lock.json`.
- [ ] Nenhuma regra de permissão foi codificada fora de `rulesets/**`. Todo `rule_id` usado em código ou teste existe no catálogo R-xx.

### Testes

- [ ] Os testes unitários e de integração passam na CI.
- [ ] A cobertura é ≥ 90% em `backend/src/ipc_analyzer/engine` e ≥ 80% no restante (NFR-16).
- [ ] Cada R-xx criado ou alterado tem pelo menos 3 casos golden (permitido na lista correta, proibido antes dela e evasão quando couber), com 0 FP e 0 FN (NFR-18).
- [ ] Os testes de contrato da API, gerados do OpenAPI, passam para todos os códigos de status documentados em 5.2.2.
- [ ] O benchmark do motor não regrediu mais de 20% (NFR-02).
- [ ] O smoke e2e (Playwright) está verde: localmente na Fase 0 e no ambiente do piloto a partir da Sprint 11.
- [ ] Quando a entrega afeta o caminho de requisição (a partir da Sprint 18), o k6 atende o NFR-01, o NFR-04 e o NFR-05.

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
- [ ] 13. O teste canário de privacidade encontra 0 ocorrências do marcador em logs, no banco e no FS (NFR-11).
- [ ] 14. Trivy, pip-audit e npm audit não encontram CVE crítica ou alta corrigível, e o gitleaks não encontra segredo (NFR-13).
- [ ] 15. HSTS e CSP estão presentes, o TLS é ≥ 1.2 e o CORS segue o NFR-10: só a origem da SPA na Fase 1 e nenhum cabeçalho CORS nas Fases 0 e 2 (a partir da Sprint 11).

### Documentação

- [ ] O OpenAPI foi regenerado e versionado, e os tipos do frontend foram regenerados a partir dele.
- [ ] `docs/mapping-R-xx.md` e o `CHANGELOG` do ruleset foram atualizados quando alguma regra ou mapeamento mudou, com o "de acordo" do professor.
- [ ] Toda mudança de decisão arquitetural tem um ADR novo ou atualizado em `docs/adr/`.
- [ ] README, `RULES.md` e runbook foram atualizados quando o setup, a operação ou o processo de regras mudou.
- [ ] Toda premissa ou questão nova ou resolvida foi registrada na tabela da seção 1.3.

### Implantação

- [ ] A imagem foi construída na CI e publicada no GHCR com tag = SHA do commit, e o compose a referencia por digest.
- [ ] Na Fase 0, `docker compose up` sobe o ambiente local a partir das imagens construídas na CI, com `/ready` = 200. A partir da Sprint 11, o deploy no Render e na Vercel é disparado pelo pipeline depois da CI (não manualmente), com smoke e2e verde e `/ready` = 200.
- [ ] O `ENABLED_LISTS` de produção corresponde às listas cujo ruleset foi validado pelo professor.
- [ ] O rollback para a imagem anterior foi testado e leva ≤ 5 min (a partir da Sprint 11).
- [ ] O UptimeRobot monitora `/ready` e a SPA a cada 5 min, com alerta por e-mail, a partir da Sprint 11; os demais alertas do NFR-15 estão ativos a partir da Sprint 14.
- [ ] Toda migração de banco é reversível e foi testada antes de ir para o piloto (a partir da Sprint 14).

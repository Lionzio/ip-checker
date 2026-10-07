# ADR-01 — Modelo de análise e isolamento do código do aluno

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

# Sprint 36 — Defeitos e documentos certos para a campanha de testes

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

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
| S36-10 | US-14 | Engenharia | Tolerância do benchmark (incluída a pedido do autor em 12/10/2026): uma razão acima de 120% da linha de base só conta como regressão se a diferença também passar de 0,5 ms, medida pela calibração da mesma rodada; nas entradas pequenas, o ruído da máquina carregada reprovava a CI sem mudança no motor | `backend/tests/benchmark/` | Autor | 0,5 | — | Teste da lógica com o caso real; o benchmark passa com a máquina carregada |

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

**Situação (12/10/2026):** engenharia concluída na release `sprint-36` (#95 a #101): S36-01 a S36-07, S36-09 (com o de acordo do professor) e S36-10, incluída a pedido do autor. A S36-06 achou que, no piloto, entradas legítimas de 40 e 50 KB recebiam 422 por prazo; o analisador do piloto passou a ter 7 s e, depois da medição com o deploy, 8 s na release `sprint-36.1` (ADR-03). Aguardando: a campanha de testes manuais da equipe (S36-08).

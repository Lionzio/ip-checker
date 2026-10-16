# Sprint 40 — A correção da turma inteira

Do blueprint até 15/10/2026, seção 7.15 (plano de polimento de 11/10/2026); o plano comum está no [README](README.md).

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
| S40-04 | US-14 | Engenharia | Benchmark estável sob carga (incluída a pedido do autor em 15/10/2026): a razão passa a ser pareada (uma calibração antes e outra depois de cada execução da ação, na mesma amostra), e uma entrada acima da tolerância é medida de novo até 2 vezes, só contando como regressão se passar nas três. A linha de base é regravada. Em 4 rodadas da CI local, o `plagio_50kb` deu razão de 47 a 52 (máximo 51) com o notebook ocupado, sem mudança no motor | `backend/tests/benchmark/` | Autor | 0,5 | — | Teste da lógica com a carga mudando no meio da rodada e com a regressão de 30%; o benchmark passa com 16 processos ocupando a máquina e reprova uma regressão de mentira de 30% |

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
- **Vercel:** Create Deployment (tela nova). As views existentes bastaram, mas a API precisou do papel que as lê: a migração `0007` vai antes do Render.
- **Depois:** sintético e exercício de alerta.

**Riscos:**
- O lote concentra muita análise de uma vez no plano gratuito (0,1 CPU); a admissão e os limites protegem o serviço, e a tela mostra o progresso.
- Uma lista grande pode levar minutos; a tela permite cancelar.

**Situação (15/10/2026):** engenharia concluída na release `sprint-40`, feita antes da 39 por pedido do autor: S40-01 a S40-04, num PR só. Decisões da sprint (detalhes no `CHANGELOG.md`): a barreira de 128 KiB por requisição não mudou, e a página lê o `.zip` (com a proteção contra *zip bomb*) e manda os arquivos em partes de até 20, abaixo de 110 KB, para o `POST /api/v1/validate/batch`, que conta 1 no limite por conta e passa cada arquivo pela admissão; o todos contra todos aceita até 60 soluções (60 em 0,35 s na máquina do autor), e as 100 do NFR-30 ficam para a S46-03; o painel por lista lê as views anônimas pela migração `0007` (`GRANT ipc_reader TO ipc_app`); a S40-04 entrou depois de 4 rodadas da CI local reprovadas por ruído (benchmark, limite por IP e prazos do Vitest), e o 429 enganoso do limite por IP com o banco lento ficou registrado para a Sprint 39 (S39-06). Deploy feito em 15/10/2026 (migração `0007` pelo autor, Render às 20:31 e Vercel às 20:33) e exercício de alerta registrado no runbook (#127 e #128). Sintético feito em 16/10/2026 (28 ms). Aguardando: o roteiro de testes manuais da equipe nas telas novas (L-05, L-06, T-09 e G-11).

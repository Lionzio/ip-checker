# Sprints 36 em diante

Um arquivo por sprint, com o objetivo, a missão, as personas, a execução, as tasks, os testes, o
deploy e a situação. Até 15/10/2026, este texto ficava nas seções 7.15 e 7.16 do blueprint; o
roadmap (a ordem e a situação de todas) continua no [blueprint](../blueprint.md), seção 7.1, e o
que cada uma entregou, no [`CHANGELOG.md`](../../CHANGELOG.md).

| Sprint | Arquivo |
|---|---|
| 36 | [Sprint 36 — Defeitos e documentos certos para a campanha de testes](sprint-36.md) |
| 37 | [Sprint 37 — Verificação mais clara](sprint-37.md) |
| 38 | [Sprint 38 — Explicar cada regra e exportar o resultado](sprint-38.md) |
| 39 | [Sprint 39 — Qualidade interna, operação e documentação](sprint-39.md) |
| 40 | [Sprint 40 — A correção da turma inteira](sprint-40.md) |
| 41 | [Sprint 41 — Fase 2: imagens no GHCR, deploy pelo servidor do CIn e staging (bloqueada)](sprint-41.md) |
| 42 | [Sprint 42 — Indícios de IA ligados no piloto (incluída a pedido do autor em 12/10/2026)](sprint-42.md) |
| 43 | [Sprint 43 — Período na interface e retenção por encerramento](sprint-43.md) |
| 44 | [Sprint 44 — Feedback rastreável e o padrão do monitor](sprint-44.md) |
| 45 | [Sprint 45 — Aprimorar com IA: validação rastreável e crítica](sprint-45.md) |
| 46 | [Sprint 46 — Plágio calibrado](sprint-46.md) |
| 47 | [Sprint 47 — Grupos de acompanhamento e histórico dos alunos (vai ao piloto com o aviso de privacidade aprovado)](sprint-47.md) |
| 48 | [Sprint 48 — Entrada com o Google no piloto (no fim da fila, decisão de 12/10/2026)](sprint-48.md) |
| 49 | [Sprint 49 — CI incremental e mais rápida](sprint-49.md) |
| 50 | [Sprint 50 — Catálogo das listas pela extensão do Dikastis (parte 1)](sprint-50.md) |
| 51 | [Sprint 51 — Gabaritos pelo painel (Notion e IP CC)](sprint-51.md) |
| 52 | [Sprint 52 — Códigos dos alunos (parte 2): guarda, retenção e a etapa 2](sprint-52.md) |
| 53 | [Sprint 53 — Plágio por turma e por período](sprint-53.md) |
| 54 | [Sprint 54 — Sincronização automática e painel de sincronizações](sprint-54.md) |

## 7.15 Tasks das Sprints 36 a 41 (plano de polimento de 11/10/2026)

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
5. **Sprint 40:** a correção da turma inteira (feita antes da 39, em 15/10/2026, por pedido do autor).

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

## 7.16 Tasks das Sprints 42 a 48 (proposta de 12/10/2026: indícios de IA, período, feedback, plágio, acompanhamento e Google)

Proposta criada em 12/10/2026 a partir da revisão técnica das seis frentes pedidas pelo autor
([`revisao-seis-frentes.md`](../revisao-seis-frentes.md)): o período da turma, a qualidade do
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
39 → 40 → **46** → **45** → **47** → **48**, e a 41 (Fase 2) por último, depois de todas (P-24, 15/10/2026), quando a P-09, a Q-12 e a validação com a coordenação e a direção permitirem.
A 42 começa assim que houver o corpus de calibração ou a resposta da Q-35 e pode correr em
paralelo com as outras, porque toca poucos arquivos. A 43 vem antes da 39 para que a refatoração de `Checker.tsx` e `Plagiarism.tsx` já inclua o
seletor de período; a 44 depende da S38-01 e da S38-02; a 46 depende da S40-02.

**Atualização (16/10/2026):** com o plano da Fase 1h (7.17), a ordem passa a ser **49 → 50 → 42.1 → 51 → 52 → 53 → 54**, depois 44, 45, 46 (o que a 53 não absorver), 47 e 48, com a 41 por último (P-24). A 42.1 vem depois da 50 porque os enunciados das referências passam a vir do catálogo (S50-06).

**Base comum:** a mesma de 7.15 (evidência por `ci-local.sh --e2e` enquanto durar a P-19, release
por `scripts/release.sh NN`, sintético e exercício de alerta depois do deploy, migração nunca junto
com o `render.yaml`, P-18).

**Decisões do plano:** respostas do autor em 12/10/2026, registradas em [`decisoes.md`](../decisoes.md).

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

## 7.17 Tasks das Sprints 49 a 54 (plano de 16/10/2026: CI incremental e integração com o Dikastis)

Plano criado em 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md)) a partir do pedido do
autor: trazer do Dikastis os enunciados e os códigos dos alunos por uma extensão do navegador,
cadastrar os gabaritos pelo painel, comparar o plágio por turma e por período, e, antes de tudo,
tornar a CI mais rápida, porque todas as sprints pagam esse custo. O autor aprovou as duas partes
da extensão com a autorização dos professores e dos monitores-chefes (Q-37 a Q-42).

**Por que é uma fase nova (Fase 1h):** a Sprint 52 é a primeira que guarda código de aluno
(ADR-16), cifrado, por 6 períodos, com base legal registrada, aviso aos alunos e exclusão a
pedido. Até ela, nada muda no que se guarda dos alunos.

**Ordem:** **49 → 50 → 42.1 → 51 → 52 → 53 → 54**, depois 44, 45, 46 (o que a 53 não absorver),
47 e 48, e a 41 por último (P-24). A 49 vem primeiro porque corta a CI de 14 para cerca de 5
minutos por PR; a 50 destrava a 42.1 (os enunciados vêm do catálogo); a 52 precisa da 50 e da
Q-37; a 53 precisa dos códigos da 52; a 54 fecha a integração.

**Base comum:** a de 7.15 e 7.16, com uma mudança desde a 49: a evidência de cada PR é o
`scripts/ci-local.sh` incremental (ADR-20), e a release exige a rodada `--completo` na ponta da
`develop`. Segredos novos (`IPC_CODE_KEY`) são gerados e gravados pelo autor no Render, nunca por
agente; as migrações `0008` e `0009` são aplicadas pelo autor, como a `0007`; deploy só com "faça o
deploy"; sintético e exercício de alerta depois; migração nunca junto com o `render.yaml` (P-18).

**Decisões do plano (16/10/2026, autor), registradas em [`decisoes.md`](../decisoes.md):**

| Decisão | Resposta | Sprints |
|---|---|---|
| Q-37: guardar o código dos alunos | Sim, o último código de cada aluno em cada questão, cifrado, para a correção e o plágio da disciplina, com a autorização dos professores e dos monitores-chefes; aviso aos alunos e ciência do encarregado de dados da UFPE antes do piloto | 52 |
| Q-38: retenção | 6 períodos (3 anos): quando entram as listas de 2029.2, saem as de 2026.2 | 52 |
| Q-39: escopos do plágio | Turma até 100 e período até 600, assíncrono | 53 |
| Q-40: gabaritos | Até dois por questão (Notion e IP CC), pelo painel; o repositório de gabaritos não entra no principal e vira arquivo | 51 |
| Q-41: enunciados nas IAs gratuitas | Liberado, só com os casos de exemplo | 42.1 e 50 |
| Q-42: CI incremental como evidência | Um passo pulado vale como verde quando as entradas dele não mudaram desde um verde registrado; a release exige a rodada completa | 49 |

| Sprint | Tema | SP | Depende de |
|---|---|---|---|
| 49 | CI incremental e mais rápida | 9 | — |
| 50 | Catálogo das listas pela extensão | 16 | 49 |
| 42.1 | Indícios para a chefia | 4 | 50 |
| 51 | Gabaritos pelo painel | 12 | 50 |
| 52 | Códigos dos alunos | 15 | 50 e Q-37 |
| 53 | Plágio por turma e por período | 13 | 52 |
| 54 | Sincronização automática e painel | 8 | 50 e 52 |

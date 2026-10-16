# Sprint 49 — CI incremental e mais rápida

Do plano de 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seção 3); o plano comum está no [README](README.md). Vem antes da integração com o Dikastis porque todas as sprints seguintes pagam o custo da CI.

**Objetivo:** um PR típico com a CI local em até 6 minutos, um PR só de documentação em até 1, e a release completa em até 9, sem enfraquecer a prova: nenhum passo é pulado sem um verde registrado para as entradas atuais.

**Missão:** que o desenvolvedor e o próximo mantenedor esperem minutos, e não um quarto de hora, por cada PR, e que a cota do GitHub Actions dure o mês quando voltar.

**Personas:** o desenvolvedor que abre vários PRs por dia (US-57) e o monitor-mantenedor que roda a CI local numa máquina compartilhada (US-14).

**Execução:**
1. A impressão digital das entradas de cada passo e o registro dos verdes (S49-01).
2. As três faixas em paralelo e a faixa silenciosa (S49-02).
3. A auditoria mais barata e os caches (S49-03 e S49-04).
4. A release por passos (S49-05) e os filtros do Actions (S49-06).
5. A medição antes e depois, e os documentos (S49-07).

**Histórias:** US-14 e US-57.

| ID | História | Tipo | Descrição técnica | Componente/API/Esquema | Responsável | Estimativa (SP) | Dependências | Critério de conclusão |
|---|---|---|---|---|---|---|---|---|
| S49-01 | US-57 | Engenharia | Cada passo do `ci-local.sh` declara os caminhos de que depende (por exemplo, o pytest depende de `backend/**` e `rulesets/**`; o Lighthouse, de `frontend/**`; o Semgrep, de todo o código e de `.semgrep/**`; a segurança, de `backend/**`, `deploy/**` e dos Dockerfiles). O script calcula o hash do conteúdo desses caminhos (`git ls-files -s` mais o conteúdo dos arquivos modificados ou não rastreados) e guarda em `.git/ci-local-passos.json` o par passo → hash → verde (`sha`, hora). Um passo com verde para o hash atual é pulado, com "pulado: igual ao verde de `<sha>`" no resumo; `--completo` força tudo. A impressão inclui os arquivos de configuração do próprio passo (`pyproject.toml`, `lighthouserc.json`, o próprio `ci-local.sh`) | `scripts/ci-local.sh`, `scripts/ci-passos.py` (novo) | Autor | 2 | — | Testes do módulo de impressão digital (pytest, em `backend/tests/test_ci_passos.py`): mesmo conteúdo dá o mesmo hash; um byte muda o hash; arquivo não rastreado conta; um PR só de `.md` roda só o teste dos links |
| S49-02 | US-57 | Engenharia | Três faixas em paralelo: A (lint, tipos, fronteiras, ruleset e pytest do backend), B (gitleaks, Semgrep, pip-audit, npm audit) e C (npm ci, tipos do OpenAPI, ESLint, TypeScript, Vitest, build e orçamento do JS). Depois, a faixa silenciosa, sozinha: benchmark, testes `timing`, Lighthouse e segurança. Por fim, o e2e. O resumo mostra o tempo de cada faixa e o caminho crítico. Os testes `timing` saem da etapa em série para a faixa silenciosa | `scripts/ci-local.sh` | Autor | 2 | S49-01 | Três rodadas seguidas verdes na máquina do autor; o benchmark e o Lighthouse dentro da variação de sempre (razão pareada da S40-04) |
| S49-03 | US-57 | Engenharia | Semgrep só nos arquivos alterados desde o último verde (as regras de `.semgrep/ip-checker.yml` são de arquivo único, então é exato), com a varredura completa no `--completo`; `pip-audit` e `npm audit` só quando o lock mudou ou o último verde tem mais de 7 dias; gitleaks a partir do último commit auditado (`--log-opts`), completo no `--completo` | `scripts/ci-local.sh` | Autor | 1 | S49-01 | Um PR que muda um arquivo Python varre só ele; um PR sem mudança de lock não roda o pip-audit; a release varre tudo |
| S49-04 | US-57 | Engenharia | `npm ci` pulado quando `package-lock.json` não mudou e `node_modules` existe; imagens do compose e da segurança com o cache do BuildKit e reaproveitadas entre os dois passos; Playwright e `@lhci/cli` conferidos no cache antes de baixar | `scripts/ci-local.sh`, `deploy/compose.yaml` | Autor | 1 | S49-02 | O compose sobe sem reconstruir quando nada do backend mudou; `npm ci` só roda com lock novo |
| S49-05 | US-57 | Engenharia | `scripts/release.sh --ci-local` aceita, além do registro da árvore inteira (`ci-local-verde`), a cobertura por passos: todos os passos com verde para as entradas atuais da ponta da `develop`. A release continua pedindo a rodada `--completo` final, para o benchmark e o Lighthouse saírem sem ruído | `scripts/release.sh` | Autor | 1 | S49-01 | Teste do script com um repositório temporário: recusa se faltar um passo; aceita com todos |
| S49-06 | US-57 | Engenharia | GitHub Actions (vale a partir de 01/11/2026): filtros de caminho por job (`frontend` não roda num PR só de backend, e vice-versa), `benchmark` e `security` só quando `backend/**`, `deploy/**` ou os Dockerfiles mudam, cache do buildx (`type=gha`) nas imagens; um passo que registra os minutos faturados do run no resumo | `.github/workflows/ci.yml` | Autor | 1 | — | Revisão do YAML (`actionlint`); a medição fica para a primeira rodada com cota |
| S49-07 | US-14 | Documentação | A medição antes e depois (a rodada de 16/10/2026 como "antes") no CHANGELOG; NFR-36 no blueprint; runbook "Sem GitHub Actions" e `README` com `--completo` e o registro dos passos; ADR-20 aceita | docs | Autor | 1 | S49-01 a S49-05 | Revisão |

**ADRs:** ADR-20 (novo).

**Critérios de aceite:**
1. Um PR que muda só `backend/src/ipc_api/routes/meta.py` pula Lighthouse, Vitest, build, segurança e benchmark, e termina em até 6 minutos.
2. Um PR que muda só `docs/*.md` roda só o teste dos links e termina em até 1 minuto.
3. `scripts/release.sh 49 --ci-local` recusa a release se algum passo não tem verde para a ponta da `develop`, e aceita depois da rodada `--completo`.
4. A rodada `--completo` termina em até 9 minutos, com o benchmark e o Lighthouse dentro da variação de sempre.

**Testes:**

| Teste | Ferramenta | Gatilho | Critério |
|---|---|---|---|
| Impressão digital | pytest (`test_ci_passos.py`) | PR | Mesmo conteúdo, mesmo hash; um byte muda; não rastreado conta; configuração do passo conta |
| Faixas | Três rodadas `--completo` seguidas | PR | Verdes; benchmark e Lighthouse sem ruído novo |
| Release por passos | Teste do `release.sh` com repositório temporário | PR | Recusa com um passo faltando; aceita com todos |
| Actions | `actionlint` e a primeira rodada com cota | PR e 01/11 | YAML válido; minutos por PR medidos |
| Regressão | `scripts/ci-local.sh --completo` | A ponta da `develop` | Verde; o resumo colado no PR |

**Deploy:** release `sprint-49`, só de scripts e CI: nada muda no Render nem na Vercel. Sem exercício de alerta; o sintético segue a rotina.

**Riscos:**
- Um passo pulado por engano: só com verde registrado para as entradas atuais, e a release roda `--completo`.
- O paralelismo reintroduz o ruído de tempo que as Sprints 39 e 40 corrigiram: benchmark, `timing`, Lighthouse e segurança ficam na faixa silenciosa, sozinhos na máquina.
- O Docker Desktop do Windows com três faixas ao mesmo tempo: a faixa B (auditorias em contêiner) é a única com Docker na fase paralela; a segurança e o e2e vêm depois.

# ADR-20 — CI incremental por impressão digital das entradas de cada passo

**Título:** Como a CI local (e, depois, a do Actions) pula o que não precisa rodar sem enfraquecer a prova de cada PR e de cada release.

**Status:** Proposto em 16/10/2026 ([`plano-dikastis.md`](../plano-dikastis.md), seção 3), aprovado pelo autor no mesmo dia (Q-42); Sprint 49.

**Contexto:** A rodada completa do `scripts/ci-local.sh --e2e` leva de 13 a 15 minutos e roda inteira a cada PR, mesmo quando só um `.md` mudou. Medida em 16/10/2026 (`970bec6`, sem outra carga): segurança 200 s, Semgrep 127 s, e2e 109 s, benchmark 66 s, pytest 103 s, Lighthouse 52 s, pip-audit 44 s, o resto cerca de 100 s. Tudo em série. Os passos mais caros conferem coisas que mudam raramente (a imagem do piloto, as dependências, o desempenho do motor), e o Semgrep varre o repositório inteiro montado no Docker do Windows, que é lento para muitos arquivos. A cota do GitHub Actions (2.000 min por mês, esgotada em 08/10/2026) volta em 01/11/2026 e precisa durar o mês.

**Decisão:**
1. **Impressão digital das entradas:** cada passo declara os caminhos de que depende (código, testes e os arquivos de configuração do próprio passo). O script calcula um hash do conteúdo desses caminhos e guarda, em `.git/ci-local-passos.json`, "passo → hash → verde (sha, hora)". Um passo com verde para o hash atual é pulado, com a linha "pulado: igual ao verde de `<sha>`" no resumo. `--completo` força tudo.
2. **Faixas em paralelo e uma faixa silenciosa:** backend, auditorias e frontend em paralelo; benchmark, testes de tempo, Lighthouse e segurança depois, sozinhos na máquina, porque medem tempo ou memória e já falharam por ruído de carga (Sprints 39 e 40); o e2e por fim.
3. **Auditoria só sobre o que mudou:** Semgrep nos arquivos alterados desde o último verde (as regras do projeto são de arquivo único, então é exato); `pip-audit` e `npm audit` só com lock novo ou verde com mais de 7 dias; gitleaks a partir do último commit auditado. A varredura completa continua na release e na auditoria semanal.
4. **A release prova tudo:** `scripts/release.sh --ci-local` aceita a cobertura por passos (todos com verde para as entradas atuais da ponta da `develop`) e exige a rodada `--completo` final, para o benchmark e o Lighthouse saírem sem ruído.
5. **No Actions**, quando a cota voltar: filtros de caminho por job, `benchmark` e `security` só quando o backend ou o deploy mudam, cache do buildx nas imagens, e a medição dos minutos faturados por PR.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|---|---|---|
| A. Tudo, sempre, em série (situação atual) | Simples e sem risco de pular | 13 a 15 minutos por PR, inclusive de documentação |
| B. Pular por caminhos alterados em relação à base do PR | Fácil de explicar | Depende da base certa; um rebase ou um segundo commit refaz tudo; não registra o que já passou |
| C. Escolhida: impressão digital das entradas por passo, com registro dos verdes | Pula só o que já passou para o mesmo conteúdo; independe da base; a release confere a cobertura | Cada passo precisa declarar as entradas certas (esquecer uma é o risco); um arquivo de registro a manter |
| D. Só paralelizar | Ganho sem mudar a prova | O custo total não cai; os passos sensíveis ao tempo ficam sob carga |

**Consequências positivas:** um PR típico em cerca de 5 minutos, um de documentação em menos de 1, a release completa em cerca de 9; menos minutos no Actions; menos tentação de pular a CI.

**Consequências negativas:** um passo com entradas mal declaradas pode ser pulado indevidamente (mitigado pela rodada `--completo` da release e pela declaração dos arquivos de configuração do próprio passo); o paralelismo exige cuidado com o Docker Desktop do Windows e com os passos sensíveis ao tempo.

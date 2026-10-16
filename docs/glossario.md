# Glossário

Os termos e as siglas que aparecem no código, nos PRs e na documentação do IP-Checker (S39-05).

## Identificadores

| Termo | O que é | Onde está |
|---|---|---|
| **R-xx** | Uma regra do catálogo de permissões, como a R-34 (laços) ou a R-05 (`import`). O catálogo transforma o documento de permissões em regras que o motor confere | [`blueprint.md`](blueprint.md), 3.1; [`mapping-R-xx.md`](mapping-R-xx.md) |
| **P-xx, C-xx, Q-xx, REC-xx** | Premissa, conflito, questão e recomendação: uma decisão do projeto, com quem decidiu e quando | [`decisoes.md`](decisoes.md) |
| **Snn-mm** | A task `mm` da Sprint `nn`, como a S39-06 | [`sprints/`](sprints/README.md) e o histórico |
| **FR-xx, NFR-xx** | Requisito funcional e não funcional (desempenho, segurança, privacidade) | [`blueprint.md`](blueprint.md), 3.2 e 3.3 |
| **US-xx** | Uma história de usuário do backlog | [`blueprint.md`](blueprint.md), 4 |
| **ADR-xx** | O registro de uma decisão de arquitetura, com o contexto e as alternativas | [`adr/`](adr/) |
| **L3-Q2** | A questão 2 da Lista 3 de um período. A numeração recomeça a cada período (P-07) | `rulesets/<período>/questions/` |

## O motor e o ruleset

| Termo | O que é |
|---|---|
| **Ruleset** | Os dados das regras de um período (`rulesets/<período>/base.yaml` e as questões). O motor só lê; ninguém escreve regra em código (ADR-02) |
| **Período** | Um semestre letivo, como `2026.2`. O **período ativo** é o do arquivo `rulesets/ATIVO` |
| **Fato** | O que o motor extrai do código para as regras conferirem, no formato `<tipo>:<nome>`, como `node:For` ou `kwarg:print.end` |
| **Categoria** | O tipo da violação: anulação imediata, proibido na questão, fora da lista, não consta no documento (R-04) e exigência não atendida |
| **Golden** | Os casos de teste com o resultado esperado de cada regra (`backend/tests/golden/`) |
| **Gabarito** | A solução oficial de uma questão. Fica no repositório privado `ip-checker-gabaritos` e nunca chega ao navegador (ADR-11) |
| **Referência por IA** | Uma solução gerada por IA a partir só do enunciado, para o sinal 5 dos indícios (ADR-08) |

## Plágio e indícios

| Termo | O que é |
|---|---|
| **Faixa** | A leitura da similaridade: "Sem suspeitas", "Ligeiramente suspeito", "Requer atenção" (a partir de 90%) e "Plágio" (FR-29) |
| **Contenção** | Quanto de um código está dentro do outro. Alta com estrutura baixa indica código acrescentado a uma cópia (ADR-07) |
| **IDF da turma** | O peso de cada trecho pela raridade na turma: o que todos escrevem quase não conta |
| **Indício** | Um motivo para conversar com o aluno sobre uso de IA, com a faixa e as linhas. Nunca é prova (ADR-08) |

## Operação

| Termo | O que é |
|---|---|
| **Piloto** | O IP-Checker no ar para a equipe: a página na Vercel, a API e o analisador no Render, o banco no Supabase |
| **Analisador** | O processo que analisa o código, isolado, sem rede e sem banco (ADR-01). A API nunca analisa código |
| **Admissão** | A fila de análises: quando está cheia, a API responde 503 `OVERLOADED` com `Retry-After`, em vez de esperar |
| **SLO** | A meta de latência e de erros do `/health/slo` (P95 até 200 ms, até 1% de 5xx), que o UptimeRobot vigia |
| **Sintético** | Uma verificação de verdade, pela página, com a conta de verificação, depois de cada deploy e nos dias úteis |
| **Canário** | A conferência mensal do banco em produção (S35-04) |
| **Exercício de alerta** | Baixar o limiar do SLO para 50 ms, gerar carga e conferir que os e-mails de queda e de volta chegam em até 5 min (S34-04) |
| **CI local** | `scripts/ci-local.sh --e2e`: a CI completa na máquina do autor, enquanto o Actions está sem cota (P-19) |
| **Release** | `scripts/release.sh NN`: a `main` avança até a `develop`, com a tag `sprint-NN` e o GitHub Release |
| **DoD** | A Definition of Done: o que todo PR precisa cumprir ([`blueprint.md`](blueprint.md), 8) |
| **Marco 2** | A apresentação à coordenação, aos professores e aos monitores-chefes, que libera o piloto |

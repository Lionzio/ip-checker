# Mapa da documentação

Onde está cada coisa no IP-Checker. Desde a S28-04, o blueprint guarda os requisitos, a arquitetura
e o plano; as decisões, os ADRs e o histórico das sprints têm arquivos próprios. Desde a S39-05, o
detalhe de cada sprint também: um arquivo por sprint em [`sprints/`](sprints/README.md), e as
Sprints 1 a 35 em [`historico/`](historico/sprints-01-35.md).

**Quem chega começa por:** [`estado.md`](estado.md) (onde o projeto está), [`glossario.md`](glossario.md)
(os termos e as siglas) e [`onboarding.md`](onboarding.md) (o ambiente).

## Para usar

| Documento | Para quem | O que tem |
|---|---|---|
| [`guia-da-equipe.md`](guia-da-equipe.md) | Equipe da disciplina | Como entrar, verificar, comparar soluções e gerar o feedback |
| [`testes-manuais.md`](testes-manuais.md) | Equipe da disciplina | Roteiro de testes manuais de todas as funções, com os resultados esperados conferidos no motor (também em Word, fora do repositório) |
| [`../RULES.md`](../RULES.md) | Monitores e professores | Como cadastrar as regras de uma questão |
| [`eficacia.md`](eficacia.md) | Professores e coordenação | Como medir os critérios de eficácia do piloto (P-09) e o formulário da pesquisa |
| [`marco-2.md`](marco-2.md) | Equipe e coordenação | A pauta do Marco 2: os casos do mapeamento e as decisões da coordenação |
| [`ensaio-cadastro.md`](ensaio-cadastro.md) | Monitores | O ensaio do cadastro de uma questão (S31-13) |
| [`indicios-de-ia.md`](indicios-de-ia.md) | Equipe e coordenação | A política dos indícios de uso de IA (ADR-08), as faixas, a calibração e como ligar no piloto |
| [`registro-de-casos.md`](registro-de-casos.md) | Chefia e coordenação | Os casos conversados a partir do painel de indícios, sem dados de aluno (S42-07) |

## Para manter

| Documento | O que tem |
|---|---|
| [`onboarding.md`](onboarding.md) | Do zero ao ambiente completo com os testes verdes, em cerca de 30 minutos |
| [`estado.md`](estado.md) | Uma página: o que está no ar, o que está em andamento e o que espera alguém |
| [`faq-mantenedor.md`](faq-mantenedor.md) | Habilitar uma lista, trocar de período, gabarito novo, reiniciar o Render, rodar a CI |
| [`rotinas.md`](rotinas.md) | A agenda: backup, restauração, sintético, exercício de alerta, canário, auditoria, rollback e a troca do token dos gabaritos |
| [`contas.md`](contas.md) | Quem administra cada serviço (Render, Vercel, Supabase, Brevo, UptimeRobot, IAs, gabaritos) e onde cada credencial é usada |
| [`glossario.md`](glossario.md) | R-xx, P/C/Q/REC, Snn-mm, FR, NFR e US, fato, faixa, contenção e os termos da operação |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Branches, PRs, checagens antes do PR, releases e as regras da casa |
| [`../SECURITY.md`](../SECURITY.md) | Como relatar uma falha e os controles em vigor |
| [`runbook.md`](runbook.md) | O que fazer quando algo dá errado no piloto: rollback, backup, banco, analisador, segredos e incidentes |
| [`../deploy/README.md`](../deploy/README.md) | Índice da implantação: [`piloto.md`](../deploy/piloto.md), [`compose.md`](../deploy/compose.md) e [`seguranca.md`](../deploy/seguranca.md) |
| [`../backend/README.md`](../backend/README.md) | Pacotes do backend, comandos e variáveis do analisador e da API |
| [`../frontend/README.md`](../frontend/README.md) | A página, o cliente simulado e o build da Vercel |
| [`../rulesets/README.md`](../rulesets/README.md) | Como o ruleset é organizado e validado, o esquema JSON (`rulesets/schema/`) e os gabaritos |

## Para entender as decisões

| Documento | O que tem |
|---|---|
| [`blueprint.md`](blueprint.md) | Visão, personas, requisitos (FR e NFR), backlog, arquitetura, modelo de ameaças, o roadmap das sprints (7.1, com o mapa das seções antigas em 7.2) e a Definition of Done |
| [`sprints/`](sprints/README.md) | Um arquivo por sprint, da 36 em diante: objetivo, missão, personas, execução, tasks, testes, deploy e situação |
| [`historico/sprints-01-35.md`](historico/sprints-01-35.md) | As tasks e as situações das Sprints 1 a 35, a matriz de rastreabilidade de 07/10/2026 e as falhas da revisão inicial |
| [`revisao-seis-frentes.md`](revisao-seis-frentes.md) | A revisão técnica de 12/10/2026: período, feedback, indícios de IA, plágio e acompanhamento dos alunos, com o mapa do código, as opções e a proposta das Sprints 42 a 48 |
| [`decisoes.md`](decisoes.md) | Premissas, conflitos, questões e recomendações (P-xx, C-xx, Q-xx, REC-xx): um resumo por linha e uma seção por ID, e as opções das decisões em aberto (era a 7.13) |
| [`adr/`](adr/) | Os ADRs, um por arquivo, com o índice na seção 6 do blueprint |
| [`../CHANGELOG.md`](../CHANGELOG.md) | O que cada sprint entregou e as decisões de implementação |
| [`mapping-R-xx.md`](mapping-R-xx.md) | Como cada regra do documento de permissões vira fatos do motor |
| [`openapi.json`](openapi.json) | O contrato da API, gerado do código e conferido na CI |

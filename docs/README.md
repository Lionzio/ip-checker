# Mapa da documentação

Onde está cada coisa no IP-Checker. Desde a S28-04, o blueprint guarda os requisitos, a arquitetura
e o plano; as decisões, os ADRs e o histórico das sprints têm arquivos próprios.

## Para usar

| Documento | Para quem | O que tem |
|---|---|---|
| [`guia-da-equipe.md`](guia-da-equipe.md) | Equipe da disciplina | Como entrar, verificar, comparar soluções e gerar o feedback |
| [`testes-manuais.md`](testes-manuais.md) | Equipe da disciplina | Roteiro de testes manuais de todas as funções, com os resultados esperados conferidos no motor (também em Word, fora do repositório) |
| [`../RULES.md`](../RULES.md) | Monitores e professores | Como cadastrar as regras de uma questão |
| [`eficacia.md`](eficacia.md) | Professores e coordenação | Como medir os critérios de eficácia do piloto (P-09) e o formulário da pesquisa |
| [`indicios-de-ia.md`](indicios-de-ia.md) | Equipe e coordenação | A política dos indícios de uso de IA (ADR-08), as faixas, a calibração e como ligar no piloto |

## Para manter

| Documento | O que tem |
|---|---|
| [`onboarding.md`](onboarding.md) | Do zero ao ambiente completo com os testes verdes, em cerca de 30 minutos |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Branches, PRs, checagens antes do PR, releases e as regras da casa |
| [`../SECURITY.md`](../SECURITY.md) | Como relatar uma falha e os controles em vigor |
| [`runbook.md`](runbook.md) | O que fazer quando algo dá errado no piloto: rollback, backup, banco, analisador, segredos e incidentes |
| [`../deploy/README.md`](../deploy/README.md) | Índice da implantação: [`piloto.md`](../deploy/piloto.md), [`compose.md`](../deploy/compose.md) e [`seguranca.md`](../deploy/seguranca.md) |
| [`../backend/README.md`](../backend/README.md) | Pacotes do backend, comandos e variáveis do analisador e da API |
| [`../frontend/README.md`](../frontend/README.md) | A página, o cliente simulado e o build da Vercel |
| [`../rulesets/README.md`](../rulesets/README.md) | Como o ruleset é organizado e validado, e os gabaritos |

## Para entender as decisões

| Documento | O que tem |
|---|---|
| [`blueprint.md`](blueprint.md) | Visão, personas, requisitos (FR e NFR), backlog, arquitetura, modelo de ameaças, roadmap das sprints e a Definition of Done |
| [`decisoes.md`](decisoes.md) | Premissas, conflitos, questões e recomendações (P-xx, C-xx, Q-xx, REC-xx) |
| [`adr/`](adr/) | Os ADRs, um por arquivo, com o índice na seção 6 do blueprint |
| [`../CHANGELOG.md`](../CHANGELOG.md) | O que cada sprint entregou e as decisões de implementação |
| [`mapping-R-xx.md`](mapping-R-xx.md) | Como cada regra do documento de permissões vira fatos do motor |
| [`openapi.json`](openapi.json) | O contrato da API, gerado do código e conferido na CI |

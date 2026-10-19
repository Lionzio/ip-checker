# Estado e pendências

Uma página só, para quem chega saber onde o projeto está (S39-05). Atualize no PR de registros de
cada release; o detalhe fica no [`CHANGELOG.md`](../CHANGELOG.md) e nas [sprints](sprints/README.md).

**Atualizado em 16/10/2026.**

## No ar

| O quê | Situação |
|---|---|
| Piloto | Release `sprint-43` (16/10/2026), Render e Vercel; o exercício de alerta e o sintético dela ficaram para depois, a pedido do autor |
| Listas habilitadas | 1 a 6 de 2026.2 (`IPC_ENABLED_LISTS` no `render.yaml`) |
| Período ativo | 2026.2; o 2027.1 existe, inativo, como cópia (P-22); com a `sprint-43`, o analisador carrega o ativo e até 5 anteriores (ADR-12) |
| Indícios de IA | Desligados no piloto (`IPC_AI_INDICATORS=0`); desde a `sprint-42`, a variável aceita `chefia`, que liga só depois da meta de acertos |
| CI e deploy | Sem cota do GitHub Actions até 01/11/2026 (P-19): CI local incremental (ADR-20, Sprint 49: completa em 9,9 min (595 s), sem mudanças de código em 21 s), release com `--ci-local` e deploy pelo painel |

## Em andamento

| O quê | Situação |
|---|---|
| Sprint 39 | Concluída e no piloto em 16/10/2026 |
| Sprint 43 | Concluída e no piloto em 16/10/2026 (release `sprint-43`); faltam o exercício de alerta e o sintético |
| Sprint 42 | Parte 1 na release `sprint-42` (16/10/2026); parte 2 na `sprint-42.1`, no piloto desde 19/10/2026: 102 referências de IA, as metas da calibração cumpridas e o painel ligado para a chefia; para toda a equipe na Sprint 51 (S51-08, opção A) |
| Sprint 49 | Concluída em 16/10/2026 (release `sprint-49`, só scripts e CI; sem deploy) |
| Sprint 50 | Concluída em 16/10/2026 (release `sprint-50`: a extensão do Dikastis, o token de importação, a migração `0008` e a tela "Listas do período"); no piloto depois da migração e do deploy, com o autor |
| Sprint 51 | Planejada em 19/10/2026 (`sprints/sprint-51.md` e o manual fora do repositório); começa com o comando do autor; a release e o deploy esperam o fim da primeira lista com a chefia usando o painel de indícios (previsão: início de novembro) |
| Fila depois dela | 52 → 53 → 54, depois 44, 45, 46, 47 e 48; a 41 (servidor do CIn) por último (P-24). Plano de 16/10/2026 em [`plano-dikastis.md`](plano-dikastis.md) |

## Esperando alguém

| O quê | Quem | Onde |
|---|---|---|
| Campanha de testes manuais (S36-08), inclusive as telas da Sprint 40 | Equipe da disciplina | [`testes-manuais.md`](testes-manuais.md) |
| Revisão dos 71 textos de explicação das regras (Q-31) | Monitor-chefe, professor ou o autor | Sprint 38 |
| Aprovação das capturas da Sprint 37 | Autor | Fora do repositório, `prints-sprint-37/` |
| Backup agendado: registrar a tarefa (o segredo já foi guardado em 16/10/2026) | Autor | [`runbook.md`](runbook.md), "Backup agendado nesta máquina" |
| Antes da Sprint 52: o aviso aos alunos publicado, a ciência do encarregado de dados da UFPE e a `IPC_CODE_KEY` no Render (Q-37) | Autor e coordenação | [`plano-dikastis.md`](plano-dikastis.md), seção 9 |
| Gabaritos das Listas 5 e 6 de 2026.2 e dos períodos anteriores; o documento de permissões de 2027.1 | Autor e coordenação | P-21 e P-22 em [`decisoes.md`](decisoes.md) |
| Quando a cota do Actions voltar (01/11/2026): os workflows na ordem do runbook | Autor ou agente | [`runbook.md`](runbook.md), "Sem GitHub Actions" |
| Sprint 50 no piloto: a migração `0008`, "faça o deploy", instalar a extensão, criar o token, a primeira sincronização, o exercício de alerta e o sintético | Autor | [`sprints/sprint-50.md`](sprints/sprint-50.md) e o guia da equipe |

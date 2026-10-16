# FAQ do mantenedor

As tarefas que mais aparecem no dia a dia, em poucos passos (S39-05). O detalhe de cada uma está no
documento citado.

## Como habilito uma lista nova?

A API só aceita as listas de `IPC_ENABLED_LISTS`. Mude o valor no [`render.yaml`](../render.yaml)
por PR (por exemplo, `"1,2,3"`) e faça a release; a mudança do `render.yaml` publica sozinha no
Render (P-18). Não junte uma migração nessa mesma release. Antes de habilitar, confira que as
regras da lista estão no ruleset do período e que o `ipc-rules validate` passa.

## Como troco de período, por exemplo, para 2027.1?

1. Se o período ainda não existe: `uv run ipc-rules new-period 2027.1 --from 2026.2`, de
   `backend/` ([`RULES.md`](../RULES.md), passo 6). O 2027.1 já existe, inativo (P-22).
2. Cadastre as mudanças do documento de permissões do período novo e as questões, por PR.
3. Troque a linha do `rulesets/ATIVO` para `2027.1`, por PR, antes da primeira correção do período.
4. Faça a release e o deploy do Render (o analisador lê o ruleset ao subir).

Detalhes: [`../rulesets/README.md`](../rulesets/README.md) e o ADR-10.

## Chegou um gabarito novo. O que faço?

Faça o PR no repositório `ip-checker-gabaritos` e, depois do merge, reinicie o serviço no Render
(**Manual Deploy > Restart service**): a API só lê os gabaritos ao subir. Confira na página que a
questão aparece com "(comparação com o gabarito)" no seletor ([`runbook.md`](runbook.md),
"Credencial dos gabaritos").

## O Render precisa reiniciar. Como?

No painel do Render, no serviço `ip-checker-api`: **Manual Deploy > Restart service** reinicia sem
mudar a versão; **Manual Deploy > Deploy latest commit** publica a `main`. Depois, confira o
`/ready` (o campo `release` diz o commit) e rode o sintético. Um deploy de código só com a release
pronta e, no piloto, só com o pedido do autor.

## O UptimeRobot mandou um e-mail de queda. Por onde começo?

Pelo índice de sintomas no começo do [`runbook.md`](runbook.md). O `/health/slo` diz o motivo
(`latencia` ou `erros`) em `reasons`.

## Como rodo a CI antes de um PR?

`scripts/ci-local.sh --e2e`, na raiz, com o Docker Desktop aberto e sem contêineres `ipc-ci-local*`
de outra sessão. Cerca de 25 minutos; com a máquina carregada, algumas etapas oscilam
([`CHANGELOG.md`](../CHANGELOG.md), S40-04 e S39-06). O resumo no fim vai colado no PR.

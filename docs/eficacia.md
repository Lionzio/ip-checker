# Relatório de eficácia do piloto

Como medir, ao fim de 2027.1, os cinco critérios da P-09 (texto em vigor desde a Q-15, em
[`decisoes.md`](decisoes.md)), que decidem se o IP-Checker migra para o servidor do CIn (US-23,
ADR-03). Preparado na S28-02; o relatório final só sai no fim do período (P-10).

O relatório é a tabela abaixo, preenchida para cada lista habilitada no período:

| Critério | Meta | Como medir | Medido | Atingido? |
|---|---|---|---|---|
| 1. Precisão | 100% no corpus golden e nenhum falso positivo confirmado sem correção em até 2 dias úteis | Seção 1 | | |
| 2. Uso pela equipe | Pelo menos 70% dos membros ativos usam a ferramenta em cada lista | Seção 2 | | |
| 3. Apoio à correção | Informativo, sem meta | Seção 3 | | — |
| 4. Satisfação | Pelo menos 70% da equipe avalia a ferramenta como útil ou muito útil | Seção 4 | | |
| 5. Operação | NFR-01 e NFR-06 atendidos e nenhum incidente de segurança | Seção 5 | | |

## 1. Precisão

- **Corpus golden:** o job "Backend" da CI roda os casos golden (`backend/tests/golden/`) e o
  `ipc-rules validate` em todo PR; o job "Gabaritos" roda as respostas oficiais de períodos
  anteriores, que precisam dar zero violação (Q-14). Anote o resultado da CI do último commit da
  `main` no período: verde é 100%.
- **Falsos positivos:** cada caso relatado pela equipe vira uma *issue* no GitHub com o rótulo
  `falso-positivo`, com a lista, a questão e a regra, sem o código do aluno (NFR-11). Para cada uma,
  conte os dias úteis entre a abertura e o merge da correção. A meta é cumprida se nenhuma
  confirmada passou de 2 dias úteis.

## 2. Uso pela equipe

A telemetria é anônima (NFR-12) e não diz quem usou. Por isso, desde a S28-02, a primeira
verificação de cada conta em cada lista do período grava um registro em `app.list_adoption`
(conta, período e lista; sem data, sem código e sem resultado), apagado junto com a conta. Quem
consulta vê só a porcentagem, pela view `telemetry.v_team_adoption_by_list`, com o papel
`ipc_reader` ([`deploy/compose.md`](../deploy/compose.md), "Telemetria e alertas"):

```sql
SELECT list_number, adoption_pct
FROM telemetry.v_team_adoption_by_list
WHERE semester = '2027.1'
ORDER BY list_number;
```

- **Membros ativos:** contas com status ativo, sem a do desenvolvedor e sem a conta de verificação
  do deploy [PREMISSA: o desenvolvedor mantém a ferramenta e não corrige listas]. A conta é a de
  hoje, então rode a consulta logo depois do fim da última lista, antes de a equipe mudar.
- **O período** vem do ruleset (`ruleset_version` 2027.1.x conta como 2027.1).
- A conta de verificação é marcada pelo pipeline (S28-02); as verificações dela não entram nem na
  telemetria nem aqui.

## 3. Apoio à correção (informativo)

A equipe registra, por lista, quantos casos de proibição, plágio e uso de IA foram identificados
com a ajuda da ferramenta. O registro é feito por quem corrige, numa planilha compartilhada da
monitoria, com só estas colunas, sem nome nem matrícula de aluno:

| Lista | Tipo (proibição, plágio ou uso de IA) | Quantidade | Observação (opcional, sem dados de aluno) |
|---|---|---|---|

Como contexto, a telemetria mostra as regras mais apontadas por lista (`v_top_rules_by_list`) e o
volume por semana (`v_weekly_volume`).

## 4. Satisfação: formulário da pesquisa

Uma pesquisa anônima (por exemplo, no Google Forms da conta da disciplina, sem coletar e-mails),
enviada à equipe depois da última lista do período. Perguntas:

1. **Qual é o seu cargo na equipe?** Monitor; monitor-chefe; professor. (Para separar as respostas,
   nunca para identificar.)
2. **Em quantas listas você usou o IP-Checker na correção?** Nenhuma; 1 ou 2; 3 ou 4; 5 ou 6.
3. **O IP-Checker foi útil na sua correção?** Muito útil; útil; pouco útil; nada útil; não usei.
   *(É esta que mede o critério 4: a soma de "muito útil" e "útil" sobre quem usou.)*
4. **Quais funções você usou?** (várias) Verificação; regras por questão; plágio entre dois códigos;
   plágio contra a turma; feedback para o aluno; correção em lote.
5. **Alguma vez o IP-Checker apontou uma violação que não existia (falso positivo)?** Não; sim, e
   relatei; sim, e não relatei.
6. **O que mais atrapalhou?** (texto livre, opcional)
7. **O que você mudaria ou acrescentaria?** (texto livre, opcional)

A meta é cumprida se pelo menos 70% de quem usou (pergunta 3, sem "não usei") respondeu "muito útil"
ou "útil".

## 5. Operação

- **NFR-01 (P95 ≤ 200 ms):** o `/health/slo` guarda só os últimos 5 minutos. Use o histórico do
  monitor do UptimeRobot nesse endereço: a porcentagem de tempo em que ele respondeu 200 (dentro da
  meta) no período, e o workflow "Carga no piloto" rodado no começo e no fim do período (resumo do
  workflow). Ver o [ADR-03](adr/ADR-03-topologia-de-implantacao-por-fase.md) sobre o plano do Render.
- **NFR-06 (disponibilidade ≥ 99,5%):** o relatório mensal do monitor do `/ready` no UptimeRobot.
- **Incidentes de segurança:** o registro de incidentes do [runbook](runbook.md). Nenhum incidente
  registrado no período atinge a meta.

# Indícios de uso de IA: política e calibração

Política da S29-04 (ADR-08, Q-21), **aprovada em 09/10/2026** (opção A de 7.13.1 do blueprint). Até a
calibração ficar na meta (S33-03), o painel fica **desligado no piloto** (`IPC_AI_INDICATORS=0` no
`render.yaml`, conferido por um teste e pelo pipeline de deploy) e só funciona no ambiente local.

## Missão

Dar à equipe motivos concretos e explicáveis para decidir **com quem conversar**, sem acusar
ninguém por um número. O IP-Checker nunca diz que um código "foi gerado por IA": não existe
detector confiável e justo para código curto de quem está aprendendo (ADR-08, contexto). A única
confirmação é uma conversa em que o aluno explica ou modifica o próprio código.

## Para quem

Só para a equipe da disciplina (monitores, monitores-chefe e professores), no resultado da
verificação. O painel **nunca** vai para o feedback do aluno, nem para a telemetria, nem para os
logs, e nada dele é guardado: os indícios são calculados na hora, a partir do código verificado.

## O que o painel mostra

Cada indício vem com o motivo, as linhas e uma faixa (baixa, média ou alta). A faixa do painel é a
maior delas.

| Sinal | O que observa | Faixas iniciais [PREMISSA, ADR-08 item 1] |
|---|---|---|
| Múltiplas violações: variedade | Proibições gerais diferentes (R-05 a R-14) no mesmo código, como `break`, `continue` e `pass` | 2 diferentes: média; 3 ou mais: alta |
| Múltiplas violações: repetição | A mesma proibição geral várias vezes, como vários `pass` | 2 vezes: baixa; 3 ou mais: alta |
| Múltiplas violações: salto de lista | Construções liberadas só 2 ou mais listas depois da escolhida (por exemplo, dicionário numa solução da Lista 3) | 1 construção: média; 2 ou mais: alta. Uma lista só de diferença (o `for` na Lista 1) não conta: é um erro comum de quem está aprendendo |
| Múltiplas violações: fora do documento | Construções que o documento de permissões não cita (R-04) | 1 ou 2: baixa; 3 ou mais: média |
| Semelhança com solução de IA | O motor do painel de plágio (ADR-07) compara a solução com as referências geradas por IA para a questão | 80%: baixa; 90%: média; 95%: alta (as faixas do plágio, FR-29) |
| Estilo | Docstrings, anotações de tipo, `if __name__ == "__main__"`, nomes e comentários em inglês | Sem faixa: são fatos, porque alguns alunos escrevem assim por conta própria |

O painel também sugere 2 ou 3 perguntas para a conversa, a partir do que encontrou (por exemplo,
"O que o `break` da linha 5 faz? Como você escreveria esse trecho sem ele?").

## Como a equipe usa

1. O painel é um motivo para **olhar com cuidado**, nunca uma conclusão. Uma faixa alta sem nenhum
   outro sinal (a solução, o histórico da turma, a conversa) não justifica nenhuma ação.
2. A conversa acontece com respeito e sem acusação: o aluno explica o código, ou faz uma pequena
   mudança nele. As perguntas do painel são um ponto de partida.
3. A decisão sobre a nota segue as regras da disciplina, pela equipe, depois da conversa.
4. Cada caso conversado entra no registro da monitoria (só a lista, a faixa, os tipos de indício e
   se o uso foi confirmado ou descartado, **sem nome nem matrícula**). Esse registro alimenta o
   critério 3 do relatório de eficácia ([`eficacia.md`](eficacia.md)) e a revisão das faixas.

## O que é dito aos alunos (proposta)

> Nesta disciplina, a equipe usa uma ferramenta que confere se as soluções respeitam as permissões
> de cada lista. Ela também pode apontar à equipe soluções que valem uma conversa. Nenhuma nota é
> dada por uma ferramenta: se a equipe pedir para você explicar a sua solução, é só uma conversa
> sobre o código que você escreveu.

## Soluções de referência por IA (S29-02)

- **Quem gera:** o monitor-chefe ou o professor responsável pela lista, ao cadastrar as regras da
  questão [PROPOSTA, a confirmar com a coordenação].
- **Como:** 2 ou 3 assistentes diferentes, a partir **só do enunciado**, sem nenhum código de aluno;
  uma ou duas soluções de cada, sem edição.
- **Onde:** `rulesets/<período>/referencias/<questão>/<assistente>.py` (até 10 por questão), neste
  repositório, que é privado. O carregador do analisador recusa referência de questão não cadastrada
  ou que não é Python válido, e o `ipc-rules validate` mostra quantas há. O passo a passo está em
  [`RULES.md`](../RULES.md).
- **Privacidade:** a comparação roda no analisador isolado, no próprio servidor; nenhum dado do
  aluno sai dele.

## Calibração (antes de ligar e a cada período)

A meta da ADR-08 é **no máximo 5%** das soluções humanas (de períodos anteriores a 2023, antes dos
assistentes de código) com faixa alta. Com as soluções organizadas como os gabaritos
(`<período>/lista-<n>/<arquivo>.py`), fora deste repositório:

```bash
cd backend
uv run ipc-rules calibrate ../rulesets/2026.2 /caminho/das/solucoes --max-alto 5
```

O comando mostra quantas soluções caem em cada faixa e, para as de faixa alta, só o caminho e os
tipos de indício (nunca o código). Sai com 1 se a faixa alta passar de 5%. Nesse caso, ajuste as
faixas em `backend/src/ipc_analyzer/engine/indicators.py`, por PR, e rode de novo. A cada período,
repita com os casos confirmados e descartados do registro da monitoria.

## Como ligar no piloto

Só depois de a coordenação aprovar esta política e de a calibração ficar dentro da meta:

1. Um PR troca `IPC_AI_INDICATORS` para `"1"` no `render.yaml` e ajusta o teste que confere o valor
   (`backend/tests/test_indicators_api.py`), com o registro da aprovação no PR.
2. No GitHub, a variável `PILOT_AI_INDICATORS` passa a `1`, para a verificação do piloto esperar os
   indícios ligados.
3. No Render, **Blueprint > Sync** (ou a variável em **Environment**), e o "Deploy do piloto".

Para desligar, o caminho inverso; a variável no Render vale na hora, sem deploy novo do código.

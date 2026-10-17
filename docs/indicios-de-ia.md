# Indícios de uso de IA: política e calibração

Política da S29-04 (ADR-08, Q-21), **aprovada em 09/10/2026** (opção A de 7.13.1 do blueprint),
com os critérios da Q-35 (12/10/2026) implementados na Sprint 42. No piloto, o painel liga por cargo
(`IPC_AI_INDICATORS`: `0`, `chefia` ou `1`), primeiro para a chefia, só com as metas da calibração
cumpridas ("Como ligar no piloto", abaixo). Até lá, fica em `0` (conferido por um teste).

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

**12/10/2026:** o autor descartou as soluções anteriores a 2023, que não existem e não serão
buscadas, e aprovou os critérios e a nova base de calibração (Q-35), que estão na seção seguinte
e entram na Sprint 42. O texto abaixo descreve o procedimento original.

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

## Critérios aprovados em 12/10/2026 (Q-35, Sprint 42)

Os quatro primeiros se apoiam no documento de permissões. Nenhum deles é prova; todos levam a uma
conversa com o aluno.

| # | Critério | Exemplo | Faixa |
|---|---|---|---|
| 1 | Construção liberada só 2 ou mais listas depois | Dicionário ou `lambda` na Lista 2 | Média com 1 construção, alta com 2 ou mais |
| 2 | Construção que o documento não cita (R-04) | `match`, `:=`, `isdigit()`, `sorted(key=...)` | Baixa com 1 ou 2, média com 3 ou mais |
| 3 | Várias proibições gerais diferentes juntas | `try/except` com `break` e `None` | Média com 2, alta com 3 ou mais |
| 4 | A mesma proibição repetida | Três `break` | No máximo média: repetir um hábito não indica IA |
| 5 | Parecida com uma solução gerada por IA para a questão | As referências do gerador aprovado (S33-09) | Baixa a partir de 80%, média a partir de 90%, alta a partir de 95% |
| 6 | Parecida com o gabarito | Pode ser IA ou gabarito vazado | As mesmas faixas, com esse aviso |

**Marcadores sem faixa, mostrados só como fatos:** docstrings, anotações de tipo,
`if __name__ == "__main__"`, nomes e comentários em inglês e, novos, texto dentro do `input()` (por
exemplo, `input("Digite um número: ")`) e validação de entrada que o enunciado não pede (por
exemplo, repetir o `input` até o valor ser válido). A suposição de que as soluções do Dikastis usam
`input()` sem texto é uma hipótese a confirmar com a equipe.

**Fora dos critérios:** detectores de texto gerado por IA, perguntar a uma IA e comparar com o
histórico do aluno, que a Q-27 tornou impossível.

**Calibração sem as soluções anteriores a 2023:**
- **Alarmes falsos:** os gabaritos da equipe; nenhum pode ficar na faixa alta (em 11/10/2026, 0%).
- **Acertos:** cerca de seis soluções novas geradas por IA por questão, diferentes das referências;
  pelo menos metade deve cair na faixa média ou alta. Com os gabaritos, a base chega às 200
  soluções da premissa validada.
- **Ligação:** primeiro só para a chefia (desenvolvedor, professores e monitores-chefes) durante
  uma lista; depois, para toda a equipe.

## Evidência e confiança (S42-03)

Desde a Sprint 42, cada indício traz a evidência (a regra do documento de permissões ou o marcador,
as linhas e um trecho de até 120 caracteres do código verificado) e a confiança (baixa, média ou
alta), separada da faixa: a faixa diz quanto o sinal pesa; a confiança, quão certo ele é. As
violações e os marcadores encontrados no código têm confiança alta; a validação da entrada, média;
os nomes e comentários em inglês, baixa; a semelhança com uma referência ou com o gabarito, alta a
partir de 95% e média abaixo. Um teste confere que nenhum texto do motor ou da página afirma uso de
IA nem é veredito.

## Referências e calibração na prática (S42-04 e S42-02)

**Gerar as referências:** os enunciados ficam fora do repositório, um arquivo por questão
(`L1-Q2.md`), e as chaves das IAs num arquivo também fora do repositório, `chaves-ia.env`
(`IPC_LLM_CHAIN` e as variáveis de cada IA, as mesmas do "Aprimorar com IA" no Render; o modelo
está em `Desktop\IP-Checker\chaves-ia.env.exemplo`), preenchido por quem mantém o projeto. Não
use o `deploy/.env`: lá, as mesmas variáveis ligariam a IA de verdade no compose e no e2e. De
`backend/`:

```bash
uv run python -m ipc_api.referencias ../rulesets/2026.2 --enunciados ../../enunciados/2026.2 --env-file ../../chaves-ia.env
```

O comando pede 2 soluções a cada IA da cadeia, só a partir do enunciado, e grava em
`rulesets/<período>/referencias/<questão>/<ia>-<n>.py`, com um cabeçalho (IA, modelo e data).
Desde a S42-04, uma questão só com gabarito, sem regras cadastradas, também ganha referências. Um
arquivo que já existe é pulado: com a cota das IAs gratuitas esgotada, rode de novo mais tarde. As
referências entram por PR, revisado por quem cadastra a questão.

**Referências redundantes (Sprint 42.1):** nas questões simples, a IA escreve a solução padrão,
a mesma do gabarito da equipe. Uma referência assim não distingue IA de quem resolve do jeito
padrão e põe o gabarito na faixa alta. Depois de cada geração, rode a calibração com
`--remover-redundantes`: ela apaga as referências 95% ou mais iguais ao gabarito da questão (o
limiar da faixa alta do sinal) antes de medir. Em 2026.2, saíram 8, todas de L1-Q1 e L1-Q3.

**Os limites do gerador:** enunciados de até 40 KB (os maiores de 2026.2 têm 25 KB); respostas de
até 8.192 tokens, porque os modelos que raciocinam antes de responder gastavam o limite antigo
no raciocínio; num 413 (o Groq gratuito conta o teto da resposta nos 8 mil tokens por minuto),
o pedido é repetido com 4.096 e depois com 2.048. A cota diária gratuita do Groq rende poucas
dezenas de pedidos com enunciados desse tamanho: o gerador retoma de onde parou.

**Gerar a base de calibração:** o mesmo comando, com `--para-calibracao ../../calibracao --por-ia 3`,
grava soluções **novas**, diferentes das referências, fora do repositório.

**Medir:** `ipc-rules calibrate` com `--gabaritos` e `--geradas` (runbook, "Recalibrar a cada
período").

**Medições:**

| Data | Base | Resultado |
|---|---|---|
| 16/10/2026 | 28 gabaritos de 2026.2 (Listas 1 a 4) | Alarmes falsos: 28 na faixa "nenhum", 0 na alta (meta cumprida); 2 com o marcador de validação da entrada, sem peso |
| 17/10/2026 | Os mesmos 28 gabaritos, com as 102 referências de IA (Sprint 42.1) | Alarmes falsos: 0 na alta (meta cumprida), 2 na média e 1 na baixa, todos pelo sinal da referência; antes de remover as 8 referências redundantes, 2 na alta (L1-Q1 e L1-Q3) |
| 17/10/2026 | 206 soluções novas geradas por IA a partir dos enunciados do catálogo (169 do Gemini, 24 do gpt-oss e 13 do Qwen), diferentes das referências | Acertos: 83,0% na média ou alta (meta: 50%; cumprida); por modelo, 81,7%, 100% e 69,2%. Com os gabaritos, 234 soluções, acima das 200 da premissa |

## Como ligar no piloto

Pela variável `IPC_AI_INDICATORS` (S42-05), em dois passos, sempre por PR no `render.yaml`, sozinho
no PR (sem migração junto, P-18):

1. **Chefia:** `IPC_AI_INDICATORS: chefia`, com as duas metas da calibração cumpridas. Liga o painel
   só para o desenvolvedor, os professores e os monitores-chefes durante uma lista inteira, com cada
   conversa no [registro de casos](registro-de-casos.md). A verificação do piloto
   (`backend/tests/pilot`) confere, com `PILOT_AI_INDICATORS=chefia`, que a conta de verificação
   recebe os indícios conforme o cargo.
2. **Toda a equipe:** `IPC_AI_INDICATORS: "1"`, só depois dessa lista e da revisão das faixas com o
   registro de casos, com o comando do autor.

Para desligar, a variável `0` no Render vale sem deploy novo do código (runbook, "Desligar os
indícios").

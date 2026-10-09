# Marco 2: apresentação a monitores-chefes e professores

Pauta da reunião em que monitores-chefes e professores ratificam as interpretações das regras e
decidem o que é da coordenação (S31-05, US-11). Até lá, tudo o que está aqui segue como em "Hoje":
do lado mais restritivo, que a equipe pode relevar quando o enunciado liberar (vale o enunciado).

- **Data:** 19/10/2026. Em 09/10/2026, o autor já decidiu os itens 2 a 5 (marcados abaixo); a
  reunião apresenta as decisões à equipe e registra o que mudar.
- **Quem:** o autor (apresenta), os monitores-chefes e os professores da disciplina.
- **Material:** esta pauta, o [guia da equipe](guia-da-equipe.md), a demonstração do piloto
  (<https://ip-checker-red-phi.vercel.app>) e, para os detalhes, o [mapeamento](mapping-R-xx.md) e
  as [decisões](decisoes.md).
- **Depois da reunião:** cada decisão vira uma linha em `docs/decisoes.md`, com a data e quem
  decidiu; as que mudam regras entram por PR no ruleset, pelo processo do [`RULES.md`](../RULES.md).

## 1. Ratificar as interpretações já aplicadas (10 min)

As decisões C-01 a C-03 e Q-02 a Q-05, tomadas pelo autor em 01/10/2026, já estão no motor
(`docs/mapping-R-xx.md`, "Decisões aplicadas"). Pergunta: **ratificar como estão?**

## 2. Os 10 casos do mapeamento (20 min)

Os casos a observar das Sprints 22 e 23 (`docs/mapping-R-xx.md`) e, desde 09/10/2026, o caso 10, já aplicado de forma provisória (`docs/decisoes.md`, Q-02). Para cada um, a decisão é
"manter como hoje" ou "liberar a partir da lista X". Liberar é uma mudança no `base.yaml`, com teste
golden, numa sprint seguinte.

| # | Caso | Hoje | Pergunta | Decisão |
|---|---|---|---|---|
| 1 | `if __name__ == "__main__":` | R-04 (não consta) | As listas usam esse padrão? Se sim, liberar a partir da L4? | Permitido a partir da L4 (R-59) |
| 2 | `f(x=1)` com função do aluno | R-04 | A R-59 ("parâmetros") inclui argumentos nomeados na chamada? | Inclui (R-59, a partir da L4) |
| 3 | `for a, b in pares:` na L3 ou depois | R-37 (condição não atendida) | A R-40 (tuplas) deve aceitar vários nomes no `for` a partir da L3? | Aceita, a partir da L3 |
| 4 | `f"{x!r}"`, `f"{x!s}"`, `f"{x!a}"` | Aceito (R-31) | A conversão conta como `repr()`, `str()` ou `ascii()`? | Aceito como está |
| 5 | `[a + b for a, b in zip(x, y)]` na L3 ou L4 | R-37 (condição não atendida) | O `for` de uma *list comprehension* conta como "comando for" para a R-37? | Conta e é permitido |
| 6 | `palavras = input().split()` como única lista, na L3 | R-02 (assunto não comprovado) | Uma lista vinda de `split()` comprova o assunto da Lista 3? | Comprova |
| 7 | `dict(a=1)`, `d.update(a=1)`, `enumerate(v, start=1)` na L5 | R-04 (só `end=` consta) | Esses argumentos nomeados fazem parte do que a Lista 5 ensina? | Fazem; permitidos desde a L5 |
| 8 | `for a, b in pares:` e `for x, y in d.values():` na L5 ou L6 | R-63 (condição não atendida) | Vários nomes no `for` valem para qualquer sequência de pares? (junto com o caso 3) | Valem |
| 9 | `f = lambda n: f(n - 1) if n else 0` na L6 | Não conta como recursão (R-68) | Recursão por `lambda` comprova o assunto da Lista 6? | Não comprova (fica como está) |
| 10 | Expressão geradora: `" ".join(str(n) for n in v)`, `sum(x for x in v)` (gabarito oficial L3-Q8 de 2026.2) | Aceito a partir da L3 (decisão provisória de 09/10/2026, R-41; antes, R-04 pela Q-02 e) | Ratificar: a expressão geradora fica permitida a partir da Lista 3, como a *list comprehension*? A *dict comprehension* continua de fora. | Ratificado |

**Aplicado em 09/10/2026 no ruleset `2026.2.5`** (casos 1, 2, 3, 5, 6, 7 e 8), com os casos golden de
cada um (`docs/mapping-R-xx.md`, "Casos do Marco 2").

Lembrete: desde a Sprint 24, uma questão cadastrada pode liberar qualquer um desses casos pela R-01,
sem mudar a regra geral.

## 3. Indícios de uso de IA (15 min, S31-01)

A proposta de política está em [`indicios-de-ia.md`](indicios-de-ia.md): para que servem, o texto
aos alunos, quem gera as soluções de referência e quando ligar no piloto. Os indícios estão
desligados no piloto até esta aprovação. **Decidir:** aprovar, aprovar com mudanças ou não usar. As
opções estão em 7.13.1 do blueprint. **Decidido (09/10/2026):** aprovada como está (opção A); os
indícios ligam no piloto depois da calibração (S33-03 e S33-06).

## 4. Decisões que dependem da coordenação e do NTI (15 min)

| Questão | O que decidir | Opções |
|---|---|---|
| Q-16 | Provedor de IA do feedback e os dados enviados (LGPD) | 7.13.2 do blueprint. **Decidido (09/10/2026, autor):** A e C combinadas: o feedback sem IA é o padrão, e um botão "Aprimorar com IA" usa provedores gratuitos em cadeia, com fallback. A coordenação toma ciência do envio a provedores gratuitos nesta reunião |
| Q-17 | Remetente dos e-mails de verificação (hoje um Gmail pelo Brevo) | 7.13.3 do blueprint. **Decidido (09/10/2026, autor):** opção A, mantém o Brevo com o remetente Gmail |
| Q-22 | Governança das regras por questão: quem aprova cada PR | 7.13.4 do blueprint. **Decidido (09/10/2026, autor):** opção A, mantém o processo atual |

## 5. Questões e gabaritos por período (10 min, ADR-10)

Como a equipe cadastra as questões de cada período (`RULES.md`) e quem guarda os gabaritos no
repositório privado `Lionzio/ip-checker-gabaritos`. **Decidido (09/10/2026, autor):** questões e
gabaritos são cadastrados por monitores, monitores-chefes, professores e o desenvolvedor; a aprovação
segue o `RULES.md` (monitor-chefe ou professor, nunca quem cadastrou). Falta decidir quem da equipe
recebe acesso ao repositório dos gabaritos.

## 6. Piloto em 2027.1 (10 min)

Os critérios de eficácia (P-09), a pesquisa de fim de piloto (S31-06) e as listas habilitadas no
começo do período (S34-05). **Decidir:** a data de início do uso pela equipe (em 09/10/2026, ainda
sem data: depende do calendário da UFPE, P-10). O formulário e a planilha da S31-06 ficam para
depois.

## Registro

| Item | Decisão | Quem decidiu | Data |
|---|---|---|---|
| 1 | A ratificar na reunião | | |
| 2 | Casos 1 a 10 como na tabela do item 2 (`2026.2.5`) | Autor | 09/10/2026 |
| 3 | Política dos indícios aprovada como está | Autor | 09/10/2026 |
| 4 | Q-16: A e C combinadas ("Aprimorar com IA" com provedores gratuitos); Q-17: A; Q-22: A | Autor | 09/10/2026 |
| 5 | Questões e gabaritos cadastrados por monitores, monitores-chefes, professores e o desenvolvedor | Autor | 09/10/2026 |
| 6 | Data do piloto: sem data (P-10) | Autor | 09/10/2026 |

# Marco 2: apresentação a monitores-chefes e professores

Pauta da reunião em que monitores-chefes e professores ratificam as interpretações das regras e
decidem o que é da coordenação (S31-05, US-11). Até lá, tudo o que está aqui segue como em "Hoje":
do lado mais restritivo, que a equipe pode relevar quando o enunciado liberar (vale o enunciado).

- **Data:** [A CONFIRMAR: marcada pelo autor com a coordenação]
- **Quem:** o autor (apresenta), os monitores-chefes e os professores da disciplina.
- **Material:** esta pauta, o [guia da equipe](guia-da-equipe.md), a demonstração do piloto
  (<https://ip-checker-red-phi.vercel.app>) e, para os detalhes, o [mapeamento](mapping-R-xx.md) e
  as [decisões](decisoes.md).
- **Depois da reunião:** cada decisão vira uma linha em `docs/decisoes.md`, com a data e quem
  decidiu; as que mudam regras entram por PR no ruleset, pelo processo do [`RULES.md`](../RULES.md).

## 1. Ratificar as interpretações já aplicadas (10 min)

As decisões C-01 a C-03 e Q-02 a Q-05, tomadas pelo autor em 01/10/2026, já estão no motor
(`docs/mapping-R-xx.md`, "Decisões aplicadas"). Pergunta: **ratificar como estão?**

## 2. Os 9 casos em aberto do mapeamento (20 min)

Os casos a observar das Sprints 22 e 23 (`docs/mapping-R-xx.md`). Para cada um, a decisão é
"manter como hoje" ou "liberar a partir da lista X". Liberar é uma mudança no `base.yaml`, com teste
golden, numa sprint seguinte.

| # | Caso | Hoje | Pergunta | Decisão |
|---|---|---|---|---|
| 1 | `if __name__ == "__main__":` | R-04 (não consta) | As listas usam esse padrão? Se sim, liberar a partir da L4? | |
| 2 | `f(x=1)` com função do aluno | R-04 | A R-59 ("parâmetros") inclui argumentos nomeados na chamada? | |
| 3 | `for a, b in pares:` na L3 ou depois | R-37 (condição não atendida) | A R-40 (tuplas) deve aceitar vários nomes no `for` a partir da L3? | |
| 4 | `f"{x!r}"`, `f"{x!s}"`, `f"{x!a}"` | Aceito (R-31) | A conversão conta como `repr()`, `str()` ou `ascii()`? | |
| 5 | `[a + b for a, b in zip(x, y)]` na L3 ou L4 | R-37 (condição não atendida) | O `for` de uma *list comprehension* conta como "comando for" para a R-37? | |
| 6 | `palavras = input().split()` como única lista, na L3 | R-02 (assunto não comprovado) | Uma lista vinda de `split()` comprova o assunto da Lista 3? | |
| 7 | `dict(a=1)`, `d.update(a=1)`, `enumerate(v, start=1)` na L5 | R-04 (só `end=` consta) | Esses argumentos nomeados fazem parte do que a Lista 5 ensina? | |
| 8 | `for a, b in pares:` e `for x, y in d.values():` na L5 ou L6 | R-63 (condição não atendida) | Vários nomes no `for` valem para qualquer sequência de pares? (junto com o caso 3) | |
| 9 | `f = lambda n: f(n - 1) if n else 0` na L6 | Não conta como recursão (R-68) | Recursão por `lambda` comprova o assunto da Lista 6? | |

Lembrete: desde a Sprint 24, uma questão cadastrada pode liberar qualquer um desses casos pela R-01,
sem mudar a regra geral.

## 3. Indícios de uso de IA (15 min, S31-01)

A proposta de política está em [`indicios-de-ia.md`](indicios-de-ia.md): para que servem, o texto
aos alunos, quem gera as soluções de referência e quando ligar no piloto. Os indícios estão
desligados no piloto até esta aprovação. **Decidir:** aprovar, aprovar com mudanças ou não usar. As
opções estão em 7.13.1 do blueprint.

## 4. Decisões que dependem da coordenação e do NTI (15 min)

| Questão | O que decidir | Opções |
|---|---|---|
| Q-16 | Provedor de IA do feedback e os dados enviados (LGPD) | 7.13.2 do blueprint |
| Q-17 | Remetente dos e-mails de verificação (hoje um Gmail pelo Brevo) | 7.13.3 do blueprint |
| Q-22 | Governança das regras por questão: quem aprova cada PR | 7.13.4 do blueprint |

## 5. Questões e gabaritos por período (10 min, ADR-10)

Como a equipe cadastra as questões de cada período (`RULES.md`) e quem guarda os gabaritos no
repositório privado `Lionzio/ip-checker-gabaritos`. **Decidir:** quem cadastra as questões de 2027.1,
quem aprova, e quem da equipe recebe acesso aos gabaritos.

## 6. Piloto em 2027.1 (10 min)

Os critérios de eficácia (P-09), a pesquisa de fim de piloto (S31-06) e as listas habilitadas no
começo do período (S33-05). **Decidir:** a data de início do uso pela equipe.

## Registro

| Item | Decisão | Quem decidiu | Data |
|---|---|---|---|
| | | | |

# Ensaio do cadastro de questões (S31-13)

Ensaio do fluxo do [`RULES.md`](../RULES.md) antes de 2027.1, quando o cadastro das questões vira
rotina. A questão abaixo foi **criada para o ensaio** a pedido do autor (09/10/2026): não foi
aplicada aos alunos. Ela recebeu o número L3-Q9 porque a Lista 3 de 2026.2 tem 8 questões, e o
título no seletor começa com "Ensaio" para ninguém confundir com uma questão real.

## O enunciado

> **L3-Q9 — Média da turma**
>
> Leia, numa única linha, as notas de uma turma, separadas por espaço. Converta as notas para
> `float` usando `map()`. Mostre a média da turma com uma casa decimal, a maior e a menor nota e
> quantos alunos ficaram com nota maior ou igual a 7.
>
> **Restrições:** não use `sum()`, `sort()` nem `sorted()`: faça as contas com um laço `for`. As
> demais permissões da Lista 3 continuam valendo.
>
> Exemplo de entrada: `7.5 4 9 6.5`
>
> Exemplo de saída:
>
> ```text
> Média: 6.8
> Maior: 9.0
> Menor: 4.0
> Aprovados: 2
> ```

## O que o enunciado muda nas regras

| Construção | Pela Lista 3 | Pelo enunciado | No cadastro |
|---|---|---|---|
| `map()` | Não consta no documento (R-04) | Permitido | `allow_facts: [builtin:map]` |
| `sum()` | Permitido (R-55) | Proibido | `deny: [R-55]` |
| `sort()` e `sorted()` | Permitidos (R-48) | Proibidos | `deny: [R-48]` |

O arquivo é [`rulesets/2026.2/questions/L3-Q9.yaml`](../rulesets/2026.2/questions/L3-Q9.yaml), e
`backend/tests/test_questions.py` confere o efeito com uma solução que respeita o enunciado e com
as que usam `sum()` e `sorted()`.

## Como testar na página

1. Escolha a **Lista 3** e a questão **L3-Q9 · Ensaio: média da turma sem sum()**.
2. Cole uma solução com `map()` e um `for`: não há violação. Sem a questão escolhida, o mesmo código
   mostra o `map()` como R-04 (não consta).
3. Troque o laço por `sum(notas)` ou ordene com `sorted(notas)`: aparece a violação R-01 (proibido
   na questão), que anula a questão.

## O que o ensaio mostrou

- O fluxo de `RULES.md` funciona do arquivo ao seletor: `ipc-rules validate ../rulesets` mostra
  "1 questão", e a questão aparece no seletor depois do deploy.
- Pelo processo (Q-22, opção A), o PR de uma questão real é aprovado por um monitor-chefe ou
  professor, nunca por quem cadastrou. Neste ensaio, quem cadastrou foi o agente, a pedido do autor.
- Falta ensaiar com a equipe: cada monitor cadastrar uma questão de verdade em 2027.1 (S33-04).

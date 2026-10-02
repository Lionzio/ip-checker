# Guia do piloto (2027.1) para alunos e monitores

> **Atenção (02/10/2026):** este guia foi escrito para um piloto aberto a alunos. Com a decisão
> de restringir o acesso à equipe da disciplina (P-13 do blueprint), ele será substituído pelo
> guia da equipe na Sprint 19.

O **IP-Checker** confere, antes do envio ao Dikastis, se a sua solução em Python respeita as
permissões da lista de Introdução à Programação. Ele **não executa o seu código**: lê o texto como
o Python o entenderia e compara cada construção com o documento "Permissões das listas".

No começo do piloto, só a **Lista 1 (comandos condicionais)** está liberada. As demais entram ao
longo do período.

## O que ele faz e o que não faz

| Faz | Não faz |
|---|---|
| Aponta construções proibidas em todas as listas (`import`, `try`, `break`, `None`, sets, classes…) | Não testa se a resposta está certa: isso continua com o Dikastis |
| Aponta o que só é liberado numa lista posterior (por exemplo, `for` na Lista 1) | Não considera ainda as regras específicas de cada questão: **se o enunciado liberar algo, vale o enunciado** |
| Aponta o que não consta no documento de permissões (por exemplo, `eval`, `lambda` antes da hora) | Não guarda nem registra o seu código |
| Exige o assunto da lista (na Lista 1, pelo menos um `if` ou um operador ternário) | Não substitui a leitura do documento de permissões |
| Mostra erros de sintaxe com linha e coluna, em português | |

## Como usar

1. Abra a página do IP-Checker.
2. Escolha a lista.
3. Cole a solução (até 50 KB e 1.000 linhas).
4. Clique em **Verificar**.

## Como ler o resultado

Cada violação mostra a categoria, a linha e a coluna, a regra do catálogo (R-xx) e uma explicação.

| Categoria | O que significa |
|---|---|
| **Anulação imediata** | Proibido em todas as listas. Se for enviado assim, a questão é anulada. |
| **Fora da lista** | Permitido só a partir de uma lista posterior, que a mensagem informa. |
| **Não consta no documento** | Não aparece no documento de permissões; por isso é proibido (R-04). |
| **Exigência não atendida** | A solução não usa o assunto obrigatório da lista. Aparece como "Solução inteira". |

Um **erro de sintaxe** é mostrado no lugar das violações: as permissões só são verificadas depois que
o código está sintaticamente correto.

Se houver mais de 200 violações, a página mostra as 200 primeiras e avisa. Corrija essas e verifique
de novo.

## Mensagens de espera

| Mensagem | O que fazer |
|---|---|
| "Limite de verificações atingido" | Cada aba pode verificar até 10 vezes por minuto. Espere a contagem e tente de novo. |
| "Serviço ocupado" | Muita gente verificando ao mesmo tempo. Espere a contagem e tente de novo. |
| "Serviço indisponível" ou "Sem resposta do servidor" | O serviço está fora do ar ou a conexão caiu. Tente de novo em alguns segundos. |

## Privacidade

- O código é analisado e descartado: não vai para log, banco nem disco.
- Não há login. Cada aba gera um identificador aleatório, usado só para o limite de 10 verificações
  por minuto; ele some quando a aba é fechada.
- O IP é usado só para o limite por rede, existe só na memória do servidor e é apagado em até
  2 minutos.

## Para monitores

- Durante o atendimento, verifique o código do aluno na lista dele: o relatório é exatamente o mesmo
  que ele veria.
- Se o IP-Checker apontar algo que o documento permite (**falso positivo**) ou deixar passar algo
  proibido (**falso negativo**), avise o autor do projeto com o código e a lista. Cada caso
  confirmado vira um teste novo, e a meta do piloto é corrigir falsos positivos em até 2 dias úteis
  (critério de eficácia 1, P-09).
- Lembre o aluno de que as regras específicas de cada questão ainda não são consideradas: em caso de
  divergência, vale o enunciado. Elas entram na Sprint 24, cadastradas pelos monitores e aprovadas
  por monitor-chefe ou professor.

## Perguntas frequentes

**Meu código passou no IP-Checker. Então está certo?**
Ele respeita as permissões da lista. Se a resposta está certa, só o Dikastis diz.

**Por que `print("oi")` sozinho dá "Exigência não atendida" na Lista 1?**
Toda questão da Lista 1 precisa usar o assunto da lista: um comando condicional (`if`, com ou sem
`elif`/`else`) ou o operador ternário. Um `if` dentro de um texto ou de um comentário não conta.

**O enunciado da questão libera algo que o IP-Checker aponta. E agora?**
Vale o enunciado. Nesse caso, a violação pode ser ignorada.

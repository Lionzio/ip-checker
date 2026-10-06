# Guia da equipe do IP-Checker

O **IP-Checker** é a ferramenta da equipe de Introdução à Programação (desenvolvedor, professores,
monitores-chefe e monitores) para apoiar a correção das listas. Ele faz três coisas:

1. **Verifica** se uma solução em Python respeita as permissões da lista, apontando cada construção
   proibida com linha, coluna e a regra do documento "Permissões das listas".
2. **Compara** duas soluções e mostra a similaridade, como indício de plágio.
3. **Redige um feedback** para o aluno a partir do resultado da verificação.

O código nunca é executado: o IP-Checker lê o texto como o Python o entenderia, num serviço isolado,
e descarta tudo depois. O acesso é só da equipe; alunos não têm conta.

## O que ele faz e o que não faz

| Faz | Não faz |
|---|---|
| Aponta construções proibidas em todas as listas (`import`, `try`, `break`, `None`, sets, classes...) | Não testa se a resposta está certa: isso continua com o Dikastis |
| Aponta o que só é liberado numa lista posterior (por exemplo, `for` na Lista 1) | Só conhece as regras de uma questão que foi cadastrada: **se o enunciado liberar algo que não foi cadastrado, vale o enunciado** |
| Aponta o que não consta no documento de permissões (por exemplo, `eval`) | Não decide se houve plágio: a porcentagem é um indício, e a decisão é da equipe |
| Exige o assunto da lista (Lista 1: `if` ou ternário; Lista 2: `for` ou `while`; Lista 3: uma lista ou tupla; Lista 4: um `def`; Lista 5: um dicionário; Lista 6: recursão) | Não guarda nem registra o código de ninguém |
| Mostra erros de sintaxe com linha e coluna, em português | Não substitui a leitura do documento de permissões |

Estão liberadas as seis listas: **1 (comandos condicionais), 2 (laços de repetição), 3 (listas e
tuplas), 4 (funções e escopo de variável), 5 (dicionários) e 6 (recursão)**.

Na Lista 3, o assunto é comprovado por uma lista ou tupla escrita no código (`[1, 2]`, `(1, 2)`,
`a, b = ...`), por `list()`, `tuple()` ou por uma *list comprehension*; uma lista que só vem de
`split()` não basta. Na Lista 4, parâmetro com valor padrão (`def f(x=1)`) e função dentro de
função não constam no documento e aparecem com a R-04.

Na Lista 2, o `zip()` segue a condição do documento: só serve para variar mais de um índice no
comando `for`. Então `for a, b in zip(nomes, notas):` passa, e o `zip()` em qualquer outro lugar
(`z = zip(a, b)`, com uma sequência só ou dentro de outra chamada) aparece com a R-37. Vários nomes
no `for` (`for a, b in ...`) só passam junto com esse `zip()`.

Na Lista 5, o assunto é comprovado por um dicionário escrito no código (`{"a": 1}`) ou por `dict()`;
uma *dict comprehension* não consta no documento e aparece com a R-04. O `zip()` fica livre, e
vários nomes no `for` passam quando o `for` percorre `zip()`, `enumerate()` ou `.items()`
(`for chave, valor in d.items():`). O `lambda` é permitido, mas `key=` (como em
`sorted(v, key=lambda x: x[1])`) continua sem constar no documento.

Na Lista 6, toda questão precisa de recursão: uma função com `def` que chama a si mesma, direta ou
indiretamente (`f` chama `g`, que chama `f`). Chamar a função várias vezes fora dela não é
recursão, e um `lambda` que chama a si mesmo não conta.

## Entrar na equipe

1. Em **Registrar**, use o seu e-mail institucional (`@cin.ufpe.br` ou `@ufpe.br`; prefira o
   `@cin.ufpe.br`), o nome com que quer aparecer, o curso e o tratamento. A senha precisa de pelo
   menos 9 caracteres, uma letra maiúscula e um caractere especial; a página mostra o que falta
   enquanto você digita. Se o Google estiver habilitado, **Registrar com o Google** dispensa a
   senha.
2. Abra o e-mail **"Confirme o seu cadastro no IP-Checker"** e clique em **"Clique aqui para
   verificar seu acesso."**. Na página que abrir, clique em **Confirmar meu e-mail**. O link vale
   por 24 horas e uma vez só; se ele vencer, peça outro na tela de registro.
3. O pedido vai para a aprovação de um monitor-chefe, de um professor ou do desenvolvedor, que
   escolhe o seu cargo. Até lá, a tela de entrada mostra "aguardando a aprovação".
4. Aprovado, entre com o nome ou o e-mail e a senha, ou com o Google.

Esqueceu a senha? Em **Entrar**, clique em **Esqueci minha senha** e informe o e-mail
institucional. Se houver uma conta com ele, chega o e-mail **"Redefina a sua senha do
IP-Checker"**, com um link que vale por 1 hora e uma vez só. Ao definir a senha nova, as sessões
abertas da conta são encerradas.

O **nome** é único e também serve para entrar. O **tratamento** (masculino, feminino ou neutro)
define como você se apresenta no feedback ("sou o monitor...", "sou a monitora...", "aqui é ...,
da monitoria"); só você o vê.

## Perfil

Em **Perfil**, você muda o nome, o curso, o tratamento e a senha. A troca de senha pede a senha
atual e encerra as suas outras sessões; a desta aba continua. Uma conta criada pelo Google pode
definir uma senha ali. O cargo não muda pelo perfil: quem aprova os cadastros é que o altera.

A sessão termina depois de 12 horas sem uso, em no máximo 7 dias, e também quando você sai, troca
a senha, muda de cargo ou é removido da equipe.

## Verificar uma solução

1. Escolha a lista.
2. Escolha a questão, se ela tiver regras cadastradas (veja abaixo). Sem questão, valem só as
   permissões da lista, e o resultado avisa isso.
3. Cole a solução (até 50 KB e 1.000 linhas).
4. Clique em **Verificar**.

Cada violação mostra a categoria, a linha e a coluna, a regra do catálogo (R-xx) e uma explicação.

| Categoria | O que significa |
|---|---|
| **Anulação imediata** | Proibido em todas as listas. Enviado assim, a questão é anulada. |
| **Fora da lista** | Permitido só a partir de uma lista posterior, que a mensagem informa. |
| **Não consta no documento** | Não aparece no documento de permissões; por isso é proibido (R-04). Também aparece quando o documento só permite a construção com uma condição que o código não cumpre, com a regra dessa condição (por exemplo, `zip()` fora do `for`, R-37). |
| **Exigência não atendida** | A solução não usa o assunto obrigatório da lista. Aparece como "Solução inteira". |

Um **erro de sintaxe** aparece no lugar das violações: as permissões só são verificadas quando o
código está sintaticamente correto. Com mais de 200 violações, a página mostra as 200 primeiras e
avisa.

## Feedback para o aluno

Depois de verificar, o painel **Feedback para o aluno** aparece ao lado do resultado.

1. Digite o **nome do aluno** e, se quiser, uma **anotação importante** (observações e dicas).
2. Clique em **Gerar feedback**.
3. **Revise o texto**: ele é editável. Depois, use **Copiar**.

O texto sempre começa com a saudação, a sua apresentação (pelo seu cargo e tratamento) e a frase
obrigatória do resultado:

- sem violações: "Sua questão está ótima, não houve nenhuma violação de regras.";
- com violações: "Sua questão apresenta problemas, como o uso de ..., portanto ela foi anulada.",
  com o que o IP-Checker encontrou.

O restante é escrito por uma IA, quando há uma configurada, ou montado por modelos de texto, sem
IA; a página diz qual dos dois. Quem decide se houve violação é sempre o IP-Checker, nunca a IA, e
o feedback é sobre o código que foi verificado, mesmo que você mude o editor depois.

- Com **erro de sintaxe**, não há feedback: corrija o código e verifique de novo.
- O **nome do aluno nunca vai para a IA**: no envio, ele vira `[ALUNO]` e volta no texto pronto. Os
  comentários e as docstrings do código também não vão, e e-mails, CPFs e matrículas viram marcas.
- Cada conta gera até **60 feedbacks por dia**. Um código com erro de sintaxe não gasta a cota.

## Painel de plágio

Em **Plágio**, cole a solução de cada aluno nas duas áreas e clique em **Verificar**. A página
mostra a similaridade, com uma casa decimal, e a faixa:

| Similaridade | Faixa |
|---|---|
| 99% ou mais | Plágio |
| de 95% a menos de 99% | Altas chances de plágio |
| de 90% a menos de 95% | Requer atenção |
| de 80% a menos de 90% | Ligeiramente suspeito |
| menos de 80% | Sem suspeitas |

A comparação resiste a nomes de variáveis trocados, espaços, comentários e trechos reordenados.
**O resultado é um indício, não uma prova**: leia os dois códigos antes de concluir. Em questões
simples, soluções independentes tendem a se parecer, e a página avisa quando um dos códigos é
curto. Os dois precisam ser Python válido; se um tiver erro de sintaxe, a página diz qual e onde.

## Gerenciar a equipe

**Gerenciar** aparece para o desenvolvedor, os professores e os monitores-chefe. Cada linha mostra
só os botões que o seu cargo permite, e o servidor confere de novo a cada ação.

- **Pedidos pendentes**: aprove com um cargo ou recuse. Recusar pede confirmação.
- **Membros ativos**: altere o cargo ou remova da equipe. Remover pede confirmação, não apaga a
  conta e encerra as sessões dela: quem nunca foi monitor-chefe vira **Ex-monitor**, quem já foi vira
  **Conselheiro**, e um professor fica **inativo**.
- **Ex-monitores, conselheiros e inativos**: reative com um cargo.
- **Registro de ações** (só o desenvolvedor e os professores veem): quem aprovou, recusou, alterou o
  cargo, removeu ou reativou cada conta nos últimos 12 meses, e quando. Ninguém edita nem apaga o
  registro; depois de 12 meses, cada ação sai sozinha.

| Seu cargo | Aprova cadastros | Atribui cargo, altera cargo e remove contas de |
|---|---|---|
| Desenvolvedor | Sim | Professores, monitores-chefe e monitores |
| Professor | Sim | Professores, monitores-chefe e monitores |
| Monitor-chefe | Sim | Monitores-chefe e monitores |
| Monitor | Não | Ninguém |

Ninguém age sobre a própria conta por essa tela, e a conta do desenvolvedor não é alterada por
ninguém. As etiquetas de cargo têm cor e nome: professor (verde), monitor-chefe (azul-claro), monitor
(roxo), monitor e desenvolvedor (dourado), contas removidas (cinza).

## Mensagens de espera

| Mensagem | O que fazer |
|---|---|
| "Limite de verificações atingido" | Cada conta pode fazer até 30 verificações, comparações ou feedbacks por minuto. Espere a contagem. |
| "Você chegou ao limite de feedbacks de hoje" | A cota diária da conta acabou; ela volta no dia seguinte. |
| "Serviço ocupado" | Muita gente usando ao mesmo tempo. Espere a contagem e tente de novo. |
| "Serviço indisponível" ou "Sem resposta do servidor" | O serviço está fora do ar ou a conexão caiu. Tente de novo em alguns segundos. |

## Privacidade

O código analisado, comparado ou usado no feedback não é guardado em lugar nenhum. A conta guarda
nome, e-mail, curso, tratamento e cargo; a senha, só como resumo criptográfico. O aviso completo está
na própria página, no link **Aviso de privacidade** do rodapé.

## Quando o IP-Checker erra

Se ele apontar algo que o documento permite (**falso positivo**) ou deixar passar algo proibido
(**falso negativo**), avise o desenvolvedor com o código e a lista. Cada caso confirmado vira um
teste novo, e a meta é corrigir falsos positivos em até 2 dias úteis (P-09).

### Regras de uma questão

Quando o enunciado de uma questão permite ou proíbe algo explicitamente (por exemplo, "use
`map()`" ou "não use `append()`"), a questão pode ser cadastrada. Escolhida no seletor **Questão**,
ela prevalece sobre as permissões da lista: o que ela libera deixa de ser apontado, e o que ela
proíbe aparece como **Proibido nesta questão**. A exigência do assunto da lista continua valendo.
Se a lista não tiver nenhuma questão cadastrada, o seletor diz isso.

O cadastro é feito por monitores, por PR, e aprovado por monitor-chefe ou professor; o passo a
passo está no [`RULES.md`](../RULES.md). Uma questão que libera uma proibição geral (por exemplo,
`break`) só entra com a aprovação de um professor.

## Perguntas frequentes

**O código passou no IP-Checker. Então está certo?**
Ele respeita as permissões da lista. Se a resposta está certa, só o Dikastis diz.

**Por que `print("oi")` sozinho dá "Exigência não atendida"?**
Toda questão precisa usar o assunto da lista: na Lista 1, um comando condicional (`if`, com ou sem
`elif`/`else`) ou o operador ternário; na Lista 2, um laço (`for` ou `while`); na Lista 3, uma lista
ou tupla; na Lista 4, uma função com `def`; na Lista 5, um dicionário; na Lista 6, recursão (R-68).
Um `if` ou um `for` dentro de um texto ou de um comentário não conta.

**O enunciado da questão libera algo que o IP-Checker aponta. E agora?**
Se a questão estiver cadastrada, escolha-a no seletor **Questão** e verifique de novo. Se não
estiver, vale o enunciado: a violação pode ser ignorada, inclusive no feedback, que você pode
editar antes de copiar. Peça o cadastro da questão a um monitor (ou cadastre seguindo o
`RULES.md`), para a próxima pessoa não passar pelo mesmo.

**O feedback saiu "montado sem IA". Está errado?**
Não. A abertura e a frase obrigatória são as mesmas; só o trecho final é mais simples. Isso
acontece quando nenhuma IA está configurada ou nenhuma respondeu a tempo.

**Esqueci a senha.**
Em **Entrar**, clique em **Esqueci minha senha** e siga o link do e-mail, que vale por 1 hora. Se a
conta tiver o Google ligado, também dá para entrar pelo Google e definir uma senha nova no perfil.

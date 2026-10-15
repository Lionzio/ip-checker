# Roteiro de testes manuais do IP-Checker

Versão do piloto: release `sprint-38` (15/10/2026), ruleset `2026.2.7` (período 2026.2).
Endereço: <https://ip-checker-red-phi.vercel.app>.

Este roteiro é para o desenvolvedor e os monitores testarem, à mão, tudo o que o IP-Checker faz
hoje. Os resultados esperados dos códigos de exemplo **foram conferidos no próprio motor do
IP-Checker** com o ruleset acima. Se a página mostrar outra coisa, é uma falha a relatar (ou o
ruleset mudou: confira a versão no rodapé do resultado).

## Como usar

1. Cada pessoa testa com a **própria conta** da equipe. Os cenários de **Gerenciar** precisam de
   uma conta de monitor-chefe, professor ou desenvolvedor e de uma conta de teste para aprovar,
   alterar e remover.
2. Use **só os códigos deste roteiro** ou códigos escritos por você. Não cole solução de aluno de
   verdade nos testes do **Aprimorar com IA**: o texto vai a provedores gratuitos de IA.
3. Nos cenários com **gabarito**, quem testa precisa ter acesso ao gabarito oficial (Notion ou
   repositório privado). **Nunca** copie o gabarito para este documento nem para o relato de
   falha: descreva o que fez ("colei o gabarito da L2-Q3 e troquei os nomes").
4. Marque **OK**, **Falhou** ou **Não testado** em cada cenário e anote o que viu. Numa falha,
   anote o **código do erro** que a página mostra (o `request_id`), a lista, a questão e o
   horário, e mande ao desenvolvedor com o código usado.
5. Alguns cenários **gastam limites** da conta (marcados com ⚠). Faça-os por último.

### Categorias do resultado

| Categoria | O que significa |
|---|---|
| Anulação imediata | Proibido em todas as listas (`import`, `try`, `break`, `None`, sets, classes...). |
| Fora da lista | Permitido só a partir de uma lista posterior, que a mensagem informa. |
| Não consta no documento | Não aparece no documento de permissões, por isso é proibido (R-04), ou não cumpre a condição da regra (por exemplo, `zip()` fora do `for`, R-37). |
| Exigência não atendida | A solução não usa o assunto obrigatório da lista. Aparece como "Solução inteira". |
| Proibido nesta questão | A questão escolhida no seletor proíbe a construção (R-01). |

### Faixas de similaridade (plágio e gabarito)

| Similaridade | Faixa |
|---|---|
| 99% ou mais | Plágio |
| de 95% a menos de 99% | Altas chances de plágio |
| de 90% a menos de 95% | Requer atenção |
| de 80% a menos de 90% | Ligeiramente suspeito |
| menos de 80% | Sem suspeitas |

## 1. Acesso e conta

### A-01. Registro com e-mail que não é institucional

- **Objetivo:** Só e-mails `@cin.ufpe.br` ou `@ufpe.br` podem se registrar.
- **Passos:**
  1. Saia da conta (ou use uma janela anônima) e abra a página.
  2. Clique em **Registrar**.
  3. Preencha com um e-mail `@gmail.com` e os outros campos válidos e envie.
- **Esperado:**
  - A página recusa o cadastro e explica que o e-mail precisa ser institucional.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-02. Senha fraca no registro

- **Objetivo:** A senha precisa de pelo menos 9 caracteres, uma letra maiúscula e um caractere especial.
- **Passos:**
  1. Em **Registrar**, digite aos poucos a senha `abc`, depois `abcdefghi`, depois `Abcdefghi`, depois `Abcdefgh!`.
- **Esperado:**
  - Enquanto você digita, a página mostra o que ainda falta.
  - Só `Abcdefgh!` é aceita.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-03. Registro válido e e-mail de confirmação

- **Objetivo:** O cadastro manda o e-mail "Confirme o seu cadastro no IP-Checker".
- **Passos:**
  1. Registre-se com um e-mail institucional seu que ainda não tenha conta (um subendereço, como `seunome+teste@cin.ufpe.br`, serve).
  2. Abra o e-mail e clique em **"Clique aqui para verificar seu acesso."**.
  3. Na página que abrir, clique em **Confirmar meu e-mail**.
- **Esperado:**
  - O e-mail chega em poucos minutos (confira o spam).
  - A confirmação dá certo, e a conta fica aguardando aprovação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-04. Link de confirmação usado duas vezes

- **Objetivo:** O link vale uma vez só.
- **Passos:**
  1. Abra de novo o mesmo link do cenário A-03 e clique em **Confirmar meu e-mail**.
- **Esperado:**
  - A página diz que o link já foi usado ou não vale mais, sem erro genérico.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-05. Entrar antes da aprovação

- **Objetivo:** Conta confirmada mas não aprovada não entra.
- **Passos:**
  1. Com a conta do A-03, clique em **Entrar** e use o e-mail e a senha.
- **Esperado:**
  - A página diz: "O seu cadastro está aguardando a aprovação de um monitor-chefe, de um professor ou do desenvolvedor."
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-06. Entrar pelo e-mail e pelo nome

- **Objetivo:** O login aceita o nome ou o e-mail.
- **Passos:**
  1. Com uma conta aprovada, entre usando o e-mail.
  2. Saia e entre de novo usando o **nome** da conta.
- **Esperado:**
  - As duas formas entram na tela de verificação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-07. Senha errada

- **Objetivo:** Senha errada não entra e não diz se a conta existe.
- **Passos:**
  1. Em **Entrar**, use um e-mail da equipe com uma senha errada.
  2. Repita com um e-mail que não tem conta.
- **Esperado:**
  - As duas tentativas mostram a mesma mensagem genérica de login inválido.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-08. ⚠ Bloqueio depois de várias senhas erradas

- **Objetivo:** Depois de 5 senhas erradas seguidas na mesma conta, o login fica bloqueado por um tempo (até 15 minutos).
- **Passos:**
  1. Use uma **conta de teste**, não a sua.
  2. Erre a senha 6 vezes seguidas.
  3. Tente com a senha certa.
- **Esperado:**
  - A partir da 6ª tentativa, a página pede para esperar, inclusive com a senha certa.
  - Depois da espera, a senha certa volta a entrar.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-09. Esqueci minha senha

- **Objetivo:** A redefinição chega por e-mail, com link de 1 hora e uso único.
- **Passos:**
  1. Em **Entrar**, clique em **Esqueci minha senha** e informe o e-mail.
  2. Abra o e-mail **"Redefina a sua senha do IP-Checker"** e defina uma senha nova.
  3. Tente abrir o mesmo link de novo.
- **Esperado:**
  - O e-mail chega.
  - A senha nova funciona, e a antiga não.
  - O link não funciona uma segunda vez.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-10. Esqueci minha senha com e-mail sem conta

- **Objetivo:** A página não revela se o e-mail tem conta.
- **Passos:**
  1. Em **Esqueci minha senha**, informe um e-mail institucional que não tem conta.
- **Esperado:**
  - A página mostra a mesma confirmação do A-09, e nenhum e-mail chega.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-11. Sair

- **Objetivo:** Sair encerra a sessão e apaga o que estava na tela.
- **Passos:**
  1. Entre, cole um código no verificador e verifique.
  2. Clique no seu primeiro nome, no canto do cabeçalho, e em **Sair**.
  3. Use o botão Voltar do navegador.
- **Esperado:**
  - Depois de sair, a página volta para a entrada.
  - Voltar não mostra o código nem o resultado anteriores, e a API não responde sem login.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-12. Rota protegida sem login

- **Objetivo:** Sem login, nenhuma tela da equipe abre.
- **Passos:**
  1. Numa janela anônima, abra https://ip-checker-red-phi.vercel.app/plagio e depois https://ip-checker-red-phi.vercel.app/gerenciar.
- **Esperado:**
  - As duas levam à tela de acesso restrito ou de entrada.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-13. Aviso de privacidade sem login

- **Objetivo:** O aviso é público.
- **Passos:**
  1. Numa janela anônima, abra a página e clique em **Aviso de privacidade** no rodapé.
- **Esperado:**
  - O aviso abre sem pedir login e explica que o código não é guardado.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### A-14. Entrar pelo Google

- **Objetivo:** Só se o Google estiver habilitado no piloto.
- **Passos:**
  1. Na tela de entrada, procure o botão **Entrar com o Google**.
- **Esperado:**
  - Hoje o Google não está configurado no piloto: o botão não aparece, ou a página avisa que está indisponível. Anote o que aparecer.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 2. Perfil e sessão

### PF-01. Mudar nome, curso e tratamento

- **Objetivo:** O perfil guarda as mudanças.
- **Passos:**
  1. Abra **Perfil** (no menu do seu primeiro nome, no cabeçalho), mude o curso e o tratamento e salve.
  2. Recarregue a página.
- **Esperado:**
  - As mudanças continuam depois de recarregar.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PF-02. Tratamento muda a apresentação no feedback

- **Objetivo:** O tratamento define "sou o monitor", "sou a monitora" ou "aqui é ..., da monitoria".
- **Passos:**
  1. No **Perfil**, escolha um tratamento.
  2. Verifique o código do V-01 na Lista 1 e gere o feedback com um nome de aluno.
  3. Troque o tratamento e gere de novo.
- **Esperado:**
  - A apresentação do feedback muda conforme o tratamento.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PF-03. Nome já usado

- **Objetivo:** O nome é único.
- **Passos:**
  1. No **Perfil**, tente usar o nome de outra pessoa da equipe.
- **Esperado:**
  - A página recusa e diz que o nome já está em uso.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PF-04. Trocar a senha encerra as outras sessões

- **Objetivo:** A troca de senha mantém esta aba e encerra as outras.
- **Passos:**
  1. Entre com a mesma conta em dois navegadores (ou numa janela normal e numa anônima).
  2. Num deles, troque a senha em **Perfil** (ela pede a senha atual).
  3. No outro, tente verificar um código.
- **Esperado:**
  - Quem trocou continua dentro.
  - O outro navegador volta para a entrada.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PF-05. Senha atual errada na troca

- **Objetivo:** Sem a senha atual certa, a troca não acontece.
- **Passos:**
  1. Em **Perfil**, tente trocar a senha com a senha atual errada.
- **Esperado:**
  - A página recusa, e a senha antiga continua valendo.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 3. Gerenciar a equipe

Precisa de uma conta de **monitor-chefe**, **professor** ou do **desenvolvedor** e de uma conta de teste
(a do A-03 serve).

### G-01. Monitor não vê Gerenciar

- **Objetivo:** Só desenvolvedor, professores e monitores-chefe gerenciam.
- **Passos:**
  1. Entre com uma conta de **monitor**.
  2. Procure **Gerenciar** no menu e abra https://ip-checker-red-phi.vercel.app/gerenciar.
- **Esperado:**
  - O menu não mostra **Gerenciar**, e o endereço não abre a tela de gerenciamento.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-02. Aprovar um pedido com cargo

- **Objetivo:** O pedido pendente é aprovado com o cargo escolhido.
- **Passos:**
  1. Com uma conta que gerencia, abra **Gerenciar > Pedidos pendentes**.
  2. Aprove a conta de teste como **monitor**.
  3. Entre com a conta de teste.
- **Esperado:**
  - A conta sai dos pendentes e aparece nos membros ativos, com a etiqueta roxa de monitor.
  - A conta de teste consegue entrar.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-03. Monitor-chefe não atribui o cargo de professor

- **Objetivo:** Cada cargo só mexe nos cargos abaixo dele.
- **Passos:**
  1. Com uma conta de **monitor-chefe**, tente aprovar ou alterar uma conta para **professor**.
- **Esperado:**
  - A opção **professor** não aparece para o monitor-chefe.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-04. Recusar pede confirmação

- **Objetivo:** Recusar é irreversível pela tela e pede confirmação.
- **Passos:**
  1. Registre outra conta de teste e confirme o e-mail.
  2. Em **Pedidos pendentes**, clique em recusar e cancele.
  3. Recuse de novo e confirme.
- **Esperado:**
  - Cancelar não muda nada.
  - Confirmar recusa o pedido.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-05. Alterar o cargo encerra as sessões da conta

- **Objetivo:** Mudar o cargo encerra as sessões abertas da conta alterada.
- **Passos:**
  1. Deixe a conta de teste aberta noutro navegador.
  2. Altere o cargo dela para **monitor-chefe**.
  3. No outro navegador, faça qualquer ação.
- **Esperado:**
  - A etiqueta muda para azul-claro.
  - A conta de teste precisa entrar de novo.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-06. Remover da equipe

- **Objetivo:** Remover não apaga a conta e muda o cargo para Ex-monitor ou Conselheiro.
- **Passos:**
  1. Remova a conta de teste (a página pede confirmação).
  2. Tente entrar com ela.
- **Esperado:**
  - Quem nunca foi monitor-chefe vira **Ex-monitor**, quem já foi vira **Conselheiro**, com etiqueta cinza.
  - A conta removida não entra.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-07. Reativar

- **Objetivo:** Uma conta removida volta com um cargo.
- **Passos:**
  1. Em **Ex-monitores, conselheiros e inativos**, reative a conta de teste como monitor.
  2. Entre com ela.
- **Esperado:**
  - A conta volta aos membros ativos e entra.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-08. Ninguém age sobre a própria conta

- **Objetivo:** A tela não oferece ações sobre a conta de quem está usando.
- **Passos:**
  1. Em **Gerenciar**, procure a sua própria linha.
- **Esperado:**
  - A sua linha não tem botões de alterar cargo nem de remover.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-09. Busca sem acento e filtro de cargo

- **Objetivo:** A busca ignora acentos.
- **Passos:**
  1. Busque um nome com acento escrevendo sem acento (por exemplo, `vinicius`).
  2. Filtre por cargo.
- **Esperado:**
  - A busca encontra o nome com acento.
  - O filtro mostra só o cargo escolhido.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### G-10. Registro de ações

- **Objetivo:** Só o desenvolvedor e os professores veem quem fez o quê.
- **Passos:**
  1. Com o desenvolvedor ou um professor, abra o **Registro de ações**.
  2. Com um monitor-chefe, procure o mesmo registro.
- **Esperado:**
  - O registro mostra as ações dos cenários G-02 a G-07, com quem fez e quando, 20 por vez, com **Mostrar mais**.
  - O monitor-chefe não vê o registro.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 4. Verificador: regras de cada lista

Em todos os cenários desta seção: escolha a lista indicada, deixe a **Questão** sem escolha (a não
ser que o cenário diga outra), cole o código e clique em **Verificar** (ou Ctrl+Enter).

### V-01. Lista 1: solução válida com if/elif/else

- **Objetivo:** Uma solução típica da Lista 1 passa sem violações.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
nota = float(input())
if nota >= 7:
    print('Aprovado')
elif nota >= 3:
    print('Final')
else:
    print('Reprovado')
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 1.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-02. Lista 1: operador ternário comprova o assunto

- **Objetivo:** O ternário conta como comando condicional na exigência da Lista 1.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
a = int(input())
b = int(input())
maior = a if a > b else b
print(maior)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 1.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-03. Lista 1: laço for ainda não liberado

- **Objetivo:** `for` e `range()` só são liberados na Lista 2.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
n = int(input())
if n > 0:
    for i in range(n):
        print(i)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-34**, Fora da lista (linha 3, liberado a partir da Lista 2).
  - **R-35**, Fora da lista (linha 3, liberado a partir da Lista 2).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-04. Lista 1: sem comando condicional

- **Objetivo:** Sem `if` nem ternário, a exigência do assunto não é atendida.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
nome = input()
print('Olá,', nome)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-05. Lista 1: if só dentro de texto e comentário não conta

- **Objetivo:** Um `if` em comentário ou em texto não comprova o assunto.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
# if x > 0: isto é só um comentário
print('if x > 0')
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-06. Lista 1: import é anulação imediata

- **Objetivo:** Todo `import`, inclusive da biblioteca padrão, anula a questão.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
import math
x = float(input())
if x >= 0:
    print(math.sqrt(x))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-05**, Anulação imediata (linha 1).
  - **R-04**, Não consta no documento (linha 4).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-07. Lista 1: try/except é anulação imediata

- **Objetivo:** `try` é proibido em todas as listas.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
try:
    x = int(input())
except ValueError:
    x = 0
if x > 0:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-06**, Anulação imediata (linha 1).
  - **R-04**, Não consta no documento (linha 3).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-08. Lista 1: None é anulação imediata

- **Objetivo:** `None` é proibido em todas as listas.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
x = None
if x == 1:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-13**, Anulação imediata (linha 1).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-09. Lista 1: eval não consta no documento

- **Objetivo:** `eval` não aparece no documento de permissões (R-04).
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
x = eval(input())
if x > 0:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 1).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-10. Lista 1: atribuição múltipla antes da Lista 3

- **Objetivo:** `a, b = ...` usa tupla, liberada só na Lista 3.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
a, b = 1, 2
if a < b:
    print(a)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-40**, Fora da lista (linha 1, liberado a partir da Lista 3).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-11. Lista 1: esconder o eval atrás de um nome não funciona

- **Objetivo:** A resolução segue a ordem de execução: o `eval` da linha 1 continua sendo o built-in.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
x = eval('1')
eval = 2
if x:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 1).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-12. Lista 1: variável com nome de built-in não é o built-in

- **Objetivo:** `len = 3` é uma variável do aluno; não há chamada a `len()`.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
len = 3
if len > 2:
    print(len)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 1.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-13. Lista 1: f-string e print com end

- **Objetivo:** f-strings (R-31) e `print(..., end=...)` (R-32) são permitidos na Lista 1.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
x = int(input())
if x % 2 == 0:
    print(f'{x} é par', end='!')
else:
    print(f'{x} é ímpar')
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 1.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-14. Lista 1: várias proibições juntas

- **Objetivo:** O relatório agrupa por regra, da mais grave para a mais leve, e o resumo conta cada categoria.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
import os
x = None
try:
    print({1, 2})
except Exception:
    exit()
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
  - **R-05**, Anulação imediata (linha 1).
  - **R-13**, Anulação imediata (linha 2).
  - **R-06**, Anulação imediata (linha 3).
  - **R-07**, Anulação imediata (linha 4).
  - **R-04**, Não consta no documento (linha 5).
  - **R-08**, Anulação imediata (linha 6).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-15. Lista 2: laço for com range

- **Objetivo:** Uma solução típica da Lista 2 passa.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
n = int(input())
total = 0
for i in range(n):
    total += int(input())
print(total)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 2.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-16. Lista 2: laço while

- **Objetivo:** `while` também comprova o assunto da Lista 2.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
x = int(input())
while x > 0:
    print(x)
    x = x - 1
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 2.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-17. Lista 2: break é anulação imediata

- **Objetivo:** `break` e `continue` são proibidos em todas as listas.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
while True:
    x = int(input())
    if x == 0:
        break
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-11**, Anulação imediata (linha 4).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-18. Lista 2: zip no cabeçalho do for, com duas sequências

- **Objetivo:** O `zip()` com 2 sequências como iterável do `for` cumpre a condição da R-37.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
a = input()
b = input()
for x, y in zip(a, b):
    print(x, y)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 2.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-19. Lista 2: zip fora do for

- **Objetivo:** Fora do cabeçalho do `for`, o `zip()` não cumpre a condição da R-37.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
a = input()
b = input()
z = zip(a, b)
for par in z:
    print(par)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-37**, Não consta no documento (linha 3).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-20. Lista 2: sem laço

- **Objetivo:** Sem `for` nem `while`, a exigência da Lista 2 não é atendida.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
x = int(input())
if x > 0:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-21. Lista 2: else de laço não consta

- **Objetivo:** O `else` de um laço não aparece no documento (R-04).
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
for i in range(3):
    print(i)
else:
    print('fim')
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 4).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-22. Lista 3: lista escrita no código e append

- **Objetivo:** Lista literal e `append()` comprovam e são permitidos na Lista 3.
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
notas = []
for i in range(3):
    notas.append(float(input()))
print(max(notas))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 3.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-23. Lista 3: split como única lista (caso 6 do Marco 2)

- **Objetivo:** `split()` comprova o assunto da Lista 3 desde o ruleset 2026.2.5.
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
palavras = input().split()
for p in palavras:
    print(p.upper())
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 3.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-24. Lista 3: vários nomes no for com tuplas (caso 3)

- **Objetivo:** A partir da Lista 3, vários nomes no `for` passam com qualquer sequência de pares.
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
pares = [(1, 'a'), (2, 'b')]
for numero, letra in pares:
    print(numero, letra)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 3.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-25. Lista 3: dicionário ainda não liberado

- **Objetivo:** Dicionário só é liberado na Lista 5.
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
d = {'a': 1}
v = [1, 2]
print(d, v)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-61**, Fora da lista (linha 1, liberado a partir da Lista 5).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-26. Lista 3: expressão geradora (caso 10)

- **Objetivo:** A expressão geradora é permitida a partir da Lista 3 (R-41).
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
v = [1, 2, 3]
print(sum(x * 2 for x in v))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 3.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-27. Lista 3: def ainda não liberado

- **Objetivo:** `def` e `return` só são liberados na Lista 4.
- **Passos:**
  1. Escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
def dobro(x):
    return x * 2
v = [1, 2]
print(dobro(v[0]))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-59**, Fora da lista (linhas 1, 2, 4, liberado a partir da Lista 4).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-28. Lista 4: função com return

- **Objetivo:** Uma solução típica da Lista 4 passa.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
def area(b, h):
    return b * h / 2
print(area(float(input()), float(input())))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 4.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-29. Lista 4: parâmetro com valor padrão não consta

- **Objetivo:** Valor padrão de parâmetro aparece com a R-04.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
def soma(a, b=0):
    return a + b
print(soma(1))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 1).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-30. Lista 4: função dentro de função não consta

- **Objetivo:** Função aninhada aparece com a R-04.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
def externa(x):
    def interna(y):
        return y + 1
    return interna(x)
print(externa(1))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 2).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-31. Lista 4: argumento nomeado e if __name__ (casos 1 e 2)

- **Objetivo:** `f(x=1)` com função do aluno e `if __name__ == '__main__':` são permitidos a partir da Lista 4.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
def saudacao(nome):
    return 'Oi, ' + nome
if __name__ == '__main__':
    print(saudacao(nome=input()))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 4.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-32. Lista 4: sem def

- **Objetivo:** Sem `def`, a exigência da Lista 4 não é atendida.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
v = [1, 2, 3]
for x in v:
    print(x)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-33. Lista 4: global é anulação imediata

- **Objetivo:** A instrução `global` é proibida em todas as listas.
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
total = 0
def soma(x):
    global total
    total = total + x
    return total
print(soma(1))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-14**, Anulação imediata (linha 3).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-34. Lista 5: dicionário e items no for

- **Objetivo:** Dicionário literal e `for chave, valor in d.items()` passam na Lista 5.
- **Passos:**
  1. Escolha a **Lista 5**, cole o código e verifique.
- **Código:**

```python
estoque = {'maçã': 3, 'pera': 5}
for fruta, qtd in estoque.items():
    print(fruta, qtd)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 5.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-35. Lista 5: dict comprehension não consta

- **Objetivo:** Dict comprehension aparece com a R-04.
- **Passos:**
  1. Escolha a **Lista 5**, cole o código e verifique.
- **Código:**

```python
v = [1, 2, 3]
d = {x: x * 2 for x in v}
print(d)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-02**, Exigência não atendida (Solução inteira).
  - **R-04**, Não consta no documento (linha 2).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-36. Lista 5: sorted com key= não consta

- **Objetivo:** O `lambda` é permitido, mas `key=` não aparece no documento.
- **Passos:**
  1. Escolha a **Lista 5**, cole o código e verifique.
- **Código:**

```python
d = {'a': 2, 'b': 1}
print(sorted(d.items(), key=lambda par: par[1]))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-04**, Não consta no documento (linha 2).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-37. Lista 5: enumerate com start e dict(a=1) (caso 7)

- **Objetivo:** `dict(a=1)` e `enumerate(v, start=1)` são permitidos desde a Lista 5.
- **Passos:**
  1. Escolha a **Lista 5**, cole o código e verifique.
- **Código:**

```python
d = dict(a=1)
for i, c in enumerate(['x', 'y'], start=1):
    d[c] = i
print(d)
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 5.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-38. Lista 5: set é anulação imediata

- **Objetivo:** `set()` é proibido em todas as listas.
- **Passos:**
  1. Escolha a **Lista 5**, cole o código e verifique.
- **Código:**

```python
d = {'a': 1}
chaves = set(d.keys())
print(chaves)
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-07**, Anulação imediata (linha 2).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-39. Lista 6: recursão direta

- **Objetivo:** Uma função que chama a si mesma comprova o assunto da Lista 6.
- **Passos:**
  1. Escolha a **Lista 6**, cole o código e verifique.
- **Código:**

```python
def fatorial(n):
    if n <= 1:
        return 1
    return n * fatorial(n - 1)
print(fatorial(int(input())))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 6.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-40. Lista 6: recursão mútua

- **Objetivo:** `par` chama `impar`, que chama `par`: recursão indireta também conta.
- **Passos:**
  1. Escolha a **Lista 6**, cole o código e verifique.
- **Código:**

```python
def par(n):
    if n == 0:
        return True
    return impar(n - 1)
def impar(n):
    if n == 0:
        return False
    return par(n - 1)
print(par(int(input())))
```

- **Esperado:**
  - Nenhuma violação: a página diz que a solução respeita as permissões da Lista 6.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-41. Lista 6: lambda que chama a si mesmo não conta (caso 9)

- **Objetivo:** Um `lambda` recursivo não comprova o assunto da Lista 6.
- **Passos:**
  1. Escolha a **Lista 6**, cole o código e verifique.
- **Código:**

```python
f = lambda n: f(n - 1) if n else 0
print(f(3))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-68**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-42. Lista 6: chamar a função várias vezes não é recursão

- **Objetivo:** Chamar a função fora dela não forma recursão.
- **Passos:**
  1. Escolha a **Lista 6**, cole o código e verifique.
- **Código:**

```python
def dobro(n):
    return n * 2
print(dobro(dobro(3)))
```

- **Esperado:**
  - O resultado mostra, uma linha por regra:
  - **R-68**, Exigência não atendida (Solução inteira).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-46. Lista 4: recursão é fora da lista (Q-33, S36-09)

- **Objetivo:** A recursão só é permitida a partir da Lista 6; nas Listas 4 e 5, ela é "Fora da lista".
- **Passos:**
  1. Escolha a **Lista 4**, cole o código e verifique.
  2. Troque para a **Lista 6** e verifique de novo.
- **Código:**

```python
def fatorial(n):
    if n <= 1:
        return 1
    return n * fatorial(n - 1)
print(fatorial(5))
```

- **Esperado:**
  - Na Lista 4, aparece a **R-68** como "Fora da lista" na linha 1, dizendo que a recursão só é permitida a partir da Lista 6.
  - Na Lista 6, nenhuma violação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-43. Erro de sintaxe: parêntese não fechado

- **Objetivo:** Com erro de sintaxe, as permissões não são verificadas, e a página mostra o erro em português.
- **Passos:**
  1. Escolha a **Lista 1**, cole o código e verifique.
- **Código:**

```python
x = int(input()
if x > 0:
    print(x)
```

- **Esperado:**
  - No lugar das violações, aparece o erro de sintaxe na **linha 1, coluna 8**: "o '(' foi aberto e nunca fechado".
  - O painel de feedback não oferece gerar texto para esse código.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-44. Erro de sintaxe: indentação

- **Objetivo:** Erro de indentação aparece com linha e coluna.
- **Passos:**
  1. Escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
for i in range(3):
print(i)
```

- **Esperado:**
  - No lugar das violações, aparece o erro de sintaxe na **linha 2, coluna 1**: "faltou um bloco indentado depois do 'for' da linha 1".
  - O painel de feedback não oferece gerar texto para esse código.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### V-45. Verificando e Cancelar (S36-05)

- **Objetivo:** A verificação mostra que está em andamento e pode ser cancelada.
- **Passos:**
  1. Escolha a **Lista 1**, cole um código de umas 30 KB (peça ao desenvolvedor a entrada do benchmark) e clique em **Verificar**.
  2. Enquanto o botão diz **Verificando…**, clique em **Cancelar**.
- **Esperado:**
  - O botão muda para **Verificando…** e aparece **Cancelar**.
  - Depois de Cancelar, o código continua no editor, e o botão volta a **Verificar**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 5. Verificador: questões cadastradas

Hoje há três questões com regras cadastradas: a **L3-Q9** (questão do ensaio: libera `map()` e
proíbe `sum()`, `sort()` e `sorted()`), a **L4-Q4** (libera `eval()` para ler listas e o
`reverse=` no `sort()`) e a **L4-Q5** (libera o valor padrão de parâmetro). As
questões que só têm gabarito aparecem no seletor como "L4-Q1 · só gabarito"; as que têm regra e
gabarito, como "L4-Q4 · gabarito" (S36-05). O título da questão e o que vale aparecem na frase logo
abaixo dos seletores.

### Q-01. L3-Q9 (ensaio): map liberado pela questão

- **Objetivo:** A questão libera `map()`, que sem ela não consta no documento.
- **Passos:**
  1. Escolha a **Lista 3** e, em **Questão**, a **L3-Q9**. Cole o código e verifique.
- **Código:**

```python
notas = list(map(float, input().split()))
total = 0
for n in notas:
    total += n
print(total / len(notas))
```

- **Esperado:**
  - Nenhuma violação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### Q-02. L3-Q9 sem escolher a questão

- **Objetivo:** Sem a questão no seletor, `map()` aparece com a R-04.
- **Passos:**
  1. Escolha a **Lista 3**, deixe a **Questão** sem escolha, cole o código e verifique.
- **Código:**

```python
notas = list(map(float, input().split()))
total = 0
for n in notas:
    total += n
print(total / len(notas))
```

- **Esperado:**
  - O resultado mostra:
  - **R-04**, Não consta no documento (linha 1).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### Q-03. L3-Q9: sum() e sorted() proibidos pela questão

- **Objetivo:** A questão proíbe `sum()` e `sorted()`, que a Lista 3 permite.
- **Passos:**
  1. Escolha a **Lista 3** e, em **Questão**, a **L3-Q9**. Cole o código e verifique.
- **Código:**

```python
notas = list(map(float, input().split()))
print(sum(notas) / len(notas))
print(sorted(notas))
```

- **Esperado:**
  - O resultado mostra:
  - **R-01**, Proibido nesta questão (linhas 2, 3).
  - As duas linhas aparecem como **Proibido nesta questão**: `sum()` na linha 2 e `sorted()` na linha 3.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### Q-04. L4-Q4: eval liberado pelo enunciado

- **Objetivo:** Na L4-Q4, `eval()` é permitido; nas outras questões da Lista 4, não.
- **Passos:**
  1. Escolha a **Lista 4** e, em **Questão**, a **L4-Q4**. Cole o código e verifique.
- **Código:**

```python
def total(apostas):
    soma = 0
    for a in apostas:
        soma += a
    return soma
print(total(eval(input())))
```

- **Esperado:**
  - Nenhuma violação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### Q-05. Lista 4 sem a questão L4-Q4

- **Objetivo:** Sem a questão, o mesmo código tem `eval()` com a R-04.
- **Passos:**
  1. Escolha a **Lista 4**, deixe a **Questão** sem escolha, cole o código e verifique.
- **Código:**

```python
def total(apostas):
    soma = 0
    for a in apostas:
        soma += a
    return soma
print(total(eval(input())))
```

- **Esperado:**
  - O resultado mostra:
  - **R-04**, Não consta no documento (linha 6).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### Q-06. O seletor de questões

- **Objetivo:** O seletor lista as questões com regras e as que só têm gabarito.
- **Passos:**
  1. Escolha a **Lista 4** e abra o seletor **Questão**.
  2. Escolha a **Lista 5** e abra o seletor de novo.
- **Esperado:**
  - Na Lista 4 aparecem a L4-Q4 e a L4-Q5, com regras ("L4-Q4 · gabarito"), e as que só têm gabarito ("L4-Q1 · só gabarito"). Nenhuma opção aparece cortada, no computador e no celular.
  - Escolhida a L4-Q4, a frase abaixo dos seletores traz o título da questão e diz que valem as regras dela e que o código também é comparado com o gabarito.
  - Na Lista 5, que ainda não tem questão nem gabarito, o seletor diz "Nenhuma questão nesta lista".
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 6. Verificador: interface

### VI-01. Clicar numa linha do relatório

- **Objetivo:** Clicar numa violação seleciona o trecho no editor.
- **Passos:**
  1. Verifique o código do V-14 na Lista 1.
  2. Clique na linha da R-13 (`None`).
- **Esperado:**
  - O trecho `None` da linha 2 fica selecionado no editor, e a linha é marcada na numeração.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-01b. Resumo por categoria e cartões (Sprint 37)

- **Objetivo:** Os contadores filtram, e os cartões abrem e fecham.
- **Passos:**
  1. Verifique o código do V-14 na Lista 1.
  2. Clique no contador **anulações imediatas** e depois em **Todas**.
  3. Clique no cabeçalho de um cartão; depois em **Abrir todos** ou **Fechar todos**, se aparecer.
- **Esperado:**
  - O contador mostra só os cartões daquela categoria; **Todas** volta a mostrar todos.
  - Até 5 regras, os cartões vêm abertos; acima disso, fechados. Aberto, o cartão mostra as linhas e o trecho com a linha da violação em destaque e uma linha de contexto de cada lado.
  - No computador, o editor fica parado na tela enquanto o resultado rola.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-01c. Por quê e o que usar; carregar e exportar (Sprint 38)

- **Objetivo:** Cada regra explica a violação; o código vem de um arquivo e o resultado sai em texto.
- **Passos:**
  1. Salve o código do V-14 num arquivo `teste.py` e use **Carregar .py** (ou arraste o arquivo para o editor).
  2. Verifique na Lista 1 e abra um cartão.
  3. Clique em **Copiar o relatório** e cole num bloco de notas; depois, **Baixar .txt**.
  4. Tente carregar um arquivo que não é `.py` ou maior que 50 KB.
- **Esperado:**
  - O editor recebe o código, com o aviso "teste.py carregado no editor".
  - Cada cartão mostra **Por quê** e **O que usar**, coerentes com o documento de permissões.
  - O relatório tem a lista, a questão, as regras, as linhas, o porquê e o que usar, e não tem o código.
  - O arquivo errado é recusado com o motivo, e o editor não muda.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-02. Relatório de um código que mudou

- **Objetivo:** Depois de mudar o código, o relatório avisa que é do código anterior.
- **Passos:**
  1. Verifique o V-03 na Lista 1.
  2. Apague o `for` no editor, sem verificar de novo.
- **Esperado:**
  - O relatório continua, com o aviso de que é do código anterior.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-03. Tab, Esc e Ctrl+Enter no editor

- **Objetivo:** O editor é usável pelo teclado.
- **Passos:**
  1. No editor, aperte Tab.
  2. Escreva três linhas, selecione as três e aperte Tab; depois, Shift+Tab (S36-03).
  3. Aperte Esc e depois Tab.
  4. Volte ao editor e aperte Ctrl+Enter.
- **Esperado:**
  - Tab insere 4 espaços.
  - Com as três linhas selecionadas, Tab indenta as três e Shift+Tab desfaz.
  - Esc e Tab tiram o foco do editor.
  - Ctrl+Enter verifica e leva o foco ao resultado.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-04. A página lembra a última lista

- **Objetivo:** A lista escolhida fica guardada neste navegador.
- **Passos:**
  1. Escolha a **Lista 3** e recarregue a página.
- **Esperado:**
  - A Lista 3 continua escolhida.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-05. Mais de 200 violações

- **Objetivo:** Com mais de 200 violações, a página mostra as 200 primeiras e avisa.
- **Passos:**
  1. Na Lista 1, cole 250 linhas `x = None` (dica: no Python, `print('x = None\n' * 250)` gera o texto) e verifique.
- **Esperado:**
  - Aparece "Mostrando as 200 primeiras violações. Corrija estas e verifique de novo."
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-06. Código acima de 1.000 linhas

- **Objetivo:** O limite é de 1.000 linhas e 50 KB.
- **Passos:**
  1. Cole 1.001 linhas `print(1)` (dica: `print('print(1)\n' * 1001)`) e verifique.
- **Esperado:**
  - A página recusa e informa o limite, sem erro genérico.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-07. Editor vazio

- **Objetivo:** Verificar sem código não chama o servidor.
- **Passos:**
  1. Limpe o editor e clique em **Verificar**.
- **Esperado:**
  - A página pede um código, ou o botão fica desabilitado.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### VI-08. Botão Colar

- **Objetivo:** O botão **Colar** cola a área de transferência no editor.
- **Passos:**
  1. Copie o código do V-01 e clique em **Colar**.
- **Esperado:**
  - O código aparece no editor (o navegador pode pedir permissão para ler a área de transferência).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 7. Comparação com o gabarito

O piloto carregou **28 gabaritos** de 2026.2 (L1-Q1 a L1-Q8, L2-Q1 a L2-Q7, L3-Q1 a L3-Q8 e L4-Q1 a
L4-Q5) no deploy de 11/10/2026. Para estes cenários, quem testa precisa ter o gabarito oficial em
mãos. **Não copie o gabarito para o relato**; descreva o que fez.

### GB-01. O próprio gabarito

- **Objetivo:** O gabarito comparado com ele mesmo dá 100%.
- **Passos:**
  1. Escolha a **Lista 2** e a **L2-Q1** no seletor.
  2. Cole o gabarito oficial da L2-Q1 e verifique.
- **Esperado:**
  - Nenhuma violação (o gabarito respeita as regras da lista).
  - Aparece o bloco **Comparação com o gabarito** com 100% e a faixa **Plágio**.
  - O texto do gabarito **não** aparece em lugar nenhum da página.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-02. Gabarito com nomes trocados

- **Objetivo:** Trocar nomes de variáveis não reduz a semelhança.
- **Passos:**
  1. Repita o GB-01 trocando todos os nomes de variáveis do gabarito.
- **Esperado:**
  - A semelhança continua em 99% ou mais.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-03. Solução própria, diferente do gabarito

- **Objetivo:** Uma solução correta e diferente fica numa faixa mais baixa.
- **Passos:**
  1. Escreva a sua solução para a mesma questão, sem olhar o gabarito, e verifique com a questão escolhida.
- **Esperado:**
  - A semelhança cai, e o bloco mostra as construções **em comum**, as que estão **só no código do aluno** e as que estão **só no gabarito**.
  - A página avisa que soluções corretas podem ser diferentes do gabarito.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-04. Trechos do aluno que coincidem

- **Objetivo:** Clicar num trecho seleciona as linhas do aluno.
- **Passos:**
  1. Copie só metade do gabarito e escreva o resto você mesmo.
  2. Clique num dos trechos listados.
- **Esperado:**
  - O trecho correspondente fica selecionado no editor; só as linhas do aluno aparecem, nunca as do gabarito.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-05. Questão sem gabarito

- **Objetivo:** Sem gabarito, não há bloco de comparação.
- **Passos:**
  1. Na **Lista 3**, escolha a **L3-Q9** (questão do ensaio, sem gabarito) e verifique o código do Q-01.
- **Esperado:**
  - Nenhum bloco **Comparação com o gabarito** aparece.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-06. Sem questão escolhida

- **Objetivo:** Sem questão, não há comparação.
- **Passos:**
  1. Verifique o gabarito da L2-Q1 na Lista 2 **sem** escolher a questão.
- **Esperado:**
  - O resultado vem sem o bloco de comparação, com o aviso de que só valem as permissões da lista.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-07. Questão cadastrada com gabarito (L4-Q4)

- **Objetivo:** Na L4-Q4, valem as regras da questão e a comparação com o gabarito.
- **Passos:**
  1. Escolha a **Lista 4** e a **L4-Q4**. Cole o gabarito oficial da L4-Q4 e verifique.
- **Esperado:**
  - Nenhuma violação: o `eval()` do gabarito é liberado pela questão.
  - A comparação dá 100%.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### GB-08. Gabarito com erro de sintaxe proposital

- **Objetivo:** Com erro de sintaxe, não há comparação.
- **Passos:**
  1. Cole o gabarito da L1-Q1 apagando um `:` e verifique com a questão escolhida.
- **Esperado:**
  - Aparece o erro de sintaxe, sem comparação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 8. Plágio: dois códigos

Em **Plágio > Dois códigos**, cole o código A e o código B e clique em **Verificar**. Os valores
esperados foram calculados pelo motor; diferenças de até 0,1 ponto vêm do arredondamento.

### P-01. Códigos idênticos

- **Objetivo:** Dois códigos iguais dão 100%.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-02. Nomes de variáveis trocados

- **Objetivo:** Trocar os nomes não esconde a cópia.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
quantidade = int(input())
soma = 0
maximo = 0
for k in range(quantidade):
    valor = int(input())
    if valor % 2 == 0:
        soma += valor
    if valor > maximo:
        maximo = valor
print('Soma dos pares:', soma)
print('Maior:', maximo)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-03. Comentários e linhas em branco acrescentados

- **Objetivo:** Comentários e linhas em branco não mudam a estrutura.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
# Lê n números
n = int(input())  # quantidade

total = 0
maior = 0

for i in range(n):
    x = int(input())
    # soma só os pares
    if x % 2 == 0:
        total += x

    if x > maior:
        maior = x

print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-04. Formas equivalentes: += e comparação invertida

- **Objetivo:** `total += x` e `total = total + x`, `x > maior` e `maior < x` são a mesma coisa para o motor.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total = total + x
    if maior < x:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-05. if com a condição negada e os ramos trocados

- **Objetivo:** Negar a condição e trocar os ramos não disfarça a cópia.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
a = int(input())
b = int(input())
if a >= b:
    print('Primeiro maior ou igual:', a)
    print('Diferença:', a - b)
else:
    print('Segundo maior:', b)
    print('Diferença:', b - a)
```

- **Código B:**

```python
a = int(input())
b = int(input())
if not a >= b:
    print('Segundo maior:', b)
    print('Diferença:', b - a)
else:
    print('Primeiro maior ou igual:', a)
    print('Diferença:', a - b)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-06. for reescrito como while com índice

- **Objetivo:** O `for` com `range` e o `while` com índice equivalente são reconhecidos.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
soma = 0
for i in range(n):
    v = int(input())
    soma += v * v
    print(i, soma)
print('Fim:', soma)
```

- **Código B:**

```python
n = int(input())
soma = 0
i = 0
while i < n:
    v = int(input())
    soma += v * v
    print(i, soma)
    i += 1
print('Fim:', soma)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
  - A página avisa que um dos códigos é curto (menos de 60 tokens), e que a semelhança pode ser coincidência.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-07. Funções em outra ordem

- **Objetivo:** Reordenar funções não muda o resultado.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
def dobro(x):
    return x * 2
def triplo(x):
    return x * 3
def media(a, b):
    return (a + b) / 2
n = int(input())
m = int(input())
print(dobro(n), triplo(m), media(n, m))
```

- **Código B:**

```python
def media(p, q):
    return (p + q) / 2
def triplo(y):
    return y * 3
def dobro(y):
    return y * 2
n = int(input())
m = int(input())
print(dobro(n), triplo(m), media(n, m))
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-08. Cópia com linhas acrescentadas no início e no fim

- **Objetivo:** Código acrescentado fora do trecho copiado não esconde a cópia: a contenção fica em 100%.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
nome = input()
print('Aluno:', nome)
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
print('Quantidade lida:', n)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio**.
  - A **Contenção** fica em 100%: o código A está inteiro dentro do B.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-09. Soluções independentes do mesmo problema

- **Objetivo:** Duas abordagens diferentes ficam em faixas baixas.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
numeros = []
for _ in range(int(input())):
    numeros.append(int(input()))
pares = [v for v in numeros if v % 2 == 0]
print('Soma dos pares:', sum(pares))
print('Maior:', max(numeros) if numeros else 0)
```

- **Esperado:**
  - Similaridade **14,7%**, faixa **Sem suspeitas**.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-10. Códigos curtos se parecem por acaso

- **Objetivo:** Em códigos curtos, a página avisa que a semelhança pode ser coincidência.
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
x = int(input())
print(x * 2)
```

- **Código B:**

```python
y = int(input())
print(y * 3)
```

- **Esperado:**
  - Similaridade **64,0%**, faixa **Sem suspeitas**.
  - A página avisa que um dos códigos é curto (menos de 60 tokens), e que a semelhança pode ser coincidência.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-11. Uma linha inserida dentro do laço copiado

- **Objetivo:** Inserir uma linha dentro de um bloco copiado não esconde a cópia (corrigido na Sprint 35, S35-07; antes, 83,2%).
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    print('Lido:', x)
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio** (a partir da release da Sprint 35).
  - A **Contenção** fica em 100%: o código A está inteiro dentro do B.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### P-12. Um else com contador acrescentado dentro do laço

- **Objetivo:** Acrescentar um `else` com um contador dentro do laço copiado não esconde a cópia (corrigido na Sprint 35, S35-07; antes, 76,1%).
- **Passos:** cole os dois códigos e clique em **Verificar**.
- **Código A:**

```python
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Código B:**

```python
n = int(input())
total = 0
maior = 0
impares = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    else:
        impares += 1
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
print('Ímpares:', impares)
```

- **Esperado:**
  - Similaridade **100,0%**, faixa **Plágio** (a partir da release da Sprint 35).
  - A **Contenção** fica em 100%: o código A está inteiro dentro do B.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 9. Plágio: interface e gabarito

### PI-01. Trechos em comum

- **Objetivo:** Clicar num par de trechos realça os dois códigos.
- **Passos:**
  1. Use o P-07.
  2. Clique num par em **Trechos em comum**.
- **Esperado:**
  - As linhas do par ficam realçadas nos dois códigos, e os dois rolam até elas.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-02. Rolar os dois códigos juntos

- **Objetivo:** Com a opção marcada, rolar um rola o outro.
- **Passos:**
  1. Use o P-03, marque **Rolar os dois códigos juntos** e role o código A.
- **Esperado:**
  - O código B rola junto.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-03. Trocar A e B, e Limpar os dois

- **Objetivo:** Os botões invertem e esvaziam os códigos.
- **Passos:**
  1. Use o P-08 e clique em **Trocar A e B**.
  2. Clique em **Limpar os dois**.
- **Esperado:**
  - Os códigos trocam de lado, e a similaridade continua a mesma.
  - Os dois campos ficam vazios.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-04. Erro de sintaxe num dos códigos

- **Objetivo:** A página diz qual código tem erro e onde.
- **Passos:**
  1. Cole o V-43 no código B e qualquer código válido no A.
- **Esperado:**
  - A página diz que o **código B** tem erro de sintaxe, com a linha.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-05. A e B contra o gabarito

- **Objetivo:** Com uma questão escolhida, o resultado mostra A×gabarito e B×gabarito.
- **Passos:**
  1. Escolha em **Questão (para comparar também com o gabarito)** a L2-Q1.
  2. Cole no A o gabarito da L2-Q1 e no B uma solução sua.
- **Esperado:**
  - Aparecem a similaridade A×B, A×gabarito (perto de 100%) e B×gabarito.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-06. Possível vazamento do gabarito

- **Objetivo:** Dois códigos parecidos entre si e com o gabarito, acima de 95%, disparam o alerta.
- **Passos:**
  1. Com a L2-Q1 escolhida, cole o gabarito no A e o gabarito com os nomes trocados no B.
- **Esperado:**
  - Aparece o alerta **"Possível vazamento do gabarito: os dois códigos coincidem entre si e com o gabarito oficial."**
  - Se o gabarito for curto, o alerta pode não aparecer: ele exige códigos com pelo menos 60 tokens.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### PI-07. Sem vazamento com uma cópia de colega

- **Objetivo:** Dois alunos iguais entre si, mas diferentes do gabarito, não disparam o alerta de vazamento.
- **Passos:**
  1. Com a L2-Q1 escolhida, cole a sua solução no A e a mesma solução com nomes trocados no B.
- **Esperado:**
  - A×B fica em **Plágio**, mas não aparece o alerta de vazamento.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 10. Plágio: contra a turma

### T-01. Ranking da turma

- **Objetivo:** A solução conferida é comparada com cada solução da turma, da mais parecida para a menos.
- **Passos:**
  1. Em **Plágio > Contra a turma**, cole no primeiro campo o código A do P-01.
  2. No campo da turma, cole o texto abaixo e clique em **Verificar**.
- **Turma:**

```python
=== Ana
quantidade = int(input())
soma = 0
maximo = 0
for k in range(quantidade):
    valor = int(input())
    if valor % 2 == 0:
        soma += valor
    if valor > maximo:
        maximo = valor
print('Soma dos pares:', soma)
print('Maior:', maximo)
=== Bruno
numeros = []
for _ in range(int(input())):
    numeros.append(int(input()))
pares = [v for v in numeros if v % 2 == 0]
print('Soma dos pares:', sum(pares))
print('Maior:', max(numeros) if numeros else 0)
=== Caio
n = int(input())
total = 0
maior = 0
for i in range(n):
    x = int(input())
    if x % 2 == 0:
        total += x
    if x > maior:
        maior = x
print('Soma dos pares:', total)
print('Maior:', maior)
```

- **Esperado:**
  - A lista vem em ordem: **Ana** e **Caio** no topo, com 100% (cópias), e **Bruno** por último, com cerca de 7% (solução independente).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-02. Comparar lado a lado

- **Objetivo:** O botão abre o par em **Dois códigos**, com os trechos.
- **Passos:**
  1. No resultado do T-01, clique em **Comparar lado a lado com Ana**.
- **Esperado:**
  - Abre **Dois códigos** com as duas soluções e os trechos em comum.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-03. Separador sem nome

- **Objetivo:** Cada solução começa por uma linha `=== nome`; sem nome, ela vira "Solução N".
- **Passos:**
  1. No campo da turma, cole duas soluções separadas por uma linha `===` sem nome.
- **Esperado:**
  - As duas aparecem como "Solução 1" e "Solução 2", sem erro genérico.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-04. Peso pela raridade

- **Objetivo:** O que toda a turma escreve quase não conta.
- **Passos:**
  1. Monte uma turma em que todos leem a entrada e fazem o mesmo laço óbvio, mas só um copia um trecho incomum da solução conferida.
- **Esperado:**
  - Quem copiou o trecho incomum aparece no topo, acima de quem só tem o trecho comum.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-05. Solução da turma com erro de sintaxe

- **Objetivo:** Uma solução inválida não derruba a comparação das outras.
- **Passos:**
  1. Na turma do T-01, apague um `:` na solução do Bruno e verifique.
- **Esperado:**
  - A página indica o problema na solução do Bruno, sem erro genérico, e compara as outras (anote o comportamento).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-06. Texto com fim de linha antigo (correção de 11/10/2026)

- **Objetivo:** Um código com caracteres especiais e linhas terminadas só em `\r` não derruba o plágio da turma.
- **Passos:**
  1. Peça ao desenvolvedor o arquivo de teste com `\r` (ele vem dos testes automáticos) e cole-o como uma das soluções da turma.
- **Esperado:**
  - A comparação termina normalmente, sem "erro inesperado".
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-07. Alunos com o mesmo nome (S36-01)

- **Objetivo:** Dois alunos com o mesmo nome não se confundem.
- **Passos:**
  1. Na turma do T-01, troque `=== Caio` por `=== Ana` e verifique.
  2. Clique em **Comparar lado a lado** na linha **Ana (2)** e depois na linha **Ana**.
- **Esperado:**
  - A página avisa que o nome Ana aparece mais de uma vez, e a segunda vira **Ana (2)**.
  - Cada botão abre o código da própria solução.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### T-08. Comentário com ### dentro do código (S36-02)

- **Objetivo:** Um comentário `### ...` dentro de uma solução não a parte em duas.
- **Passos:**
  1. Na turma do T-01, acrescente a linha `### calcula a soma` dentro da solução da Ana e verifique.
  2. Repita com a turma toda no formato antigo, trocando cada `===` por `###`.
- **Esperado:**
  - Com `===`, continuam 3 soluções, sem aviso.
  - No formato antigo, a página avisa para usar `=== nome`, porque o comentário partiu a solução.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 11. Feedback para o aluno

### F-01. Feedback sem violações

- **Objetivo:** Sem violações, a frase obrigatória é a de questão ótima.
- **Passos:**
  1. Verifique o V-01 na Lista 1.
  2. Digite o nome `Maria` e clique em **Gerar feedback**.
- **Esperado:**
  - O texto começa com a saudação a Maria, a sua apresentação e "Sua questão está ótima, não houve nenhuma violação de regras."
  - A página diz "Montado sem IA, a partir do resultado do IP-Checker."
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-02. Feedback com violações

- **Objetivo:** Com violações, a frase obrigatória lista o que foi encontrado e diz que a questão foi anulada.
- **Passos:**
  1. Verifique o V-06 na Lista 1 e gere o feedback para `João`.
- **Esperado:**
  - O texto traz "Sua questão apresenta problemas, como o uso de ..., portanto ela foi anulada.", citando o `import`.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-03. Anotação importante

- **Objetivo:** A anotação entra no texto.
- **Passos:**
  1. Repita o F-02 com a anotação `Lembre de ler a entrada uma vez só.`
- **Esperado:**
  - O texto aproveita a anotação.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-04. Aprimorar com IA

- **Objetivo:** A IA reescreve a continuação; a página diz qual IA respondeu.
- **Passos:**
  1. Depois do F-02, clique em **Aprimorar com IA**.
- **Esperado:**
  - Em alguns segundos, o texto muda e a página mostra "Aprimorado por IA (gemini)" (ou outra IA da cadeia).
  - A abertura e a frase obrigatória continuam as mesmas.
  - O nome do aluno aparece certo no texto final.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-05. Desfazer

- **Objetivo:** **Desfazer** volta ao texto sem IA.
- **Passos:**
  1. Depois do F-04, clique em **Desfazer**.
- **Esperado:**
  - O texto volta a ser o montado sem IA.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-06. Texto editável e Copiar

- **Objetivo:** O texto pode ser editado antes de copiar.
- **Passos:**
  1. Edite uma frase do feedback e clique em **Copiar**.
  2. Cole num bloco de notas.
- **Esperado:**
  - O texto colado tem a sua edição.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-07. Sem feedback com erro de sintaxe

- **Objetivo:** Com erro de sintaxe, não há feedback.
- **Passos:**
  1. Verifique o V-43 e procure **Gerar feedback**.
- **Esperado:**
  - O painel não oferece gerar o feedback; pede para corrigir o código.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-08. Aviso de nome do aluno anterior

- **Objetivo:** Verificar outro código sem trocar o nome gera um aviso.
- **Passos:**
  1. Gere o feedback do F-01 para `Maria`.
  2. Cole e verifique o V-03 sem mudar o nome.
- **Esperado:**
  - O painel avisa, antes de gerar, que o nome pode ser do aluno anterior.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-09. Feedback é do código verificado

- **Objetivo:** Mudar o editor depois de verificar não muda o feedback.
- **Passos:**
  1. Verifique o V-01, mude o código no editor e gere o feedback.
- **Esperado:**
  - O feedback fala do código verificado, não do que está no editor agora.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### F-10. Dados pessoais no código

- **Objetivo:** E-mails e matrículas no código não vão para a IA.
- **Passos:**
  1. Na Lista 1, verifique o código abaixo e use **Aprimorar com IA**.
- **Código:**

```python
# aluno: fulano@cin.ufpe.br, matrícula 2026123456
x = int(input())
if x > 0:
    print(x)
```

- **Esperado:**
  - O texto final não repete o e-mail nem o número do código (eles viram marcas antes do envio).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 12. Correção em lote

### L-01. Fluxo pelo teclado

- **Objetivo:** Ctrl+Enter, nome e Enter, Copiar e Próximo aluno.
- **Passos:**
  1. Cole o V-01 e aperte Ctrl+Enter.
  2. Digite o nome do aluno e aperte Enter.
  3. Clique em **Copiar** e em **Próximo aluno**.
- **Esperado:**
  - Ctrl+Enter verifica e leva o foco ao resultado.
  - Enter no nome gera o feedback e leva o foco a **Copiar**.
  - **Próximo aluno** limpa o código, o nome, a anotação e o resultado, mantém a lista e a questão e volta ao editor.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### L-01b. Atalhos Alt+N e Ctrl+Shift+C (Sprint 37)

- **Objetivo:** Os atalhos copiam o feedback e passam ao próximo aluno.
- **Passos:**
  1. Cole o V-01, aperte Ctrl+Enter, digite o nome e aperte Enter.
  2. Aperte **Ctrl+Shift+C** e cole o texto num bloco de notas.
  3. Aperte **Alt+N**.
  4. Abra **Atalhos do teclado**, abaixo dos botões.
- **Esperado:**
  - Ctrl+Shift+C copia o feedback gerado (dentro de um campo de texto, o atalho fica com o campo).
  - Alt+N faz o mesmo que **Próximo aluno**.
  - A ajuda lista Ctrl+Enter, Tab e Shift+Tab, Esc e Tab, Alt+N e Ctrl+Shift+C.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### L-02. Rascunho guardado na navegação e no recarregamento

- **Objetivo:** O editor e o painel continuam ao trocar de tela e ao recarregar a página.
- **Passos:**
  1. Cole um código e gere um feedback.
  2. Vá a **Plágio** e volte.
  3. Aperte F5.
- **Esperado:**
  - Depois do passo 2, o código, o resultado e o feedback continuam lá.
  - Depois do F5, o código, a questão, o nome e a anotação continuam (o resultado precisa de uma nova verificação).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### L-03. Sair apaga o rascunho

- **Objetivo:** **Sair** apaga o que estava no editor e no painel.
- **Passos:**
  1. Com um código e um feedback na tela, clique em **Sair** (no menu do seu primeiro nome) e entre de novo.
- **Esperado:**
  - O editor e o painel estão vazios.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### L-04. Dez alunos seguidos

- **Objetivo:** O fluxo aguenta uma sequência real de correção.
- **Passos:**
  1. Corrija 10 códigos seguidos deste roteiro (V-01 a V-10), com nomes diferentes, sem recarregar a página.
- **Esperado:**
  - Nenhum feedback sai com o nome errado, e nenhum erro aparece.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 13. Indícios de uso de IA

**No piloto, os indícios estão desligados** até a calibração com soluções de alunos (P-21). Por
isso o painel **não aparece** no piloto. Os cenários I-01 a I-04 valem para o ambiente local do
desenvolvedor (`docker compose`), em que os indícios ficam ligados, ou para o piloto depois que
forem ligados.

### I-00. Painel desligado no piloto

- **Objetivo:** Confirma que o piloto não mostra indícios.
- **Passos:**
  1. No piloto, verifique o código do I-01 na Lista 2.
- **Esperado:**
  - Aparecem só as violações (R-11 e R-12); o painel **Indícios de uso de IA** não aparece.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### I-01. Múltiplas proibições gerais (break, continue e pass)

- **Objetivo:** Proibições gerais diferentes no mesmo código formam um indício.
- **Passos:**
  1. No ambiente com indícios ligados, escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
for i in range(10):
    if i == 2:
        continue
    if i == 5:
        break
    if i == 7:
        pass
    print(i)
```

- **Esperado:**
  - O painel **Indícios de uso de IA** aparece, na **Faixa alta**.
  - 3 proibições gerais diferentes no mesmo código: 'continue', 'break' e 'pass'. Cada uma anula a questão, e juntas são raras numa solução escrita para a lista. (Faixa alta; linhas 3, 5, 7).
  - No fim, aparecem as perguntas para a conversa com o aluno, e nada do painel entra no feedback.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### I-02. Salto de lista: dicionário numa solução da Lista 3

- **Objetivo:** Construções de listas bem posteriores entram como indício.
- **Passos:**
  1. No ambiente com indícios ligados, escolha a **Lista 3**, cole o código e verifique.
- **Código:**

```python
notas = [7.0, 8.5]
contagem = {}
for n in notas:
    contagem[n] = contagem.get(n, 0) + 1
print(contagem)
```

- **Esperado:**
  - O painel **Indícios de uso de IA** aparece, na **Faixa alta**.
  - Construções de listas bem posteriores numa solução da Lista 3: 'dicionário' (Lista 5) e '.get()' (Lista 5); o maior salto é de 2 listas. (Faixa alta; linhas 2, 4).
  - No fim, aparecem as perguntas para a conversa com o aluno, e nada do painel entra no feedback.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### I-03. Marcadores de estilo: docstring, tipos e nomes em inglês

- **Objetivo:** Docstring, anotações de tipo, `__main__` e nomes em inglês aparecem como fatos, sem faixa.
- **Passos:**
  1. No ambiente com indícios ligados, escolha a **Lista 4**, cole o código e verifique.
- **Código:**

```python
def calculate_average(values: list) -> float:
    """Return the average of the values."""
    total = 0
    for value in values:
        total += value
    return total / len(values)

if __name__ == "__main__":
    print(calculate_average([1, 2, 3]))
```

- **Esperado:**
  - O painel **Indícios de uso de IA** aparece, sem faixa geral (só marcadores de estilo).
  - Docstring (texto entre aspas triplas no início da função ou do programa), incomum nas soluções das listas. (sem faixa; linhas 2).
  - Anotações de tipo (como 'x: int' ou '-> float'), que a disciplina não ensina. (sem faixa; linhas 1).
  - if __name__ == "__main__", que a disciplina não ensina. (sem faixa; linhas 8).
  - A maioria dos nomes está em inglês ('calculate_average', 'values', 'value') num curso em português. (sem faixa; linhas 1, 4).
  - No fim, aparecem as perguntas para a conversa com o aluno, e nada do painel entra no feedback.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### I-04. Código de aluno sem indício

- **Objetivo:** Sem indício, o painel não aparece.
- **Passos:**
  1. No ambiente com indícios ligados, escolha a **Lista 2**, cole o código e verifique.
- **Código:**

```python
n = int(input())
soma = 0
for i in range(n):
    soma += int(input())
print(soma)
```

- **Esperado:**
  - O painel **Indícios de uso de IA** não aparece.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 14. Limites e mensagens

### M-01. ⚠ Limite de verificações por minuto

- **Objetivo:** Cada conta faz até 30 verificações, comparações ou feedbacks por minuto.
- **Passos:**
  1. Clique em **Verificar** 31 vezes seguidas em menos de um minuto.
- **Esperado:**
  - A 31ª mostra "Limite de verificações atingido", com uma contagem regressiva.
  - Depois da contagem, a verificação volta a funcionar.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### M-02. Serviço lento ou fora do ar

- **Objetivo:** Sem resposta do servidor, a página explica e não trava.
- **Passos:**
  1. Desligue o Wi-Fi e clique em **Verificar**.
  2. Ligue de novo e verifique.
- **Esperado:**
  - A página diz que não houve resposta do servidor.
  - Com a rede de volta, funciona.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### M-03. Primeira verificação do dia

- **Objetivo:** O piloto fica acordado pelo monitoramento.
- **Passos:**
  1. Logo cedo, faça a primeira verificação do dia.
- **Esperado:**
  - O resultado vem em menos de 2 segundos (o servidor leva cerca de 20 ms; o resto é a rede).
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 15. Privacidade e segurança

### S-01. A API não responde fora da página

- **Objetivo:** O servidor só atende pela página.
- **Passos:**
  1. Abra no navegador https://ip-checker-api-qqn9.onrender.com/api/v1/lists.
- **Esperado:**
  - A resposta é um erro de acesso (403), sem dados.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### S-02. Nada do código fica guardado

- **Objetivo:** O código não é guardado.
- **Passos:**
  1. Verifique um código, saia, entre de novo e procure o código em qualquer tela.
- **Esperado:**
  - O código não aparece em lugar nenhum.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### S-03. Gabarito nunca vai ao navegador

- **Objetivo:** Nem o texto do gabarito nem trechos dele aparecem.
- **Passos:**
  1. Repita o GB-03 e, no navegador, abra as ferramentas do desenvolvedor (F12) > Rede, e veja a resposta da verificação.
- **Esperado:**
  - A resposta traz porcentagem, nomes de construções e linhas do aluno, nunca o código do gabarito.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## 16. Celular, tema e acessibilidade

### U-01. Celular

- **Objetivo:** A página funciona no celular.
- **Passos:**
  1. Abra https://ip-checker-red-phi.vercel.app no celular, entre, verifique o V-01 e gere o feedback.
- **Esperado:**
  - O menu se adapta à tela, nada fica cortado e não há rolagem lateral.
  - Depois de verificar, o resultado, os indícios e o feedback aparecem em abas, e **Voltar ao código** leva ao editor.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### U-02. Tema claro, escuro e do sistema

- **Objetivo:** O tema escolhido vale neste navegador; "Do sistema" segue o sistema.
- **Passos:**
  1. No menu do seu primeiro nome (ou em **Perfil > Aparência**), escolha **Escuro** e recarregue.
  2. Escolha **Claro** com o sistema no tema escuro.
  3. Escolha **Do sistema** e mude o tema do sistema.
- **Esperado:**
  - **Escuro** deixa a página escura, sem piscar ao recarregar, com texto legível em todas as telas.
  - **Claro** ignora o tema do sistema; **Do sistema** o acompanha.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### U-03. Só o teclado

- **Objetivo:** Dá para usar a página sem mouse.
- **Passos:**
  1. Com Tab, Shift+Tab, Enter e Esc, entre, verifique um código e gere o feedback.
- **Esperado:**
  - Todo controle recebe foco visível, na ordem da tela.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

### U-04. Zoom de 200%

- **Objetivo:** A página continua usável com zoom.
- **Passos:**
  1. Aumente o zoom do navegador para 200%.
- **Esperado:**
  - Os textos e botões continuam visíveis e utilizáveis.
- **Resultado:** ☐ OK ☐ Falhou ☐ Não testado
- **Observações:**

## Ficha de falha

Copie para cada falha encontrada:

| Campo | Preencha |
|---|---|
| Cenário | (ex.: V-19) |
| Quem testou e quando | |
| Navegador e aparelho | |
| O que fez | |
| O que esperava | |
| O que aconteceu | |
| Código do erro (`request_id`), se houver | |
| Captura de tela | |

Mande ao desenvolvedor. Falsos positivos (o IP-Checker aponta algo que o documento permite) têm
meta de correção de 2 dias úteis (P-09).

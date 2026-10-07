# Como cadastrar as regras de uma questão

Guia para monitores, monitores-chefes e professores (R-01, US-13, S24-03). As regras de uma
questão dizem o que o **enunciado** permite ou proíbe explicitamente, além das permissões da
lista. Quando a pessoa escolhe a questão na página, essas regras prevalecem sobre as da lista,
inclusive sobre as proibições gerais (C-02).

> Só cadastre o que está escrito no enunciado. Se o enunciado não diz nada sobre uma construção,
> valem as permissões da lista: não precisa de cadastro.

## 1. Escreva o arquivo da questão

Crie `rulesets/<período>/questions/L<lista>-Q<número>.yaml`, com a numeração oficial do período
(P-07). Exemplo comentado, para a questão 2 da Lista 3 de 2026.2:

```yaml
# rulesets/2026.2/questions/L3-Q2.yaml
question_id: L3-Q2          # igual ao nome do arquivo
list: 3                     # a lista da questão (tem de bater com o L3 do nome)
title: Soma dos pares       # aparece no seletor da página, até 80 caracteres
source: >-                  # o trecho do enunciado que justifica o cadastro
  Enunciado da L3-Q2 (2026.2): "Use map() para converter a entrada. Não use append()."

allow_facts:                # construções que o documento de permissões não cita
  - builtin:map
deny:                       # regras do catálogo (R-xx) ou fatos que a questão proíbe
  - R-46                    # append(), insert(), pop() e remove()
```

Os campos:

| Campo | Obrigatório | Para que serve |
|---|---|---|
| `question_id` | sim | `L<lista>-Q<número>`, igual ao nome do arquivo |
| `list` | sim | A lista da questão |
| `title` | sim | Nome curto, mostrado no seletor |
| `source` | sim | O trecho do enunciado, para quem revisa conferir |
| `allow` | não | Regras inteiras do catálogo (`R-xx`) que o enunciado libera, mesmo antes da lista delas. Valem com as condições da regra (ex.: a R-37 libera o `zip` só no cabeçalho do `for`) |
| `allow_facts` | não | Fatos que o enunciado libera e que nenhuma regra cobre (ex.: `builtin:map`) |
| `deny` | não | Regras (`R-xx`) ou fatos que o enunciado proíbe, mesmo que a lista permita |
| `message` | não | Texto da violação por `deny`; pode usar `{construct}` e `{question_id}`. Sem ela: "'append()' é proibido nesta questão (L3-Q2), pelo enunciado." |

Pelo menos um de `allow`, `allow_facts` e `deny` precisa ter um item. Os nomes dos fatos
(`builtin:map`, `method:append`, `node:For`...) estão em [`docs/mapping-R-xx.md`](docs/mapping-R-xx.md),
e as regras, na seção 3.1 do blueprint.

O que **não** dá para cadastrar numa questão:

- as meta-regras (R-01 a R-04) e as exigências (R-02 e R-68): uma questão não dispensa o assunto da
  lista;
- proibir uma proibição geral que já vale em todas as listas (R-05 a R-14);
- liberar e proibir a mesma construção;
- fatos estruturais (`node:Name`, `node:Call`...), que o motor sempre aceita.

## 2. Valide antes de abrir o PR

```bash
cd backend
uv run ipc-rules validate ../rulesets/2026.2
```

O comando mostra o arquivo e o campo de cada erro e sai com código diferente de zero se algo estiver
errado. Ele também **avisa** quando a questão libera uma proibição geral (R-05 a R-14).

Se quiser conferir o efeito, rode o ambiente local (`deploy/README.md`), escolha a lista e a questão
na página e verifique um código que use o que o enunciado libera ou proíbe.

## 3. Abra o PR para a `develop`

Use o modelo de PR de regras: na página de criação do PR, acrescente `?template=regras.md` ao
endereço. Um PR de questão muda só `rulesets/<período>/questions/`.

## 4. Revisão e aprovação

Até a release do piloto, a aprovação é **por processo** (a Q-22, que trata de fork e de um check
automático, foi adiada para depois da release):

- ninguém aprova o próprio PR;
- o PR é aprovado por um monitor-chefe ou por um professor, que confere o `source` contra o
  enunciado;
- uma questão que **libera proibição geral** (R-05 a R-14) só entra com a aprovação de um
  **professor** (C-02). A CI mostra um aviso nesse caso;
- quem faz o merge confere essas aprovações e a CI verde.

Depois do merge na `develop` e da release na `main`, o deploy publica o ruleset novo e a questão
aparece no seletor da página.

## 5. Soluções de referência por IA (opcional, S29-02)

Para o sinal de semelhança com IA do painel de indícios ([`docs/indicios-de-ia.md`](docs/indicios-de-ia.md)),
quem cadastra a questão pode gerar 2 ou 3 soluções com assistentes diferentes, **a partir só do
enunciado** e sem nenhum código de aluno, e guardá-las sem edição em:

```text
rulesets/2026.2/referencias/L3-Q2/assistente-a.py
rulesets/2026.2/referencias/L3-Q2/assistente-b.py
```

A pasta tem o nome da questão, que precisa estar cadastrada em `questions/`; cada arquivo é uma
solução em Python válido, de até 50 KB, e o nome do arquivo (sem `.py`) aparece no painel. O
`ipc-rules validate` recusa uma referência inválida e mostra quantas há. Vão no mesmo PR da questão
ou num PR à parte, com a mesma aprovação.

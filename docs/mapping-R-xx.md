# Matriz de mapeamento R-xx → fatos da AST

Traduz cada regra do documento "Permissões das listas de Introdução à Programação" para os fatos
que o motor extrai do código (blueprint, seção 5.2.3). Decisões tomadas pelo autor do projeto em
01/10/2026, a ratificar por monitores-chefes e professores na apresentação (Marco 2).

## Convenções

- **Fato** = `<tipo>:<nome>`. Tipos: `node` (classe de nó do `ast`), `op` (operador), `cmp`
  (comparação), `builtin`, `method` (todo atributo, chamado ou não), `kwarg` (`<função>.<nome>` ou
  `**`), `const`, `param`, `call`, `return`, `target`, `derived`.
- **Fatos estruturais** são sempre aceitos, porque o nó pai ou um fato mais específico já decide:
  `node:Module`, `node:Expr`, `node:Name`, `node:Call`, `node:keyword`, `node:Load`, `node:Store`,
  `node:Constant` (decidido por `const:*`), `node:Attribute` (decidido por `method:*`),
  `node:arguments`, `node:arg`, `node:comprehension`, `node:alias`, `node:ExceptHandler` e
  `derived:recursion` (só serve à exigência da R-68; o `def` e a chamada são da R-59).
- **Fatos contextuais substituem o fato genérico** do mesmo nó: `*x` numa chamada gera
  `call:star_args` (e não `node:Starred`); `a, b` como alvo de qualquer `for` gera
  `target:for_unpack` (e não `node:Tuple`).
- **Fatos que acompanham o nó**: `call:user` (chamada de função do aluno), `call:user_kwarg`
  (argumento nomeado nessa chamada, ex.: `f(x=1)`; em `dict()` e `update()`, o nome é uma chave
  livre e o fato é `kwarg:dict.*` ou `kwarg:update.*`), `return:multi` (`return a, b`) e os de
  parâmetro: `param:vararg`, `param:kwarg`, `param:default`, `param:kwonly` (`def f(*, k)`) e
  `param:posonly` (`def f(a, /)`).
- **Fatos derivados** marcam sintaxe que não tem nó próprio na AST. Nenhum deles tem regra que o
  permita, então todos viram R-04 (não consta):
  - `derived:loop_else`: o `else` de `for`/`while` (Q-02, item g); aponta para o primeiro comando
    do `else`;
  - `derived:decorator`: cada `@decorador` de função ou classe, que é uma chamada implícita
    (S7-01, DoD item 9); aponta para a expressão depois do `@`;
  - `derived:dict_unpack`: cada `**d` dentro de um dicionário literal (S7-01); aponta para `d`;
  - `derived:nested_function`: cada `def` dentro de outra função ou de um `lambda` (Q-02, item f;
    Sprint 22); aponta para o `def` de dentro. Métodos de classe não contam (a classe já é R-09).

  `derived:recursion` (Sprint 23) é a exceção: é estrutural e marca cada `def` que está num ciclo
  do grafo de chamadas entre funções do aluno, direto (`f` chama `f`) ou mútuo (`f` chama `g`, que
  chama `f`), pela C-03. As chamadas são pelo nome, como `call:user`; chamar um parâmetro, citar a
  função sem chamá-la ou chamá-la só no módulo não forma ciclo, e um `lambda` não entra no grafo.
- **Alvo do `for` com vários nomes** (`target:for_unpack`): até a Lista 4, só com `zip()` de 2 ou
  mais sequências como o iterável do comando `for` (R-37); a partir da Lista 3, com qualquer
  iterável (R-40, casos 3 e 8 do Marco 2). A partir da Lista 5, `zip()` (R-64), `enumerate()`
  (R-63) e `.items()` (R-65) também o liberam. Os predicados estão no blueprint, 5.2.3; o
  `zip_in_for_header` também vale para o `for` de uma compreensão (caso 5).
- O tipo do operando não é inferido: `in` para strings, listas e `range()` é o mesmo fato `cmp:In`.
- **Built-in ou nome do aluno** (`engine/symbols.py`): `len = 3` seguido de `print(len)` não gera
  `builtin:len`. A resolução segue a ordem de execução, para impedir que o aluno esconda um
  built-in proibido atribuindo o mesmo nome depois: `eval('1')` seguido de `eval = 2` ainda gera
  `builtin:eval`, e em `len = len(x)` o `len(x)` é o built-in. Dentro de funções, um built-in que
  não é local continua sendo o built-in.

## Casos do Marco 2 (decididos pelo autor em 09/10/2026, ruleset `2026.2.5`)

As Listas 3 e 4 entraram na Sprint 22 e as Listas 5 e 6 na Sprint 23 com estes casos do lado mais
restritivo. O autor os decidiu em 09/10/2026 (pauta do Marco 2, `docs/marco-2.md`, apresentada à
equipe em 19/10/2026); uma questão cadastrada continua podendo liberar ou proibir qualquer um deles
pela R-01.

| Caso | Antes | Decisão | No motor |
|---|---|---|---|
| 1. `if __name__ == "__main__":` | R-04 | Permitido a partir da L4 | `builtin:__name__` na R-59 |
| 2. `f(x=1)` com função do aluno | R-04 | Os "parâmetros" da R-59 incluem o argumento nomeado | `call:user_kwarg` na R-59 |
| 3. `for a, b in pares:` na L3 ou depois | R-37 (condição não atendida) | As tuplas aceitam vários nomes no `for` a partir da L3 | `target:for_unpack` na R-40, sem condição; na L2, só com o `zip` da R-37 |
| 4. `f"{x!r}"`, `f"{x!s}"`, `f"{x!a}"` | Aceito (R-31) | Aceito | Sem mudança |
| 5. `[a + b for a, b in zip(x, y)]` na L3 ou L4 | R-37 (condição não atendida) | O `for` de uma compreensão conta como comando `for` | `zip_in_for_header` também marca o `zip()` iterável de uma compreensão, com a mesma condição de 2 ou mais sequências |
| 6. `palavras = input().split()` como única lista, na L3 | R-02 | Comprova o assunto da Lista 3 | `method:split` na exigência R-02 da L3 |
| 7. `dict(a=1)`, `d.update(a=1)`, `enumerate(v, start=1)` na L5 | R-04 | Permitidos desde a L5 | `kwarg:dict.*` na R-62, `kwarg:update.*` na R-66 e `kwarg:enumerate.start` na R-63; os nomes de `dict()` e `update()` são chaves livres, então qualquer nome é o mesmo fato |
| 8. `for a, b in pares:` e `for x, y in d.values():` na L5 ou L6 | R-63 (condição não atendida) | Valem com qualquer sequência de pares | Pela R-40 (caso 3) |
| 9. `f = lambda n: f(n - 1) if n else 0` na L6 | Não conta como recursão (R-68) | Continua não contando | Sem mudança |
| 10. Expressão geradora | R-04 até o `2026.2.4` | Ratificada: R-41 a partir da L3 | `node:GeneratorExp` na R-41 (`2026.2.4`) |

Os outros argumentos nomeados continuam fora (Q-02 c): `sep=`, `key=` e `reverse=`, e qualquer
outro nome em `enumerate()`.

**Consequência da Q-02 (c) na Lista 5:** `sorted(v, key=lambda x: ...)`, o uso mais comum de
`lambda`, continua na R-04 pelo `key=`. O `lambda` em si (R-67) é permitido: atribuído a um nome,
chamado ou passado a uma função do aluno.

## Decisões aplicadas

| ID | Decisão |
|---|---|
| C-01 | `async for`, `async def`, `async with` e `await` não constam → R-04. |
| C-02 | Override da questão (R-01) acima de tudo, inclusive das proibições gerais (exige professor). |
| C-03 | R-68 aceita recursão direta e mútua. |
| Q-02 | (a) `format` função e método → R-28; (b) `not in` → R-30, `is not` → R-17; (c) `sep=`, `key=`, `reverse=` → R-04; (d) `a, b = …` antes da L3 → R-04, exceto alvo de `for` com `zip`; (e) dict comprehension → R-04; expressão geradora → R-41 a partir da L3 desde 09/10/2026 (antes, R-04; revisão provisória, a ratificar no Marco 2, caso 10); (f) parâmetro com valor padrão e função aninhada → R-04; (g) `else` em laço → R-04; (h) `*` e `**` em chamadas → R-10. |
| Q-03 | R-14 = só a instrução `global`. |
| Q-04 | Condição do `zip` (R-37) vale nas Listas 2–4; na L5 em diante é livre (R-64). |
| Q-05 | Assunto obrigatório (R-02): L1 `if`/ternário; L2 `for`/`while`; L3 lista ou tupla; L4 `def`; L5 dicionário; L6 recursão. |
| Q-06 | Todo `import`, inclusive da biblioteca padrão → R-05 (anulação). |
| Q-07 | `type()` com 3 argumentos → R-09; com 1 argumento → R-33. |

**Q-02 (d) desde a Sprint 22:** com as tuplas na Lista 3 (R-40), `a, b = 1, 2` antes da L3 aparece
como "Fora da lista" pela R-40, e não mais como R-04. A decisão não muda: é proibido antes da
Lista 3 e permitido dali em diante; só a mensagem passa a dizer em que lista ele é liberado.

## Matriz

| Regra | Fatos | Situação |
|---|---|---|
| R-01 | Regras por questão em `questions/L<n>-Q<m>.yaml`: `allow` (regras, com as condições delas), `allow_facts` e `deny` (regras ou fatos); a proibição sai como `PROIBIDO_NA_QUESTAO` com o ID R-01 | No motor (Sprint 24); cadastradas: a questão do ensaio (L3-Q9, S31-13) e, de 2026.2, a L4-Q4 (`eval()` e `reverse=` no `sort()`) e a L4-Q5 (valor padrão de parâmetro), por `allow_facts` |
| R-02 | Bloco `requirements` por lista (Q-05); na L3, também `method:split` (caso 6) | L1 na Sprint 12; L2 na 20; L3 e L4 na 22; L5 na 23 (na L6, a exigência é a R-68); `split()` no `2026.2.5` |
| R-03 | Semântica do motor: `since_list ≤ lista ≤ until_list` | Meta-regra no `base.yaml` |
| R-04 | Semântica do motor: fato sem regra → violação `NAO_CONSTA` | Meta-regra no `base.yaml` |
| R-05 | `node:Import`, `node:ImportFrom` | No ruleset |
| R-06 | `node:Try`, `node:TryStar` | No ruleset |
| R-07 | `node:Set`, `node:SetComp`, `builtin:set`, `builtin:frozenset` | No ruleset |
| R-08 | `builtin:exit`, `method:exit` | No ruleset |
| R-09 | `node:ClassDef`; `builtin:type` com `call_args` ≥ 3 | No ruleset |
| R-10 | `param:vararg`, `param:kwarg`, `call:star_args`, `kwarg:**` | No ruleset |
| R-11 | `node:Break`, `node:Continue` | No ruleset |
| R-12 | `node:Pass` | No ruleset |
| R-13 | `const:None` | No ruleset |
| R-14 | `node:Global` | No ruleset |
| R-15 | `node:If` | No ruleset |
| R-16 | `node:Assign`, `const:int`, `const:float`, `const:str` | No ruleset |
| R-17 | `cmp:Is`, `cmp:IsNot` | No ruleset |
| R-18 | `node:BinOp`, `node:UnaryOp`, `node:AugAssign`, `op:Add`, `op:Sub`, `op:Mult`, `op:Div`, `op:FloorDiv`, `op:Mod`, `op:Pow`, `op:UAdd`, `op:USub` | No ruleset |
| R-19 | `node:BoolOp`, `node:Compare`, `op:And`, `op:Or`, `op:Not`, `cmp:Eq`, `cmp:NotEq`, `cmp:Lt`, `cmp:LtE`, `cmp:Gt`, `cmp:GtE`, `const:bool` | No ruleset |
| R-20 | `node:IfExp` | No ruleset |
| R-21 | `op:Add` (igual à R-18; sem inferência de tipo) | No ruleset |
| R-22 | `builtin:print`, `builtin:input` | No ruleset |
| R-23 | `builtin:abs` | No ruleset |
| R-24 | `builtin:int`, `builtin:float`, `builtin:str` | No ruleset |
| R-25 | `builtin:max`, `builtin:min` | No ruleset |
| R-26 | `builtin:round` | No ruleset |
| R-27 | `builtin:len` | No ruleset |
| R-28 | `builtin:format`, `method:format` | No ruleset |
| R-29 | `method:capitalize`, `method:upper`, `method:lower`, `method:isupper`, `method:islower`, `method:isnumeric` | No ruleset |
| R-30 | `cmp:In`, `cmp:NotIn` | No ruleset |
| R-31 | `node:JoinedStr`, `node:FormattedValue` | No ruleset |
| R-32 | `kwarg:print.end` (o `\n` faz parte do texto) | No ruleset |
| R-33 | `builtin:type` com `call_args` = 1 | No ruleset |
| R-34 | `node:For`, `node:While` | No ruleset |
| R-35 | `builtin:range` | No ruleset |
| R-36 | `cmp:In` | No ruleset |
| R-37 | `builtin:zip` + `target:for_unpack`, predicado `zip_in_for_header` (`zip()` built-in como o iterável do comando `for` ou, desde o `2026.2.5`, do `for` de uma compreensão, com ≥ 2 argumentos), Listas 2–4 | No ruleset (Sprint 20; compreensão no `2026.2.5`) |
| R-38–R-43 | `node:List` (R-38 e R-39: matriz = lista de listas); `node:Tuple` e, desde o `2026.2.5`, `target:for_unpack` (R-40, inclusive a atribuição múltipla e vários nomes no `for`); `node:ListComp` e, desde 09/10/2026, `node:GeneratorExp` (R-41; Q-02 e revista); `node:Subscript`; `node:Slice` | No ruleset (Sprint 22; expressão geradora no `2026.2.4`) |
| R-44 | `cmp:In` | No ruleset (Sprint 22) |
| R-45–R-49 | `builtin:list`; `method:append`, `insert`, `pop`, `remove`; `node:Delete`, `node:Del`; `method:sort`, `builtin:sorted`; `method:reverse`, `builtin:reversed` | No ruleset (Sprint 22) |
| R-50–R-58 | `method:strip`, `replace`, `index`, `join`, `split`, `rsplit`, `count`, `copy`; `builtin:sum`, `builtin:tuple` | No ruleset (Sprint 22) |
| R-59–R-60 | `node:FunctionDef`, `node:Return`, `call:user`, `call:user_kwarg` e `builtin:__name__` (casos 1 e 2, `2026.2.5`); `return:multi`. `param:default` e `derived:nested_function` ficam na R-04 (Q-02 f) | No ruleset (Sprint 22) |
| R-61–R-62 | `node:Dict`; `builtin:dict`, `kwarg:dict.*` (caso 7, `2026.2.5`). Dict comprehension e `**` num dicionário ficam na R-04 (Q-02 e) | No ruleset (Sprint 23) |
| R-63 | `builtin:enumerate`, `kwarg:enumerate.start` (caso 7, `2026.2.5`); `target:for_unpack` com `enumerate_in_for_header` | No ruleset (Sprint 23) |
| R-64 | `builtin:zip` (livre, Q-04); `target:for_unpack` com `zip_in_for_header` (`min: 1`) | No ruleset (Sprint 23) |
| R-65–R-66 | `method:keys`, `values`, `items`; `target:for_unpack` com `items_in_for_header`; `method:get`, `update`, `kwarg:update.*` (caso 7, `2026.2.5`) | No ruleset (Sprint 23) |
| R-67 | `node:Lambda` (valor padrão de parâmetro segue na R-04, Q-02 f) | No ruleset (Sprint 23) |
| R-68 | `derived:recursion` (exigência na Lista 6, C-03) | No ruleset (Sprint 23) |

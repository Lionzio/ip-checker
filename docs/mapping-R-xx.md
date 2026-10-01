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
  `node:arguments`, `node:arg`, `node:comprehension`, `node:alias` e `node:ExceptHandler`.
- **Fatos contextuais substituem o fato genérico** do mesmo nó: `*x` numa chamada gera
  `call:star_args` (e não `node:Starred`); `a, b` como alvo de qualquer `for` gera
  `target:for_unpack` (e não `node:Tuple`).
- **Fatos que acompanham o nó**: `call:user` (chamada de função do aluno), `call:user_kwarg`
  (argumento nomeado nessa chamada, ex.: `f(x=1)`), `return:multi` (`return a, b`) e os de
  parâmetro: `param:vararg`, `param:kwarg`, `param:default`, `param:kwonly` (`def f(*, k)`) e
  `param:posonly` (`def f(a, /)`).
- **Fatos derivados** marcam sintaxe que não tem nó próprio na AST. Nenhum deles tem regra que o
  permita, então todos viram R-04 (não consta):
  - `derived:loop_else`: o `else` de `for`/`while` (Q-02, item g); aponta para o primeiro comando
    do `else`;
  - `derived:decorator`: cada `@decorador` de função ou classe, que é uma chamada implícita
    (S7-01, DoD item 9); aponta para a expressão depois do `@`;
  - `derived:dict_unpack`: cada `**d` dentro de um dicionário literal (S7-01); aponta para `d`.

  `derived:recursion` entra na Sprint 16.
- O tipo do operando não é inferido: `in` para strings, listas e `range()` é o mesmo fato `cmp:In`.
- **Built-in ou nome do aluno** (`engine/symbols.py`): `len = 3` seguido de `print(len)` não gera
  `builtin:len`. A resolução segue a ordem de execução, para impedir que o aluno esconda um
  built-in proibido atribuindo o mesmo nome depois: `eval('1')` seguido de `eval = 2` ainda gera
  `builtin:eval`, e em `len = len(x)` o `len(x)` é o built-in. Dentro de funções, um built-in que
  não é local continua sendo o built-in.

## Casos a observar (decidir antes da Sprint 15)

| Caso | Hoje | Pergunta |
|---|---|---|
| `if __name__ == "__main__":` | Gera `builtin:__name__` → R-04 (não consta) | As listas usam esse padrão? Se sim, liberar a partir da L4. |
| `f(x=1)` com função do aluno | `call:user_kwarg` → R-04 | A R-59 ("parâmetros") inclui argumentos nomeados na chamada? |
| `for a, b in pares:` na L3 ou depois | `target:for_unpack` | A R-40 (tuplas) deve casar `target:for_unpack` a partir da L3, além da R-37 (zip, L2–L4). |
| `f"{x!r}"`, `f"{x!s}"`, `f"{x!a}"` | Aceito como parte da f-string (R-31) | A conversão chama `repr()`, `str()` ou `ascii()` por baixo. Deve contar como esses built-ins (`repr` e `ascii` não constam)? |

## Decisões aplicadas

| ID | Decisão |
|---|---|
| C-01 | `async for`, `async def`, `async with` e `await` não constam → R-04. |
| C-02 | Override da questão (R-01) acima de tudo, inclusive das proibições gerais (exige professor). |
| C-03 | R-68 aceita recursão direta e mútua. |
| Q-02 | (a) `format` função e método → R-28; (b) `not in` → R-30, `is not` → R-17; (c) `sep=`, `key=`, `reverse=` → R-04; (d) `a, b = …` antes da L3 → R-04, exceto alvo de `for` com `zip`; (e) expressão geradora e dict comprehension → R-04; (f) parâmetro com valor padrão e função aninhada → R-04; (g) `else` em laço → R-04; (h) `*` e `**` em chamadas → R-10. |
| Q-03 | R-14 = só a instrução `global`. |
| Q-04 | Condição do `zip` (R-37) vale nas Listas 2–4; na L5 em diante é livre (R-64). |
| Q-05 | Assunto obrigatório (R-02): L1 `if`/ternário; L2 `for`/`while`; L3 lista ou tupla; L4 `def`; L5 dicionário; L6 recursão. |
| Q-06 | Todo `import`, inclusive da biblioteca padrão → R-05 (anulação). |
| Q-07 | `type()` com 3 argumentos → R-09; com 1 argumento → R-33. |

## Matriz

| Regra | Fatos | Situação |
|---|---|---|
| R-01 | Override por questão (`questions/<id>.yaml`) | Sprint 17 |
| R-02 | Bloco `requirements` por lista (Q-05) | L1 na Sprint 12; L2 na 13; L3–L6 na 16 |
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
| R-37 | `builtin:zip` + `target:for_unpack`, predicado `zip_in_for_header` (≥ 2 argumentos), Listas 2–4 | Sprint 13 |
| R-38–R-43 | `node:List`; `node:Tuple`; `node:ListComp`; `node:Subscript`; `node:Slice` | Sprint 15 |
| R-44 | `cmp:In` | Sprint 15 |
| R-45–R-49 | `builtin:list`; `method:append`, `insert`, `pop`, `remove`; `node:Delete`, `node:Del`; `method:sort`, `builtin:sorted`; `method:reverse`, `builtin:reversed` | Sprint 15 |
| R-50–R-58 | `method:strip`, `replace`, `index`, `join`, `split`, `rsplit`, `count`, `copy`; `builtin:sum`, `builtin:tuple` | Sprint 15 |
| R-59–R-60 | `node:FunctionDef`, `node:Return`, `call:user`; `return:multi` | Sprint 15 |
| R-61–R-67 | `node:Dict`; `builtin:dict`, `enumerate`, `zip` (livre); `method:keys`, `values`, `items`, `get`, `update`; `node:Lambda` | Sprint 16 |
| R-68 | `derived:recursion` (exigência na Lista 6) | Sprint 16 |

# rulesets

Regras de permissão das listas de Introdução à Programação, como **dados**. O motor do backend só
lê e valida estes arquivos: mudar uma regra nunca exige mudar código (ADR-02, NFR-17).

## Organização

```
rulesets/
└── <período>/            ex.: 2026.2 — a numeração das questões reinicia a cada período (P-07)
    ├── base.yaml         regras das listas, traduzidas do documento de permissões
    └── questions/        regras de cada questão (R-01), uma por arquivo: L<lista>-Q<número>.yaml
```

Gabaritos **nunca** entram aqui nem em nenhuma pasta deste repositório: ficam num repositório
privado separado (Q-14).

## Campos de uma regra em `base.yaml`

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | ID do catálogo (`R-05`). Nunca crie IDs fora do catálogo do blueprint (seção 3.1). |
| `name` | sim | Nome curto, para pessoas. |
| `effect` | sim | `deny` para proibição geral (anula a questão) ou `allow` para permissão. |
| `category` | só em `deny` | Sempre `ANULACAO`. |
| `since_list` | só em `allow` | Primeira lista em que a construção é permitida (vale daí em diante, R-03). |
| `until_list` | não | Última lista em que a regra vale (ex.: o `zip` condicional da R-37 vai até a Lista 4). |
| `match` | sim | Fatos da AST que a regra cobre, no formato `<tipo>:<nome>` (ver `docs/mapping-R-xx.md`). Um item pode ter condição (ver abaixo). |
| `message` | sim | Texto mostrado ao aluno. Pode usar `{allowed_from_list}` e `{construct}`. Chaves literais são escritas duplicadas: `{{a, b}}`. |
| `source` | sim | Página e seção do documento de permissões, começando por `Permissões, p.` |

Tudo que nenhuma regra `allow` cobre é proibido (R-04, *default deny*).

### Fatos com condição

Um item de `match` pode trocar o texto do fato por um objeto com `fact` e `when`. O fato só casa
com a regra quando o predicado é verdadeiro. Exemplo real (R-09): `type()` só cria classe com 3
ou mais argumentos.

```yaml
match:
  - "node:ClassDef"
  - fact: "builtin:type"
    when: { predicate: call_args, params: { min: 3 } }
```

Predicados disponíveis (lista fechada; um predicado novo exige código e ADR):

| Predicado | Parâmetros | Verdadeiro quando |
|---|---|---|
| `call_args` | `min`, `max` | O fato é a função de uma chamada com esse número de argumentos |
| `zip_in_for_header` | `min` | O fato é o `zip()` que serve de iterável ao comando `for`, ou o alvo desse `for` (`for a, b in zip(x, y)`), com `min` ou mais sequências (R-37 e R-64) |
| `enumerate_in_for_header` | nenhum | O fato é o alvo de um `for` cujo iterável é `enumerate(...)` (R-63) |
| `items_in_for_header` | nenhum | O fato é o alvo de um `for` cujo iterável é `x.items()` (R-65) |

Os predicados ficam num registro único, `backend/src/ipc_analyzer/engine/predicates.py`, que o
carregador usa para validar os parâmetros e o motor usa para conferir a condição.

Numa regra `allow`, `when.message` é a mensagem mostrada quando a regra vale na lista, mas a
condição não é atendida (ex.: `type()` com 2 argumentos).

## Regras de uma questão (R-01)

O que o enunciado de uma questão permite ou proíbe explicitamente fica em
`questions/L<lista>-Q<número>.yaml`, cadastrado por monitores e aprovado por monitor-chefe ou
professor. O passo a passo, com um exemplo comentado, está em [`RULES.md`](../RULES.md).

## Como validar uma mudança

```bash
cd backend
uv run ipc-rules validate ../rulesets/2026.2 --golden tests/golden
uv run pytest
```

O `ipc-rules validate` carrega o `base.yaml` e as questões exatamente como o analisador, mostra o
caminho de cada erro e avisa das questões que liberam proibições gerais (só com professor, C-02).
O mesmo comando roda na CI e bloqueia o PR.

Toda regra criada ou alterada precisa de casos em `backend/tests/golden/` (pelo menos 3 por
regra: permitido na lista certa, proibido antes dela e evasão quando couber). Cada caso traz o
código, a lista e as violações esperadas, comparadas de forma exata.

O teste falha, com o caminho do campo, se o arquivo tiver ID repetido, fato inexistente (ex.:
`node:Fro`), marcador desconhecido na mensagem, fato permitido e proibido ao mesmo tempo, entre
outros.

## Gabaritos de períodos anteriores (Q-14, Sprint 20)

Os gabaritos oficiais confirmam que o motor não aponta nada numa solução correta: cada um precisa
ter **zero violação** na sua lista. Eles nunca entram neste repositório; ficam num repositório
privado separado, que a CI baixa com um token só de leitura (job "Gabaritos" do `ci.yml`). Sem essa
configuração, o job fica como *skipped* e o resto da CI segue normal.

**Organização do repositório privado:**

```
<período>/lista-<n>/<questão>.py      ex.: 2025.2/lista-2/q03.py
excecoes.yaml                          opcional
```

Um gabarito do período do ruleset ativo cujo nome é a questão (`2026.2/lista-3/L3-Q2.py`) é
analisado com as regras dela, de `questions/`. Como a numeração reinicia a cada período (P-07), as
questões de períodos anteriores não ficam cadastradas: para elas, registre no `excecoes.yaml` as
regras que o enunciado libera naquele arquivo e o motivo:

```yaml
"2025.2/lista-2/q03.py":
  regras: ["R-37"]
  motivo: "o enunciado pede zip() fora do for"
```

**Configuração (uma vez, feita por você no GitHub):**

1. Crie um repositório **privado**, por exemplo `Lionzio/ip-checker-gabaritos`, e copie os
   gabaritos do Notion para ele, na organização acima.
2. Em **Settings > Developer settings > Personal access tokens > Fine-grained tokens**, crie um
   token com acesso **só** a esse repositório e a permissão **Contents: Read-only**.
3. No `Lionzio/ip-checker`, em **Settings > Secrets and variables > Actions**: crie o segredo
   `GABARITOS_TOKEN` com o token e a variável `GABARITOS_REPO` com `dono/repositório`.

Para rodar localmente, com o repositório privado clonado fora desta pasta:

```bash
cd backend
IPC_GABARITOS_DIR=../../ip-checker-gabaritos uv run pytest tests/official_answers --no-cov
```

O resultado mostra só o arquivo, a regra e a linha, nunca o código. Gabaritos de listas ainda não
habilitadas são pulados.

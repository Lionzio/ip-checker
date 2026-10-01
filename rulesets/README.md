# rulesets

Regras de permissão das listas de Introdução à Programação, como **dados**. O motor do backend só
lê e valida estes arquivos: mudar uma regra nunca exige mudar código (ADR-02, NFR-17).

## Organização

```
rulesets/
└── <período>/            ex.: 2026.2 — a numeração das questões reinicia a cada período (P-07)
    ├── base.yaml         regras das listas, traduzidas do documento de permissões
    └── questions/        (Sprint 17) permissões e proibições explícitas de cada questão
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

Numa regra `allow`, `when.message` é a mensagem mostrada quando a regra vale na lista, mas a
condição não é atendida (ex.: `type()` com 2 argumentos).

## Como validar uma mudança

```bash
cd backend
uv run pytest
```

O teste falha, com o caminho do campo, se o arquivo tiver ID repetido, fato inexistente (ex.:
`node:Fro`), marcador desconhecido na mensagem, fato permitido e proibido ao mesmo tempo, entre
outros. A CLI `ipc-rules validate` entra na Sprint 17.

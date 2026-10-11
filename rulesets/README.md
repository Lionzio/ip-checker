# rulesets

Regras de permissão das listas de Introdução à Programação, como **dados**. O motor do backend só
lê e valida estes arquivos: mudar uma regra nunca exige mudar código (ADR-02, NFR-17).

## Organização

```
rulesets/
├── ATIVO                 uma linha só, o período ativo (ex.: 2026.2): trocar de período é mudar
│                         essa linha (S31-09); o analisador, a CI e o ipc-rules leem daqui
└── <período>/            ex.: 2026.2 — a numeração das questões reinicia a cada período (P-07)
    ├── base.yaml         regras das listas, traduzidas do documento de permissões
    ├── questions/        regras de cada questão (R-01), uma por arquivo: L<lista>-Q<número>.yaml
    └── referencias/      soluções geradas por IA a partir do enunciado, por questão (S29-02):
                          referencias/L<lista>-Q<número>/<assistente>.py (RULES.md, passo 5)
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
uv run ipc-rules validate ../rulesets --golden tests/golden
uv run pytest
```

`../rulesets` valida o período ativo; a pasta de um período (`../rulesets/2027.1`) valida aquele
período. Um período novo nasce com `uv run ipc-rules new-period 2027.1 --from 2026.2` (`RULES.md`,
passo 6). O 2027.1 já existe (S35-09, 11/10/2026), como cópia do 2026.2 (P-22), ainda inativo: ele
passa a valer quando o `ATIVO` mudar, antes da primeira correção de 2027.1.

O `ipc-rules validate` carrega o `base.yaml` e as questões exatamente como o analisador, mostra o
caminho de cada erro e avisa das questões que liberam proibições gerais (só com professor, C-02).
O mesmo comando roda na CI e bloqueia o PR.

Toda regra criada ou alterada precisa de casos em `backend/tests/golden/` (pelo menos 3 por
regra: permitido na lista certa, proibido antes dela e evasão quando couber). Cada caso traz o
código, a lista e as violações esperadas, comparadas de forma exata.

O teste falha, com o caminho do campo, se o arquivo tiver ID repetido, fato inexistente (ex.:
`node:Fro`), marcador desconhecido na mensagem, fato permitido e proibido ao mesmo tempo, entre
outros.

### Esquema JSON e ruleset compilado (S35-05)

`schema/ruleset.schema.json` e `schema/question.schema.json` saem dos próprios modelos do
carregador (`uv run ipc-rules schema`, de `backend/`); a CI falha se o modelo mudar sem os
esquemas gerados de novo, e confere que todo `base.yaml` e toda questão seguem o esquema. No VS
Code, com a extensão YAML da Red Hat, o editor passa a completar e sublinhar os campos com esta
configuração do usuário (o esquema não substitui o `ipc-rules validate`, que confere também os
fatos, as mensagens e as referências entre regras):

```json
"yaml.schemas": {
  "./rulesets/schema/ruleset.schema.json": "rulesets/*/base.yaml",
  "./rulesets/schema/question.schema.json": "rulesets/*/questions/*.yaml"
}
```

`uv run ipc-rules compile ../rulesets --saida ruleset.json` grava o ruleset do período ativo em
JSON, com o `ruleset_sha256` que o analisador publica no manifesto: o mesmo valor nos dois
confere que o deploy carregou exatamente os arquivos do repositório.

## Gabaritos de períodos anteriores (Q-14, Sprint 20)

Os gabaritos oficiais confirmam que o motor não aponta nada numa solução correta: cada um precisa
ter **zero violação** na sua lista. Eles nunca entram neste repositório; ficam num repositório
privado separado, [`Lionzio/ip-checker-gabaritos`](https://github.com/Lionzio/ip-checker-gabaritos),
que a CI baixa com uma chave de implantação só de leitura (job "Gabaritos" do `ci.yml`, ADR-10).
Enquanto a variável `GABARITOS_REPO` não existe, o job fica como *skipped* e o resto da CI segue
normal. O README daquele repositório explica, para a equipe, como acrescentar gabaritos.

**Organização do repositório privado:**

```
<período>/lista-<n>/L<n>-Q<m>.py      ex.: 2026.2/lista-3/L3-Q2.py
excecoes.yaml                          opcional
```

Um gabarito do período do ruleset ativo cujo nome é a questão (`2026.2/lista-3/L3-Q2.py`) é
analisado com as regras dela, de `questions/`. Como a numeração reinicia a cada período (P-07), as
questões de períodos anteriores não ficam cadastradas: para elas, registre no `excecoes.yaml` as
regras que o enunciado libera naquele arquivo e o motivo:

```yaml
"2025.2/lista-2/L2-Q3.py":
  regras: ["R-37"]
  motivo: "o enunciado pede zip() fora do for"
```

**Configuração (08/10/2026):** o repositório privado `Lionzio/ip-checker-gabaritos` já existe, com
as pastas de 2026.2, e a chave de implantação só de leitura já está nele (**Settings > Deploy
keys**), com a parte privada no segredo `GABARITOS_SSH_KEY` deste repositório. Falta:

1. Copiar os gabaritos do Notion para lá, na organização acima (S33-01; o README de lá mostra como
   fazer pelo navegador). Desde a Sprint 33, o `ipc-rules import-gabaritos` faz isso a partir de
   uma exportação do Notion em Markdown (veja abaixo).
2. ~~Depois do primeiro gabarito, ligar o job~~: feito em 08/10/2026 (`GABARITOS_REPO`).

**Importar do Notion (S33-08):** no Notion, abra a página dos gabaritos do período e use **... >
Export > Markdown & CSV**, com as subpáginas. Descompacte numa pasta fora deste repositório e, de
`backend/`, rode primeiro só para ver o que seria feito:

```bash
uv run ipc-rules import-gabaritos /caminho/da/exportacao ../../ip-checker-gabaritos --periodo 2025.2 --simular
```

Cada bloco de código Python vira `<período>/lista-<n>/L<n>-Q<m>.py`. A questão vem do título acima
do bloco, do nome da página ou das pastas (`L3-Q2`, `L3 Q2`, ou "Lista 3" e "Questão 2"). Duas
soluções para a mesma questão, ou um bloco sem questão reconhecida, ficam de fora e aparecem na
saída para você decidir. O comando nunca grava neste repositório, não sobrescreve um gabarito
existente sem `--sobrescrever` e não mostra código. Sem `--simular`, ele grava; depois, rode o
harness (abaixo) e, se tudo passar, faça o commit no repositório dos gabaritos.

Para trocar a chave (alguém saiu da equipe técnica): apague a chave em **Deploy keys** e, no Git
Bash, gere outra, cadastre a parte pública e grave a privada sem mostrá-la:

```bash
ssh-keygen -q -t ed25519 -N "" -C ci-ip-checker-gabaritos -f ./gab && gh repo deploy-key add ./gab.pub --repo Lionzio/ip-checker-gabaritos --title "CI do ip-checker (só leitura)" && gh secret set GABARITOS_SSH_KEY --repo Lionzio/ip-checker < ./gab; rm -f ./gab ./gab.pub
```

Para rodar localmente, com o repositório privado clonado fora desta pasta:

```bash
cd backend
IPC_GABARITOS_DIR=../../ip-checker-gabaritos uv run pytest tests/official_answers --no-cov
```

O resultado mostra só o arquivo, a regra e a linha, nunca o código. Gabaritos de listas ainda não
habilitadas são pulados.

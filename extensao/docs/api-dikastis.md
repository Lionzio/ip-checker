# A API do Dikastis usada pela extensão (S50-02)

Registro da descoberta de 16/10/2026 (seção 3.0 do plano da Sprint 50): **só os formatos** (nomes
de campos e tipos), nunca valores. A descoberta foi feita a partir do JavaScript público do
Dikastis, sem login e sem ler dado de aluno. Os validadores ficam em `src/dikastis/formatos.ts`; as
respostas sintéticas dos testes, em `test/respostas/dikastis.ts`.

## Autenticação

- A API fica em `https://dikastis.com.br/api`, na mesma origem da página.
- O Dikastis guarda o token da sessão em `localStorage["@Dikastis:token"]` e o manda como
  `Authorization: Bearer <token>`.
- A extensão lê esse token **só no script da página** (`src/content/`), na aba em que o monitor já
  está logado. O token não vai ao service worker, ao IP-Checker nem ao console. Ausente ou vencido
  (o `exp` do JWT, quando legível), a leitura para com "Sem sessão no Dikastis".
- `401` é tratado como sessão vencida; `429` e `5xx` repetem até 3 vezes (2 s, 4 s, 8 s); outros
  `4xx` não repetem. No máximo 2 pedidos por segundo.

## Endereços usados (só leitura, só GET)

| Endereço | Campos usados | Observações |
|---|---|---|
| `GET /api/organizations/<id>` | `teams[].id` (texto), `teams[].name` (texto) | A organização da disciplina de IP; o id fica em `src/config.ts` |
| `GET /api/teams/<id>` | `tasks[].id` (texto), `tasks[].title` (texto) | A resposta traz também os membros da turma: **a extensão não lê esse campo** |
| `GET /api/tasks/<id>` | `title` (texto), `beginTime` e `endTime` (data ISO ou nulo), `problems[].problem.id` e `problems[].problem.title` (texto) | `problems[].order` e `weight` existem e não são usados |
| `GET /api/problems/<id>` | `title` (texto), `description`, `inputDescription`, `outputDescription` (texto ou nulo), `timeLimit` (número ou nulo), `testCases[].isSample` (verdadeiro ou falso), `testCases[].input` e `.output` (texto) | Só os casos com `isSample: true` são lidos; os ocultos são descartados no validador e nunca saem dele |

**Nunca usados:** placar (`/overview`), submissões (`/submissions`), pessoas (`/people`) e qualquer
outro endereço com dado de aluno.

## Formatos que dependem de conferência na primeira sincronização (seção 6.3)

- `timeLimit`: tratado como **segundos** até 60 e como milissegundos acima disso
  (`limiteEmMs`). Conferir com um problema de limite conhecido.
- Os textos (`description` e as outras) vão como vieram, sem interpretar HTML ou Markdown.

## Nomes do Dikastis → catálogo

| No Dikastis | No catálogo |
|---|---|
| Turma "IP SI UFPE 2026.2" | período `2026.2`, curso `SI` (também `EC`, `CC/IA`, `CC`; senão `outro`); só de 2026.2 em diante, e só o período mais recente |
| Tarefa "Lista de Treinamento" | `treino`, sem número |
| Tarefa "Lista 3", "Lista 3 - Laços" | `lista` 3 |
| Tarefa "Prova 1" | `prova` 1 |
| Outras tarefas | ignoradas (contadas no resumo) |
| Problema "26.2L1Q1 - Título" (também "26.2L3Q8👮 Título", "26.2L2Q6 -⏳Título", "20.2L1Q01") | `L1-Q1` do período 2026.2, título "Título"; o de outro período é ignorado |
| A mesma questão em várias turmas | lida uma vez; a primeira cópia vale |

## Quando o formato muda

Um campo usado que falta ou muda de tipo lança `FormatoDesconhecido(endereço, campo, esperado)`:
a leitura para inteira, **nada é enviado** ao IP-Checker (NFR-34) e o popup mostra o endereço e o
campo. A correção é atualizar o validador e as respostas sintéticas juntos.

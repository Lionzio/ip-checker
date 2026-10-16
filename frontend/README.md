# frontend

SPA do IP-Checker: React 19, Vite, TypeScript e Tailwind CSS (blueprint, 5.3). Nas Fases 0 e 2 é
servida pelo Caddy do compose, na mesma origem da API; no piloto (2027.1), pela Vercel.

Desde a S9-02, a página fala com a **API real** (`src/services/api.ts`). O cliente simulado
(`src/services/mockClient.ts`) continua disponível num build com `VITE_DEMO_MODE=1`, que mostra o
aviso "Modo demonstração" e serve para ver os estados de erro.

## Comandos

```bash
npm install
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
```

`npm run dev` sobe a página em http://localhost:5180 e repassa `/api` para o compose
(http://127.0.0.1:8180). Para usar a API rodando fora do Docker, defina
`IPC_API_URL=http://127.0.0.1:8101`.

## Piloto na Vercel

No piloto, a página fica na Vercel e a API no Render, mas o navegador só vê a origem da Vercel:
ela repassa `/api/*` ao Render por *rewrite* (S16-02, ADR-04), o que mantém o cookie da sessão
na origem da página e dispensa o CORS. O projeto da Vercel usa `frontend/` como raiz e o
`vercel.json` daqui: `npm ci` e `npm run build:vercel`, sem deploy automático a cada push (o
pipeline de deploy chama o deploy hook depois da CI).

`npm run build:vercel` exige `IPC_API_ORIGIN` (endereço HTTPS da API no Render, lido só no build)
e gera `.vercel/output` (Build Output API v3): a página, o *rewrite* de `/api/*`, os cabeçalhos de
segurança (CSP com `connect-src 'self'`, HSTS, `nosniff`, `no-referrer`) e `version.json` com o
commit do build. Para testar localmente:

```bash
IPC_API_ORIGIN=https://ip-checker-api.onrender.com npm run build:vercel
```

## Contrato da API

Os tipos de `src/types/openapi.ts` são gerados do contrato versionado (`docs/openapi.json`) e nunca
editados à mão; `src/types/api.ts` dá nomes curtos a eles. Depois de mudar a API, regenere:

```bash
npm run gen:api
```

A CI falha se o arquivo gerado estiver diferente do OpenAPI. Como os tipos vêm do contrato, uma
mudança na API que a página não acompanhou quebra a compilação.

## Desempenho (NFR-03) e os degraus do FCP

Duas etapas da CI cuidam do carregamento (S35-02): `scripts/js-budget.mjs` soma o JS inicial com
gzip (limite de 350 KB) e o Lighthouse CI (`lighthouserc.json`, lhci 0.15.1, preset móvel padrão)
reprova com o FCP acima de 1.650 ms (Q-25), com o `dist/` servido com gzip pelo
`scripts/serve-dist.mjs`. Os KB dos scripts são de 1.024 bytes; o Vite mostra kB de 1.000 bytes
(107,84 kB no build são 104,3 KB no `js-budget.mjs`).

O FCP do Lighthouse não cresce de forma contínua com o JS. O Lantern, a simulação de rede do
Lighthouse (4G lento: 150 ms de ida e volta, 1,6 Mbit/s), baixa cada arquivo em idas e voltas
inteiras da janela de congestionamento do TCP, que chega no máximo a 21 segmentos de 1.460 bytes
(30.660 bytes, 29,9 KB). Enquanto o index cabe no mesmo número de janelas, mais bytes não mudam o
FCP; quando passa do limite de uma, o FCP pula ~150 ms de uma vez. Na S39-01, 0,3 KB a mais levaram o
FCP de 1.505 para 1.656 ms. Degraus medidos em 16/10/2026 (tamanho do index com gzip, como no
`js-budget.mjs`; o Lighthouse conta ~0,2 KB a mais, dos cabeçalhos da resposta):

| Degrau | Último tamanho sem o pulo | FCP antes → depois (mediana) |
|---|---|---|
| 1 | 112,4 KB (115.089 bytes) | ~1.510 → ~1.670 ms (passa da meta) |
| 2 | 142,3 KB (145.745 bytes) | ~1.670 → ~1.810 ms |
| 3 | 172,3 KB (176.401 bytes) | ~1.810 → ~1.960 ms |
| 4 | 202,2 KB (207.057 bytes) | ~1.960 → ~2.110 ms |
| 5 | 232,1 KB (237.713 bytes) | ~2.110 → ~2.260 ms |
| 6 | 262,1 KB (268.369 bytes) | ~2.260 → ~2.410 ms |
| 7 | 292,0 KB (299.025 bytes) | ~2.410 → ~2.560 ms |
| 8 | 322,0 KB (329.745 bytes) | ~2.560 → ~2.710 ms |

O pulo vem até 64 bytes depois do tamanho da tabela, e os degraus se repetem a cada 30.656 bytes,
uma janela inteira. O de baixo, que não dá para medir acrescentando bytes, deve ficar perto de
82,5 KB. Os valores absolutos do FCP variam algumas dezenas de ms com a carga da máquina (a parte
de CPU da simulação vem do tempo medido, multiplicado por 4), e uma rodada sozinha às vezes sai ~80
ms acima; a posição dos degraus, que é de rede, não muda.

Só o primeiro degrau importa para a meta: depois dele, o FCP já passa de 1.650 ms. Por isso o
`js-budget.mjs` mostra a folga até o próximo degrau e avisa, sem reprovar, quando ela fica abaixo
de 2 KB; no `scripts/ci-local.sh`, a folga entra no resumo do PR. Com o aviso, antes de somar JS ao
carregamento inicial, carregue algo sob demanda (`lazy`, como o Plágio, o Gerenciar, o Perfil e a
Turma) ou aceite que o FCP vai pular.

Os degraus dependem também do que é baixado junto com o index (o HTML, o CSS e o `theme.js`) e da
configuração do Lighthouse; foram medidos com o CSS de 6,9 KB com gzip. Remeça depois de o CSS ou o
HTML crescerem bastante, de trocar a versão do lhci ou de a página ganhar outro script ou
`modulepreload` inicial, e atualize o `DEGRAUS` do `js-budget.mjs`. O `scripts/fcp-degraus.mjs`
acrescenta um comentário de bytes aleatórios ao index do `dist/` (o tamanho transferido muda, o que
a página executa não), roda o Lighthouse com a configuração da CI a cada tamanho (uma rodada) e,
onde o FCP pula, confirma e refina o pulo até 64 bytes com a mediana de 3 rodadas, como a CI. Até
350 KB, leva perto de uma hora, e a máquina precisa estar livre (a porta 4173 é a mesma do
Lighthouse da CI local):

```bash
npm run build && node scripts/fcp-degraus.mjs
```

Os argumentos opcionais são o início, o fim e o passo da varredura, em KB (`node
scripts/fcp-degraus.mjs 104 150 2`). O `dist/` volta ao original no fim; rode o build de novo se
a medição for interrompida de outro jeito que não o Ctrl+C.

## Estados da verificação (FR-20)

| Resposta | O que a página mostra |
|---|---|
| 200 | Sem violações, lista de violações ou erro de sintaxe com linha e coluna |
| 413 | "O código excede 50 KB" e a explicação da API |
| 422 | "O código não pôde ser verificado" e a explicação da API |
| 429 | "Limite de verificações atingido", com contagem regressiva da espera |
| 503 | "Serviço ocupado" ou "Serviço indisponível", com contagem regressiva da espera |
| Sem resposta em 10 s ou falha de rede | "Sem resposta do servidor" e "Tentar novamente" |

Nos estados 429 e 503, o botão "Tentar novamente" só é liberado quando a espera pedida pelo
servidor termina. Desde a Sprint 13, o limite é de 30 verificações por minuto por conta da
equipe, identificada pelo cookie da sessão (`__Host-ipc_session`, HttpOnly); a página não guarda
nenhum identificador próprio.

## Smoke e2e (Playwright)

Os testes de `e2e/` usam o Chromium contra o compose completo (Caddy, API, analyzer, banco e
Mailpit). O projeto `login` entra com a conta do desenvolvedor; `chromium` roda os testes em
paralelo, inclusive o registro que lê o e-mail no Mailpit; `contas` cria, pelo registro de
verdade, uma conta para cada projeto que mexe na própria conta (S28-04); e, juntos, `conta` troca a
senha e a devolve, `feedback` troca o tratamento (com o lote e o plágio por árvore) e `limite`
esgota o limite por conta, cada um com a sua.

```bash
docker compose -f ../deploy/compose.yaml up --build -d --wait
```

```bash
npx playwright install chromium
```

```bash
npm run e2e
```

A senha vem de `E2E_PASSWORD` ou do `IPC_DEV_INITIAL_PASSWORD` do `deploy/.env`, que só vale para
um banco novo. Se você já trocou a senha da sua conta local, rode o e2e num projeto separado, com
outro `.env` e outras portas, como a CI faz: `E2E_BASE_URL` e `E2E_MAILPIT_URL` apontam para ele.
Os testes também criam contas de teste, que assim não ficam no seu banco.

```bash
docker compose -p ipc-e2e -f ../deploy/compose.yaml --env-file /caminho/e2e.env up --build -d --wait
```

Com `IPC_HTTP_PORT=28180` e `IPC_MAIL_UI_PORT=28125` no `e2e.env`:

```bash
E2E_BASE_URL=http://127.0.0.1:28180 E2E_MAILPIT_URL=http://127.0.0.1:28125 E2E_PASSWORD=... npm run e2e
```

## Estrutura

| Caminho | Papel |
|---|---|
| `src/types/openapi.ts` | Tipos gerados do OpenAPI (não editar) |
| `src/types/api.ts` | Nomes curtos para os tipos do contrato |
| `src/services/client.ts` | Interface `ValidationClient` e `ApiError` |
| `src/services/api.ts` | Cliente HTTP real (mesma origem, `/api/v1/...`) |
| `src/services/mockClient.ts` | Cliente simulado do modo demonstração |
| `src/hooks/useValidateCode.ts` | Envio com tempo limite de 10 s e cancelamento da requisição anterior |
| `src/components/` | Área de código, seletor de lista e painel de resultado |
| `src/pages/` | Inicial, Entrar, Registrar, Confirmar o e-mail, Registrar com o Google, Perfil, Gerenciar, Plágio e o verificador |
| `src/google.ts` | O início da entrada pelo Google e as mensagens das recusas (`/entrar?google=...`) |
| `src/components/RoleBadge.tsx` | Etiquetas de cargo com cor e nome escrito (FR-28) |
| `src/passwordPolicy.ts` | A mesma política de senha do backend, mostrada enquanto se digita |
| `e2e/` | Smoke e2e: verificador, acesso, registro com e-mail, gerenciamento e plágio (com axe), perfil e limite |

## Cenários do modo demonstração

O cliente simulado reconhece `for`/`while`, `try`, `import`, `break`/`continue`, `eval(` e parêntese
não fechado; não é o motor de regras. Para ver os estados de erro, inclua no código um comentário
`# simular: <cenário>`:

| Cenário | Resultado |
|---|---|
| `sobrecarga` | 503, serviço sobrecarregado, nova tentativa em 10 s |
| `limite` | 429, muitas verificações, nova tentativa em 30 s |
| `indisponivel` | 503, analisador indisponível |
| `rede` | Falha de rede |
| `lento` | Resposta em 15 s, que estoura o tempo limite de 10 s |

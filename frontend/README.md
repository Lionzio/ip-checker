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
paralelo, inclusive o registro que lê o e-mail no Mailpit; `conta` troca a senha e a devolve; e
`limite` esgota o limite por conta, por último.

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

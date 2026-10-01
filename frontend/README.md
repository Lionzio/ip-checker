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

## Contrato da API

Os tipos de `src/types/openapi.ts` são gerados do contrato versionado (`docs/openapi.json`) e nunca
editados à mão; `src/types/api.ts` dá nomes curtos a eles. Depois de mudar a API, regenere:

```bash
npm run gen:api
```

A CI falha se o arquivo gerado estiver diferente do OpenAPI. Como os tipos vêm do contrato, uma
mudança na API que a página não acompanhou quebra a compilação.

## Smoke e2e (Playwright)

Os testes de `e2e/` usam o Chromium contra o compose completo (Caddy, API e analyzer):

```bash
docker compose -f ../deploy/compose.yaml up --build -d --wait
```

```bash
npx playwright install chromium
```

```bash
npm run e2e
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
| `e2e/` | Smoke e2e do Marco 1 |

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

# frontend

SPA do IP-Checker: React 19, Vite, TypeScript e Tailwind CSS (blueprint, 5.3). No piloto (2027.1),
é publicada na Vercel.

Até a Sprint 9, a página usa um **cliente simulado** (`src/services/mockClient.ts`), que segue o
contrato da API (5.2.2) sem análise real e mostra o aviso "Modo demonstração". Na Sprint 9 (S9-02),
o cliente HTTP real o substitui, sem mudar os componentes.

## Comandos

```bash
npm install
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
```

## Estrutura

| Caminho | Papel |
|---|---|
| `src/types/api.ts` | Tipos do contrato da API |
| `src/services/client.ts` | Interface `ValidationClient` e `ApiError` |
| `src/services/mockClient.ts` | Cliente simulado do MVP |
| `src/hooks/useValidateCode.ts` | Envio com tempo limite de 10 s e cancelamento da requisição anterior |
| `src/components/` | Área de código, seletor de lista e painel de resultado |

## Cenários do cliente simulado

O cliente simulado reconhece `for`/`while`, `try`, `import`, `break`/`continue`, `eval(` e parêntese
não fechado. Para ver os estados de erro, inclua no código um comentário `# simular: <cenário>`:

| Cenário | Resultado |
|---|---|
| `sobrecarga` | 503, serviço sobrecarregado, nova tentativa em 10 s |
| `limite` | 429, muitas verificações, nova tentativa em 30 s |
| `indisponivel` | 503, analisador indisponível |
| `rede` | Falha de rede |
| `lento` | Resposta em 15 s, que estoura o tempo limite de 10 s |

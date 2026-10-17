# Extensão do Dikastis (Sprint 50)

Uma extensão do Chrome (Manifest V3) que lê as listas e os enunciados de IP no Dikastis, com a
sessão do próprio monitor, e envia ao IP-Checker só o que é novo ou mudou (ADR-15 e ADR-19). O
servidor do IP-Checker nunca fala com o Dikastis.

- **Instalar e usar:** o [guia da equipe](../docs/guia-da-equipe.md), seção "Listas do período e a extensão do Dikastis".
- **Formatos da API do Dikastis:** [docs/api-dikastis.md](docs/api-dikastis.md).

## Desenvolvimento

```bash
npm ci
npm run lint && npm run typecheck
npm run test:coverage
npm run build
```

O `npm run build` gera `dist/`, a pasta carregada em `chrome://extensions` (Modo do desenvolvedor →
Carregar sem compactação).

## Partes

| Pasta | O quê |
|---|---|
| `src/dikastis/` | O adaptador: o único lugar que conhece a API do Dikastis (ritmo de 2/s, formatos) |
| `src/catalogo/` | Descoberta, mapeamento (`26.2L1Q1` → `L1-Q1`) e o hash do enunciado |
| `src/sincronizacao/` | Manifesto, partes de até 100 KB e retomada |
| `src/ipchecker/` | O cliente das rotas `/api/v1/import/*` |
| `src/content/` | O script da página no `dikastis.com.br` (lê o token da sessão; ele não sai dali) |
| `src/background/` | O service worker: mensagens e o selo do modo semi-automático |
| `src/popup/` | O popup, sem framework |

## O ID fixo

O `key` do `manifest.json` é a chave pública que fixa o ID `hbndgmplpohgfbmdemopbbibfocbkdhh`,
o mesmo que a API aceita como origem (`DEFAULT_EXTENSION_ID` em `backend/src/ipc_api/settings.py`;
o teste `test/manifest.test.ts` confere os dois). A chave privada não existe no repositório: a
extensão é carregada sem empacotar. Para trocar o ID, `npm run chave` gera um par novo; ponha o
`key` no manifesto e o `id` no `settings.py` (ou em `IPC_IMPORT_EXTENSION_IDS`).

## O que a extensão guarda

Em `chrome.storage.local`: o endereço do IP-Checker, o token de importação, a escolha do modo
semi-automático, a data da última verificação e o resumo (só contagens). Nunca enunciado, nunca
dado de aluno, nunca o token do Dikastis.

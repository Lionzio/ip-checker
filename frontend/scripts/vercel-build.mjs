/**
 * Build da página para a Vercel (piloto; S11-02). Roda como Build Command do projeto na Vercel:
 *
 *     npm run build:vercel
 *
 * 1. Confere `IPC_API_ORIGIN` (endereço HTTPS da API no Render): sem ela, o build falha.
 * 2. Gera a página com o Vite. A página chama `/api/...` na própria origem (S16-02).
 * 3. Monta `.vercel/output` (Build Output API v3): os arquivos estáticos, o *rewrite* de `/api/*`
 *    para o Render, o middleware que acrescenta o segredo da página (S30-03), os cabeçalhos de
 *    segurança e `version.json`, com o commit do build, que o pipeline usa para saber que o deploy
 *    entrou no ar.
 */
import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import {
  MIDDLEWARE,
  MIDDLEWARE_FUNCTION_CONFIG,
  buildOutputConfig,
  parseApiOrigin,
} from "./vercel-config.mjs";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = `${root}.vercel/output`;

const apiOrigin = parseApiOrigin(process.env.IPC_API_ORIGIN);

await build({ root, logLevel: "warn" });

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(`${root}dist`, `${output}/static`, { recursive: true });
await writeFile(
  `${output}/static/version.json`,
  `${JSON.stringify({ release: process.env.VERCEL_GIT_COMMIT_SHA ?? null })}\n`,
);
// O middleware de /api/* (S30-03), como função de Edge Runtime da Build Output API v3.
const middleware = `${output}/functions/${MIDDLEWARE}.func`;
await mkdir(middleware, { recursive: true });
await cp(`${root}scripts/edge-middleware.mjs`, `${middleware}/index.js`);
await writeFile(
  `${middleware}/.vc-config.json`,
  `${JSON.stringify(MIDDLEWARE_FUNCTION_CONFIG, null, 2)}\n`,
);
await writeFile(`${output}/config.json`, `${JSON.stringify(buildOutputConfig({ apiOrigin }), null, 2)}\n`);

console.log(`Build da Vercel pronto em .vercel/output (API: ${apiOrigin}).`);

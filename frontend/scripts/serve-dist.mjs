// Serve o dist/ com gzip, como a Vercel entrega a página, para o Lighthouse medir em condições de
// produção (S35-02). O servidor estático do Lighthouse CI não comprime, e o JS chegaria ao celular
// simulado com o triplo do tamanho. Uso: node scripts/serve-dist.mjs [porta]
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { gzipSync } from "node:zlib";

const root = join(import.meta.dirname, "..", "dist");
const port = Number(process.argv[2] ?? 4173);
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

createServer(async (request, response) => {
  const path = normalize(decodeURIComponent(new URL(request.url, "http://local").pathname));
  let file = join(root, path);
  if (!file.startsWith(root)) {
    response.writeHead(403).end();
    return;
  }
  let body;
  try {
    body = await readFile(file);
  } catch {
    // Rotas da página (SPA): o index.html, como o rewrite da Vercel.
    file = join(root, "index.html");
    body = await readFile(file);
  }
  const type = TYPES[extname(file)] ?? "application/octet-stream";
  const headers = { "Content-Type": type };
  if (/text|javascript|json|svg/.test(type) && /gzip/.test(request.headers["accept-encoding"] ?? "")) {
    body = gzipSync(body);
    headers["Content-Encoding"] = "gzip";
  }
  response.writeHead(200, headers).end(body);
}).listen(port, "127.0.0.1", () => console.log(`dist pronto em http://127.0.0.1:${port}/`));

// Orçamento do JS inicial (S35-02, NFR-03): o JS que a página baixa para abrir, com gzip, até 350 KB.
//
// Lê o dist/index.html do build de produção, soma o script de entrada e os módulos pré-carregados
// (<link rel="modulepreload">), comprimidos com gzip, e falha acima do limite. De frontend/,
// depois do build: node scripts/js-budget.mjs
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const LIMIT_KB = 350;
const dist = join(import.meta.dirname, "..", "dist");
const html = readFileSync(join(dist, "index.html"), "utf8");

const sources = [
  ...html.matchAll(/<script[^>]+type="module"[^>]+src="([^"]+)"/g),
  ...html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="([^"]+)"/g),
].map((match) => match[1]);
if (sources.length === 0) {
  console.error("js-budget: nenhum script no dist/index.html; rode o build antes");
  process.exit(2);
}

let total = 0;
for (const source of new Set(sources)) {
  const size = gzipSync(readFileSync(join(dist, source.replace(/^\//, "")))).length;
  total += size;
  console.log(`${(size / 1024).toFixed(1).padStart(7)} KB  ${source}`);
}
const kb = total / 1024;
console.log(`JS inicial com gzip: ${kb.toFixed(1)} KB (limite: ${LIMIT_KB} KB, NFR-03)`);
if (kb > LIMIT_KB) {
  console.error(`js-budget: ${kb.toFixed(1)} KB passa do limite de ${LIMIT_KB} KB`);
  process.exit(1);
}

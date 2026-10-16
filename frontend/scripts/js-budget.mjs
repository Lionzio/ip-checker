// Orçamento do JS inicial (S35-02, NFR-03): o JS que a página baixa para abrir, com gzip, até 350 KB.
//
// Lê o dist/index.html do build de produção, soma o script de entrada e os módulos pré-carregados
// (<link rel="modulepreload">), comprimidos com gzip, e falha acima do limite. De frontend/,
// depois do build: node scripts/js-budget.mjs
//
// Também mostra a folga até o próximo degrau do FCP do Lighthouse móvel (S39-01): na simulação de
// rede do Lighthouse, o FCP não cresce de forma contínua com o JS, mas pula ~150 ms (uma ida e volta
// do 4G lento) quando o JS cruza o limite de uma janela do TCP. Com folga abaixo de 2 KB, avisa sem
// reprovar: o próximo acréscimo de JS pode estourar a meta de 1.650 ms (Q-25) de uma vez.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const LIMIT_KB = 350;
const WARN_KB = 2;
// Maior tamanho do JS inicial com gzip, em bytes, medido sem o pulo do FCP antes de cada degrau (o
// pulo vem até 64 bytes depois). Medidos com o scripts/fcp-degraus.mjs em 16/10/2026: lhci 0.15.1,
// preset padrão, CSS de 6,9 KB com gzip. Um a cada 30.656 bytes, ~150 ms cada; o FCP passa da meta
// já no primeiro. Remeça se o HTML, o CSS ou o Lighthouse mudarem muito (frontend/README.md).
const DEGRAUS = [115_089, 145_745, 176_401, 207_057, 237_713, 268_369, 299_025, 329_745];

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

const next = DEGRAUS.find((bytes) => bytes >= total);
if (next === undefined) {
  console.log("Folga até o próximo degrau do FCP: desconhecida (acima do último degrau medido)");
} else {
  const slack = (next - total) / 1024;
  console.log(
    `Folga até o próximo degrau do FCP: ${slack.toFixed(1)} KB (degrau logo acima de ${(next / 1024).toFixed(1)} KB)`,
  );
  if (slack < WARN_KB) {
    const warning =
      `folga de só ${slack.toFixed(1)} KB até o próximo degrau do FCP: mais JS inicial pode somar` +
      " ~150 ms ao Lighthouse móvel; veja frontend/README.md";
    console.log(`AVISO: ${warning}`);
    if (process.env.GITHUB_ACTIONS === "true") console.log(`::warning title=JS inicial (NFR-03)::${warning}`);
  }
}

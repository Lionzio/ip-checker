// Mede os degraus do FCP simulado do Lighthouse móvel em função do tamanho do JS inicial (S39-01).
//
// O Lantern, a simulação de rede do Lighthouse, baixa cada arquivo em idas e voltas inteiras da
// janela de congestionamento do TCP (~150 ms no 4G lento). Por isso o FCP não cresce de forma
// contínua com o JS: fica parado e pula ~150 ms quando o index cruza o limite de uma janela. Este
// script acrescenta um comentário de bytes aleatórios ao index do dist/ (o que muda o tamanho
// transferido sem mudar o que a página executa), roda o Lighthouse com a mesma configuração da CI e
// procura os tamanhos em que o FCP pula. Os degraus medidos vão para o DEGRAUS do js-budget.mjs.
//
// De frontend/, depois do build, com a máquina livre (perto de uma hora até 350 KB; o dist/ volta ao
// original no fim):
//   node scripts/fcp-degraus.mjs [de KB] [até KB] [passo KB]
// Os tamanhos são do JS com gzip, em KB de 1.024 bytes, como no js-budget.mjs. Sem argumentos, vai
// do tamanho atual até o limite de 350 KB, de 4 em 4 KB, e refina cada degrau até 64 bytes.
import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const frontend = join(import.meta.dirname, "..");
const dist = join(frontend, "dist");
const lhciDir = join(frontend, ".lighthouseci");
const html = readFileSync(join(dist, "index.html"), "utf8");
const entry = html.match(/<script[^>]+type="module"[^>]+src="\/([^"]+)"/)?.[1];
if (!entry) {
  console.error("fcp-degraus: nenhum script de entrada no dist/index.html; rode o build antes");
  process.exit(2);
}
const entryPath = join(dist, entry);
const original = readFileSync(entryPath);
const baseSize = gzipSync(original).length;

// Comentário de caracteres base64 pseudoaleatórios (sempre os mesmos), que o gzip quase não comprime.
// SHA-256 de um contador: um gerador congruencial repetiria os bits baixos, e o gzip os comprimiria.
const noise = Array.from({ length: 12_500 }, (_, i) =>
  createHash("sha256").update(`ip-checker ${i}`).digest("base64").slice(0, 40),
).join("");
const padded = (chars) =>
  chars === 0 ? original : Buffer.concat([original, Buffer.from(`\n/*${noise.slice(0, chars)}*/\n`)]);

// O menor comentário que leva o index (com gzip) a pelo menos `target` bytes.
function padTo(target) {
  let low = 0;
  let high = noise.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (gzipSync(padded(middle)).length >= target) high = middle;
    else low = middle + 1;
  }
  const body = padded(low);
  const size = gzipSync(body).length;
  if (size < target) throw new Error(`fcp-degraus: não chegou a ${target} bytes (parou em ${size})`);
  writeFileSync(entryPath, body);
  return size;
}

// O FCP de um tamanho: uma rodada na varredura; a mediana de 3, como na CI, para confirmar e
// refinar um pulo (de vez em quando, uma rodada sozinha sai ~80 ms acima, sem degrau nenhum).
const cache = new Map();
function measure(target, runs = 1) {
  const bytes = padTo(target);
  const key = `${bytes}/${runs}`;
  if (cache.has(key)) return cache.get(key);
  rmSync(lhciDir, { recursive: true, force: true });
  execSync(`npx --yes @lhci/cli@0.15.1 collect --config=lighthouserc.json --numberOfRuns=${runs}`, {
    cwd: frontend,
    stdio: "ignore",
  });
  const lhrs = readdirSync(lhciDir)
    .filter((name) => /^lhr-.*\.json$/.test(name))
    .map((name) => JSON.parse(readFileSync(join(lhciDir, name), "utf8")));
  const fcps = lhrs.map((lhr) => lhr.audits["first-contentful-paint"].numericValue).sort((a, b) => a - b);
  const fcp = Math.round(fcps[Math.floor(fcps.length / 2)]);
  const request = lhrs[0].audits["network-requests"].details.items.find((item) =>
    item.url.endsWith(`/${entry}`),
  );
  const result = { bytes, fcp, transfer: request?.transferSize ?? 0 };
  cache.set(key, result);
  console.log(
    `${(bytes / 1024).toFixed(2).padStart(8)} KB com gzip` +
      ` (${(result.transfer / 1024).toFixed(2)} KB transferidos)  FCP ${fcp} ms` +
      (runs > 1 ? ` (mediana de ${runs})` : ""),
  );
  return result;
}

const kb = (value, fallback) => Math.round(Number(value ?? fallback) * 1024);
const from = kb(process.argv[2], baseSize / 1024);
const to = kb(process.argv[3], 350);
const step = kb(process.argv[4], 4);
const JUMP_MS = 60; // ruído do FCP entre rodadas: poucos ms; um degrau: ~150 ms

process.on("SIGINT", () => {
  writeFileSync(entryPath, original);
  process.exit(130);
});
try {
  const points = [];
  for (let target = from; target <= to; target += step) points.push(measure(target));
  const steps = [];
  for (let i = 1; i < points.length; i++) {
    if (points[i].fcp - points[i - 1].fcp < JUMP_MS) continue;
    let low = measure(points[i - 1].bytes, 3);
    let high = measure(points[i].bytes, 3);
    if (high.fcp - low.fcp < JUMP_MS) continue; // uma rodada fora da curva, não um degrau
    while (high.bytes - low.bytes > 64) {
      const middle = measure(Math.floor((low.bytes + high.bytes) / 2), 3);
      if (middle.fcp - low.fcp < JUMP_MS) low = middle;
      else high = middle;
    }
    steps.push({ low, high });
  }
  console.log("\nDegraus (último tamanho sem o pulo → primeiro com o pulo):");
  for (const { low, high } of steps) {
    console.log(
      `  ${low.bytes} → ${high.bytes} bytes com gzip (${(high.bytes / 1024).toFixed(2)} KB):` +
        ` FCP ${low.fcp} → ${high.fcp} ms`,
    );
  }
} finally {
  writeFileSync(entryPath, original);
}

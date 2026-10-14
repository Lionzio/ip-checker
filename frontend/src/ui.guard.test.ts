import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Guarda dos componentes comuns (S37-03): nenhuma tela escreve um `<button>` nem a classe de um
 * botão por conta própria; todas usam `Button`, `LineChip` e os outros de `components/ui.tsx`.
 * Sem isso, cada cópia das classes some com o foco visível ou com os 44 px do toque de um jeito.
 */
const SRC = join(import.meta.dirname);
const ALLOWED = ["components/ui.tsx"];

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sources(path);
    return entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx") ? [path] : [];
  });
}

describe("guarda dos componentes comuns", () => {
  const files = sources(SRC).map((path) => relative(SRC, path).split(sep).join("/"));

  it("encontra as telas e os componentes", () => {
    expect(files).toContain("pages/Checker.tsx");
    expect(files).toContain("components/ResultPanel.tsx");
  });

  it("nenhum <button> fora de components/ui.tsx", () => {
    const offenders = files.filter((file) => !ALLOWED.includes(file) && /<button\b/.test(readFileSync(join(SRC, file), "utf-8")));

    expect(offenders).toEqual([]);
  });

  it("nenhuma classe de botão copiada (min-h-11 com hover e rounded num mesmo atributo)", () => {
    const copied = /className=["`][^"`]*\bmin-h-11\b[^"`]*\bhover:bg-[^"`]*\brounded/;
    const offenders = files.filter((file) => !ALLOWED.includes(file) && copied.test(readFileSync(join(SRC, file), "utf-8")));

    expect(offenders).toEqual([]);
  });
});

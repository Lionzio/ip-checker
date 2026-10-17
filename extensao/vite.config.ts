import { copyFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

const aqui = import.meta.dirname;

// Duas construções (S50-01): esta gera o popup e o service worker como módulos ES e copia o
// manifest.json; a do vite.content.config.ts gera o script da página como IIFE, porque scripts de
// página não carregam módulos. As duas escrevem em dist/, a pasta carregada no Chrome.
export default defineConfig(({ mode }) => ({
  // O popup.html fica em src/popup/; com a raiz ali, ele sai como dist/popup.html.
  root: mode === "test" ? aqui : resolve(aqui, "src/popup"),
  build: {
    outDir: resolve(aqui, "dist"),
    emptyOutDir: true,
    target: "chrome120",
    modulePreload: false,
    rollupOptions: {
      input: {
        popup: resolve(aqui, "src/popup/popup.html"),
        background: resolve(aqui, "src/background/index.ts"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "partes/[name].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
  plugins: [
    {
      name: "copiar-manifest",
      writeBundle() {
        copyFileSync(resolve(aqui, "manifest.json"), resolve(aqui, "dist/manifest.json"));
      },
    },
  ],
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    // Cobertura (S50-01): 80% no núcleo; o popup e o script da página, que só ligam o núcleo ao
    // navegador, ficam com 60%. Os index.ts do service worker e do script da página só registram
    // os ouvintes do Chrome e ficam de fora (testados à mão na primeira sincronização, 6.3).
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/background/index.ts", "src/content/index.ts", "src/**/*.d.ts"],
      reporter: ["text-summary", "text"],
      thresholds: {
        statements: 80,
        lines: 80,
        functions: 80,
        branches: 75,
        "src/popup/**": { statements: 60, lines: 60, functions: 60, branches: 50 },
        "src/content/**": { statements: 60, lines: 60, functions: 60, branches: 50 },
      },
    },
  },
}));

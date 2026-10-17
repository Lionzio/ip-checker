import { resolve } from "node:path";
import { defineConfig } from "vite";

const aqui = import.meta.dirname;

// O script da página (S50-01): um arquivo só, em IIFE, sem import; roda depois da outra
// construção e não apaga o que ela gerou.
export default defineConfig({
  build: {
    outDir: resolve(aqui, "dist"),
    emptyOutDir: false,
    target: "chrome120",
    lib: {
      entry: resolve(aqui, "src/content/index.ts"),
      formats: ["iife"],
      name: "ipcCheckerDikastis",
      fileName: () => "content.js",
    },
  },
});

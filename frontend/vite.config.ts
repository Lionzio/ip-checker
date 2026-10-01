import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Portas próprias do IP-Checker (ver README da raiz): a 5173, padrão do Vite, é do DidacticGen.
// strictPort faz o servidor falhar em vez de pular para outra porta em uso.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5180, strictPort: true },
  preview: { port: 5181, strictPort: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Portas próprias do IP-Checker (ver README da raiz): a 5173, padrão do Vite, é do DidacticGen.
// strictPort faz o servidor falhar em vez de pular para outra porta em uso.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5180,
    strictPort: true,
    // Mesma origem também no desenvolvimento: /api vai para o compose (Caddy na 8180) ou, com
    // IPC_API_URL=http://127.0.0.1:8101, para a API rodando fora do Docker. O Host original
    // (localhost:5180) segue até a API, que só aceita POST cujo Origin é o próprio Host (CSRF,
    // S13-02); o atalho de string do Vite trocaria o Host pelo do destino.
    proxy: {
      "/api": { target: process.env.IPC_API_URL ?? "http://127.0.0.1:8180", changeOrigin: false },
    },
  },
  preview: { port: 5181, strictPort: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Os testes ponta a ponta (e2e/) rodam com o Playwright, contra o compose.
    include: ["src/**/*.test.{ts,tsx}", "scripts/**/*.test.mjs"],
  },
});

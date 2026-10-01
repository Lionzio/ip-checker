import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";
import { createApiClient } from "./services/api";
import { createMockClient } from "./services/mockClient";

const root = document.getElementById("root");
if (root === null) throw new Error("elemento #root não encontrado");

// A página fala com a API real. O modo demonstração (respostas simuladas, para mostrar os estados
// de erro) só existe num build feito com VITE_DEMO_MODE=1.
const demoMode = import.meta.env.VITE_DEMO_MODE === "1";
// Nas Fases 0 e 2 a API está na mesma origem (Caddy). No piloto, a página está na Vercel e a API
// no Render: o build da Vercel define VITE_API_BASE_URL (scripts/vercel-build.mjs).
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

createRoot(root).render(
  <StrictMode>
    <App client={demoMode ? createMockClient() : createApiClient({ baseUrl: apiBaseUrl })} demoMode={demoMode} />
  </StrictMode>,
);

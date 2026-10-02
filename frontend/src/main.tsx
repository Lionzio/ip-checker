import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import "./index.css";
import { createApiClient } from "./services/api";
import { createMockClient } from "./services/mockClient";

const root = document.getElementById("root");
if (root === null) throw new Error("elemento #root não encontrado");

// A página fala com a API real. O modo demonstração (respostas simuladas, para mostrar os estados
// de erro) só existe num build feito com VITE_DEMO_MODE=1.
const demoMode = import.meta.env.VITE_DEMO_MODE === "1";
// A API está sempre na mesma origem da página: o Caddy nas Fases 0 e 2 e, no piloto, o rewrite
// de /api/* da Vercel para o Render (S16-02). O cookie da sessão só funciona assim (ADR-04).

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <App client={demoMode ? createMockClient() : createApiClient()} demoMode={demoMode} />
    </BrowserRouter>
  </StrictMode>,
);

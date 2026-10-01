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

createRoot(root).render(
  <StrictMode>
    <App client={demoMode ? createMockClient() : createApiClient()} demoMode={demoMode} />
  </StrictMode>,
);

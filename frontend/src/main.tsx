import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";
import { createMockClient } from "./services/mockClient";

const root = document.getElementById("root");
if (root === null) throw new Error("elemento #root não encontrado");

// O cliente HTTP real substitui o simulado na Sprint 9 (S9-02).
createRoot(root).render(
  <StrictMode>
    <App client={createMockClient()} demoMode />
  </StrictMode>,
);

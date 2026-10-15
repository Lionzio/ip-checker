import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

// A espera padrão de 1 s dos findBy estourava com a máquina carregada, na CI local, sem nenhum
// defeito no código (Sprint 37): 3 s dão folga sem esconder uma tela que não aparece.
configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  // O rascunho fica na aba (S37-05): um teste não herda o código do anterior. Os testes dos
  // scripts rodam sem navegador (ambiente node), sem sessionStorage.
  if (typeof window !== "undefined") window.sessionStorage.clear();
});

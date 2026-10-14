import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // O rascunho fica na aba (S37-05): um teste não herda o código do anterior. Os testes dos
  // scripts rodam sem navegador (ambiente node), sem sessionStorage.
  if (typeof window !== "undefined") window.sessionStorage.clear();
});

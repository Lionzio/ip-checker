import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { createMockClient } from "../services/mockClient";

/** A tela inicial sem sessão (FR-22; os três blocos desde a S37-04). */
describe("Tela inicial", () => {
  it("explica Verificar, Plágio e Feedback em três blocos, com Entrar e Registrar", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App client={createMockClient({ latencyMs: 0 })} />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Acesso restrito à equipe da disciplina" })).toBeInTheDocument();
    const features = within(screen.getByRole("list", { name: "O que o IP-Checker faz" }));
    expect(features.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent)).toEqual(["Verificar", "Plágio", "Feedback"]);
    expect(features.getByText(/não é executado nem guardado/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/entrar");
    expect(screen.getByRole("link", { name: "Registrar" })).toHaveAttribute("href", "/registrar");
    expect(screen.queryByLabelText("Código Python")).not.toBeInTheDocument();
  });
});

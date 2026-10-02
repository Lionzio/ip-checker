import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { createMockClient } from "../services/mockClient";

function renderAt(path: string, signedIn = false) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={createMockClient({ latencyMs: 0, signedIn, google: true })} />
    </MemoryRouter>,
  );
  return user;
}

describe("Aviso de privacidade (S19-02, Q-19 d)", () => {
  it("abre sem login, pelo rodapé", async () => {
    const user = renderAt("/");

    await user.click(await screen.findByRole("link", { name: "Aviso de privacidade" }));

    expect(await screen.findByRole("heading", { name: "Aviso de privacidade" })).toBeInTheDocument();
    expect(screen.getByText(/não vai para o banco, para o disco nem para os logs/)).toBeInTheDocument();
    expect(screen.getByText(/O nome do aluno é trocado por \[ALUNO\]/)).toBeInTheDocument();
    // Telemetria (S21-01): anônima, agregada e apagada em 12 meses.
    expect(screen.getByText(/não guarda o código, a conta, o nome de ninguém nem\s+o IP/)).toBeInTheDocument();
    expect(screen.getByText(/apagados depois de 12 meses/)).toBeInTheDocument();
  });

  it("também abre com sessão", async () => {
    renderAt("/privacidade", true);

    expect(await screen.findByRole("heading", { name: "Aviso de privacidade" })).toBeInTheDocument();
  });

  it("aparece resumido no registro, com o link", async () => {
    renderAt("/registrar");

    const link = await screen.findByRole("link", { name: "aviso de privacidade" });
    expect(link).toHaveAttribute("href", "/privacidade");
    expect(link.closest("p")).toHaveTextContent("O tratamento só você vê.");
  });

  it("aparece resumido no registro pelo Google", async () => {
    renderAt("/google/concluir");

    expect(await screen.findByRole("link", { name: "aviso de privacidade" })).toHaveAttribute(
      "href",
      "/privacidade",
    );
  });
});

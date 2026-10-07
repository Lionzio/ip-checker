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
    expect(screen.getByText(/o nome do aluno é trocado\s+por \[ALUNO\]/)).toBeInTheDocument();
    // S25-05 e Q-19 d: dados pessoais mascarados antes da IA e contas paradas apagadas.
    expect(screen.getByText(/e-mails, CPFs e números com 8 ou mais dígitos/)).toBeInTheDocument();
    expect(screen.getByText(/365 dias sem nenhuma atividade é apagada/)).toBeInTheDocument();
    // Telemetria (S21-01): anônima, agregada e apagada em 12 meses.
    expect(screen.getByText(/não guarda o código, a conta, o nome de ninguém nem\s+o IP/)).toBeInTheDocument();
    expect(screen.getByText(/apagados depois de 12 meses/)).toBeInTheDocument();
    // S28-02 e S28-03: adoção por lista, só em porcentagem, e o backup criptografado.
    expect(screen.getByText(/só a porcentagem da equipe que\s+usou cada lista, nunca quem/)).toBeInTheDocument();
    expect(screen.getByText(/criptografada, e guardada por 90 dias/)).toBeInTheDocument();
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

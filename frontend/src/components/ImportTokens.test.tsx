import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ApiError } from "../services/client";
import { createMockClient, DEMO_ACCOUNT, DEMO_MANAGER } from "../services/mockClient";

/** O token de importação no Perfil (S50-04): só a chefia; o valor aparece uma vez. */

function renderProfile(client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/perfil"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return { user, client };
}

describe("Token de importação (S50-04)", () => {
  it("a chefia cria um token, vê o valor uma vez e o revoga", async () => {
    const { user } = renderProfile();

    await user.type(await screen.findByLabelText("Onde vai ficar"), "Chrome do notebook");
    await user.click(screen.getByRole("button", { name: "Criar token" }));

    const shown = await screen.findByText(/^ipc_imp_simulado/);
    expect(screen.getByText("Copie agora: o token não será mostrado de novo.")).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Seus tokens de importação" });
    expect(within(list).getByText("Chrome do notebook")).toBeInTheDocument();
    expect(within(list).getByText(/nunca usado/)).toBeInTheDocument();
    expect(list).not.toHaveTextContent(shown.textContent ?? "");

    await user.click(within(list).getByRole("button", { name: "Revogar" }));

    expect(await screen.findByText("Token “Chrome do notebook” revogado.")).toBeInTheDocument();
    expect(screen.queryByText(/^ipc_imp_simulado/)).not.toBeInTheDocument();
    expect(within(list).getByText(/revogado em/)).toBeInTheDocument();
  });

  it("copia o token para a área de transferência", async () => {
    const { user } = renderProfile();
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    await user.type(await screen.findByLabelText("Onde vai ficar"), "Edge");
    await user.click(screen.getByRole("button", { name: "Criar token" }));
    await user.click(await screen.findByRole("button", { name: "Copiar" }));

    expect(writeText).toHaveBeenCalledWith(expect.stringMatching(/^ipc_imp_/));
    expect(await screen.findByText("Token copiado. Cole no popup da extensão.")).toBeInTheDocument();
  });

  it("sem área de transferência, pede para copiar à mão", async () => {
    const { user } = renderProfile();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new Error("negado")) },
      configurable: true,
    });

    await user.type(await screen.findByLabelText("Onde vai ficar"), "Edge");
    await user.click(screen.getByRole("button", { name: "Criar token" }));
    await user.click(await screen.findByRole("button", { name: "Copiar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("copie à mão");
  });

  it("com 3 ativos, o botão fica desligado", async () => {
    const { user } = renderProfile();
    for (const label of ["A", "B", "C"]) {
      await user.type(await screen.findByLabelText("Onde vai ficar"), label);
      await user.click(screen.getByRole("button", { name: "Criar token" }));
      await screen.findByText(label);
    }

    await user.type(screen.getByLabelText("Onde vai ficar"), "D");

    expect(screen.getByRole("button", { name: "Criar token" })).toBeDisabled();
  });

  it("a recusa do servidor aparece", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
    client.createImportToken = () => Promise.reject(new ApiError(422, "INVALID_INPUT", "Você já tem 3 tokens ativos."));
    const { user } = renderProfile(client);

    await user.type(await screen.findByLabelText("Onde vai ficar"), "X");
    await user.click(screen.getByRole("button", { name: "Criar token" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Você já tem 3 tokens ativos.");
  });

  it("uma falha ao listar aparece", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
    client.listImportTokens = () => Promise.reject(new ApiError(503, "DATABASE_UNAVAILABLE", "O banco não respondeu."));
    renderProfile(client);

    expect(await screen.findByRole("alert")).toHaveTextContent("O banco não respondeu.");
  });

  it("uma monitora não vê a seção", async () => {
    renderProfile(createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_ACCOUNT }));

    await screen.findByRole("heading", { name: "Aparência" });

    expect(screen.queryByRole("heading", { name: "Token de importação" })).not.toBeInTheDocument();
  });
});

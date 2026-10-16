import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";

/**
 * Os caminhos de erro do Perfil (S39-03). O fluxo feliz, a troca de senha e a senha atual errada
 * estão no `App.test.tsx`.
 */

const expired = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre de novo."));

function renderProfile(client = createMockClient({ latencyMs: 0, signedIn: true })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/perfil"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

describe("Perfil: erros (S39-03)", () => {
  it("mostra a recusa do servidor ao salvar e mantém o que foi digitado", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.updateProfile = () => Promise.reject(new ApiError(409, "NAME_TAKEN", "Esse nome já está em uso na equipe."));
    const user = renderProfile(client);

    const name = await screen.findByLabelText("Nome");
    await user.clear(name);
    await user.type(name, "Nome Repetido");
    await user.click(screen.getByRole("button", { name: "Salvar perfil" }));

    expect(await screen.findByText("Esse nome já está em uso na equipe.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toHaveValue("Nome Repetido");
    expect(screen.queryByText("Perfil salvo.")).not.toBeInTheDocument();
  });

  it("leva para Entrar quando a sessão venceu ao salvar o perfil", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.updateProfile = expired;
    const user = renderProfile(client);

    await user.click(await screen.findByRole("button", { name: "Salvar perfil" }));

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("leva para Entrar quando a sessão venceu ao trocar a senha", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.changePassword = expired;
    const user = renderProfile(client);

    await user.type(await screen.findByLabelText("Senha atual"), "Senha-antiga-1");
    await user.type(screen.getByLabelText("Nova senha"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a nova senha"), "Senha-nova-2!");
    await user.click(screen.getByRole("button", { name: "Alterar a senha" }));

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });
});

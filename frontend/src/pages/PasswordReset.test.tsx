import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";

function renderAt(path: string, client = createMockClient({ latencyMs: 0 })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return { user, client };
}

describe("Esqueci minha senha (S24-04, Q-19 b)", () => {
  it("Entrar leva ao pedido do link", async () => {
    const { user } = renderAt("/entrar");

    await user.click(await screen.findByRole("link", { name: "Esqueci minha senha" }));

    expect(await screen.findByRole("heading", { name: "Esqueci minha senha" })).toBeInTheDocument();
  });

  it("pede o link e responde sem revelar se a conta existe", async () => {
    const { user, client } = renderAt("/esqueci-senha");
    const forgot = vi.spyOn(client, "forgotPassword");

    await user.type(await screen.findByLabelText("E-mail institucional"), " ana@cin.ufpe.br ");
    await user.click(screen.getByRole("button", { name: "Enviar o link" }));

    expect(forgot).toHaveBeenCalledWith("ana@cin.ufpe.br");
    expect(await screen.findByRole("status")).toHaveTextContent("Se houver uma conta com ana@cin.ufpe.br");
  });

  it("define a senha nova só com as duas senhas iguais e fortes", async () => {
    const { user, client } = renderAt("/redefinir-senha?token=abc");
    const reset = vi.spyOn(client, "resetPassword");
    const button = await screen.findByRole("button", { name: "Definir a senha nova" });

    await user.type(screen.getByLabelText("Senha nova"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a senha nova"), "Senha-nova-3!");
    expect(screen.getByText("As duas senhas não são iguais.")).toBeInTheDocument();
    expect(button).toBeDisabled();

    await user.clear(screen.getByLabelText("Repita a senha nova"));
    await user.type(screen.getByLabelText("Repita a senha nova"), "Senha-nova-2!");
    await user.click(button);

    expect(reset).toHaveBeenCalledWith("abc", "Senha-nova-2!");
    expect(await screen.findByRole("status")).toHaveTextContent("Senha nova definida.");
    expect(screen.getByRole("link", { name: "entre com a senha nova" })).toHaveAttribute("href", "/entrar");
  });

  it("mostra a recusa de um link vencido e oferece outro", async () => {
    const client = createMockClient({ latencyMs: 0 });
    client.resetPassword = () =>
      Promise.reject(
        new ApiError(422, "INVALID_TOKEN", "O link de redefinição é inválido, já foi usado ou venceu. Peça um novo."),
      );
    const { user } = renderAt("/redefinir-senha?token=velho", client);

    await user.type(await screen.findByLabelText("Senha nova"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a senha nova"), "Senha-nova-2!");
    await user.click(screen.getByRole("button", { name: "Definir a senha nova" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("já foi usado ou venceu");
    expect(screen.getByRole("link", { name: "Pedir outro link" })).toHaveAttribute("href", "/esqueci-senha");
  });

  it("avisa quando o endereço não traz o código do link", async () => {
    renderAt("/redefinir-senha");

    expect(await screen.findByRole("alert")).toHaveTextContent("não traz o código do link");
  });
});

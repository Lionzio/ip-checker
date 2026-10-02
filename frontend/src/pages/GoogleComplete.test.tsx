import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { type ApiClient, ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";

function renderAt(client: ApiClient, path: string) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

describe("Entrada pelo Google (S16-01, FR-24)", () => {
  it("mostra Entrar com o Google quando o servidor tem o Google configurado", async () => {
    renderAt(createMockClient({ latencyMs: 0, google: true }), "/entrar");

    expect(await screen.findByRole("link", { name: /Entrar com o Google/ })).toHaveAttribute(
      "href",
      "/api/v1/auth/google/start",
    );
  });

  it("esconde o Google quando ele não está configurado", async () => {
    renderAt(createMockClient({ latencyMs: 0 }), "/entrar");

    expect(await screen.findByLabelText("Nome ou e-mail institucional")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Google/ })).not.toBeInTheDocument();
  });

  it("esconde o Google quando as opções não respondem", async () => {
    const client = createMockClient({ latencyMs: 0, google: true });
    client.options = () => Promise.reject(new TypeError("Failed to fetch"));
    renderAt(client, "/registrar");

    expect(await screen.findByRole("heading", { name: "Registrar" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Google/ })).not.toBeInTheDocument();
  });

  it("oferece Registrar com o Google na tela de registro", async () => {
    renderAt(createMockClient({ latencyMs: 0, google: true }), "/registrar");

    expect(await screen.findByRole("link", { name: /Registrar com o Google/ })).toBeInTheDocument();
  });

  it.each([
    ["dominio", "Só e-mails @cin.ufpe.br e @ufpe.br têm acesso"],
    ["email_nao_verificado", "O Google não confirmou este e-mail"],
    ["estado", "expirou ou foi aberta em outra aba"],
    ["ACCOUNT_PENDING_APPROVAL", "aguardando a aprovação"],
    ["ACCOUNT_REMOVED", "removida da equipe"],
    ["qualquer-coisa", "Não foi possível entrar pelo Google"],
  ])("explica a recusa %s na volta do Google", async (reason, text) => {
    renderAt(createMockClient({ latencyMs: 0, google: true }), `/entrar?google=${reason}`);

    expect(await screen.findByRole("alert")).toHaveTextContent(text);
  });

  it("completa o cadastro pelo Google com o nome sugerido e vai para a aprovação", async () => {
    const client = createMockClient({ latencyMs: 0, google: true });
    const sent: unknown[] = [];
    client.completeGoogle = (request) => {
      sent.push(request);
      return Promise.resolve("demonstracao.google@cin.ufpe.br");
    };
    const user = renderAt(client, "/google/concluir");

    expect(await screen.findByText("demonstracao.google@cin.ufpe.br")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome", { exact: true })).toHaveValue("Pessoa do Google");
    expect(screen.queryByLabelText(/Senha/)).not.toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Enviar cadastro" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Curso"), "Sistemas de Informação");
    await user.click(screen.getByLabelText(/Neutro/));
    await user.click(button);

    expect(await screen.findByRole("status")).toHaveTextContent("aguarda a aprovação");
    expect(sent).toEqual([{ name: "Pessoa do Google", course: "Sistemas de Informação", treatment: "neutro" }]);
  });

  it("mostra a recusa do formulário e deixa corrigir", async () => {
    const client = createMockClient({ latencyMs: 0, google: true });
    client.completeGoogle = () =>
      Promise.reject(new ApiError(409, "NAME_TAKEN", "Este nome já é usado por outra conta; ele serve para entrar."));
    const user = renderAt(client, "/google/concluir");

    await user.type(await screen.findByLabelText("Curso"), "CC");
    await user.click(screen.getByLabelText(/Feminino/));
    await user.click(screen.getByRole("button", { name: "Enviar cadastro" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Este nome já é usado");
    expect(screen.getByRole("button", { name: "Enviar cadastro" })).toBeEnabled();
  });

  it("avisa quando o cadastro pelo Google venceu", async () => {
    renderAt(createMockClient({ latencyMs: 0 }), "/google/concluir");

    expect(await screen.findByRole("alert")).toHaveTextContent("expirou");
    expect(screen.getByRole("link", { name: "Ir para Entrar" })).toHaveAttribute("href", "/entrar");
  });
});

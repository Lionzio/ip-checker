import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { type ApiClient, ApiError } from "./services/client";
import { createMockClient, DEMO_ACCOUNT } from "./services/mockClient";

function renderApp(client: ApiClient, path = "/", demoMode = true) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} demoMode={demoMode} />
    </MemoryRouter>,
  );
  return user;
}

async function setup() {
  const user = renderApp(createMockClient({ latencyMs: 0, signedIn: true }));
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  return user;
}

describe("App sem sessão (FR-22)", () => {
  it("mostra só Registrar e Entrar", async () => {
    renderApp(createMockClient({ latencyMs: 0 }));

    expect(await screen.findByRole("link", { name: "Registrar" })).toHaveAttribute("href", "/registrar");
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/entrar");
    expect(screen.queryByLabelText("Código Python")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sair" })).not.toBeInTheDocument();
  });

  it("entra com nome ou e-mail e senha e chega ao painel", async () => {
    const user = renderApp(createMockClient({ latencyMs: 0 }), "/entrar");

    await user.type(await screen.findByLabelText("Nome ou e-mail institucional"), "demo@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByLabelText("Código Python")).toBeInTheDocument();
    expect(screen.getByText(DEMO_ACCOUNT.name)).toBeInTheDocument();
    expect(screen.getByText(/· Monitor/)).toBeInTheDocument();
  });

  it("mostra a mensagem da API quando a entrada é recusada", async () => {
    const client = createMockClient({ latencyMs: 0 });
    client.login = () =>
      Promise.reject(new ApiError(401, "INVALID_CREDENTIALS", "Nome, e-mail ou senha incorretos."));
    const user = renderApp(client, "/entrar");

    await user.type(await screen.findByLabelText("Nome ou e-mail institucional"), "x@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Nome, e-mail ou senha incorretos.");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
  });

  it("mostra a espera depois de muitas tentativas", async () => {
    const client = createMockClient({ latencyMs: 0 });
    client.login = () =>
      Promise.reject(new ApiError(429, "RATE_LIMITED", "Muitas tentativas de entrada.", 600));
    const user = renderApp(client, "/entrar");

    await user.type(await screen.findByLabelText("Nome ou e-mail institucional"), "x@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Tente de novo em 600 s.");
  });

  it("explica que o cadastro ainda não abriu", async () => {
    renderApp(createMockClient({ latencyMs: 0 }), "/registrar");

    expect(await screen.findByRole("heading", { name: "Registrar" })).toBeInTheDocument();
    expect(screen.getByText(/ainda não está disponível/)).toBeInTheDocument();
  });

  it("leva qualquer outro endereço para o início", async () => {
    renderApp(createMockClient({ latencyMs: 0 }), "/qualquer");

    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();
  });

  it("oferece nova tentativa quando o servidor não responde", async () => {
    const client = createMockClient({ latencyMs: 0 });
    let calls = 0;
    const me = client.me.bind(client);
    client.me = (signal) => {
      calls += 1;
      return calls === 1 ? Promise.reject(new TypeError("Failed to fetch")) : me(signal);
    };
    const user = renderApp(client);

    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();
  });
});

describe("App com sessão", () => {
  it("avisa antes da verificação que as regras de questão ainda não valem", async () => {
    await setup();

    expect(
      screen.getByText(/As regras específicas de cada questão\s+ainda não são consideradas/),
    ).toBeInTheDocument();
  });

  it("avisa que as respostas são simuladas", async () => {
    await setup();

    expect(screen.getByRole("note")).toHaveTextContent("Modo demonstração");
  });

  it("só habilita Verificar com lista escolhida e código preenchido", async () => {
    const user = await setup();
    const button = screen.getByRole("button", { name: "Verificar" });

    expect(button).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    expect(button).toBeDisabled();
    await user.click(screen.getByLabelText("Código Python"));
    await user.paste("x = 1");
    expect(button).toBeEnabled();
  });

  it("verifica o código e mostra a violação na linha certa", async () => {
    const user = await setup();

    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(screen.getByLabelText("Código Python"));
    await user.paste("x = 3\nfor i in x:\n    print(i)\n");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByText("Fora da lista")).toBeInTheDocument();
    expect(screen.getByText("Linha 2, coluna 1")).toBeInTheDocument();
  });

  it("numera as linhas do código", async () => {
    const user = await setup();

    await user.click(screen.getByLabelText("Código Python"));
    await user.paste("a = 1\nb = 2\nc = 3");

    expect(screen.getByTestId("line-numbers").textContent).toBe("1\n2\n3");
  });

  it("sai e volta para a tela inicial", async () => {
    const user = await setup();

    await user.click(screen.getByRole("button", { name: "Sair" }));

    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Código Python")).not.toBeInTheDocument();
  });

  it("volta para a tela inicial com aviso quando a sessão termina durante o uso", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.validate = () =>
      Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre com a sua conta da equipe."));
    const user = renderApp(client);
    await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });

    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(screen.getByLabelText("Código Python"));
    await user.paste("x = 1");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("status")).toHaveTextContent("A sua sessão terminou.");
    expect(screen.getByRole("link", { name: "Entrar" })).toBeInTheDocument();
  });

  it("também volta quando as listas respondem 401", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.listLists = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre."));
    renderApp(client);

    expect(await screen.findByRole("status")).toHaveTextContent("A sua sessão terminou.");
  });

  it("vai para o painel quem abre /entrar já logado", async () => {
    renderApp(createMockClient({ latencyMs: 0, signedIn: true }), "/entrar");

    expect(await screen.findByLabelText("Código Python")).toBeInTheDocument();
  });

  it("sem o modo demonstração, não mostra o aviso de respostas simuladas", async () => {
    renderApp(createMockClient({ latencyMs: 0, signedIn: true }), "/", false);
    await screen.findByLabelText("Código Python");

    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});

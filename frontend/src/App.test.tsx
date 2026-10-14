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
    expect(screen.queryByRole("button", { name: /Menu da conta/ })).not.toBeInTheDocument();
  });

  it("entra com nome ou e-mail e senha e chega ao painel", async () => {
    const user = renderApp(createMockClient({ latencyMs: 0 }), "/entrar");

    await user.type(await screen.findByLabelText("Nome ou e-mail institucional"), "demo@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByLabelText("Código Python")).toBeInTheDocument();
    // O nome completo e o cargo ficam no menu da conta, aberto pelo primeiro nome (S37-04).
    expect(screen.getByRole("button", { name: `Menu da conta: ${DEMO_ACCOUNT.name}` })).toHaveTextContent("Monitora");
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

  it("registra com e-mail institucional e pede a confirmação do e-mail (FR-23)", async () => {
    const client = createMockClient({ latencyMs: 0 });
    const sent: unknown[] = [];
    const register = client.register.bind(client);
    client.register = (request) => {
      sent.push(request);
      return register(request);
    };
    const user = renderApp(client, "/registrar");

    await user.type(await screen.findByLabelText("Nome"), "Ana Lima");
    await user.type(screen.getByLabelText("E-mail institucional"), "Ana@CIN.ufpe.br");
    const button = screen.getByRole("button", { name: "Registrar" });
    await user.type(screen.getByLabelText("Senha"), "fraca");
    expect(screen.getByText(/Pelo menos 9 caracteres/)).toHaveTextContent("(falta)");
    expect(button).toBeDisabled();
    await user.clear(screen.getByLabelText("Senha"));
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    expect(screen.getByText(/Pelo menos 9 caracteres/)).toHaveTextContent("(atendido)");
    await user.type(screen.getByLabelText("Curso"), "Ciência da Computação");
    await user.click(screen.getByLabelText(/Feminino/));
    await user.click(button);

    expect(await screen.findByRole("heading", { name: "Confirme o seu e-mail" })).toBeInTheDocument();
    expect(screen.getByText("ana@cin.ufpe.br")).toBeInTheDocument();
    expect(sent).toEqual([
      {
        name: "Ana Lima",
        email: "Ana@CIN.ufpe.br",
        password: "Senha-forte-1",
        course: "Ciência da Computação",
        treatment: "feminino",
      },
    ]);
    await user.click(screen.getByRole("button", { name: "Não recebi: enviar de novo" }));
    expect(await screen.findByRole("status")).toHaveTextContent("enviamos um novo link");
  });

  it("mostra a recusa do registro", async () => {
    const client = createMockClient({ latencyMs: 0 });
    client.register = () =>
      Promise.reject(new ApiError(409, "NAME_TAKEN", "Este nome já é usado por outra conta; ele serve para entrar."));
    const user = renderApp(client, "/registrar");

    await user.type(await screen.findByLabelText("Nome"), "Ana");
    await user.type(screen.getByLabelText("E-mail institucional"), "ana@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    await user.type(screen.getByLabelText("Curso"), "CC");
    await user.click(screen.getByLabelText(/Neutro/));
    await user.click(screen.getByRole("button", { name: "Registrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Este nome já é usado");
  });

  it("confirma o e-mail só pelo botão, nunca ao abrir o link (ameaça 21)", async () => {
    const client = createMockClient({ latencyMs: 0 });
    const tokens: string[] = [];
    client.verifyEmail = (token) => {
      tokens.push(token);
      return Promise.resolve();
    };
    const user = renderApp(client, "/verificar?token=abc");

    const button = await screen.findByRole("button", { name: "Confirmar meu e-mail" });
    expect(tokens).toEqual([]);
    await user.click(button);

    expect(await screen.findByRole("status")).toHaveTextContent("E-mail confirmado");
    expect(tokens).toEqual(["abc"]);
  });

  it("avisa quando o link não traz o código", async () => {
    renderApp(createMockClient({ latencyMs: 0 }), "/verificar");

    expect(await screen.findByRole("alert")).toHaveTextContent("não traz o código de verificação");
  });

  it("mostra quando o link venceu", async () => {
    const client = createMockClient({ latencyMs: 0 });
    client.verifyEmail = () =>
      Promise.reject(new ApiError(422, "INVALID_TOKEN", "O link de verificação é inválido, já foi usado ou venceu. Peça um novo."));
    const user = renderApp(client, "/verificar?token=velho");

    await user.click(await screen.findByRole("button", { name: "Confirmar meu e-mail" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("já foi usado ou venceu");
  });

  it("leva para Entrar quem abre o perfil sem sessão", async () => {
    renderApp(createMockClient({ latencyMs: 0 }), "/perfil");

    expect(await screen.findByLabelText("Nome ou e-mail institucional")).toBeInTheDocument();
  });

  it("mostra os créditos com GitHub e LinkedIn", async () => {
    renderApp(createMockClient({ latencyMs: 0 }));

    expect(await screen.findByText(/Desenvolvido por Vinícius Leôncio \(Lionzio\)/)).toHaveTextContent(
      "Desenvolvido por Vinícius Leôncio (Lionzio) para a disciplina de Introdução a Programação (IP).",
    );
    expect(screen.getByRole("link", { name: "GitHub" })).toHaveAttribute("href", "https://github.com/Lionzio");
    const linkedin = screen.getByRole("link", { name: "LinkedIn" });
    expect(linkedin).toHaveAttribute("href", "https://www.linkedin.com/in/vin%C3%ADcius-le%C3%B4ncio-3226a9366/");
    expect(linkedin).toHaveAttribute("rel", "noopener noreferrer");
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
  it("escolhe a questão depois da lista e aplica as regras dela (R-01)", async () => {
    const user = await setup();
    const question = screen.getByRole("combobox", { name: "Questão" });

    expect(question).toBeDisabled();
    expect(question).toHaveDisplayValue("Escolha a lista primeiro");
    expect(screen.getByText(/Sem questão, valem só as permissões da lista/)).toBeInTheDocument();

    // A Lista 1 não tem questões cadastradas; a 3 tem uma, na demonstração.
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    expect(question).toHaveDisplayValue("Nenhuma questão nesta lista");
    await user.selectOptions(screen.getByLabelText("Lista"), "3");
    await user.selectOptions(question, "L3-Q1");
    expect(screen.getByText(/regras da questão L3-Q1/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Código Python"), "v = [[1]{enter}print(v)");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByText(/questão L3-Q1/, { selector: "p.text-xs" })).toBeInTheDocument();
    // Trocar de lista volta para "sem questão".
    await user.selectOptions(screen.getByLabelText("Lista"), "2");
    expect(question).toHaveDisplayValue("Nenhuma questão nesta lista");
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

    const gutter = screen.getByTestId("line-numbers");
    expect([...gutter.children].map((line) => line.textContent)).toEqual(["1", "2", "3"]);
  });

  it("sai e volta para a tela inicial", async () => {
    const user = await setup();

    await user.click(screen.getByRole("button", { name: /Menu da conta/ }));
    await user.click(screen.getByRole("menuitem", { name: "Sair" }));

    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Código Python")).not.toBeInTheDocument();
  });

  it("vai para Entrar com aviso quando a sessão termina durante o uso (S26-04)", async () => {
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
    // A sessão acaba na hora; a ida para Entrar é uma transição do roteador e pode chegar um
    // instante depois do aviso (o teste falhava conforme a ordem e a carga da máquina).
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Código Python")).not.toBeInTheDocument();
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

  it("edita o perfil e mostra o nome novo no cabeçalho (FR-26)", async () => {
    const user = renderApp(createMockClient({ latencyMs: 0, signedIn: true }), "/perfil");

    const name = await screen.findByLabelText("Nome");
    expect(name).toHaveValue(DEMO_ACCOUNT.name);
    await user.clear(name);
    await user.type(name, "Monitora Renomeada");
    await user.click(screen.getByLabelText(/Neutro/));
    await user.click(screen.getByRole("button", { name: "Salvar perfil" }));

    expect(await screen.findByText("Perfil salvo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menu da conta: Monitora Renomeada" })).toBeInTheDocument();
  });

  it("troca a senha com a atual e a nova repetida", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const calls: [string | null, string][] = [];
    client.changePassword = (current, next) => {
      calls.push([current, next]);
      return Promise.resolve();
    };
    const user = renderApp(client, "/perfil");

    await user.type(await screen.findByLabelText("Senha atual"), "Senha-antiga-1");
    await user.type(screen.getByLabelText("Nova senha"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a nova senha"), "Senha-nova-X");
    expect(screen.getByRole("alert")).toHaveTextContent("não são iguais");
    expect(screen.getByRole("button", { name: "Alterar a senha" })).toBeDisabled();
    await user.clear(screen.getByLabelText("Repita a nova senha"));
    await user.type(screen.getByLabelText("Repita a nova senha"), "Senha-nova-2!");
    await user.click(screen.getByRole("button", { name: "Alterar a senha" }));

    expect(await screen.findByText(/Senha alterada/)).toBeInTheDocument();
    expect(calls).toEqual([["Senha-antiga-1", "Senha-nova-2!"]]);
  });

  it("numa conta sem senha, define uma sem pedir a atual", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.me = () => Promise.resolve({ ...DEMO_ACCOUNT, has_password: false });
    const calls: [string | null, string][] = [];
    client.changePassword = (current, next) => {
      calls.push([current, next]);
      return Promise.resolve();
    };
    const user = renderApp(client, "/perfil");

    expect(await screen.findByRole("heading", { name: "Definir uma senha" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Senha atual")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Nova senha"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a nova senha"), "Senha-nova-2!");
    await user.click(screen.getByRole("button", { name: "Definir a senha" }));

    expect(await screen.findByText(/Senha alterada/)).toBeInTheDocument();
    expect(calls).toEqual([[null, "Senha-nova-2!"]]);
  });

  it("mostra o erro da senha atual errada", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.changePassword = () => Promise.reject(new ApiError(403, "INVALID_CREDENTIALS", "A senha atual está incorreta."));
    const user = renderApp(client, "/perfil");

    await user.type(await screen.findByLabelText("Senha atual"), "Errada-1!");
    await user.type(screen.getByLabelText("Nova senha"), "Senha-nova-2!");
    await user.type(screen.getByLabelText("Repita a nova senha"), "Senha-nova-2!");
    await user.click(screen.getByRole("button", { name: "Alterar a senha" }));

    expect(await screen.findByText("A senha atual está incorreta.")).toBeInTheDocument();
  });

  it("sem o modo demonstração, não mostra o aviso de respostas simuladas", async () => {
    renderApp(createMockClient({ latencyMs: 0, signedIn: true }), "/", false);
    await screen.findByLabelText("Código Python");

    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});

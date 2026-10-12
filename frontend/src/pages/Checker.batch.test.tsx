import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { type ApiClient, ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { FeedbackRequest } from "../types/api";

const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";

function renderApp(client: ApiClient = createMockClient({ latencyMs: 0, signedIn: true }), path = "/") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

async function ready(client?: ApiClient) {
  const user = renderApp(client);
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  return user;
}

function editor() {
  return screen.getByLabelText("Código Python") as HTMLTextAreaElement;
}

function result() {
  return screen.getByRole("region", { name: "Resultado da verificação" });
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Correção em lote (S26-02)", () => {
  it("Ctrl+Enter verifica e o foco vai ao resultado", async () => {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(VALID);

    await user.keyboard("{Control>}{Enter}{/Control}");

    const heading = await within(result()).findByRole("heading", { name: "Nenhuma violação encontrada" });
    await waitFor(() => expect(heading).toHaveFocus());
  });

  it("Próximo aluno limpa o código, o nome e o resultado, mantém a lista e volta ao editor", async () => {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(VALID);
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await user.type(await screen.findByLabelText("Nome do aluno"), "Isabella");

    await user.click(screen.getByRole("button", { name: "Próximo aluno" }));

    expect(editor()).toHaveValue("");
    expect(editor()).toHaveFocus();
    expect(screen.getByLabelText("Lista")).toHaveValue("1");
    expect(screen.queryByLabelText("Nome do aluno")).not.toBeInTheDocument();
    expect(result()).toHaveTextContent("Cole o código, escolha a lista e clique em Verificar.");
  });

  it("lembra a última lista neste navegador", async () => {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText("Lista"), "2");

    expect(window.localStorage.getItem("ipc:ultima-lista")).toBe("2");
  });

  it("começa na lista lembrada", async () => {
    window.localStorage.setItem("ipc:ultima-lista", "3");

    await ready();

    expect(screen.getByLabelText("Lista")).toHaveValue("3");
  });

  it("o rascunho sobrevive à navegação", async () => {
    const user = await ready();
    await user.click(editor());
    await user.paste("print('rascunho')");

    await user.click(screen.getByRole("link", { name: "Plágio" }));
    await screen.findByRole("heading", { name: "Plágio" });
    await user.click(screen.getByRole("link", { name: "Verificar" }));

    expect(await screen.findByLabelText("Código Python")).toHaveValue("print('rascunho')");
  });

  it("o rascunho sobrevive a um novo login depois de a sessão vencer, e Sair o apaga", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const user = await ready(client);
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(VALID);
    const validate = client.validate;
    client.validate = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre."));
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await screen.findByRole("heading", { name: "Entrar" });
    client.validate = validate;

    await user.type(screen.getByLabelText("Nome ou e-mail institucional"), "demo@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByLabelText("Código Python")).toHaveValue(VALID);
    await user.click(screen.getByRole("button", { name: "Sair" }));
    await user.click(await screen.findByRole("link", { name: "Entrar" }));
    await user.type(screen.getByLabelText("Nome ou e-mail institucional"), "demo@cin.ufpe.br");
    await user.type(screen.getByLabelText("Senha"), "Senha-forte-1");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByLabelText("Código Python")).toHaveValue("");
  });

  it("avisa quando o código mudou e o nome do aluno não", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const sent: FeedbackRequest[] = [];
    const original = client.feedback;
    client.feedback = (request, signal) => {
      sent.push(request);
      return original(request, signal);
    };
    const user = await ready(client);
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(VALID);
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await user.type(await screen.findByLabelText("Nome do aluno"), "Isabella");
    await user.click(screen.getByRole("button", { name: "Gerar feedback" }));
    // Gerado o texto, o foco vai a Copiar.
    await waitFor(() => expect(screen.getByRole("button", { name: "Copiar" })).toHaveFocus());

    await user.click(editor());
    await user.paste("\nprint('outro aluno')");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByText(/o nome do aluno é o mesmo do último feedback \(Isabella\)/)).toHaveAttribute("role", "note");
    expect(sent).toHaveLength(1);
  });
});

describe("Editor (S26-02)", () => {
  it("Tab insere 4 espaços, e Esc libera o Tab para sair do editor", async () => {
    const user = await ready();
    await user.click(editor());

    await user.keyboard("if x:{Enter}{Tab}y");
    expect(editor()).toHaveValue("if x:\n    y");

    await user.keyboard("{Escape}{Tab}");
    expect(editor()).not.toHaveFocus();
  });

  it("Limpar esvazia o editor e Colar lê a área de transferência", async () => {
    const user = await ready();
    await user.click(editor());
    await user.paste("x = 1");

    await user.click(screen.getByRole("button", { name: "Limpar" }));
    expect(editor()).toHaveValue("");

    await navigator.clipboard.writeText("y = 2");
    await user.click(screen.getByRole("button", { name: "Colar" }));
    await waitFor(() => expect(editor()).toHaveValue("y = 2"));
  });

  it("explica quando o navegador não deixa colar", async () => {
    const user = await ready();
    vi.spyOn(navigator.clipboard, "readText").mockRejectedValue(new Error("negado"));

    await user.click(screen.getByRole("button", { name: "Colar" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Cole com Ctrl+V no editor.");
  });
});

describe("Relatório (S26-03)", () => {
  const CODE = "for i in range(3):\n    print(i)\nfor j in range(2):\n    print(j)\n";

  async function verifyCode(code = CODE) {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(code);
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await within(result()).findByRole("heading", { name: /violaç/ });
    return user;
  }

  it("agrupa por regra, da mais grave para a mais leve, com resumo e trecho", async () => {
    await verifyCode();

    const cards = within(result()).getAllByRole("listitem");
    // A exigência (R-02) vem antes do fora da lista; o for das linhas 1 e 3 é um cartão só.
    expect(cards[0]).toHaveTextContent("Exigência não atendida");
    const loops = cards.find((card) => card.textContent?.includes("R-34"));
    expect(loops).toBeDefined();
    expect(within(loops as HTMLElement).getAllByRole("button", { name: /selecionar no editor/ })).toHaveLength(2);
    expect(loops).toHaveTextContent("for i in range(3):");
    expect(result()).toHaveTextContent(/1 exigência não atendida, \d+ fora da lista/);
  });

  it("clicar numa linha seleciona o trecho no editor e marca a linha", async () => {
    const user = await verifyCode();

    await user.click(within(result()).getByRole("button", { name: "Linha 3, coluna 1: selecionar no editor" }));

    const area = editor();
    expect(area).toHaveFocus();
    expect(area.value.slice(area.selectionStart, area.selectionEnd)).toBe("for j in range(2):");
    const marked = screen.getByTestId("line-numbers").querySelectorAll("[data-marked]");
    expect([...marked].map((line) => line.textContent)).toEqual(["3"]);
  });

  it("avisa quando o código mudou desde a verificação", async () => {
    const user = await verifyCode();

    await user.click(editor());
    await user.keyboard("{End}#");

    expect(within(result()).getByRole("note")).toHaveTextContent("O código mudou desde a verificação");
  });

  it("o leitor de tela recebe só o resumo", async () => {
    await verifyCode();

    const live = result().querySelector("[aria-live='polite']");
    expect(live?.textContent).toMatch(/^\d+ violações encontradas: 1 exigência não atendida, \d+ fora da lista\.$/);
    expect(result()).not.toHaveAttribute("aria-live");
  });
});

describe("Verificando e Cancelar (S36-05)", () => {
  it("enquanto verifica, o botão diz Verificando… e o Cancelar interrompe", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const signals: AbortSignal[] = [];
    vi.spyOn(client, "validate").mockImplementation(
      (_request, signal) =>
        new Promise((_resolve, reject) => {
          if (signal) signals.push(signal);
          signal?.addEventListener("abort", () => reject(signal.reason));
        }),
    );
    const user = await ready(client);
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.click(editor());
    await user.paste(VALID);
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(screen.getByRole("button", { name: "Verificando…" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(signals[0]?.aborted).toBe(true);
    expect(screen.getByRole("button", { name: "Verificar" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Cancelar" })).not.toBeInTheDocument();
    expect(editor()).toHaveValue(VALID);
  });

  it("a opção da questão é curta, e o título aparece na descrição", async () => {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText("Lista"), "3");
    const question = screen.getByRole("combobox", { name: "Questão" });
    expect(within(question).getByRole("option", { name: "Sem questão" })).toBeInTheDocument();

    await user.selectOptions(question, "L3-Q1");
    expect(question).toHaveDisplayValue(/^L3-Q1/);
    expect(question).toHaveAccessibleDescription(/L3-Q1, ".+": valem as permissões da lista e as regras da questão L3-Q1/);
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { DRAFT_KEY } from "../draftContext";
import { createMockClient } from "../services/mockClient";

/** Atalhos, ajuda e o rascunho que sobrevive ao F5 (S37-05). */
const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";

function renderApp() {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter initialEntries={["/"]}>
      <App client={createMockClient({ latencyMs: 0, signedIn: true })} />
    </MemoryRouter>,
  );
  return { user, view };
}

async function ready() {
  const { user, view } = renderApp();
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  await user.selectOptions(screen.getByLabelText("Lista"), "1");
  return { user, view };
}

const editor = () => screen.getByLabelText("Código Python") as HTMLTextAreaElement;

async function generateFeedback(user: ReturnType<typeof userEvent.setup>) {
  await user.click(editor());
  await user.paste(VALID);
  await user.click(screen.getByRole("button", { name: "Verificar" }));
  await user.type(await screen.findByLabelText("Nome do aluno"), "Isabella");
  await user.click(screen.getByRole("button", { name: "Gerar feedback" }));
  await screen.findByLabelText("Texto do feedback");
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("atalhos (S37-05)", () => {
  it("Alt+N faz o Próximo aluno de qualquer lugar da tela, inclusive do editor", async () => {
    const { user } = await ready();
    await user.click(editor());
    await user.paste(VALID);

    await user.keyboard("{Alt>}n{/Alt}");

    expect(editor()).toHaveValue("");
    expect(editor()).toHaveFocus();
  });

  it("Ctrl+Shift+C copia o feedback gerado, mas não de dentro de um campo de texto", async () => {
    const { user } = await ready();
    // Depois do setup do user-event, que instala a própria área de transferência.
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await generateFeedback(user);

    // Depois de gerar, o foco está em Copiar: o atalho copia.
    await user.keyboard("{Control>}{Shift>}c{/Shift}{/Control}");
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringMatching(/^Olá, Isabella/)));

    // Dentro do campo do texto, o atalho fica com o campo.
    await user.click(screen.getByLabelText("Texto do feedback"));
    await user.keyboard("{Control>}{Shift>}c{/Shift}{/Control}");
    expect(writeText).toHaveBeenCalledOnce();
  });

  it("sem feedback gerado, Ctrl+Shift+C não faz nada", async () => {
    const { user } = await ready();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    await user.keyboard("{Control>}{Shift>}c{/Shift}{/Control}");

    expect(writeText).not.toHaveBeenCalled();
  });

  it("a ajuda lista os atalhos", async () => {
    const { user } = await ready();

    await user.click(screen.getByRole("button", { name: "Atalhos do teclado" }));

    const help = screen.getByRole("button", { name: "Atalhos do teclado" });
    expect(help).toHaveAttribute("aria-expanded", "true");
    for (const keys of ["Ctrl+Enter", "Tab e Shift+Tab", "Esc e depois Tab", "Alt+N", "Ctrl+Shift+C"]) {
      expect(screen.getByText(keys)).toBeInTheDocument();
    }
  });
});

describe("rascunho nesta aba (S37-05)", () => {
  it("sobrevive a um recarregamento da página e some no Sair", async () => {
    const { user, view } = await ready();
    await user.click(editor());
    await user.paste("print('rascunho')");
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await user.type(await screen.findByLabelText("Nome do aluno"), "Isabella");

    expect(JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) ?? "{}")).toMatchObject({ code: "print('rascunho')", feedback: { student: "Isabella" } });

    // Um F5: a página inteira nasce de novo, e o rascunho volta da aba.
    view.unmount();
    const again = await ready();
    expect(editor()).toHaveValue("print('rascunho')");

    await again.user.click(screen.getByRole("button", { name: /Menu da conta/ }));
    await again.user.click(screen.getByRole("menuitem", { name: "Sair" }));
    await screen.findByRole("link", { name: "Entrar" });
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("ignora um rascunho corrompido na aba", async () => {
    window.sessionStorage.setItem(DRAFT_KEY, "{não é json");

    await ready();

    expect(editor()).toHaveValue("");
  });
});

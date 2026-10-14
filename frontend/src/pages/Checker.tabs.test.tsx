import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { createMockClient } from "../services/mockClient";

/**
 * Abas no celular e painéis à vista no computador (S37-02). A largura vem do `matchMedia`, que o
 * jsdom não tem: sem ele, a página se comporta como no computador.
 */
const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";
/** Duas proibições gerais diferentes: o cliente simulado responde com indícios (S29). */
const SUSPICIOUS = "x = int(input())\nif x > 0:\n    pass\nelse:\n    break\n";

function narrowScreen() {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("max-width"),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

async function ready() {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App client={createMockClient({ latencyMs: 0, signedIn: true })} />
    </MemoryRouter>,
  );
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  await user.selectOptions(screen.getByLabelText("Lista"), "1");
  return user;
}

const editor = () => screen.getByLabelText("Código Python") as HTMLTextAreaElement;

async function verify(user: ReturnType<typeof userEvent.setup>, code: string) {
  await user.click(editor());
  await user.clear(editor());
  await user.paste(code);
  await user.click(screen.getByRole("button", { name: "Verificar" }));
  await screen.findByRole("heading", { name: /violaç/ });
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("no computador", () => {
  it("não há abas, e o resultado e o feedback ficam à vista juntos", async () => {
    const user = await ready();
    await verify(user, VALID);

    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Feedback para o aluno" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Voltar ao código" })).not.toBeInTheDocument();
  });

  it("a coluna do editor fica fixa enquanto o resultado rola", async () => {
    const user = await ready();
    await verify(user, VALID);

    expect(editor().closest("form")?.className).toContain("lg:sticky");
  });
});

describe("no celular", () => {
  beforeEach(narrowScreen);

  it("o resultado vem em abas: Resultado ativa, Feedback escondida até ser escolhida", async () => {
    const user = await ready();
    await verify(user, VALID);
    const tabs = within(screen.getByRole("tablist", { name: "Painéis do resultado" }));

    expect(tabs.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Resultado", "Feedback"]);
    expect(tabs.getByRole("tab", { name: "Resultado" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("heading", { name: "Feedback para o aluno" })).not.toBeInTheDocument();

    await user.click(tabs.getByRole("tab", { name: "Feedback" }));

    expect(screen.getByRole("heading", { name: "Feedback para o aluno" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Resultado da verificação" })).not.toBeInTheDocument();
    expect(screen.getByRole("tabpanel", { name: "Feedback" })).toBeVisible();
  });

  it("a aba Indícios só aparece quando a resposta traz indícios", async () => {
    const user = await ready();
    await verify(user, SUSPICIOUS);
    const tabs = within(screen.getByRole("tablist"));

    expect(tabs.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Resultado", "Indícios", "Feedback"]);
    await user.click(tabs.getByRole("tab", { name: "Indícios" }));
    expect(screen.getByRole("region", { name: "Indícios de uso de IA" })).toBeVisible();
  });

  it("as setas trocam a aba e levam o foco com elas", async () => {
    const user = await ready();
    await verify(user, VALID);
    const tabs = within(screen.getByRole("tablist"));
    tabs.getByRole("tab", { name: "Resultado" }).focus();

    await user.keyboard("{ArrowRight}");
    expect(tabs.getByRole("tab", { name: "Feedback" })).toHaveFocus();
    expect(tabs.getByRole("tab", { name: "Feedback" })).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowRight}");
    expect(tabs.getByRole("tab", { name: "Resultado" })).toHaveFocus();
    await user.keyboard("{End}");
    expect(tabs.getByRole("tab", { name: "Feedback" })).toHaveFocus();
  });

  it("Voltar ao código põe o foco no editor", async () => {
    const user = await ready();
    await verify(user, VALID);

    await user.click(screen.getByRole("button", { name: "Voltar ao código" }));

    expect(editor()).toHaveFocus();
  });

  it("uma nova verificação volta à aba Resultado, com o foco no título", async () => {
    const user = await ready();
    await verify(user, VALID);
    await user.click(screen.getByRole("tab", { name: "Feedback" }));

    await verify(user, SUSPICIOUS);

    expect(screen.getByRole("tab", { name: "Resultado" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(screen.getByRole("heading", { name: /violaç/ })).toHaveFocus());
  });
});

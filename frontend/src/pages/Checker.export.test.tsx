import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { createMockClient } from "../services/mockClient";

/** Carregar .py e exportar o relatório (S38-03), pela tela de verificação. */
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

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Carregar .py e exportar (S38-03)", () => {
  it("carrega o arquivo no editor e avisa o nome", async () => {
    const user = await ready();

    await user.upload(screen.getByLabelText("Arquivo .py para carregar no editor"), new File(["x = int(input())\r\n"], "ana.py"));

    expect(editor()).toHaveValue("x = int(input())\n");
    expect(await screen.findByText('"ana.py" carregado no editor.')).toBeInTheDocument();
  });

  it("recusa arquivo grande demais sem mexer no editor", async () => {
    const user = await ready();
    await user.click(editor());
    await user.paste("print(1)");

    await user.upload(screen.getByLabelText("Arquivo .py para carregar no editor"), new File(["x".repeat(51_201)], "grande.py"));

    expect(await screen.findByRole("alert")).toHaveTextContent("o limite é 50 KB");
    expect(editor()).toHaveValue("print(1)");
  });

  it("copia o relatório em texto, sem o código", async () => {
    const user = await ready();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await user.click(editor());
    await user.paste("n = int(input())\nfor i in range(n):\n    print(i)\n");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    await user.click(await screen.findByRole("button", { name: "Copiar o relatório" }));

    const text = writeText.mock.calls[0]?.[0] as string;
    expect(text).toContain("Lista 1: Comandos condicionais · sem questão");
    expect(text).toContain("Por quê:");
    expect(text).not.toContain("print(i)");
    expect(screen.getByText("Relatório copiado.")).toBeInTheDocument();
  });
});

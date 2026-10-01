import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { createMockClient } from "./services/mockClient";

async function setup() {
  const user = userEvent.setup();
  render(<App client={createMockClient({ latencyMs: 0 })} demoMode />);
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  return user;
}

describe("App", () => {
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
});

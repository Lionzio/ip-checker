import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { createMockClient } from "../services/mockClient";

const SAME = "n = int(input())\nif n > 0:\n    print('positivo')\n";
const OTHER = "x = float(input())\nprint(round(x * 1.8 + 32, 1))\n";

async function matrixMode() {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/plagio"]}>
      <App client={createMockClient({ latencyMs: 0, signedIn: true })} />
    </MemoryRouter>,
  );
  await user.click(await screen.findByRole("button", { name: "Todos contra todos" }));
  return user;
}

describe("Todos contra todos (S40-02)", () => {
  it("compara a turma, mostra os grupos e os pares, e leva um par para o lado a lado", async () => {
    const user = await matrixMode();
    await user.click(screen.getByLabelText("Soluções da turma para todos contra todos"));
    await user.paste(`=== Ana\n${SAME}=== Bruno\n${OTHER}=== Carla\n${SAME}`);
    expect(screen.getByText(/3 soluções\./)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Comparar todos" }));

    const result = within(await screen.findByRole("region", { name: "Resultado todos contra todos" }));
    const groups = await result.findByRole("list");
    expect(within(groups).getByRole("listitem")).toHaveTextContent("Ana, Carla");
    expect(result.getByRole("rowheader", { name: "Ana × Carla" })).toBeInTheDocument();

    await user.click(result.getByRole("button", { name: "Comparar Ana e Carla lado a lado" }));
    expect(screen.getByRole("button", { name: "Dois códigos" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Código A")).toHaveValue(SAME);
  });

  it("pede de 2 a 60 soluções", async () => {
    const user = await matrixMode();
    await user.click(screen.getByLabelText("Soluções da turma para todos contra todos"));
    await user.paste(`=== Ana\n${SAME}`);

    expect(screen.getByRole("button", { name: "Comparar todos" })).toBeDisabled();

    await user.clear(screen.getByLabelText("Soluções da turma para todos contra todos"));
    await user.paste(Array.from({ length: 61 }, (_, index) => `=== A${index}\nx = ${index}\n`).join(""));
    expect(screen.getByText(/o limite do todos contra todos é 60/)).toBeInTheDocument();
  });
});

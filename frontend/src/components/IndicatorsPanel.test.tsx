import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "../App";
import { type ApiClient } from "../services/client";
import { createMockClient, simulatedIndicators } from "../services/mockClient";
import type { Indicators } from "../types/api";
import { IndicatorsPanel } from "./IndicatorsPanel";

const SUSPICIOUS = "for i in range(5):\n    if i == 1:\n        break\n    if i == 2:\n        continue\n    pass\n";
const CLEAN = "x = int(input())\nif x > 0:\n    print(x)\n";

const STYLE_ONLY: Indicators = {
  level: null,
  items: [
    {
      signal: "estilo",
      kind: "docstring",
      level: null,
      reason: "Docstring (texto entre aspas triplas no início da função ou do programa), incomum nas soluções das listas.",
      lines: [2],
    },
  ],
  questions: ["Pergunta um?", "Pergunta dois?"],
  notice: "Indícios não são prova de uso de IA.",
};

function renderApp(client: ApiClient = createMockClient({ latencyMs: 0, signedIn: true })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

async function verify(code: string, list = "2") {
  const user = renderApp();
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  await user.selectOptions(screen.getByLabelText("Lista"), list);
  await user.click(screen.getByLabelText("Código Python"));
  await user.paste(code);
  await user.click(screen.getByRole("button", { name: "Verificar" }));
  await screen.findByRole("heading", { level: 2, name: /violaç|Nenhuma violação/ });
  return user;
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("Painel de indícios de uso de IA (S29-03, US-34)", () => {
  it("mostra cada indício com o motivo, a faixa, o aviso e as perguntas", async () => {
    await verify(SUSPICIOUS);

    const panel = await screen.findByRole("region", { name: "Indícios de uso de IA" });
    expect(within(panel).getByText("Faixa alta")).toBeInTheDocument();
    expect(panel).toHaveTextContent("3 proibições gerais diferentes no mesmo código: 'break', 'continue' e 'pass'.");
    expect(within(panel).getByRole("note")).toHaveTextContent("não são prova");
    expect(within(panel).getByRole("note")).toHaveTextContent("não entra no feedback");
    const questions = within(panel).getByRole("heading", { name: "Perguntas para a conversa com o aluno" });
    expect(questions.nextElementSibling?.querySelectorAll("li")).toHaveLength(2);
  });

  it("uma solução sem indícios não mostra o painel", async () => {
    await verify(CLEAN, "1");

    expect(screen.queryByRole("region", { name: "Indícios de uso de IA" })).not.toBeInTheDocument();
  });

  it("clicar numa linha do indício seleciona a linha no editor", async () => {
    const user = await verify(SUSPICIOUS);

    const panel = await screen.findByRole("region", { name: "Indícios de uso de IA" });
    await user.click(within(panel).getByRole("button", { name: "Linha 5: selecionar no editor" }));

    const area = screen.getByLabelText("Código Python") as HTMLTextAreaElement;
    expect(area.value.slice(area.selectionStart, area.selectionEnd)).toBe("        continue");
  });

  it("o painel some no próximo aluno", async () => {
    const user = await verify(SUSPICIOUS);
    await screen.findByRole("region", { name: "Indícios de uso de IA" });

    await user.click(screen.getByRole("button", { name: "Próximo aluno" }));

    expect(screen.queryByRole("region", { name: "Indícios de uso de IA" })).not.toBeInTheDocument();
  });

  it("só marcadores de estilo aparecem sem faixa, separados", () => {
    render(<IndicatorsPanel indicators={STYLE_ONLY} />);

    const panel = screen.getByRole("region", { name: "Indícios de uso de IA" });
    expect(within(panel).getByText("Só marcadores de estilo")).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Marcadores de estilo" })).toBeInTheDocument();
    expect(within(panel).queryByText(/Faixa (alta|média|baixa)/)).not.toBeInTheDocument();
    // Sem onde selecionar, as linhas aparecem como texto.
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
  });

  it("o simulado só aponta indício com duas ou mais proibições gerais diferentes", () => {
    expect(simulatedIndicators("for i in range(2):\n    break\n")).toBeNull();
    expect(simulatedIndicators("for i in range(2):\n    break\n    pass\n")?.level).toBe("medio");
    expect(simulatedIndicators(SUSPICIOUS)?.items[0]?.lines).toEqual([3, 5, 6]);
  });
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { classBytes, parseClass } from "../plagiarismClass";
import { type ApiClient } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { SimilarityResponse } from "../types/api";

function renderAt(client: ApiClient = createMockClient({ latencyMs: 0, signedIn: true })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/plagio"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

function gutter(label: string) {
  const editor = screen.getByLabelText(label);
  const box = editor.parentElement;
  if (box === null) throw new Error("editor sem gutter");
  return within(box).getByTestId("line-numbers");
}

function marked(label: string, attribute = "data-marked") {
  return [...gutter(label).querySelectorAll(`[${attribute}]`)].map((line) => line.textContent);
}

const ANSWER: SimilarityResponse = {
  request_id: "r1",
  status: "compared",
  similarity: 100,
  band: { id: "plagio", label: "Plágio", minimum: 99 },
  short_code: false,
  syntax_error: null,
  notice: "A similaridade é um indício, não uma prova: a decisão final sobre plágio é sempre da equipe.",
  metrics: { sequence: 72.2, tree_dice: 100, tree_containment: 100 },
  matches: [
    { a_first: 1, a_last: 2, b_first: 3, b_last: 4 },
    { a_first: 4, a_last: 4, b_first: 1, b_last: 1 },
  ],
};

describe("Trechos em comum (S27-03)", () => {
  async function compared() {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.compare = () => Promise.resolve(ANSWER);
    const user = renderAt(client);
    await user.click(await screen.findByLabelText("Código A"));
    await user.paste("a = 1\nb = 2\nc = 3\nd = 4\n");
    await user.click(screen.getByLabelText("Código B"));
    await user.paste("d = 4\nx = 0\na = 1\nb = 2\n");
    await user.click(screen.getByRole("button", { name: "Verificar" }));
    await screen.findByText("Trechos em comum (2)");
    return user;
  }

  it("mostra as métricas e marca os trechos nos dois códigos", async () => {
    await compared();

    expect(screen.getByText(/Estrutura: 100,0% · Contenção: 100,0% · Sequência: 72,2%/)).toBeInTheDocument();
    expect(marked("Código A")).toEqual(["1", "2", "4"]);
    expect(marked("Código B")).toEqual(["1", "3", "4"]);
  });

  it("escolher um trecho destaca o par nos dois lados", async () => {
    const user = await compared();

    const button = screen.getByRole("button", { name: "A: linhas 1–2 ↔ B: linhas 3–4" });
    await user.click(button);

    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(marked("Código A", "data-current")).toEqual(["1", "2"]);
    expect(marked("Código B", "data-current")).toEqual(["3", "4"]);
  });

  it("Trocar A e B troca os códigos e os trechos", async () => {
    const user = await compared();

    await user.click(screen.getByRole("button", { name: "Trocar A e B" }));

    expect(screen.getByLabelText("Código A")).toHaveValue("d = 4\nx = 0\na = 1\nb = 2\n");
    expect(screen.getByRole("button", { name: "A: linhas 3–4 ↔ B: linhas 1–2" })).toBeInTheDocument();
    expect(marked("Código A")).toEqual(["1", "3", "4"]);
  });

  it("os trechos somem quando um código muda, e Limpar os dois esvazia tudo", async () => {
    const user = await compared();

    await user.type(screen.getByLabelText("Código A"), "#");
    expect(screen.getByRole("note")).toHaveTextContent("Os códigos mudaram desde a comparação");
    expect(marked("Código A")).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Limpar os dois" }));
    expect(screen.getByLabelText("Código A")).toHaveValue("");
    expect(screen.getByLabelText("Código B")).toHaveValue("");
    expect(screen.queryByText(/Trechos em comum/)).not.toBeInTheDocument();
  });

  it("o cliente simulado também devolve trechos e métricas", async () => {
    const user = renderAt();
    await user.click(await screen.findByLabelText("Código A"));
    await user.paste("x = int(input())\nprint(x)\n");
    await user.click(screen.getByLabelText("Código B"));
    await user.paste("print(x)\nx = int(input())\n");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByText("Trechos em comum (2)")).toBeInTheDocument();
  });
});

describe("Contra a turma (S27-02)", () => {
  it("separa as soluções pelas linhas === (S36-02)", () => {
    expect(parseClass("=== Ana\nx = 1\n\n=== Bruno\ny = 2\n===\nz = 3")).toEqual({
      solutions: [
        { label: "Ana", code: "x = 1\n" },
        { label: "Bruno", code: "y = 2\n" },
        { label: "Solução 3", code: "z = 3\n" },
      ],
      legacy: false,
      repeated: [],
    });
    expect(parseClass("x = 1\n").solutions).toEqual([{ label: "Solução 1", code: "x = 1\n" }]);
    expect(parseClass("   \n").solutions).toEqual([]);
    expect(classBytes("ção", [{ label: "A", code: "é" }])).toBe(7);
  });

  it("com ===, um comentário ### ou ##### dentro do código não parte a solução (S36-02)", () => {
    const parsed = parseClass("=== Ana\n### calcula a média\nm = 1\n#####\nprint(m)\n=== Bruno\ny = 2\n");
    expect(parsed.legacy).toBe(false);
    expect(parsed.solutions).toEqual([
      { label: "Ana", code: "### calcula a média\nm = 1\n#####\nprint(m)\n" },
      { label: "Bruno", code: "y = 2\n" },
    ]);
  });

  it("sem nenhum ===, aceita o formato antigo ### e avisa (S36-02)", () => {
    const parsed = parseClass("### Ana\nx = 1\n\n### Bruno\ny = 2\n###\nz = 3");
    expect(parsed.legacy).toBe(true);
    expect(parsed.solutions.map((item) => item.label)).toEqual(["Ana", "Bruno", "Solução 3"]);
  });

  it("nomes repetidos ganham um número, e o rótulo continua com até 80 caracteres (S36-01)", () => {
    const longName = "x".repeat(80);
    const parsed = parseClass(`=== Ana\na = 1\n=== Ana\nb = 2\n=== Ana\nc = 3\n=== ${longName}\nd = 4\n=== ${longName}\ne = 5\n`);
    expect(parsed.solutions.map((item) => item.label)).toEqual([
      "Ana",
      "Ana (2)",
      "Ana (3)",
      longName,
      `${"x".repeat(76)} (2)`,
    ]);
    expect(parsed.repeated).toEqual(["Ana", longName]);
  });

  it("duas alunas com o mesmo nome: cada uma abre o próprio código lado a lado (S36-01)", async () => {
    const user = renderAt();
    await user.click(await screen.findByRole("button", { name: "Contra a turma" }));
    await user.click(screen.getByLabelText("Solução comparada"));
    await user.paste("n = int(input())\nprint(n * 2)\n");
    await user.click(screen.getByLabelText("Soluções da turma"));
    await user.paste("=== Ana\nprint('oi')\n=== Ana\nn = int(input())\nprint(n * 2)\n");

    expect(screen.getByRole("note")).toHaveTextContent('Este nome aparece mais de uma vez: Ana. As repetições ganharam um número, como "Ana (2)"');
    await user.click(screen.getByRole("button", { name: "Comparar com a turma" }));

    const rows = within(await screen.findByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getByRole("rowheader").textContent)).toEqual(["Ana (2)", "Ana"]);
    await user.click(within(rows[1] as HTMLElement).getByRole("button", { name: "Comparar lado a lado com Ana" }));
    expect(screen.getByLabelText("Código B")).toHaveValue("print('oi')\n");
  });

  it("o formato antigo ### mostra o aviso para usar === (S36-02)", async () => {
    const user = renderAt();
    await user.click(await screen.findByRole("button", { name: "Contra a turma" }));
    await user.click(screen.getByLabelText("Soluções da turma"));
    await user.paste("### Ana\nx = 1\n### Bruno\ny = 2\n");
    expect(screen.getByRole("note")).toHaveTextContent("formato antigo");
  });

  it("compara com a turma, da mais parecida para a menos, e abre o par lado a lado", async () => {
    const user = renderAt();
    await user.click(await screen.findByRole("button", { name: "Contra a turma" }));
    await user.click(screen.getByLabelText("Solução comparada"));
    await user.paste("n = int(input())\nprint(n * 2)\n");
    await user.click(screen.getByLabelText("Soluções da turma"));
    await user.paste("### Ana\nprint('oi')\n### Bruno\nn = int(input())\nprint(n * 2)\n### Caio\n");

    expect(screen.getByText(/3 soluções\./)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Comparar com a turma" }));

    const rows = within(await screen.findByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getByRole("rowheader").textContent)).toEqual(["Bruno", "Ana", "Caio"]);
    expect(rows[0]).toHaveTextContent("Plágio");
    expect(rows[2]).toHaveTextContent("O código está vazio.");

    await user.click(within(rows[0] as HTMLElement).getByRole("button", { name: "Comparar lado a lado com Bruno" }));
    expect(screen.getByRole("button", { name: "Dois códigos" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Código B")).toHaveValue("n = int(input())\nprint(n * 2)\n");
    await waitFor(() => expect(screen.getByText("Trechos em comum (2)")).toBeInTheDocument());
  });

  it("recusa mais de 100 soluções antes de enviar", async () => {
    const user = renderAt();
    await user.click(await screen.findByRole("button", { name: "Contra a turma" }));
    await user.click(screen.getByLabelText("Solução comparada"));
    await user.paste("x = 1\n");
    await user.click(screen.getByLabelText("Soluções da turma"));
    await user.paste(Array.from({ length: 101 }, (_, index) => `### ${index}\nx = ${index}\n`).join(""));

    expect(screen.getByRole("alert")).toHaveTextContent("São 101 soluções; o limite é 100.");
    expect(screen.getByRole("button", { name: "Comparar com a turma" })).toBeDisabled();
  });
});

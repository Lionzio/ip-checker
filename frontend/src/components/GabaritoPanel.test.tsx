import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { questionOptions, GABARITO_ONLY_TITLE } from "../questions";
import { createMockClient } from "../services/mockClient";
import type { GabaritoComparison, ListInfo, SimilarityResponse, ValidateResponse } from "../types/api";
import { GabaritoPanel } from "./GabaritoPanel";

const COMPARED: GabaritoComparison = {
  question_id: "L1-Q1",
  status: "compared",
  similarity: 96.4,
  band: { id: "altas_chances", label: "Altas chances de plágio", minimum: 95 },
  short_code: false,
  common: ["while", "if", "print()"],
  only_student: ["f-string"],
  only_gabarito: [],
  student_lines: [
    { first: 1, last: 1 },
    { first: 3, last: 8 },
  ],
  message: "Semelhança com o gabarito oficial da questão.",
};

describe("Comparação com o gabarito na verificação (S32-06, ADR-11)", () => {
  it("mostra a semelhança com a faixa, as construções e os trechos do aluno", async () => {
    const select = vi.fn();
    const user = userEvent.setup();
    render(<GabaritoPanel comparison={COMPARED} onSelectLines={select} />);

    expect(screen.getByRole("heading", { name: "Comparação com o gabarito · L1-Q1" })).toBeInTheDocument();
    expect(screen.getByLabelText("Semelhança com o gabarito de 96,4%")).toBeInTheDocument();
    expect(screen.getByText("Altas chances de plágio")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Em comum" })).getAllByRole("listitem")).toHaveLength(3);
    expect(within(screen.getByRole("list", { name: "Só no código do aluno" })).getByText("f-string")).toBeInTheDocument();
    expect(screen.getByText("Nenhuma.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "linhas 3–8: selecionar no editor" }));
    expect(select).toHaveBeenCalledWith(3, 8);
  });

  it("sem gabarito ou com os gabaritos fora do ar, mostra só o aviso", () => {
    render(
      <GabaritoPanel
        comparison={{
          ...COMPARED,
          status: "unavailable",
          similarity: null,
          band: null,
          common: [],
          only_student: [],
          student_lines: [],
          message: "Os gabaritos não estão disponíveis neste servidor agora.",
        }}
      />,
    );

    expect(screen.getByRole("note")).toHaveTextContent("Os gabaritos não estão disponíveis");
    expect(screen.queryByText("Em comum")).not.toBeInTheDocument();
  });

  it("avisa quando o código é curto", () => {
    render(<GabaritoPanel comparison={{ ...COMPARED, short_code: true }} />);

    expect(screen.getByRole("note")).toHaveTextContent("Código curto");
  });
});

describe("Seletor de questões com gabarito (ADR-11, item 6)", () => {
  it("junta as questões com regra e as que só têm gabarito, em ordem", () => {
    const list: ListInfo = {
      number: 3,
      title: "Listas e tuplas",
      questions: [{ id: "L3-Q9", title: "Ensaio" }, { id: "L3-Q2", title: "Soma" }],
      gabaritos: ["L3-Q1", "L3-Q2"],
    };

    expect(questionOptions(list)).toEqual([
      { id: "L3-Q1", title: GABARITO_ONLY_TITLE },
      { id: "L3-Q2", title: "Soma · com gabarito" },
      { id: "L3-Q9", title: "Ensaio" },
    ]);
    expect(questionOptions(undefined)).toEqual([]);
  });
});

function renderApp(client: ReturnType<typeof createMockClient>, path = "/") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

describe("Verificação com uma questão que só tem gabarito", () => {
  it("manda a questão, avisa que valem as regras da lista e mostra a comparação", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const lists = await client.listLists();
    client.listLists = vi.fn(async () =>
      lists.map((list) => (list.number === 1 ? { ...list, gabaritos: ["L1-Q1"] } : list)),
    );
    const response: ValidateResponse = {
      request_id: "r1",
      ruleset_version: "2026.2.5",
      status: "valid",
      list_number: 1,
      question_id: "L1-Q1",
      notices: ["QUESTION_RULES_NOT_REGISTERED"],
      syntax_error: null,
      violations: [],
      truncated: false,
      gabarito: COMPARED,
    };
    const validate = vi.fn(async () => response);
    client.validate = validate;
    const user = renderApp(client);

    await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.selectOptions(screen.getByLabelText("Questão"), "L1-Q1");
    expect(screen.getByText(/não tem regra cadastrada: valem as permissões da lista/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Código Python"), "x = 1");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("heading", { name: "Comparação com o gabarito · L1-Q1" })).toBeInTheDocument();
    expect(validate).toHaveBeenCalledWith(expect.objectContaining({ question_id: "L1-Q1" }), expect.anything());
  });
});

describe("Plágio com o gabarito (S32-07, ADR-11, item 5)", () => {
  it("compara com a questão escolhida e mostra o alerta de possível vazamento", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const lists = await client.listLists();
    client.listLists = vi.fn(async () =>
      lists.map((list) => (list.number === 1 ? { ...list, gabaritos: ["L1-Q1"] } : list)),
    );
    const band = { id: "plagio" as const, label: "Plágio", minimum: 99 };
    const answer: SimilarityResponse = {
      request_id: "r1",
      status: "compared",
      similarity: 99.5,
      band,
      short_code: false,
      syntax_error: null,
      notice: "A similaridade é um indício, não uma prova.",
      gabarito: {
        question_id: "L1-Q1",
        status: "compared",
        a: { similarity: 99.1, band },
        b: { similarity: 98.7, band: { id: "altas_chances", label: "Altas chances de plágio", minimum: 95 } },
        leak_alert: true,
        message: "Possível vazamento do gabarito: os dois códigos coincidem entre si e com o gabarito oficial.",
      },
    };
    const compare = vi.fn(async () => answer);
    client.compare = compare;
    const user = renderApp(client, "/plagio");

    await user.selectOptions(await screen.findByLabelText("Questão (para comparar também com o gabarito)"), "L1-Q1");
    await user.type(screen.getByLabelText("Código A"), "x = 1");
    await user.type(screen.getByLabelText("Código B"), "y = 1");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Possível vazamento do gabarito");
    expect(screen.getByText("Código A com o gabarito:")).toBeInTheDocument();
    expect(compare).toHaveBeenCalledWith("x = 1", "y = 1", expect.anything(), "L1-Q1");
  });

  it("sem questões com gabarito, o seletor nem aparece", async () => {
    renderApp(createMockClient({ latencyMs: 0, signedIn: true }), "/plagio");

    await screen.findByLabelText("Código A");
    expect(screen.queryByLabelText("Questão (para comparar também com o gabarito)")).not.toBeInTheDocument();
  });
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ApiError } from "../services/client";
import { createMockClient, DEMO_ACCOUNT, DEMO_MANAGER } from "../services/mockClient";
import type { CatalogResponse } from "../types/api";

/** A tela "Listas do período" (S50-06): estados, chips da etapa 1 e o .zip só para a chefia. */

function renderLists(client = createMockClient({ latencyMs: 0, signedIn: true })) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/listas"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

const WHEN = "2026-10-16T15:00:00Z";
const CATALOG: CatalogResponse = {
  period: "2026.2",
  last_sync: WHEN,
  lists: [
    {
      kind: "lista",
      number: 3,
      title: "Lista 3 - Listas e tuplas",
      starts_at: "2026-10-01T03:00:00Z",
      ends_at: "2026-10-08T02:59:00Z",
      classes: ["IP EC UFPE 2026.2", "IP SI UFPE 2026.2"],
      missing_since: null,
      questions: [
        { question_id: "L3-Q1", title: "Média", version: 2, updated_at: WHEN, missing_since: null, has_rules: true, has_gabarito: true },
        { question_id: "L3-Q2", title: "Sumiu", version: 1, updated_at: WHEN, missing_since: WHEN, has_rules: false, has_gabarito: false },
      ],
    },
    {
      kind: "treino",
      number: null,
      title: "Lista de Treinamento",
      starts_at: null,
      ends_at: null,
      classes: [],
      missing_since: WHEN,
      questions: [],
    },
  ],
};

afterEach(() => vi.restoreAllMocks());

describe("Listas do período (S50-06)", () => {
  it("mostra as listas, as turmas, as datas e o estado de cada questão", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.catalog = vi.fn(() => Promise.resolve(CATALOG));
    renderLists(client);

    const lista = await screen.findByRole("region", { name: "Lista 3 - Listas e tuplas" });

    expect(within(lista).getByText(/de 01\/10 a 07\/10 · turmas: IP EC UFPE 2026.2, IP SI UFPE 2026.2/)).toBeInTheDocument();
    const rows = within(lista).getAllByRole("row").slice(1);
    expect(within(rows[0]!).getByText("✓ regras")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("✓ gabarito")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("2")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("sem regras próprias")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("Não encontrada na última sincronização.")).toBeInTheDocument();
    const treino = screen.getByRole("region", { name: "Lista de Treinamento" });
    expect(within(treino).getByText("Não encontrada no Dikastis na última sincronização.")).toBeInTheDocument();
    expect(screen.getByText(/Última sincronização: 16\/10\/2026, 12:00/)).toBeInTheDocument();
    expect(client.catalog).toHaveBeenCalledWith("2026.2", expect.any(AbortSignal));
    expect(document.title).toContain("Listas do período");
  });

  it("uma monitora não vê o botão do .zip", async () => {
    renderLists(createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_ACCOUNT }));

    await screen.findByRole("region", { name: "Lista 1" });

    expect(screen.queryByRole("button", { name: "Baixar enunciados (.zip)" })).not.toBeInTheDocument();
  });

  it("a chefia baixa os enunciados", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
    const zip = vi.spyOn(client, "statementsZip");
    const created = vi.fn(() => "blob:enunciados");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: created, revokeObjectURL: vi.fn() }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const user = renderLists(client);

    await user.click(await screen.findByRole("button", { name: "Baixar enunciados (.zip)" }));

    expect(zip).toHaveBeenCalledWith("2026.2");
    expect(created).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
  });

  it("um erro ao baixar aparece na tela", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
    client.statementsZip = () => Promise.reject(new ApiError(422, "INVALID_INPUT", "Sem enunciados ainda."));
    const user = renderLists(client);

    await user.click(await screen.findByRole("button", { name: "Baixar enunciados (.zip)" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Sem enunciados ainda.");
  });

  it("sem catálogo, explica como sincronizar", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
    client.catalog = (period) => Promise.resolve({ period, last_sync: null, lists: [] });
    renderLists(client);

    const empty = await screen.findByRole("region", { name: "Sem listas ainda" });

    expect(empty).toHaveTextContent("O período 2026.2 ainda não tem listas no IP-Checker.");
    expect(within(empty).getByRole("link", { name: "Perfil" })).toHaveAttribute("href", "/perfil");
    expect(screen.queryByRole("button", { name: "Baixar enunciados (.zip)" })).not.toBeInTheDocument();
  });

  it("um erro do servidor aparece", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.catalog = () => Promise.reject(new ApiError(503, "DATABASE_UNAVAILABLE", "O banco não respondeu."));
    renderLists(client);
    expect(await screen.findByRole("alert")).toHaveTextContent("O banco não respondeu.");
  });

  it("uma sessão vencida volta para Entrar", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.catalog = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre de novo."));
    renderLists(client);

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });
});

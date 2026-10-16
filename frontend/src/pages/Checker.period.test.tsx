import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { type ApiClient } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { ListInfo, ValidateRequest } from "../types/api";

const PERIODS = [
  { period: "2027.1", active: true, ruleset_version: "2027.1.0" },
  { period: "2026.2", active: false, ruleset_version: "2026.2.7" },
];

/** O cliente simulado com dois períodos: as listas de 2026.2 têm a L3-Q9. */
function twoPeriods(): ApiClient & { periodsAsked: (string | null | undefined)[]; validated: ValidateRequest[] } {
  const client = createMockClient({ latencyMs: 0, signedIn: true });
  const lists = client.listLists.bind(client);
  const validate = client.validate.bind(client);
  const periodsAsked: (string | null | undefined)[] = [];
  const validated: ValidateRequest[] = [];
  return Object.assign(client, {
    periodsAsked,
    validated,
    listPeriods: () => Promise.resolve(PERIODS),
    async listLists(signal?: AbortSignal, period?: string | null): Promise<ListInfo[]> {
      periodsAsked.push(period);
      const base = await lists(signal);
      if (period !== "2026.2") return base;
      return base.map((list) => ({ ...list, title: `${list.title} (2026.2)` }));
    },
    validate(request: ValidateRequest, signal?: AbortSignal) {
      validated.push(request);
      return validate(request, signal);
    },
  });
}

function renderChecker(client: ApiClient) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("Período na verificação (S43-03)", () => {
  it("com um período só, o seletor não aparece", async () => {
    renderChecker(createMockClient({ latencyMs: 0, signedIn: true }));

    await screen.findByLabelText("Lista");
    expect(screen.queryByLabelText("Período")).not.toBeInTheDocument();
  });

  it("verifica uma lista atrasada com as regras do período dela", async () => {
    const client = twoPeriods();
    const user = renderChecker(client);

    const selector = await screen.findByLabelText("Período");
    expect(selector).toHaveValue("2027.1");
    expect(screen.getByRole("option", { name: "2027.1 (ativo)" })).toBeInTheDocument();

    await user.selectOptions(selector, "2026.2");
    await screen.findByRole("option", { name: /Lista 1: .* \(2026\.2\)/ });
    expect(client.periodsAsked).toContain("2026.2");
    await user.selectOptions(screen.getByLabelText("Lista"), "1");
    await user.type(screen.getByLabelText("Código Python"), "x = int(input())");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    await waitFor(() => expect(client.validated).toHaveLength(1));
    expect(client.validated[0]).toMatchObject({ list_number: 1, period: "2026.2" });
  });

  it("trocar de período limpa a lista; o Próximo aluno mantém o período", async () => {
    const client = twoPeriods();
    const user = renderChecker(client);
    await screen.findByLabelText("Período");
    await user.selectOptions(screen.getByLabelText("Lista"), "1");

    await user.selectOptions(screen.getByLabelText("Período"), "2026.2");
    expect(screen.getByLabelText("Lista")).toHaveValue("");

    await user.selectOptions(await screen.findByLabelText("Lista"), "1");
    await user.type(screen.getByLabelText("Código Python"), "x = 1");
    await user.click(screen.getByRole("button", { name: "Próximo aluno" }));
    expect(screen.getByLabelText("Período")).toHaveValue("2026.2");
  });

  it("voltar ao ativo manda o pedido sem período", async () => {
    const client = twoPeriods();
    const user = renderChecker(client);
    await user.selectOptions(await screen.findByLabelText("Período"), "2026.2");
    await user.selectOptions(screen.getByLabelText("Período"), "2027.1");
    await user.selectOptions(await screen.findByLabelText("Lista"), "1");
    await user.type(screen.getByLabelText("Código Python"), "x = 1");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    await waitFor(() => expect(client.validated).toHaveLength(1));
    expect(client.validated[0]?.period ?? null).toBeNull();
  });

  it("o rascunho da aba guarda o período", async () => {
    vi.spyOn(Storage.prototype, "setItem");
    const client = twoPeriods();
    const user = renderChecker(client);
    await user.selectOptions(await screen.findByLabelText("Período"), "2026.2");

    await waitFor(() => expect(JSON.parse(window.sessionStorage.getItem("ipc:rascunho") ?? "{}")).toMatchObject({ period: "2026.2" }));
    vi.restoreAllMocks();
  });
});

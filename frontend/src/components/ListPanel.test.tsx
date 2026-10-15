import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../services/client";
import { createMockClient, DEMO_MANAGER } from "../services/mockClient";
import { ListPanel } from "./ListPanel";

const manager = () => createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });

describe("Painel por lista (S40-03)", () => {
  it("mostra as regras mais violadas, a taxa de erro de sintaxe e a adoção da lista escolhida", async () => {
    const client = manager();
    const listPanel = vi.spyOn(client, "listPanel");
    const user = userEvent.setup();
    render(<ListPanel client={client} />);

    const panel = screen.getByRole("region", { name: "Painel por lista" });
    expect(await within(panel).findByText(/60 verificações, 13,3% com erro de sintaxe; 62,5% da equipe/)).toBeInTheDocument();
    const rows = within(panel).getAllByRole("rowheader").map((cell) => cell.textContent);
    expect(rows).toEqual(["R-34", "R-11", "R-04"]);
    expect(listPanel).toHaveBeenLastCalledWith(1, null, expect.any(AbortSignal));

    await user.selectOptions(within(panel).getByLabelText("Lista do painel"), "3");
    expect(listPanel).toHaveBeenLastCalledWith(3, null, expect.any(AbortSignal));
  });

  it("avisa quando a lista não tem violações", async () => {
    const client = manager();
    client.listPanel = () =>
      Promise.resolve({ semester: "2026.2", list_number: 1, top_rules: [], events: 0, syntax_errors: 0, adoption_pct: null });
    render(<ListPanel client={client} />);

    expect(await screen.findByText("Nenhuma violação registrada nesta lista ainda.")).toBeInTheDocument();
    expect(screen.getByText(/Período 2026\.2: 0 verificações\./)).toBeInTheDocument();
  });

  it("devolve à tela de entrada quando a sessão venceu e mostra o erro nos outros casos", async () => {
    const client = manager();
    const onUnauthenticated = vi.fn();
    client.listPanel = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre de novo."));
    const { unmount } = render(<ListPanel client={client} onUnauthenticated={onUnauthenticated} />);
    await vi.waitFor(() => expect(onUnauthenticated).toHaveBeenCalled());
    unmount();

    client.listPanel = () => Promise.reject(new ApiError(503, "INTERNAL_ERROR", "O banco não respondeu."));
    render(<ListPanel client={client} />);
    expect(await screen.findByText(/O banco não respondeu/)).toBeInTheDocument();
  });
});

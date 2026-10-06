import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { type ApiClient, ApiError } from "../services/client";
import { createMockClient, DEMO_MANAGER } from "../services/mockClient";

function renderAt(client: ApiClient, path = "/gerenciar") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

function manager() {
  return createMockClient({ latencyMs: 0, signedIn: true, as: DEMO_MANAGER });
}

function section(name: RegExp) {
  return screen.getByRole("region", { name });
}

function row(region: HTMLElement, name: string) {
  const header = within(region).getByRole("rowheader", { name });
  const found = header.closest("tr");
  if (found === null) throw new Error(`sem linha para ${name}`);
  return found;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Gerenciamento da equipe (S15-03, FR-28)", () => {
  it("mostra Gerenciar só para quem gerencia", async () => {
    renderAt(manager(), "/");

    expect(await screen.findByRole("link", { name: "Gerenciar" })).toHaveAttribute("href", "/gerenciar");
  });

  it("não mostra Gerenciar a um monitor, e o endereço volta ao painel", async () => {
    renderAt(createMockClient({ latencyMs: 0, signedIn: true }));

    expect(await screen.findByLabelText("Código Python")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gerenciar" })).not.toBeInTheDocument();
  });

  it("leva para Entrar quem abre o gerenciamento sem sessão", async () => {
    renderAt(createMockClient({ latencyMs: 0 }));

    expect(await screen.findByLabelText("Nome ou e-mail institucional")).toBeInTheDocument();
  });

  it("lista pedidos, membros e removidos com as etiquetas escritas", async () => {
    renderAt(manager());

    const pending = await screen.findByRole("region", { name: /Pedidos pendentes/ });
    const pedido = row(pending, "Ana Pereira");
    expect(pedido).toHaveTextContent("E-mail e senha");
    expect(pedido).toHaveTextContent("01/10/2026");
    expect(within(pedido).getByRole("combobox", { name: "Cargo para aprovar Ana Pereira" })).toHaveDisplayValue("Professor");

    const active = section(/Membros ativos/);
    expect(row(active, "Vinícius Leôncio")).toHaveTextContent("Monitor e desenvolvedor");
    expect(within(row(active, "Vinícius Leôncio")).queryByRole("button")).not.toBeInTheDocument();
    expect(row(active, "Bruno Lima")).toHaveTextContent("Monitor");

    const removed = section(/Ex-monitores, conselheiros e inativos/);
    expect(row(removed, "Carla Souza")).toHaveTextContent("Ex-monitor");
    expect(row(removed, "Carla Souza")).toHaveTextContent("Último cargo: Monitor");
  });

  it("aprova com o cargo escolhido e recarrega as listas", async () => {
    const client = manager();
    const approve = vi.spyOn(client, "approve");
    const user = renderAt(client);

    const pending = await screen.findByRole("region", { name: /Pedidos pendentes/ });
    await user.selectOptions(within(pending).getByRole("combobox"), "Monitor-chefe");
    await user.click(within(pending).getByRole("button", { name: "Aprovar Ana Pereira" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Ana Pereira foi aprovado(a) como Monitor-chefe.");
    expect(approve).toHaveBeenCalledWith("ana", "monitor_chefe");
    // As listas são recarregadas depois da ação.
    await waitFor(() => expect(row(section(/Membros ativos/), "Ana Pereira")).toHaveTextContent("Monitor-chefe"));
    expect(within(section(/Pedidos pendentes/)).getByText("Nenhum pedido aguardando aprovação.")).toBeInTheDocument();
  });

  it("pede confirmação antes de recusar e não recusa se a pessoa desistir", async () => {
    const client = manager();
    const reject = vi.spyOn(client, "reject");
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = renderAt(client);

    await user.click(await screen.findByRole("button", { name: "Recusar Ana Pereira" }));

    expect(confirm).toHaveBeenCalledWith("Recusar o pedido de Ana Pereira? A pessoa não terá acesso.");
    expect(reject).not.toHaveBeenCalled();
  });

  it("confirma a remoção dizendo o que a conta vira", async () => {
    const client = manager();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = renderAt(client);

    await user.click(await screen.findByRole("button", { name: "Remover Bruno Lima" }));

    expect(confirm).toHaveBeenCalledWith(
      "Remover Bruno Lima da equipe? A conta passa a Ex-monitor, perde o acesso e as sessões abertas são encerradas.",
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Bruno Lima foi removido(a) da equipe (Ex-monitor).");
    await waitFor(() =>
      expect(row(section(/Ex-monitores, conselheiros e inativos/), "Bruno Lima")).toHaveTextContent("Ex-monitor"),
    );
  });

  it("altera o cargo e reativa com os cargos permitidos", async () => {
    const client = manager();
    const user = renderAt(client);

    const active = await screen.findByRole("region", { name: /Membros ativos/ });
    const novo = within(row(active, "Bruno Lima")).getByRole("combobox", { name: "Novo cargo de Bruno Lima" });
    expect(within(novo).getAllByRole("option").map((option) => option.textContent)).toEqual(["Professor", "Monitor-chefe"]);
    await user.selectOptions(novo, "Monitor-chefe");
    await user.click(screen.getByRole("button", { name: "Alterar cargo Bruno Lima" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Bruno Lima agora é Monitor-chefe.");

    await user.click(screen.getByRole("button", { name: "Reativar Carla Souza" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Carla Souza foi reativado(a) como Professor.");
  });

  it("mostra a recusa do servidor e mantém a tela utilizável", async () => {
    const client = manager();
    client.approve = () => Promise.reject(new ApiError(403, "FORBIDDEN", "Você não tem permissão para esta ação."));
    const user = renderAt(client);

    await user.click(await screen.findByRole("button", { name: "Aprovar Ana Pereira" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Você não tem permissão para esta ação.");
    // Depois da recusa, as listas são recarregadas; o botão volta quando o recarregamento termina.
    await waitFor(() => expect(screen.getByRole("button", { name: "Aprovar Ana Pereira" })).toBeEnabled());
  });

  it("mostra no registro de ações quem aprovou e o que mudou (REC-06)", async () => {
    const client = manager();
    const user = renderAt(client);

    const log = await screen.findByRole("region", { name: /Registro de ações/ });
    expect(within(log).getByText("Nenhuma ação registrada nos últimos 12 meses.")).toBeInTheDocument();

    const pending = section(/Pedidos pendentes/);
    await user.selectOptions(within(pending).getByRole("combobox"), "Monitor-chefe");
    await user.click(within(pending).getByRole("button", { name: "Aprovar Ana Pereira" }));

    await waitFor(() => expect(within(section(/Registro de ações/)).getAllByRole("row")).toHaveLength(2));
    const entry = within(section(/Registro de ações/)).getAllByRole("row")[1];
    expect(entry).toHaveTextContent("Professora de Demonstração");
    expect(entry).toHaveTextContent("Aprovou Ana Pereira");
    expect(entry).toHaveTextContent("Pendente → Ativo (Monitor-chefe)");
  });

  it("não mostra o registro de ações a quem gerencia sem ser professor nem desenvolvedor", async () => {
    const chefe = { ...DEMO_MANAGER, role: "monitor_chefe" as const, role_label: "Monitor-chefe", can_view_log: false };
    const client = createMockClient({ latencyMs: 0, signedIn: true, as: chefe });
    const managementLog = vi.spyOn(client, "managementLog");
    renderAt(client);

    expect(await screen.findByRole("region", { name: /Membros ativos/ })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /Registro de ações/ })).not.toBeInTheDocument();
    expect(managementLog).not.toHaveBeenCalled();
  });

  it("oferece nova tentativa quando as listas não carregam", async () => {
    const client = manager();
    const listMembers = client.listMembers.bind(client);
    let failures = 1;
    client.listMembers = (signal) =>
      failures-- > 0 ? Promise.reject(new TypeError("Failed to fetch")) : listMembers(signal);
    const user = renderAt(client);

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível falar com o servidor.");
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByRole("region", { name: /Membros ativos/ })).toBeInTheDocument();
  });
});

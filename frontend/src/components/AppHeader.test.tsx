import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { createMockClient, DEMO_MANAGER } from "../services/mockClient";

function renderAt(path: string, manager = false) {
  const user = userEvent.setup();
  const client = createMockClient({ latencyMs: 0, signedIn: true, ...(manager ? { as: DEMO_MANAGER } : {}) });
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

describe("Cabeçalho e navegação (S26-01)", () => {
  it("marca a tela atual com aria-current", async () => {
    const user = renderAt("/", true);
    const nav = await screen.findByRole("navigation", { name: "Principal" });

    expect(within(nav).getByRole("link", { name: "Verificar" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Plágio" })).not.toHaveAttribute("aria-current");

    await user.click(within(nav).getByRole("link", { name: "Gerenciar" }));
    expect(within(nav).getByRole("link", { name: "Gerenciar" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Verificar" })).not.toHaveAttribute("aria-current");
  });

  it.each([
    ["/", "Verificação · IP-Checker"],
    ["/plagio", "Plágio · IP-Checker"],
    ["/perfil", "Perfil · IP-Checker"],
    ["/privacidade", "Aviso de privacidade · IP-Checker"],
  ])("cada tela tem o próprio título (%s)", async (path, title) => {
    renderAt(path);

    await waitFor(() => expect(document.title).toBe(title));
  });

  it("a verificação tem um título de seção", async () => {
    renderAt("/");

    expect(await screen.findByRole("heading", { level: 2, name: "Verificação" })).toBeInTheDocument();
  });

  it("o subtítulo some nas telas estreitas", async () => {
    renderAt("/");
    await screen.findByRole("navigation", { name: "Principal" });

    expect(screen.getByText(/Verificação das permissões das listas/)).toHaveClass("hidden", "sm:block");
  });
});

describe("Menu da conta (S37-04)", () => {
  it("abre pelo primeiro nome, com o nome completo, o cargo, Perfil e Sair; Esc fecha e devolve o foco", async () => {
    const user = renderAt("/");
    const trigger = await screen.findByRole("button", { name: /Menu da conta: / });
    const fullName = trigger.getAttribute("aria-label")?.replace("Menu da conta: ", "") ?? "";

    expect(trigger).toHaveTextContent(fullName.split(" ")[0] ?? "");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Perfil" })).not.toBeInTheDocument();

    await user.click(trigger);

    const menu = screen.getByRole("menu", { name: `Conta de ${fullName}` });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("banner")).toHaveTextContent(fullName);
    expect(screen.getByRole("banner")).toHaveTextContent(/Monitor/);
    expect(within(menu).getByRole("menuitem", { name: "Perfil" })).toHaveFocus();
    expect(within(menu).getByRole("menuitem", { name: "Sair" })).toBeInTheDocument();

    await user.keyboard("{ArrowDown}");
    expect(within(menu).getByRole("menuitem", { name: "Sair" })).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(within(menu).getByRole("menuitem", { name: "Perfil" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("Perfil leva ao perfil e fecha o menu; Sair encerra a sessão", async () => {
    const user = renderAt("/");
    await user.click(await screen.findByRole("button", { name: /Menu da conta/ }));
    await user.click(screen.getByRole("menuitem", { name: "Perfil" }));

    expect(await screen.findByRole("heading", { name: "Perfil" })).toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Menu da conta/ }));
    await user.click(screen.getByRole("menuitem", { name: "Sair" }));

    // Sem sessão, o perfil manda para Entrar.
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Menu da conta/ })).not.toBeInTheDocument();
  });

  it("a navegação principal fica só com as telas; Perfil e Sair não estão nela", async () => {
    renderAt("/", true);
    const nav = await screen.findByRole("navigation", { name: "Principal" });

    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Verificar", "Plágio", "Gerenciar"]);
    expect(within(nav).queryByRole("button")).not.toBeInTheDocument();
  });
});

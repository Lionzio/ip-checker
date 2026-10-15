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

    // As setas percorrem Perfil, os três temas e Sair, dando a volta nas pontas.
    await user.keyboard("{ArrowUp}");
    expect(within(menu).getByRole("menuitem", { name: "Sair" })).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(within(menu).getByRole("menuitem", { name: "Perfil" })).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(within(menu).getByRole("menuitemradio", { name: "Claro" })).toHaveFocus();

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

  it("o tema é escolhido no menu, vale no <html> e fica neste navegador (S37-05)", async () => {
    const user = renderAt("/");
    await user.click(await screen.findByRole("button", { name: /Menu da conta/ }));
    const options = screen.getAllByRole("menuitemradio");

    expect(options.map((item) => item.textContent?.replace("✓", ""))).toEqual(["Claro", "Escuro", "Do sistema"]);
    expect(screen.getByRole("menuitemradio", { name: "Do sistema" })).toHaveAttribute("aria-checked", "true");

    await user.click(screen.getByRole("menuitemradio", { name: "Escuro" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("ipc:tema")).toBe("dark");
    expect(screen.getByRole("menuitemradio", { name: "Escuro" })).toHaveAttribute("aria-checked", "true");

    await user.click(screen.getByRole("menuitemradio", { name: "Claro" }));
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("no Perfil, Aparência mostra a mesma escolha do menu", async () => {
    window.localStorage.setItem("ipc:tema", "dark");
    const user = renderAt("/perfil");

    const escuro = await screen.findByRole("radio", { name: "Escuro" });
    expect(escuro).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Claro" }));
    expect(window.localStorage.getItem("ipc:tema")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("a navegação principal fica só com as telas; Perfil e Sair não estão nela", async () => {
    renderAt("/", true);
    const nav = await screen.findByRole("navigation", { name: "Principal" });

    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Verificar", "Plágio", "Turma", "Gerenciar"]);
    expect(within(nav).queryByRole("button")).not.toBeInTheDocument();
  });
});

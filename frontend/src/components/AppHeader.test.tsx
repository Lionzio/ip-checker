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

  it("o subtítulo e o nome de quem está logado somem nas telas estreitas", async () => {
    renderAt("/");
    await screen.findByRole("navigation", { name: "Principal" });

    expect(screen.getByText(/Verificação das permissões das listas/)).toHaveClass("hidden", "sm:block");
    expect(screen.getByText(/· Monitor/).closest("p")).toHaveClass("hidden", "lg:block");
  });
});

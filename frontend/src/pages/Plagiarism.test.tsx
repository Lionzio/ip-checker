import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { type ApiClient, ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { SimilarityResponse } from "../types/api";

function renderAt(client: ApiClient, path = "/plagio") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  );
  return user;
}

function answer(similarity: number, band: SimilarityResponse["band"], shortCode = false): SimilarityResponse {
  return {
    request_id: "r1",
    status: "compared",
    similarity,
    band,
    short_code: shortCode,
    syntax_error: null,
    notice: "A similaridade é um indício, não uma prova: a decisão final sobre plágio é sempre da equipe.",
  };
}

async function compareWith(client: ApiClient) {
  const user = renderAt(client);
  await user.type(await screen.findByLabelText("Código A"), "x = 1");
  await user.type(screen.getByLabelText("Código B"), "y = 1");
  await user.click(screen.getByRole("button", { name: "Verificar" }));
  return user;
}

describe("Painel de plágio (S17-03, FR-29)", () => {
  it("aparece no cabeçalho para qualquer conta ativa", async () => {
    renderAt(createMockClient({ latencyMs: 0, signedIn: true }), "/");

    expect(await screen.findByRole("link", { name: "Plágio" })).toHaveAttribute("href", "/plagio");
  });

  it("leva para Entrar quem abre o painel sem sessão", async () => {
    renderAt(createMockClient({ latencyMs: 0 }));

    expect(await screen.findByLabelText("Nome ou e-mail institucional")).toBeInTheDocument();
  });

  it("só habilita Verificar com os dois códigos preenchidos", async () => {
    const user = renderAt(createMockClient({ latencyMs: 0, signedIn: true }));

    const button = await screen.findByRole("button", { name: "Verificar" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Código A"), "x = 1");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Código B"), "x = 1");
    expect(button).toBeEnabled();
  });

  it("mostra a porcentagem com uma casa decimal, a faixa escrita e o aviso de indício", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const sent: [string, string][] = [];
    client.compare = (a, b) => {
      sent.push([a, b]);
      return Promise.resolve(answer(99, { id: "plagio", label: "Plágio", minimum: 99 }));
    };
    await compareWith(client);

    const result = screen.getByRole("region", { name: "Resultado da comparação" });
    expect(await screen.findByText("99,0%")).toBeInTheDocument();
    expect(result).toHaveTextContent("Plágio");
    expect(result).toHaveTextContent("a decisão final sobre plágio é sempre da equipe");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
    expect(sent).toEqual([["x = 1", "y = 1"]]);
  });

  it("avisa quando um dos códigos é curto", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.compare = () =>
      Promise.resolve(answer(84.5, { id: "ligeiramente_suspeito", label: "Ligeiramente suspeito", minimum: 80 }, true));
    await compareWith(client);

    expect(await screen.findByText("84,5%")).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent("Um dos códigos é curto");
  });

  it("diz qual código tem o erro de sintaxe", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.compare = () =>
      Promise.resolve({
        ...answer(0, null),
        status: "syntax_error",
        similarity: null,
        syntax_error: { code: "b", line: 2, col: 5, message: "Faltou ':' no fim da linha." },
      });
    await compareWith(client);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("O código B tem um erro de sintaxe");
    expect(alert).toHaveTextContent("Linha 2, coluna 5: Faltou ':' no fim da linha.");
  });

  it("mostra a recusa da API com a espera", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.compare = () =>
      Promise.reject(new ApiError(429, "RATE_LIMITED", "Você fez muitas requisições em pouco tempo.", 12));
    await compareWith(client);

    expect(await screen.findByRole("alert")).toHaveTextContent("Tente de novo em 12 s.");
  });

  it("leva para Entrar quando a sessão termina", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.compare = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre com a sua conta."));
    await compareWith(client);

    expect(await screen.findByLabelText("Nome ou e-mail institucional")).toBeInTheDocument();
  });

  it("compara de verdade no cliente simulado", async () => {
    const user = renderAt(createMockClient({ latencyMs: 0, signedIn: true }));
    const code = "a = int(input())\nif a > 0:\n    print('positivo')\n";

    await user.type(await screen.findByLabelText("Código A"), code);
    await user.type(screen.getByLabelText("Código B"), code);
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByText("100,0%")).toBeInTheDocument();
  });
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { type ApiClient, ApiError } from "../services/client";
import { createMockClient } from "../services/mockClient";
import type { FeedbackRequest, FeedbackResponse } from "../types/api";

const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";

function answer(text: string, source: FeedbackResponse["source"] = "llm"): FeedbackResponse {
  return { request_id: "f1", status: "valid", text, source, provider: source === "llm" ? "primary" : null };
}

async function verified(client: ApiClient, code = VALID) {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <App client={client} />
    </MemoryRouter>,
  );
  await screen.findByRole("option", { name: "Lista 1: Comandos condicionais" });
  await user.selectOptions(screen.getByLabelText("Lista"), "1");
  await user.type(screen.getByLabelText("Código Python"), code);
  await user.click(screen.getByRole("button", { name: "Verificar" }));
  await screen.findByRole("heading", { name: "Feedback para o aluno" });
  return user;
}

function panel() {
  return screen.getByRole("region", { name: "Feedback para o aluno" });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Feedback para o aluno (S19-01, FR-30)", () => {
  it("gera o feedback do código verificado, com nome e anotação", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const sent: FeedbackRequest[] = [];
    client.feedback = (request) => {
      sent.push(request);
      return Promise.resolve(answer("Olá, Isabella, sou a monitora Ana e seu código estava muito bom."));
    };
    const user = await verified(client);

    const button = within(panel()).getByRole("button", { name: "Gerar feedback" });
    expect(button).toBeDisabled();
    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Isabella Schultz");
    await user.type(within(panel()).getByLabelText(/Anotação importante/), "Testar o zero.");
    // Mudar o editor depois de verificar não muda o código do feedback.
    await user.type(screen.getByLabelText("Código Python"), "\nprint('depois')");
    await user.click(button);

    const text = await within(panel()).findByLabelText("Texto do feedback");
    expect(text).toHaveValue("Olá, Isabella, sou a monitora Ana e seu código estava muito bom.");
    expect(panel()).toHaveTextContent("Escrito com IA a partir do resultado do IP-Checker.");
    expect(sent).toEqual([
      {
        code: VALID,
        list_number: 1,
        question_id: null,
        student_name: "Isabella Schultz",
        annotation: "Testar o zero.",
      },
    ]);
  });

  it("sem anotação, manda null", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    const sent: FeedbackRequest[] = [];
    client.feedback = (request) => {
      sent.push(request);
      return Promise.resolve(answer("Texto.", "template"));
    };
    const user = await verified(client);

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));

    expect(await within(panel()).findByText(/Montado sem IA/)).toBeInTheDocument();
    expect(sent[0]?.annotation).toBeNull();
  });

  it("mostra o texto como texto puro e deixa editar", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () => Promise.resolve(answer("<b>negrito</b> <script>alert(1)</script>"));
    const user = await verified(client);

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));

    const text = await within(panel()).findByLabelText("Texto do feedback");
    expect(text).toHaveValue("<b>negrito</b> <script>alert(1)</script>");
    expect(panel().querySelector("b")).toBeNull();
    expect(panel().querySelector("script")).toBeNull();
    await user.clear(text);
    await user.type(text, "Texto revisado.");
    expect(text).toHaveValue("Texto revisado.");
  });

  it("copia o texto editado", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () => Promise.resolve(answer("Original."));
    const user = await verified(client);
    // Depois do userEvent.setup(), que instala a própria área de transferência.
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));
    const text = await within(panel()).findByLabelText("Texto do feedback");
    await user.type(text, " Com ajuste.");
    await user.click(within(panel()).getByRole("button", { name: "Copiar" }));

    expect(writeText).toHaveBeenCalledWith("Original. Com ajuste.");
    expect(await within(panel()).findByRole("status")).toHaveTextContent("Copiado.");
  });

  it("explica quando não dá para copiar", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () => Promise.resolve(answer("Texto."));
    const user = await verified(client);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new Error("negado")) },
      configurable: true,
    });

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));
    await user.click(await within(panel()).findByRole("button", { name: "Copiar" }));

    expect(await within(panel()).findByRole("status")).toHaveTextContent("Selecione o texto e copie com Ctrl+C.");
  });

  it("com erro de sintaxe não há feedback (Q-18 c)", async () => {
    await verified(createMockClient({ latencyMs: 0, signedIn: true }), "print((1)\n");

    expect(panel()).toHaveTextContent("as permissões não foram verificadas, então não há feedback");
    expect(within(panel()).queryByRole("button", { name: "Gerar feedback" })).not.toBeInTheDocument();
  });

  it("uma nova verificação esconde o texto anterior", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () => Promise.resolve(answer("Texto antigo."));
    const user = await verified(client);

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));
    await within(panel()).findByLabelText("Texto do feedback");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    await waitFor(() => expect(within(panel()).queryByLabelText("Texto do feedback")).not.toBeInTheDocument());
    expect(within(panel()).getByLabelText("Nome do aluno")).toHaveValue("Caio");
  });

  it("mostra a recusa da API com a espera", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () =>
      Promise.reject(new ApiError(429, "RATE_LIMITED", "Você chegou ao limite de feedbacks de hoje.", 3600));
    const user = await verified(client);

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));

    expect(await within(panel()).findByRole("alert")).toHaveTextContent("Tente de novo em 3600 s.");
  });

  it("volta para o início quando a sessão termina", async () => {
    const client = createMockClient({ latencyMs: 0, signedIn: true });
    client.feedback = () => Promise.reject(new ApiError(401, "UNAUTHENTICATED", "Entre."));
    const user = await verified(client);

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Caio");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("o cliente simulado monta o texto pela apresentação de quem avalia", async () => {
    const user = await verified(createMockClient({ latencyMs: 0, signedIn: true }));

    await user.type(within(panel()).getByLabelText("Nome do aluno"), "Isabella Schultz");
    await user.click(within(panel()).getByRole("button", { name: "Gerar feedback" }));

    const text = await within(panel()).findByLabelText("Texto do feedback");
    expect((text as HTMLTextAreaElement).value).toMatch(
      /^Olá, Isabella Schultz, sou a monitora Monitora de Demonstração e seu código estava muito bom\. Sua questão está ótima/,
    );
  });
});

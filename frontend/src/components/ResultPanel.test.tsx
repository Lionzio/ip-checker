import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ValidationState } from "../hooks/useValidateCode";
import type { ValidateResponse } from "../types/api";
import { ResultPanel } from "./ResultPanel";

const BASE: ValidateResponse = {
  request_id: "r1",
  ruleset_version: "2026.2.0",
  status: "valid",
  list_number: 1,
  question_id: null,
  notices: ["QUESTION_RULES_NOT_APPLIED"],
  syntax_error: null,
  violations: [],
};

function renderState(state: ValidationState, onRetry = vi.fn()) {
  render(<ResultPanel state={state} onRetry={onRetry} />);
  return onRetry;
}

describe("ResultPanel", () => {
  it("orienta o aluno antes da primeira verificação", () => {
    renderState({ kind: "idle" });

    expect(screen.getByText("Cole o código, escolha a lista e clique em Verificar.")).toBeInTheDocument();
  });

  it("indica que está verificando", () => {
    renderState({ kind: "loading" });

    expect(screen.getByText("Verificando…")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resultado da verificação" })).toHaveAttribute("aria-busy", "true");
  });

  it("mostra código válido com o aviso de regras da questão", () => {
    renderState({ kind: "success", response: BASE });

    expect(screen.getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeInTheDocument();
    expect(screen.getByText(/permissões específicas da questão não foram consideradas/)).toBeInTheDocument();
    expect(screen.getByText("Regras 2026.2.0")).toBeInTheDocument();
  });

  it("lista as violações com categoria, linha e coluna", () => {
    renderState({
      kind: "success",
      response: {
        ...BASE,
        status: "invalid",
        violations: [
          {
            rule_id: "R-06",
            category: "ANULACAO",
            line: 3,
            col: 1,
            end_line: 3,
            end_col: 4,
            construct: "node:Try",
            allowed_from_list: null,
            message: "try/except é proibido em todas as listas e anula a questão.",
          },
          {
            rule_id: "R-34",
            category: "FORA_DA_LISTA",
            line: 5,
            col: 5,
            end_line: 5,
            end_col: 8,
            construct: "node:For",
            allowed_from_list: 2,
            message: "Laços de repetição (for, while) só são permitidos a partir da Lista 2.",
          },
        ],
      },
    });

    expect(screen.getByRole("heading", { name: "2 violações encontradas" })).toBeInTheDocument();
    expect(screen.getByText("Anulação imediata")).toBeInTheDocument();
    expect(screen.getByText("Linha 3, coluna 1")).toBeInTheDocument();
    expect(screen.getByText("Fora da lista")).toBeInTheDocument();
    expect(screen.getByText(/a partir da Lista 2/)).toBeInTheDocument();
  });

  it("mostra o erro de sintaxe com linha e coluna", () => {
    renderState({
      kind: "success",
      response: {
        ...BASE,
        status: "syntax_error",
        syntax_error: { line: 4, col: 7, message: "faltou ':'" },
      },
    });

    expect(screen.getByRole("heading", { name: "Erro de sintaxe" })).toBeInTheDocument();
    expect(screen.getByText("Linha 4, coluna 7: faltou ':'")).toBeInTheDocument();
  });

  it("explica a entrada recusada sem oferecer nova tentativa", () => {
    renderState({ kind: "rejected", code: "PAYLOAD_TOO_LARGE", message: "O código excede 50 KB." });

    expect(screen.getByText("O código excede 50 KB.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });

  it("mostra o tempo de espera quando o serviço está ocupado", async () => {
    const onRetry = renderState({ kind: "busy", code: "RATE_LIMITED", message: "Muitas verificações.", retryAfterS: 30 });

    expect(screen.getByText("Tente novamente em 30 segundos.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it.each([
    { kind: "network", message: "Não foi possível falar com o servidor." },
    { kind: "timeout", message: "O servidor não respondeu em 10 segundos." },
  ] as const)("oferece nova tentativa em $kind", async (state) => {
    const onRetry = renderState(state);

    expect(screen.getByText(state.message)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

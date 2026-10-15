import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  truncated: false,
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
    expect(screen.getByText(/Nenhuma questão foi escolhida: valeram só as permissões da lista/)).toBeInTheDocument();
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
            explanation: "Por que não vale.",
            alternative: "O que usar no lugar.",
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
            explanation: "Por que não vale.",
            alternative: "O que usar no lugar.",
          },
        ],
      },
    });

    expect(screen.getByRole("heading", { name: "2 violações encontradas" })).toBeInTheDocument();
    expect(screen.getByText("Anulação imediata")).toBeInTheDocument();
    expect(screen.getByText("Linha 3, coluna 1")).toBeInTheDocument();
    expect(screen.getByText("Fora da lista")).toBeInTheDocument();
    expect(screen.getByText(/a partir da Lista 2/)).toBeInTheDocument();
    expect(screen.queryByText(/primeiras violações/)).not.toBeInTheDocument();
  });

  it("mostra a exigência da lista como algo da solução inteira (R-02)", () => {
    renderState({
      kind: "success",
      response: {
        ...BASE,
        status: "invalid",
        violations: [
          {
            rule_id: "R-02",
            category: "EXIGENCIA",
            line: 1,
            col: 1,
            end_line: 1,
            end_col: 1,
            construct: "requirement:R-02",
            allowed_from_list: null,
            message: "A solução não usa o assunto da Lista 1.",
            explanation: "Por que não vale.",
            alternative: "O que usar no lugar.",
          },
        ],
      },
    });

    expect(screen.getByText("Exigência não atendida")).toBeInTheDocument();
    expect(screen.getByText("Solução inteira")).toBeInTheDocument();
    expect(screen.queryByText("Linha 1, coluna 1")).not.toBeInTheDocument();
  });

  it("avisa quando o relatório foi cortado em 200 violações", () => {
    const violation = {
      rule_id: "R-04",
      category: "NAO_CONSTA" as const,
      col: 1,
      end_col: 2,
      construct: "node:Tuple",
      allowed_from_list: null,
      message: "Tuplas não constam no documento.",
      explanation: "Por que não vale.",
      alternative: "O que usar no lugar.",
    };
    const violations = Array.from({ length: 200 }, (_, index) => ({
      ...violation,
      line: index + 1,
      end_line: index + 1,
    }));

    renderState({ kind: "success", response: { ...BASE, status: "invalid", violations, truncated: true } });

    expect(screen.getByText("Mostrando as 200 primeiras violações. Corrija estas e verifique de novo.")).toBeInTheDocument();
  });

  describe("resumo, filtros e cartões (S37-01)", () => {
    const violation = (rule_id: string, category: ValidateResponse["violations"][number]["category"], line: number, message = `Mensagem da ${rule_id}.`) => ({
      rule_id,
      category,
      line,
      col: 1,
      end_line: line,
      end_col: 4,
      construct: "node:X",
      allowed_from_list: null,
      message,
      explanation: `Por que a ${rule_id} não vale.`,
      alternative: `O que usar no lugar da ${rule_id}.`,
    });
    const three = [violation("R-06", "ANULACAO", 3), violation("R-13", "ANULACAO", 5), violation("R-34", "FORA_DA_LISTA", 7)];
    const cards = () => within(screen.getByRole("list", { name: "Regras violadas" })).getAllByRole("listitem");
    const filters = () => within(screen.getByRole("group", { name: "Filtrar por categoria" }));

    it("mostra um contador por categoria e filtra os cartões ao clicar", async () => {
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: three } });

      expect(filters().getByRole("button", { name: "2 anulações imediatas" })).toHaveAttribute("aria-pressed", "false");
      expect(cards()).toHaveLength(3);

      await userEvent.click(filters().getByRole("button", { name: "1 fora da lista" }));
      expect(filters().getByRole("button", { name: "1 fora da lista" })).toHaveAttribute("aria-pressed", "true");
      expect(cards()).toHaveLength(1);
      expect(cards()[0]).toHaveTextContent("R-34");

      await userEvent.click(screen.getByRole("button", { name: "Todas" }));
      expect(cards()).toHaveLength(3);
    });

    it("até 5 regras, os cartões nascem abertos e fecham pelo cabeçalho", async () => {
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: three } });
      const header = screen.getByRole("button", { name: /R-06/, expanded: true });

      expect(screen.getByText("Linha 3, coluna 1")).toBeInTheDocument();
      await userEvent.click(header);

      expect(header).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText("Linha 3, coluna 1")).not.toBeInTheDocument();
      expect(screen.getByText("Mensagem da R-06.")).toBeInTheDocument();
    });

    it("acima de 5 regras, os cartões nascem fechados, e Abrir todos abre todos", async () => {
      const six = ["R-05", "R-06", "R-11", "R-13", "R-34", "R-35"].map((rule, index) => violation(rule, "ANULACAO", index + 1));
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: six } });

      expect(screen.getAllByRole("button", { expanded: false })).toHaveLength(6);
      expect(screen.queryByRole("button", { expanded: true })).not.toBeInTheDocument();

      await userEvent.click(screen.getByRole("button", { name: "Abrir todos" }));
      expect(screen.getAllByRole("button", { expanded: true })).toHaveLength(6);
      expect(screen.getByRole("button", { name: "Fechar todos" })).toBeInTheDocument();
    });

    it("cada regra mostra o porquê e o que usar no lugar (S38-01)", () => {
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: three } });
      const card = cards()[0];

      expect(card).toHaveTextContent("Por quê: Por que a R-06 não vale.");
      expect(card).toHaveTextContent("O que usar: O que usar no lugar da R-06.");
    });

    it("sem os textos (analisador antigo), o cartão não mostra rótulos vazios", () => {
      const bare = three.map((item) => ({ ...item, explanation: "", alternative: "" }));
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: bare } });

      expect(screen.queryByText("Por quê:")).not.toBeInTheDocument();
    });

    it("a exigência (solução inteira) não abre nem fecha", () => {
      renderState({ kind: "success", response: { ...BASE, status: "invalid", violations: [violation("R-02", "EXIGENCIA", 1)] } });

      expect(screen.getByText("Solução inteira")).toBeInTheDocument();
      expect(screen.queryByRole("button", { expanded: false })).not.toBeInTheDocument();
      expect(screen.getByText(/O que usar no lugar da R-02/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { expanded: true })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Abrir todos|Fechar todos/ })).not.toBeInTheDocument();
    });

    it("o trecho traz uma linha de contexto de cada lado, com a da violação em destaque", () => {
      const code = "a = 1\nfor i in x:\n    pass\nb = 2\n";
      render(
        <ResultPanel
          state={{ kind: "success", response: { ...BASE, status: "invalid", violations: [violation("R-34", "FORA_DA_LISTA", 2)] } }}
          onRetry={vi.fn()}
          code={code}
        />,
      );
      const snippet = screen.getByText("for i in x:").closest("pre");

      expect(snippet).toHaveTextContent(/a = 1/);
      expect(snippet).toHaveTextContent(/pass/);
      expect(snippet).not.toHaveTextContent(/b = 2/);
      expect(screen.getByText("for i in x:").closest("[data-marked]")).not.toBeNull();
      expect(screen.getByText("a = 1").closest("[data-marked]")).toBeNull();
    });
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
    renderState({ kind: "rejected", code: "INVALID_INPUT", message: "O código está vazio." });

    expect(screen.getByRole("heading", { name: "O código não pôde ser verificado" })).toBeInTheDocument();
    expect(screen.getByText("O código está vazio.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });

  it("diz que o código excede 50 KB quando a API responde 413 (US-18)", () => {
    renderState({
      kind: "rejected",
      code: "PAYLOAD_TOO_LARGE",
      message: "O código tem 51.201 bytes; o limite é 51.200 bytes (50 KB).",
    });

    expect(screen.getByRole("heading", { name: "O código excede 50 KB" })).toBeInTheDocument();
    expect(screen.getByText("O código tem 51.201 bytes; o limite é 51.200 bytes (50 KB).")).toBeInTheDocument();
  });

  it.each([
    ["RATE_LIMITED", "Limite de verificações atingido"],
    ["OVERLOADED", "Serviço ocupado"],
    ["ANALYZER_UNAVAILABLE", "Serviço indisponível"],
  ] as const)("dá um título próprio ao estado %s", (code, title) => {
    renderState({ kind: "busy", code, message: "Explicação.", retryAfterS: null, receivedAt: Date.now() });

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    // Sem tempo de espera informado, a nova tentativa fica liberada.
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeEnabled();
  });

  describe("tempo de espera (US-18)", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    function renderBusy(retryAfterS: number) {
      return renderState({
        kind: "busy",
        code: "RATE_LIMITED",
        message: "Você fez muitas verificações em pouco tempo.",
        retryAfterS,
        receivedAt: Date.now(),
      });
    }

    it("conta o tempo de espera e só então libera a nova tentativa", () => {
      const onRetry = renderBusy(30);
      const retry = screen.getByRole("button", { name: "Tentar novamente" });

      expect(screen.getByText("Tente novamente em 30 segundos.")).toBeInTheDocument();
      expect(retry).toBeDisabled();

      act(() => void vi.advanceTimersByTime(29_000));
      expect(screen.getByText("Tente novamente em 1 segundo.")).toBeInTheDocument();
      expect(retry).toBeDisabled();

      act(() => void vi.advanceTimersByTime(1_000));
      expect(screen.getByText("Já pode tentar novamente.")).toBeInTheDocument();
      expect(retry).toBeEnabled();

      fireEvent.click(retry);
      expect(onRetry).toHaveBeenCalledOnce();
    });

    it("recomeça a contagem quando chega uma nova resposta de limite", () => {
      const first = { kind: "busy", code: "RATE_LIMITED", message: "Calma.", retryAfterS: 10, receivedAt: Date.now() } as const;
      const { rerender } = render(<ResultPanel state={first} onRetry={vi.fn()} />);
      act(() => void vi.advanceTimersByTime(10_000));
      expect(screen.getByText("Já pode tentar novamente.")).toBeInTheDocument();

      rerender(<ResultPanel state={{ ...first, retryAfterS: 20, receivedAt: Date.now() }} onRetry={vi.fn()} />);

      expect(screen.getByText("Tente novamente em 20 segundos.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
    });

    it("não anuncia cada segundo da contagem a leitores de tela", () => {
      renderBusy(30);

      expect(screen.getByText("Tente novamente em 30 segundos.")).toHaveAttribute("aria-live", "off");
    });
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

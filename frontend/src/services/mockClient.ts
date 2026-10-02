/**
 * Cliente simulado (S2-02): imita o contrato da API sem análise real, para desenvolver a interface
 * antes do backend estar pronto. Reconhece só alguns padrões de texto; não é o motor de regras.
 *
 * Para demonstrar os estados de erro, inclua no código um comentário `# simular: <cenário>`, em que
 * o cenário é `sobrecarga`, `limite`, `indisponivel`, `rede` ou `lento`.
 *
 * A entrada também é simulada (Sprint 13): qualquer nome e senha preenchidos entram como uma
 * monitora de demonstração. Nada é verificado, porque não há servidor.
 */
import type { Account, ListInfo, ValidateRequest, ValidateResponse, Violation } from "../types/api";
import { type ApiClient, ApiError } from "./client";

const MAX_BYTES = 51_200;
const RULESET_VERSION = "2026.2.0";
const ENABLED_LISTS: ListInfo[] = [{ number: 1, title: "Comandos condicionais" }];
export const DEMO_ACCOUNT: Account = {
  name: "Monitora de Demonstração",
  email: "demonstracao@cin.ufpe.br",
  course: "Ciência da Computação",
  treatment: "feminino",
  role: "monitor",
  role_label: "Monitor",
};

type Finding = Pick<Violation, "rule_id" | "category" | "construct" | "allowed_from_list" | "message">;

interface SimulatedRule {
  pattern: RegExp;
  finding: (keyword: string) => Finding;
}

const SIMULATED_RULES: SimulatedRule[] = [
  {
    pattern: /^\s*(for|while)\b/,
    finding: (keyword) => ({
      rule_id: "R-34",
      category: "FORA_DA_LISTA",
      construct: keyword === "for" ? "node:For" : "node:While",
      allowed_from_list: 2,
      message: "Laços de repetição (for, while) só são permitidos a partir da Lista 2.",
    }),
  },
  {
    pattern: /^\s*(try)\s*:/,
    finding: () => ({
      rule_id: "R-06",
      category: "ANULACAO",
      construct: "node:Try",
      allowed_from_list: null,
      message: "try/except é proibido em todas as listas e anula a questão.",
    }),
  },
  {
    pattern: /^\s*(import|from)\s/,
    finding: () => ({
      rule_id: "R-05",
      category: "ANULACAO",
      construct: "node:Import",
      allowed_from_list: null,
      message:
        "O uso de bibliotecas (import) é proibido em todas as listas e anula a questão, inclusive bibliotecas padrão como math.",
    }),
  },
  {
    pattern: /\b(break|continue)\b/,
    finding: (keyword) => ({
      rule_id: "R-11",
      category: "ANULACAO",
      construct: keyword === "break" ? "node:Break" : "node:Continue",
      allowed_from_list: null,
      message: "break e continue são proibidos em todas as listas e anulam a questão.",
    }),
  },
  {
    pattern: /\b(eval)\s*\(/,
    finding: () => ({
      rule_id: "R-04",
      category: "NAO_CONSTA",
      construct: "builtin:eval",
      allowed_from_list: null,
      message: "'eval' não consta no documento de permissões nem no enunciado da questão, por isso é proibido.",
    }),
  },
];

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason);
      return;
    }
    const onAbort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

function thousands(value: number): string {
  return value.toLocaleString("pt-BR");
}

/** Procura o último '(' sem fechamento, ignorando o conteúdo de strings simples. */
function findUnclosedParenthesis(code: string): { line: number; col: number } | null {
  const open: { line: number; col: number }[] = [];
  code.split("\n").forEach((text, index) => {
    let quote: string | null = null;
    for (let col = 0; col < text.length; col += 1) {
      const char = text[col];
      if (quote !== null) {
        if (char === quote) quote = null;
      } else if (char === "'" || char === '"') {
        quote = char;
      } else if (char === "#") {
        break;
      } else if (char === "(") {
        open.push({ line: index + 1, col: col + 1 });
      } else if (char === ")") {
        open.pop();
      }
    }
  });
  return open.at(-1) ?? null;
}

function simulateScenario(code: string): Promise<never> | null {
  const scenario = /#\s*simular:\s*(\w+)/.exec(code)?.[1];
  switch (scenario) {
    case "sobrecarga":
      return Promise.reject(
        new ApiError(503, "OVERLOADED", "O serviço está sobrecarregado no momento.", 10),
      );
    case "limite":
      return Promise.reject(
        new ApiError(429, "RATE_LIMITED", "Muitas verificações em pouco tempo.", 30),
      );
    case "indisponivel":
      return Promise.reject(
        new ApiError(503, "ANALYZER_UNAVAILABLE", "O analisador está indisponível no momento.", 60),
      );
    case "rede":
      return Promise.reject(new TypeError("Failed to fetch"));
    default:
      return null;
  }
}

function findViolations(code: string): Violation[] {
  const violations: Violation[] = [];
  code.split("\n").forEach((text, index) => {
    for (const rule of SIMULATED_RULES) {
      const match = rule.pattern.exec(text);
      const keyword = match?.[1];
      if (match === null || keyword === undefined) continue;
      const col = match.index + match[0].indexOf(keyword) + 1;
      violations.push({
        ...rule.finding(keyword),
        line: index + 1,
        col,
        end_line: index + 1,
        end_col: col + keyword.length,
      });
    }
  });
  return violations;
}

export function createMockClient({
  latencyMs = 400,
  signedIn = false,
}: { latencyMs?: number; signedIn?: boolean } = {}): ApiClient {
  let requests = 0;
  let account: Account | null = signedIn ? DEMO_ACCOUNT : null;

  return {
    async me(signal) {
      await wait(latencyMs, signal);
      if (account === null) {
        throw new ApiError(401, "UNAUTHENTICATED", "Entre com a sua conta da equipe para usar o IP-Checker.");
      }
      return account;
    },

    async login(login, password) {
      await wait(latencyMs);
      if (login.trim() === "" || password === "") {
        throw new ApiError(422, "INVALID_INPUT", "Requisição inválida: envie login (nome ou e-mail) e password (senha).");
      }
      account = DEMO_ACCOUNT;
      return account;
    },

    async logout() {
      await wait(latencyMs);
      account = null;
    },

    async listLists(signal) {
      await wait(latencyMs, signal);
      return ENABLED_LISTS;
    },

    async validate(request: ValidateRequest, signal) {
      const lento = /#\s*simular:\s*lento\b/.test(request.code);
      await wait(lento ? 15_000 : latencyMs, signal);

      const scenario = simulateScenario(request.code);
      if (scenario !== null) return scenario;

      const size = new TextEncoder().encode(request.code).length;
      if (size > MAX_BYTES) {
        throw new ApiError(
          413,
          "PAYLOAD_TOO_LARGE",
          `O código tem ${thousands(size)} bytes; o limite é ${thousands(MAX_BYTES)} bytes (50 KB).`,
        );
      }
      if (request.code.trim() === "") {
        throw new ApiError(422, "INVALID_INPUT", "O código está vazio.");
      }
      if (!ENABLED_LISTS.some((list) => list.number === request.list_number)) {
        throw new ApiError(
          422,
          "LIST_NOT_ENABLED",
          `A Lista ${request.list_number} ainda não está habilitada.`,
        );
      }

      requests += 1;
      const base = {
        request_id: `simulado-${requests}`,
        ruleset_version: RULESET_VERSION,
        list_number: request.list_number,
        question_id: request.question_id ?? null,
        notices: request.question_id === null ? ["QUESTION_RULES_NOT_APPLIED" as const] : [],
      };

      const unclosed = findUnclosedParenthesis(request.code);
      if (unclosed !== null) {
        return {
          ...base,
          status: "syntax_error",
          syntax_error: { ...unclosed, message: "o '(' foi aberto e nunca fechado" },
          violations: [],
          truncated: false,
        } satisfies ValidateResponse;
      }

      const violations = findViolations(request.code);
      // Exigência da Lista 1 (R-02): sem if nem ternário, a solução inteira é apontada.
      if (!/\bif\b/.test(request.code.replace(/#.*$/gm, ""))) {
        violations.unshift({
          rule_id: "R-02",
          category: "EXIGENCIA",
          construct: "requirement:R-02",
          allowed_from_list: null,
          message:
            "A solução não usa o assunto da Lista 1: é obrigatório um comando condicional (if, com ou sem elif/else) ou o operador ternário. Sem ele, a questão é anulada.",
          line: 1,
          col: 1,
          end_line: 1,
          end_col: 1,
        });
      }
      return {
        ...base,
        status: violations.length === 0 ? "valid" : "invalid",
        syntax_error: null,
        violations,
        truncated: false,
      } satisfies ValidateResponse;
    },
  };
}

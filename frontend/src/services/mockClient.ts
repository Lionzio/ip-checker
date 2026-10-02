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
import type {
  Account,
  ListInfo,
  ManagedAccount,
  Role,
  SimilarityBand,
  ValidateRequest,
  ValidateResponse,
  Violation,
} from "../types/api";
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
  has_password: true,
  can_manage: false,
};
/** Uma conta que gerencia a equipe, para os testes da tela de gerenciamento (Sprint 15). */
export const DEMO_MANAGER: Account = {
  ...DEMO_ACCOUNT,
  name: "Professora de Demonstração",
  email: "professora@cin.ufpe.br",
  role: "professor",
  role_label: "Professor",
  can_manage: true,
};

const ROLE_LABELS: Record<Role, string> = {
  desenvolvedor: "Monitor e desenvolvedor",
  professor: "Professor",
  monitor_chefe: "Monitor-chefe",
  monitor: "Monitor",
};
/** O simulado age como um professor: atribui professor, monitor-chefe e monitor (FR-27). */
const MANAGER_ROLES: Role[] = ["professor", "monitor_chefe", "monitor"];

function teamMember(
  id: string,
  name: string,
  status: ManagedAccount["status"],
  role: Role | null,
  wasHeadMonitor = false,
): ManagedAccount & { wasHeadMonitor: boolean } {
  return {
    id,
    name,
    email: `${id}@cin.ufpe.br`,
    course: "Ciência da Computação",
    signup_method: "senha",
    requested_at: "2026-10-01T12:00:00Z",
    role,
    role_label: role === null ? null : ROLE_LABELS[role],
    status,
    status_label: "",
    actions: [],
    roles: [],
    removal_status: null,
    wasHeadMonitor,
  };
}

/** As faixas do FR-29, só para a simulação; as de verdade vêm da API. */
const SIMULATED_BANDS: SimilarityBand[] = [
  { id: "plagio", label: "Plágio", minimum: 99 },
  { id: "altas_chances", label: "Altas chances de plágio", minimum: 95 },
  { id: "requer_atencao", label: "Requer atenção", minimum: 90 },
  { id: "ligeiramente_suspeito", label: "Ligeiramente suspeito", minimum: 80 },
  { id: "sem_suspeitas", label: "Sem suspeitas", minimum: 0 },
];

const STATUS_LABELS: Record<ManagedAccount["status"], string> = {
  aguardando_verificacao: "E-mail não confirmado",
  aguardando_aprovacao: "Pendente",
  ativo: "Ativo",
  recusado: "Recusado",
  ex_monitor: "Ex-monitor",
  conselheiro: "Conselheiro",
  inativo: "Inativo",
};

/** As ações e os cargos que a professora simulada vê em cada conta. */
function asSeen(member: ManagedAccount & { wasHeadMonitor: boolean }): ManagedAccount {
  const { wasHeadMonitor, ...account } = member;
  const base = { ...account, status_label: STATUS_LABELS[account.status], removal_status: null };
  if (account.role === "desenvolvedor") return { ...base, actions: [], roles: [] };
  if (account.status === "aguardando_aprovacao") return { ...base, actions: ["aprovar", "recusar"], roles: MANAGER_ROLES };
  if (account.status === "ativo") {
    const removal = account.role === "professor" ? "inativo" : wasHeadMonitor ? "conselheiro" : "ex_monitor";
    return {
      ...base,
      actions: ["alterar_cargo", "remover"],
      roles: MANAGER_ROLES.filter((role) => role !== account.role),
      removal_status: removal,
    };
  }
  return { ...base, actions: ["reativar"], roles: MANAGER_ROLES };
}

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
  as = DEMO_ACCOUNT,
  google = false,
}: { latencyMs?: number; signedIn?: boolean; as?: Account; google?: boolean } = {}): ApiClient {
  let requests = 0;
  let account: Account | null = signedIn ? as : null;
  const team = [
    teamMember("dev", "Vinícius Leôncio", "ativo", "desenvolvedor"),
    teamMember("ana", "Ana Pereira", "aguardando_aprovacao", null),
    teamMember("bruno", "Bruno Lima", "ativo", "monitor"),
    teamMember("carla", "Carla Souza", "ex_monitor", "monitor"),
  ];

  function find(id: string) {
    const member = team.find((candidate) => candidate.id === id);
    if (member === undefined) throw new ApiError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.");
    return member;
  }

  function requireManager() {
    if (account === null || !account.can_manage) {
      throw new ApiError(403, "FORBIDDEN", "Você não tem permissão para esta ação.");
    }
  }

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
      account = as;
      return account;
    },

    async logout() {
      await wait(latencyMs);
      account = null;
    },

    async register(request) {
      await wait(latencyMs);
      return request.email.trim().toLowerCase();
    },

    async verifyEmail(token) {
      await wait(latencyMs);
      if (token === "") {
        throw new ApiError(422, "INVALID_TOKEN", "O link de verificação é inválido, já foi usado ou venceu. Peça um novo.");
      }
    },

    async resendVerification() {
      await wait(latencyMs);
    },

    async updateProfile(update) {
      await wait(latencyMs);
      const current = account ?? DEMO_ACCOUNT;
      account = {
        ...current,
        name: update.name ?? current.name,
        course: update.course ?? current.course,
        treatment: update.treatment ?? current.treatment,
      };
      return account;
    },

    async changePassword() {
      await wait(latencyMs);
    },

    async compare(codeA, codeB, signal) {
      await wait(latencyMs, signal);
      // Simulação grosseira: compara as linhas sem espaços. O detector de verdade é o do analisador.
      const lines = (code: string) =>
        new Set(code.split("\n").map((line) => line.replace(/\s+/g, "")).filter(Boolean));
      const a = lines(codeA);
      const b = lines(codeB);
      if (a.size === 0 || b.size === 0) {
        throw new ApiError(422, "INVALID_INPUT", "Cole os dois códigos para comparar.");
      }
      const shared = [...a].filter((line) => b.has(line)).length;
      const similarity = Math.round((2000 * shared) / (a.size + b.size)) / 10;
      const band = SIMULATED_BANDS.find((candidate) => similarity >= candidate.minimum) ?? {
        id: "sem_suspeitas" as const,
        label: "Sem suspeitas",
        minimum: 0,
      };
      return {
        request_id: `simulado-${(requests += 1)}`,
        status: "compared",
        similarity,
        band,
        short_code: Math.min(a.size, b.size) < 6,
        syntax_error: null,
        notice: "A similaridade é um indício, não uma prova: a decisão final sobre plágio é sempre da equipe.",
      };
    },

    async options(signal) {
      await wait(latencyMs, signal);
      return { google };
    },

    async googlePending(signal) {
      await wait(latencyMs, signal);
      if (!google) {
        throw new ApiError(422, "INVALID_TOKEN", "O cadastro pelo Google expirou. Entre com o Google de novo para continuar.");
      }
      return { email: "demonstracao.google@cin.ufpe.br", name: "Pessoa do Google" };
    },

    async completeGoogle() {
      await wait(latencyMs);
      return "demonstracao.google@cin.ufpe.br";
    },

    async listRequests(signal) {
      await wait(latencyMs, signal);
      requireManager();
      return team.filter((member) => member.status === "aguardando_aprovacao").map(asSeen);
    },

    async listMembers(signal) {
      await wait(latencyMs, signal);
      requireManager();
      return {
        active: team.filter((member) => member.status === "ativo").map(asSeen),
        removed: team
          .filter((member) => ["ex_monitor", "conselheiro", "inativo"].includes(member.status))
          .map(asSeen),
      };
    },

    async approve(id, role) {
      await wait(latencyMs);
      requireManager();
      Object.assign(find(id), { status: "ativo", role, role_label: ROLE_LABELS[role] });
    },

    async reject(id) {
      await wait(latencyMs);
      requireManager();
      find(id).status = "recusado";
    },

    async changeRole(id, role) {
      await wait(latencyMs);
      requireManager();
      const member = find(id);
      Object.assign(member, { role, role_label: ROLE_LABELS[role] });
      member.wasHeadMonitor ||= role === "monitor_chefe";
    },

    async remove(id) {
      await wait(latencyMs);
      requireManager();
      const member = find(id);
      member.status = asSeen(member).removal_status ?? "ex_monitor";
    },

    async reactivate(id, role) {
      await wait(latencyMs);
      requireManager();
      Object.assign(find(id), { status: "ativo", role, role_label: ROLE_LABELS[role] });
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

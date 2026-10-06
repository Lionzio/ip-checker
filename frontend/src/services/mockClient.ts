/**
 * Cliente simulado (S2-02): imita o contrato da API sem análise real, para desenvolver a interface
 * antes do backend estar pronto. Reconhece só alguns padrões de texto; não é o motor de regras.
 *
 * Para demonstrar os estados de erro, inclua no código um comentário `# simular: <cenário>`, em que
 * o cenário é `sobrecarga`, `limite`, `indisponivel`, `rede` ou `lento`. Desde a S26-04 há também
 * `truncado` (o relatório cortado em 200 violações), `limite_analise` (o 422 `ANALYSIS_LIMIT`) e `ia`
 * (o feedback com o trecho livre "escrito por uma IA").
 *
 * Como a API, o simulado exige a sessão (S26-04): sem entrar, as listas, a verificação, o plágio e o
 * feedback respondem 401.
 *
 * A entrada também é simulada (Sprint 13): qualquer nome e senha preenchidos entram como uma
 * monitora de demonstração. Nada é verificado, porque não há servidor.
 */
import type {
  Account,
  ListInfo,
  ManagedAccount,
  ManagementLogEntry,
  Role,
  SimilarityBand,
  SimilarityMatch,
  ValidateRequest,
  ValidateResponse,
  Violation,
} from "../types/api";
import { type ApiClient, ApiError } from "./client";

const MAX_BYTES = 51_200;
const RULESET_VERSION = "2026.2.3";
const ENABLED_LISTS: ListInfo[] = [
  { number: 1, title: "Comandos condicionais" },
  { number: 2, title: "Laços de repetição" },
  // Uma questão só da demonstração, para o seletor de questões (R-01) ter o que mostrar.
  { number: 3, title: "Listas e tuplas", questions: [{ id: "L3-Q1", title: "Questão de demonstração" }] },
  { number: 4, title: "Funções e escopo de variável" },
  { number: 5, title: "Dicionários" },
  { number: 6, title: "Recursão" },
];
export const DEMO_ACCOUNT: Account = {
  name: "Monitora de Demonstração",
  email: "demonstracao@cin.ufpe.br",
  course: "Ciência da Computação",
  treatment: "feminino",
  role: "monitor",
  role_label: "Monitor",
  has_password: true,
  can_manage: false,
  can_view_log: false,
};
/** Uma conta que gerencia a equipe, para os testes da tela de gerenciamento (Sprint 15). */
export const DEMO_MANAGER: Account = {
  ...DEMO_ACCOUNT,
  name: "Professora de Demonstração",
  email: "professora@cin.ufpe.br",
  role: "professor",
  role_label: "Professor",
  can_manage: true,
  can_view_log: true,
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

/** A apresentação do FR-30, só para a simulação; a de verdade é montada pela API. */
const SIMULATED_PRESENTATIONS: Record<Exclude<Role, "desenvolvedor">, Record<Account["treatment"], string>> = {
  monitor: { masculino: "sou o monitor {nome}", feminino: "sou a monitora {nome}", neutro: "aqui é {nome}, da monitoria" },
  monitor_chefe: {
    masculino: "sou o monitor-chefe {nome}",
    feminino: "sou a monitora-chefe {nome}",
    neutro: "aqui é {nome}, da chefia da monitoria",
  },
  professor: {
    masculino: "sou o professor {nome}",
    feminino: "sou a professora {nome}",
    neutro: "aqui é {nome}, docente da disciplina",
  },
};

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
    case "limite_analise":
      return Promise.reject(
        new ApiError(422, "ANALYSIS_LIMIT", "O código é complexo demais para ser analisado (limite de nós da árvore)."),
      );
    default:
      return null;
  }
}

/** A exigência do assunto de cada lista (R-02, Q-05; R-68 na Lista 6), só para a simulação. */
const SIMULATED_REQUIREMENTS: Record<number, { pattern: RegExp; message: string; ruleId?: string }> = {
  1: {
    pattern: /\bif\b/,
    message:
      "A solução não usa o assunto da Lista 1: é obrigatório um comando condicional (if, com ou sem elif/else) ou o operador ternário. Sem ele, a questão é anulada.",
  },
  2: {
    pattern: /\b(for|while)\b/,
    message:
      "A solução não usa o assunto da Lista 2: é obrigatório um laço de repetição (for ou while). Sem ele, a questão é anulada.",
  },
  3: {
    pattern: /\[|\(.*,.*\)|\blist\(|\btuple\(/,
    message:
      "A solução não usa o assunto da Lista 3: é obrigatório usar uma lista ou uma tupla (literal, list(), tuple() ou list comprehension). Sem isso, a questão é anulada.",
  },
  4: {
    pattern: /\bdef\b/,
    message: "A solução não usa o assunto da Lista 4: é obrigatório definir uma função com def. Sem ela, a questão é anulada.",
  },
  5: {
    pattern: /\{|\bdict\(/,
    message:
      "A solução não usa o assunto da Lista 5: é obrigatório usar um dicionário (literal ou dict()). Sem ele, a questão é anulada.",
  },
  6: {
    // Aproximação: um def que chama o próprio nome no corpo (o motor real usa o grafo de chamadas).
    pattern: /^def\s+(\w+)\s*\(.*\n(?:[ \t]+.*\n)*?[ \t]+.*\b\1\s*\(/m,
    ruleId: "R-68",
    message:
      "A solução não usa o assunto da Lista 6: é obrigatória a recursão, uma função que chama a si mesma, direta ou indiretamente. Sem ela, a questão é anulada.",
  },
};

function findViolations(code: string, listNumber: number): Violation[] {
  const violations: Violation[] = [];
  code.split("\n").forEach((text, index) => {
    for (const rule of SIMULATED_RULES) {
      const match = rule.pattern.exec(text);
      const keyword = match?.[1];
      if (match === null || keyword === undefined) continue;
      const finding = rule.finding(keyword);
      // Cumulatividade (R-03): o que é liberado numa lista vale dali em diante.
      if (finding.allowed_from_list !== null && finding.allowed_from_list <= listNumber) continue;
      const col = match.index + match[0].indexOf(keyword) + 1;
      violations.push({
        ...finding,
        line: index + 1,
        col,
        end_line: index + 1,
        end_col: col + keyword.length,
      });
    }
  });
  return violations;
}

const SIMULATED_NOTICE =
  "A similaridade é um indício, não uma prova: a decisão final sobre plágio é sempre da equipe.";

function simulatedBand(similarity: number): SimilarityBand {
  return (
    SIMULATED_BANDS.find((candidate) => similarity >= candidate.minimum) ?? {
      id: "sem_suspeitas",
      label: "Sem suspeitas",
      minimum: 0,
    }
  );
}

/** Linhas iguais (sem espaços) nos dois códigos, cada uma usada uma vez: os "trechos" simulados. */
function simulatedMatches(codeA: string, codeB: string): SimilarityMatch[] {
  const linesB = codeB.split("\n").map((line) => line.replace(/\s+/g, ""));
  const used = new Set<number>();
  const found: SimilarityMatch[] = [];
  codeA.split("\n").forEach((line, index) => {
    const text = line.replace(/\s+/g, "");
    if (text === "") return;
    const other = linesB.findIndex((candidate, position) => candidate === text && !used.has(position));
    if (other === -1) return;
    used.add(other);
    found.push({ a_first: index + 1, a_last: index + 1, b_first: other + 1, b_last: other + 1 });
  });
  return found;
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

  function requireSession() {
    if (account === null) {
      throw new ApiError(401, "UNAUTHENTICATED", "Entre com a sua conta da equipe para usar o IP-Checker.");
    }
  }

  function requireManager() {
    if (account === null || !account.can_manage) {
      throw new ApiError(403, "FORBIDDEN", "Você não tem permissão para esta ação.");
    }
  }

  // Registro das ações (REC-06): o simulado anota cada ação, como o backend faz na transação.
  const log: ManagementLogEntry[] = [];
  const ACTION_LABELS: Record<ManagementLogEntry["action"], string> = {
    aprovar: "Aprovou",
    recusar: "Recusou",
    alterar_cargo: "Alterou o cargo de",
    remover: "Removeu",
    reativar: "Reativou",
  };

  function record(action: ManagementLogEntry["action"], id: string, change: () => void) {
    const member = find(id);
    const before = { status: member.status, role: member.role };
    change();
    log.unshift({
      at: new Date().toISOString(),
      action,
      action_label: ACTION_LABELS[action],
      actor_name: account?.name ?? "",
      actor_role_label: account?.role_label ?? null,
      target_name: member.name,
      from_status: before.status,
      from_status_label: STATUS_LABELS[before.status],
      to_status: member.status,
      to_status_label: STATUS_LABELS[member.status],
      from_role: before.role,
      from_role_label: before.role === null ? null : ROLE_LABELS[before.role],
      to_role: member.role,
      to_role_label: member.role === null ? null : ROLE_LABELS[member.role],
    });
  }

  const client: ApiClient = {
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

    async forgotPassword() {
      await wait(latencyMs);
    },

    async resetPassword(token) {
      await wait(latencyMs);
      if (token === "") {
        throw new ApiError(422, "INVALID_TOKEN", "O link de redefinição é inválido, já foi usado ou venceu. Peça um novo.");
      }
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
      requireSession();
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
      const containment = Math.round((1000 * shared) / Math.min(a.size, b.size)) / 10;
      return {
        request_id: `simulado-${(requests += 1)}`,
        status: "compared",
        similarity,
        band: simulatedBand(similarity),
        short_code: Math.min(a.size, b.size) < 6,
        syntax_error: null,
        notice: SIMULATED_NOTICE,
        metrics: { sequence: similarity, tree_dice: similarity, tree_containment: containment },
        matches: simulatedMatches(codeA, codeB),
      };
    },

    async compareClass(code, solutions, signal) {
      await wait(latencyMs, signal);
      requireSession();
      if (code.trim() === "") throw new ApiError(422, "INVALID_INPUT", "Solução comparada: o código está vazio.");
      const results = await Promise.all(
        solutions.map(async (solution) => {
          if (solution.code.trim() === "") {
            return {
              label: solution.label,
              status: "rejected" as const,
              similarity: null,
              band: null,
              short_code: false,
              metrics: null,
              syntax_error: null,
              message: "O código está vazio.",
            };
          }
          const compared = await client.compare(code, solution.code, signal);
          return {
            label: solution.label,
            status: "compared" as const,
            similarity: compared.similarity,
            band: compared.band,
            short_code: compared.short_code,
            metrics: compared.metrics ? { ...compared.metrics, sequence: null } : null,
            syntax_error: null,
            message: null,
          };
        }),
      );
      results.sort((first, second) => (second.similarity ?? -1) - (first.similarity ?? -1));
      return {
        request_id: `simulado-${(requests += 1)}`,
        status: "compared",
        syntax_error: null,
        results,
        notice: SIMULATED_NOTICE,
      };
    },

    async options(signal) {
      await wait(latencyMs, signal);
      return { google, feedback_ai: false };
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
      record("aprovar", id, () => Object.assign(find(id), { status: "ativo", role, role_label: ROLE_LABELS[role] }));
    },

    async reject(id) {
      await wait(latencyMs);
      requireManager();
      record("recusar", id, () => {
        find(id).status = "recusado";
      });
    },

    async changeRole(id, role) {
      await wait(latencyMs);
      requireManager();
      record("alterar_cargo", id, () => {
        const member = find(id);
        Object.assign(member, { role, role_label: ROLE_LABELS[role] });
        member.wasHeadMonitor ||= role === "monitor_chefe";
      });
    },

    async remove(id) {
      await wait(latencyMs);
      requireManager();
      record("remover", id, () => {
        const member = find(id);
        member.status = asSeen(member).removal_status ?? "ex_monitor";
      });
    },

    async managementLog(signal) {
      await wait(latencyMs, signal);
      if (account === null || !account.can_view_log) {
        throw new ApiError(403, "FORBIDDEN", "Você não tem permissão para esta ação.");
      }
      return [...log];
    },

    async reactivate(id, role) {
      await wait(latencyMs);
      requireManager();
      record("reativar", id, () => Object.assign(find(id), { status: "ativo", role, role_label: ROLE_LABELS[role] }));
    },

    async listLists(signal) {
      await wait(latencyMs, signal);
      requireSession();
      return ENABLED_LISTS;
    },

    async validate(request: ValidateRequest, signal) {
      const lento = /#\s*simular:\s*lento\b/.test(request.code);
      await wait(lento ? 15_000 : latencyMs, signal);
      requireSession();

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
      const list = ENABLED_LISTS.find((item) => item.number === request.list_number);
      if (list === undefined) {
        throw new ApiError(
          422,
          "LIST_NOT_ENABLED",
          `A Lista ${request.list_number} ainda não está habilitada.`,
        );
      }
      const questionId = request.question_id ?? null;
      if (questionId !== null && !(list.questions ?? []).some((question) => question.id === questionId)) {
        throw new ApiError(422, "UNKNOWN_QUESTION", `A questão ${questionId} não está cadastrada no IP-Checker.`);
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

      const violations = findViolations(request.code, request.list_number);
      if (/#\s*simular:\s*truncado\b/.test(request.code)) {
        // O motor para em 200 violações (NFR-08); o simulado repete a primeira linha do código.
        const filler = Array.from({ length: 200 }, (_, index): Violation => ({
          rule_id: "R-04",
          category: "NAO_CONSTA",
          construct: "node:Simulado",
          allowed_from_list: null,
          message: "Construção simulada que não consta no documento da lista.",
          line: index + 1,
          col: 1,
          end_line: index + 1,
          end_col: 2,
        }));
        return {
          ...base,
          status: "invalid",
          syntax_error: null,
          violations: filler,
          truncated: true,
        } satisfies ValidateResponse;
      }
      // Exigência do assunto da lista (R-02; R-68 na Lista 6): sem ele, a solução inteira é apontada.
      const requirement = SIMULATED_REQUIREMENTS[request.list_number];
      if (requirement !== undefined && !requirement.pattern.test(request.code.replace(/#.*$/gm, ""))) {
        const ruleId = requirement.ruleId ?? "R-02";
        violations.unshift({
          rule_id: ruleId,
          category: "EXIGENCIA",
          construct: `requirement:${ruleId}`,
          allowed_from_list: null,
          message: requirement.message,
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

    async feedback(request, signal) {
      await wait(latencyMs, signal);
      requireSession();
      const checked = await client.validate(
        { code: request.code, list_number: request.list_number, question_id: null },
        signal,
      );
      if (checked.status === "syntax_error") {
        throw new ApiError(
          422,
          "INVALID_INPUT",
          "O código tem um erro de sintaxe: as permissões não foram verificadas, então não há feedback.",
        );
      }
      const who = account ?? DEMO_ACCOUNT;
      const row = who.role === "desenvolvedor" ? "monitor" : who.role;
      const presentation = SIMULATED_PRESENTATIONS[row][who.treatment].replace("{nome}", who.name);
      const valid = checked.status === "valid";
      const joint = who.treatment === "neutro" ? ", e" : " e";
      const opening = `Olá, ${request.student_name.trim()}, ${presentation}${joint} seu código ${
        valid ? "estava muito bom" : "precisa de ajustes"
      }.`;
      const used = [...new Set(checked.violations.map((violation) => violation.construct.split(":").pop() ?? ""))];
      const sentence = valid
        ? "Sua questão está ótima, não houve nenhuma violação de regras."
        : `Sua questão apresenta problemas, como o uso de ${used.join(", ")}, portanto ela foi anulada.`;
      const ai = /#\s*simular:\s*ia\b/.test(request.code);
      return {
        request_id: `simulado-${(requests += 1)}`,
        status: valid ? "valid" : "invalid",
        text: ai
          ? `${opening} ${sentence} Gostei de como você organizou a leitura dos dados; vale revisar os nomes das variáveis.`
          : `${opening} ${sentence} Texto simulado: no servidor, uma IA ou os modelos de texto escrevem esta parte.`,
        source: ai ? "llm" : "template",
        provider: ai ? "primary" : null,
      };
    },
  };
  return client;
}

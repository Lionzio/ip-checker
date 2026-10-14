/** O relatório da verificação (S26-03): agrupar, ordenar e resumir as violações. */
import type { ValidationState } from "./hooks/useValidateCode";
import { BUSY_TITLES, CATEGORY_COUNTS } from "./labels";
import type { Category, Violation } from "./types/api";

/** Da mais grave para a mais leve: é a ordem do relatório e do resumo. */
export const SEVERITY: Category[] = ["ANULACAO", "PROIBIDO_NA_QUESTAO", "EXIGENCIA", "FORA_DA_LISTA", "NAO_CONSTA"];

export interface RuleGroup {
  ruleId: string;
  category: Category;
  message: string;
  occurrences: Violation[];
}

/** Uma linha por regra, com todas as linhas em que ela aparece, da mais grave para a mais leve. */
export function groupViolations(violations: Violation[]): RuleGroup[] {
  const groups = new Map<string, RuleGroup>();
  for (const violation of violations) {
    const key = `${violation.category}|${violation.rule_id}|${violation.message}`;
    const group = groups.get(key);
    if (group === undefined) {
      groups.set(key, {
        ruleId: violation.rule_id,
        category: violation.category,
        message: violation.message,
        occurrences: [violation],
      });
    } else {
      group.occurrences.push(violation);
    }
  }
  const firstLine = (group: RuleGroup) => Math.min(...group.occurrences.map((item) => item.line));
  return [...groups.values()]
    .map((group) => ({ ...group, occurrences: [...group.occurrences].sort((a, b) => a.line - b.line || a.col - b.col) }))
    .sort((a, b) => SEVERITY.indexOf(a.category) - SEVERITY.indexOf(b.category) || firstLine(a) - firstLine(b));
}

export interface CategoryCount {
  category: Category;
  count: number;
  /** "2 anulações imediatas", "1 fora da lista": o texto do contador e do resumo. */
  label: string;
}

/** Quantas violações há em cada categoria, da mais grave para a mais leve, só as que aparecem (S37-01). */
export function categoryCounts(violations: Violation[]): CategoryCount[] {
  return SEVERITY.flatMap((category) => {
    const count = violations.filter((violation) => violation.category === category).length;
    return count > 0 ? [{ category, count, label: `${count} ${CATEGORY_COUNTS[category][count === 1 ? 0 : 1]}` }] : [];
  });
}

/** "2 anulações imediatas, 1 fora da lista": o resumo do relatório e do leitor de tela. */
export function summarize(violations: Violation[]): string {
  return categoryCounts(violations)
    .map((item) => item.label)
    .join(", ");
}

export interface SnippetLine {
  line: number;
  text: string;
  /** A linha é da violação (e não do contexto). */
  marked: boolean;
}

/** As linhas do trecho (S37-01): a violação com uma linha de contexto antes e outra depois, sem o recuo comum. */
export function snippetLines(code: string, first: number, last: number): SnippetLine[] {
  const all = code.split("\n");
  const end = Math.max(first, last);
  const window: SnippetLine[] = [];
  for (let line = Math.max(1, first - 1); line <= Math.min(all.length, end + 1); line += 1) {
    window.push({ line, text: (all[line - 1] ?? "").replace(/\s+$/, ""), marked: line >= first && line <= end });
  }
  const indents = window.filter((item) => item.text !== "").map((item) => item.text.length - item.text.trimStart().length);
  const indent = indents.length === 0 ? 0 : Math.min(...indents);
  return window.map((item) => ({ ...item, text: item.text.slice(indent) }));
}

/** O texto curto que o leitor de tela anuncia (S26-04): só o resumo, nunca o relatório inteiro. */
export function announcement(state: ValidationState): string {
  switch (state.kind) {
    case "loading":
      // O painel já diz "Verificando…" e fica com aria-busy; anunciar de novo seria repetir.
      return "";
    case "success": {
      const { response } = state;
      if (response.status === "syntax_error") return "Erro de sintaxe.";
      if (response.status === "valid") return "Nenhuma violação encontrada.";
      const count = response.violations.length;
      return `${count === 1 ? "1 violação encontrada" : `${count} violações encontradas`}: ${summarize(response.violations)}.`;
    }
    case "rejected":
      return "O código não pôde ser verificado.";
    case "busy":
      return BUSY_TITLES[state.code] ?? "Serviço ocupado";
    case "network":
    case "timeout":
      return "Sem resposta do servidor.";
    default:
      return "";
  }
}


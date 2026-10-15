/** A correção da turma inteira (S40-01): rótulos, resumo e o CSV, sem nenhum código dentro. */
import type { BatchResult, Category } from "./types/api";

export const BATCH_STATUS: Record<BatchResult["status"], string> = {
  valid: "Válida",
  invalid: "Com violações",
  syntax_error: "Erro de sintaxe",
  rejected: "Recusada",
};

/** As colunas de categoria, da mais grave para a mais leve (a ordem do relatório). */
export const BATCH_COLUMNS: { category: Category; label: string }[] = [
  { category: "ANULACAO", label: "Anulação" },
  { category: "PROIBIDO_NA_QUESTAO", label: "Proibido na questão" },
  { category: "EXIGENCIA", label: "Exigência" },
  { category: "FORA_DA_LISTA", label: "Fora da lista" },
  { category: "NAO_CONSTA", label: "Não consta" },
];

/** O aluno pelo nome do arquivo, sem o `.py`. */
export function studentOf(name: string): string {
  return name.replace(/\.py(?= \(\d+\)$|$)/i, "");
}

export function summary(results: BatchResult[]): Record<BatchResult["status"], number> {
  const counts = { valid: 0, invalid: 0, syntax_error: 0, rejected: 0 };
  for (const result of results) counts[result.status] += 1;
  return counts;
}

const csvCell = (value: string | number) => {
  const text = String(value);
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

/**
 * O CSV da turma: uma linha por aluno, com o status, as violações por categoria, as regras e a
 * semelhança com o gabarito. Separado por ponto e vírgula e com o BOM do UTF-8, para o Excel em
 * português abrir com os acentos certos. Nunca leva o código.
 */
export function batchCsv(results: BatchResult[], context: { list: string; questionId: string | null }): string {
  const header = [
    "aluno",
    "status",
    ...BATCH_COLUMNS.map((column) => column.label.toLowerCase()),
    "regras",
    "gabarito (%)",
    "lista",
    "questão",
  ];
  const rows = results.map((result) => [
    studentOf(result.name),
    BATCH_STATUS[result.status],
    ...BATCH_COLUMNS.map((column) => result.counts[column.category] ?? 0),
    result.rule_ids.join(" "),
    result.gabarito_similarity === null || result.gabarito_similarity === undefined
      ? ""
      : String(result.gabarito_similarity).replace(".", ","),
    context.list,
    context.questionId ?? "",
  ]);
  return "﻿" + [header, ...rows].map((row) => row.map(csvCell).join(";")).join("\r\n") + "\r\n";
}

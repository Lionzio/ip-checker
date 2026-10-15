import { describe, expect, it } from "vitest";
import { reportFileName, reportText } from "./report";
import type { ValidateResponse, Violation } from "./types/api";

const BASE: ValidateResponse = {
  request_id: "r1",
  ruleset_version: "2026.2.7",
  status: "invalid",
  list_number: 1,
  question_id: null,
  notices: [],
  syntax_error: null,
  violations: [],
  truncated: false,
};

const violation = (rule_id: string, category: Violation["category"], line: number): Violation => ({
  rule_id,
  category,
  line,
  col: 1,
  end_line: line,
  end_col: 4,
  construct: "node:X",
  allowed_from_list: null,
  message: `Mensagem da ${rule_id}.`,
  explanation: `Porquê da ${rule_id}.`,
  alternative: `Alternativa da ${rule_id}.`,
});

const CONTEXT = { list: "Lista 1: Comandos condicionais", questionId: null };

describe("Relatório em texto (S38-03)", () => {
  it("lista cada regra com a categoria, as linhas, o porquê e o que usar, sem o código", () => {
    const text = reportText(
      { ...BASE, violations: [violation("R-02", "EXIGENCIA", 1), violation("R-06", "ANULACAO", 3), violation("R-06", "ANULACAO", 7)] },
      CONTEXT,
    );

    expect(text).toBe(
      [
        "IP-Checker: resultado da verificação",
        "Lista 1: Comandos condicionais · sem questão (valem as permissões da lista)",
        "Regras 2026.2.7",
        "",
        "3 violações: 2 anulações imediatas, 1 exigência não atendida.",
        "",
        "[Anulação imediata] R-06: Mensagem da R-06.",
        "  Linhas: 3 (coluna 1), 7 (coluna 1)",
        "  Por quê: Porquê da R-06.",
        "  O que usar: Alternativa da R-06.",
        "",
        "[Exigência não atendida] R-02: Mensagem da R-02.",
        "  Onde: a solução inteira",
        "  Por quê: Porquê da R-02.",
        "  O que usar: Alternativa da R-02.",
        "",
      ].join("\n"),
    );
  });

  it("código válido e erro de sintaxe", () => {
    expect(reportText({ ...BASE, status: "valid" }, { ...CONTEXT, questionId: "L3-Q9" })).toContain("questão L3-Q9");
    expect(reportText({ ...BASE, status: "valid" }, CONTEXT)).toContain("Nenhuma violação encontrada.");
    expect(
      reportText({ ...BASE, status: "syntax_error", syntax_error: { line: 2, col: 9, message: "faltou ':'" } }, CONTEXT),
    ).toContain("Erro de sintaxe na linha 2, coluna 9: faltou ':'");
  });

  it("dá o nome do arquivo pela questão ou pela lista", () => {
    expect(reportFileName(1, null)).toBe("ip-checker-lista-1.txt");
    expect(reportFileName(3, "L3-Q9")).toBe("ip-checker-L3-Q9.txt");
  });
});

/**
 * As soluções da turma coladas num campo só (S27-02): cada uma começa por uma linha `### nome`.
 * Sem nenhuma linha assim, o texto inteiro é uma solução só.
 */
import type { ClassSolution } from "./types/api";

export const MAX_CLASS = 100;
/** O corpo da requisição tem até 128 KB; sobra espaço para os nomes e o JSON. */
export const MAX_CLASS_BYTES = 120 * 1024;

const HEADER = /^#{3,}\s*(.*?)\s*$/;

export function parseClass(text: string): ClassSolution[] {
  const solutions: ClassSolution[] = [];
  let label: string | null = null;
  let lines: string[] = [];
  const flush = () => {
    const code = lines.join("\n").replace(/^\n+|\s+$/g, "");
    if (label !== null || code !== "") {
      const name = (label ?? "").slice(0, 80) || `Solução ${solutions.length + 1}`;
      solutions.push({ label: name, code: code === "" ? "" : `${code}\n` });
    }
  };
  for (const line of text.split("\n")) {
    const header = HEADER.exec(line);
    if (header !== null) {
      flush();
      label = header[1] ?? "";
      lines = [];
    } else {
      lines.push(line);
    }
  }
  flush();
  return solutions;
}

export function classBytes(code: string, solutions: readonly ClassSolution[]): number {
  const encoder = new TextEncoder();
  return encoder.encode(code).length + solutions.reduce((total, item) => total + encoder.encode(item.code).length, 0);
}

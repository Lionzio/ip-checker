/**
 * As soluções da turma coladas num campo só (S27-02, S36-02): cada uma começa por uma linha
 * `=== nome`, que não é Python válido e nunca aparece num código. Numa turma sem nenhuma linha
 * `===`, o formato antigo `### nome` continua aceito, com um aviso, porque um comentário
 * `### ...` dentro do código parte a solução. Sem nenhum separador, o texto inteiro é uma solução.
 *
 * Cada solução sai com um rótulo único (S36-01): um nome repetido ganha um número, como
 * "Ana (2)", para que o resultado e o "Comparar lado a lado" nunca troquem um aluno por outro.
 */
import type { ClassSolution } from "./types/api";

export const MAX_CLASS = 100;
/** O corpo da requisição tem até 128 KB; sobra espaço para os nomes e o JSON. */
export const MAX_CLASS_BYTES = 120 * 1024;
/** O rótulo tem até 80 caracteres na API. */
const MAX_LABEL = 80;

const SEPARATOR = /^={3,}\s*(.*?)\s*$/;
const LEGACY = /^#{3,}\s*(.*?)\s*$/;

export interface ParsedClass {
  solutions: ClassSolution[];
  /** A turma usou o formato antigo `### nome`. */
  legacy: boolean;
  /** Os nomes que apareceram mais de uma vez, na ordem em que apareceram. */
  repeated: string[];
}

export function parseClass(text: string): ParsedClass {
  const allLines = text.split("\n");
  const legacy = !allLines.some((line) => SEPARATOR.test(line)) && allLines.some((line) => LEGACY.test(line));
  const header = legacy ? LEGACY : SEPARATOR;
  const solutions: ClassSolution[] = [];
  const used = new Set<string>();
  const repeated: string[] = [];
  let label: string | null = null;
  let lines: string[] = [];

  const unique = (name: string): string => {
    if (!used.has(name)) return name;
    if (!repeated.includes(name)) repeated.push(name);
    for (let n = 2; ; n++) {
      const suffix = ` (${n})`;
      const candidate = `${name.slice(0, MAX_LABEL - suffix.length)}${suffix}`;
      if (!used.has(candidate)) return candidate;
    }
  };
  const flush = () => {
    const code = lines.join("\n").replace(/^\n+|\s+$/g, "");
    if (label !== null || code !== "") {
      const name = unique((label ?? "").slice(0, MAX_LABEL) || `Solução ${solutions.length + 1}`);
      used.add(name);
      solutions.push({ label: name, code: code === "" ? "" : `${code}\n` });
    }
  };
  for (const line of allLines) {
    const match = header.exec(line);
    if (match !== null) {
      flush();
      label = match[1] ?? "";
      lines = [];
    } else {
      lines.push(line);
    }
  }
  flush();
  return { solutions, legacy, repeated };
}

export function classBytes(code: string, solutions: readonly ClassSolution[]): number {
  const encoder = new TextEncoder();
  return encoder.encode(code).length + solutions.reduce((total, item) => total + encoder.encode(item.code).length, 0);
}

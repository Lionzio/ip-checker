import { type FormEvent, useState } from "react";
import { BAND_STYLES, PERCENT } from "../bands";
import { useApiCall } from "../hooks/useApiCall";
import { classBytes, MAX_CLASS_BYTES, parseClass } from "../plagiarismClass";
import type { PlagiarismClient } from "../services/client";
import type { SimilarityMatrixResponse } from "../types/api";
import { CodeEditor } from "./CodeEditor";
import { Button, Card, ErrorText } from "./ui";

/** Todos contra todos: até 60 soluções (1.770 pares) cabem no prazo do analisador (S40-02). */
export const MAX_MATRIX = 60;
/** O analisador tem 10 s para a turma; o resto cobre a fila e a rede. */
const MATRIX_TIMEOUT_MS = 20_000;
/** Pares mostrados de início: os que pedem leitura, a partir de "Ligeiramente suspeito". */
const SHOWN_MIN = 80;

interface ClassMatrixProps {
  client: PlagiarismClient;
  onUnauthenticated: () => void;
  /** "Comparar lado a lado": leva os dois códigos para o modo "Dois códigos". */
  onSideBySide: (codeA: string, codeB: string) => void;
}

/**
 * Plágio todos contra todos (S40-02, US-31): cada solução da turma com todas as outras, com o peso
 * pela raridade na turma, e os grupos de soluções ligadas a partir de "Requer atenção". O formato
 * é o mesmo do "Contra a turma": cada solução começa por uma linha `=== nome`.
 */
export function ClassMatrix({ client, onUnauthenticated, onSideBySide }: ClassMatrixProps) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<{ response: SimilarityMatrixResponse; codes: Map<string, string> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const call = useApiCall(MATRIX_TIMEOUT_MS, onUnauthenticated);

  const { solutions, repeated } = parseClass(text);
  const problem =
    solutions.length > MAX_MATRIX
      ? `São ${solutions.length} soluções; o limite do todos contra todos é ${MAX_MATRIX}. Use o "Contra a turma" para uma solução de cada vez.`
      : classBytes("", solutions) > MAX_CLASS_BYTES
        ? "As soluções passam de 120 KB juntas: compare a turma em partes."
        : null;
  const ready = solutions.length >= 2 && problem === null && !call.loading;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setShowAll(false);
    const sent = solutions;
    const outcome = await call.run((signal) => client.compareMatrix(sent, signal));
    if (outcome === null) return;
    if (outcome.ok) setResult({ response: outcome.value, codes: new Map(sent.map((item) => [item.label, item.code])) });
    else setError(outcome.message);
  }

  const pairs = result === null ? [] : result.response.pairs;
  const shown = showAll ? pairs : pairs.filter((pair) => pair.similarity >= SHOWN_MIN);
  const invalid = result === null ? [] : result.response.solutions.filter((item) => item.status !== "compared");

  function sideBySide(a: string, b: string) {
    const codeA = result?.codes.get(a);
    const codeB = result?.codes.get(b);
    if (codeA !== undefined && codeB !== undefined) onSideBySide(codeA, codeB);
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        <h3 className="font-medium">Soluções da turma</h3>
        <CodeEditor
          value={text}
          onChange={setText}
          readOnly={call.loading}
          label="Soluções da turma para todos contra todos"
          placeholder={"=== Ana\nn = int(input())\n...\n=== Bruno\n..."}
          describedBy="matriz-dica"
        />
        <p id="matriz-dica" className="text-sm text-slate-600 dark:text-slate-300">
          Cada solução começa por uma linha <code>=== nome</code>. De 2 a {MAX_MATRIX} soluções, somando até 120 KB.{" "}
          {solutions.length === 1 ? "1 solução." : `${solutions.length} soluções.`}
        </p>
        {repeated.length > 0 && (
          <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
            Nomes repetidos ganharam um número, como "{repeated[0]} (2)".
          </p>
        )}
        {problem !== null && <ErrorText>{problem}</ErrorText>}
      </div>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={!ready}>
          {call.loading ? "Comparando…" : "Comparar todos"}
        </Button>
        {call.loading && (
          <Button variant="secondary" onClick={call.cancel}>
            Cancelar
          </Button>
        )}
      </div>
      <section aria-live="polite" aria-label="Resultado todos contra todos" className="flex flex-col gap-3">
        {error !== null && <ErrorText>{error}</ErrorText>}
        {result !== null && (
          <>
            <Card as="div" className="flex flex-col gap-2">
              <h3 className="font-semibold">Grupos de soluções parecidas</h3>
              {result.response.groups.length === 0 ? (
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Nenhum grupo: nenhum par chegou a "Requer atenção" (90%).
                </p>
              ) : (
                <ol className="list-decimal space-y-1 pl-6 text-sm">
                  {result.response.groups.map((group) => (
                    <li key={group.join("|")}>{group.join(", ")}</li>
                  ))}
                </ol>
              )}
              <p className="text-xs text-slate-600 dark:text-slate-300">
                Um grupo junta as soluções ligadas por pares a partir de 90%: se A parece com B e B com C, os três
                ficam juntos.
              </p>
            </Card>
            {invalid.length > 0 && (
              <ul className="text-sm text-red-700 dark:text-red-300">
                {invalid.map((item) => (
                  <li key={item.label}>
                    {item.label}:{" "}
                    {item.syntax_error
                      ? `erro de sintaxe na linha ${item.syntax_error.line}, coluna ${item.syntax_error.col}`
                      : item.message}
                  </li>
                ))}
              </ul>
            )}
            <Card as="div" padding="none" className="overflow-x-auto">
              <table className="w-full min-w-md text-left text-sm">
                <caption className="px-3 py-2 text-left text-sm font-semibold">
                  {showAll ? "Todos os pares" : `Pares a partir de ${SHOWN_MIN}%`}, do mais parecido para o menos
                </caption>
                <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  <tr>
                    <th scope="col" className="px-3 py-2 font-semibold">Par</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Similaridade</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Faixa</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((pair) => (
                    <tr key={`${pair.a}|${pair.b}`} className="border-t border-slate-200 dark:border-slate-700">
                      <th scope="row" className="px-3 py-2 font-medium">
                        {pair.a} × {pair.b}
                      </th>
                      <td className="px-3 py-2 tabular-nums">{PERCENT.format(pair.similarity)}%</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BAND_STYLES[pair.band.id]}`}>
                          {pair.band.label}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <Button variant="link" onClick={() => sideBySide(pair.a, pair.b)} aria-label={`Comparar ${pair.a} e ${pair.b} lado a lado`}>
                          Comparar lado a lado
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {shown.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-2 text-slate-600 dark:text-slate-300">
                        Nenhum par a partir de {SHOWN_MIN}%.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>
            {!showAll && pairs.length > shown.length && (
              <Button variant="link" className="self-start" onClick={() => setShowAll(true)}>
                Mostrar todos os {pairs.length} pares
              </Button>
            )}
            <p className="text-sm text-slate-600 dark:text-slate-300">{result.response.notice}</p>
          </>
        )}
      </section>
    </form>
  );
}

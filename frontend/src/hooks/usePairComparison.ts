import { useRef, useState } from "react";
import type { CodeEditorHandle, LineRange } from "../components/CodeEditor";
import type { PlagiarismClient } from "../services/client";
import type { SimilarityMatch, SimilarityResponse } from "../types/api";
import { useApiCall } from "./useApiCall";

/** A comparação de dois códigos de 50 KB leva menos de 1 s; o resto cobre a fila e a rede. */
export const PLAGIARISM_TIMEOUT_MS = 15_000;

interface Compared {
  codeA: string;
  codeB: string;
  result: SimilarityResponse;
}

/**
 * O estado do modo "Dois códigos" do Plágio (S17-03, FR-29). Fica na página, e não no formulário,
 * para o que foi colado sobreviver à troca de modo (S39-01).
 */
export function usePairComparison(client: PlagiarismClient, onUnauthenticated: () => void) {
  const [codeA, setCodeA] = useState("");
  const [codeB, setCodeB] = useState("");
  const [compared, setCompared] = useState<Compared | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<number | null>(null);
  const [sync, setSync] = useState(true);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const call = useApiCall(PLAGIARISM_TIMEOUT_MS, onUnauthenticated);
  const editorA = useRef<CodeEditorHandle>(null);
  const editorB = useRef<CodeEditorHandle>(null);

  // Os trechos só valem para os códigos que foram comparados.
  const fresh = compared !== null && compared.codeA === codeA && compared.codeB === codeB;
  const matches: SimilarityMatch[] = fresh ? (compared.result.matches ?? []) : [];
  const chosen = current !== null ? matches[current] : undefined;

  async function compare(first = codeA, second = codeB) {
    setError(null);
    setCompared(null);
    setCurrent(null);
    const outcome = await call.run((signal) => client.compare(first, second, signal, questionId));
    if (outcome === null) return;
    if (outcome.ok) setCompared({ codeA: first, codeB: second, result: outcome.value });
    else setError(outcome.message);
  }

  /** Os dois códigos de outro modo, já comparados (S27-03 e S40-02). */
  function compareThese(first: string, second: string) {
    setCodeA(first);
    setCodeB(second);
    void compare(first, second);
  }

  function swap() {
    setCodeA(codeB);
    setCodeB(codeA);
    setCurrent(null);
    if (compared !== null) {
      const result = compared.result;
      setCompared({
        codeA: compared.codeB,
        codeB: compared.codeA,
        result: {
          ...result,
          matches: (result.matches ?? []).map((m) => ({ a_first: m.b_first, a_last: m.b_last, b_first: m.a_first, b_last: m.a_last })),
          gabarito: result.gabarito ? { ...result.gabarito, a: result.gabarito.b, b: result.gabarito.a } : result.gabarito,
        },
      });
    }
  }

  function clear() {
    setCodeA("");
    setCodeB("");
    setCompared(null);
    setError(null);
    setCurrent(null);
    editorA.current?.focus();
  }

  function show(index: number) {
    const match = matches[index];
    if (match === undefined) return;
    setCurrent(index);
    editorA.current?.scrollToLine(match.a_first);
    editorB.current?.scrollToLine(match.b_first);
  }

  const marksA: LineRange[] = matches.map((m) => ({ first: m.a_first, last: m.a_last }));
  const marksB: LineRange[] = matches.map((m) => ({ first: m.b_first, last: m.b_last }));

  return {
    codeA,
    setCodeA,
    codeB,
    setCodeB,
    compared,
    fresh,
    error,
    matches,
    chosen,
    current,
    sync,
    setSync,
    questionId,
    setQuestionId,
    loading: call.loading,
    cancel: call.cancel,
    editorA,
    editorB,
    marksA,
    marksB,
    ready: codeA.trim() !== "" && codeB.trim() !== "" && !call.loading,
    compare,
    compareThese,
    swap,
    clear,
    show,
  };
}

export type PairComparison = ReturnType<typeof usePairComparison>;

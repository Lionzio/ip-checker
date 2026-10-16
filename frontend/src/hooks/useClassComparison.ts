import { type FormEvent, useMemo, useState } from "react";
import { classBytes, MAX_CLASS, MAX_CLASS_BYTES, parseClass } from "../plagiarismClass";
import type { PlagiarismClient } from "../services/client";
import type { SimilarityClassResponse } from "../types/api";
import { useApiCall } from "./useApiCall";

/** Contra a turma, o analisador tem até 10 s. */
export const CLASS_TIMEOUT_MS = 20_000;

/**
 * O estado do modo "Contra a turma" do Plágio (S27-02). Fica na página, e não no formulário, para
 * o que foi colado sobreviver à troca de modo (S39-01).
 */
export function useClassComparison(client: PlagiarismClient, onUnauthenticated: () => void) {
  const [target, setTarget] = useState("");
  const [classText, setClassText] = useState("");
  const [result, setResult] = useState<{ response: SimilarityClassResponse; codes: Map<string, string> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const call = useApiCall(CLASS_TIMEOUT_MS, onUnauthenticated);

  // Separar a turma percorre o texto inteiro: só de novo quando ele muda, não a cada tecla na
  // solução comparada (S39-01).
  const parsed = useMemo(() => parseClass(classText), [classText]);
  const { solutions } = parsed;
  const bytes = classBytes(target, solutions);
  const problem =
    solutions.length > MAX_CLASS
      ? `São ${solutions.length} soluções; o limite é ${MAX_CLASS}.`
      : bytes > MAX_CLASS_BYTES
        ? "As soluções passam de 120 KB juntas: compare a turma em partes."
        : null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    const sent = solutions;
    const outcome = await call.run((signal) => client.compareClass(target, sent, signal));
    if (outcome === null) return;
    if (outcome.ok) setResult({ response: outcome.value, codes: new Map(sent.map((item) => [item.label, item.code])) });
    else setError(outcome.message);
  }

  return {
    target,
    setTarget,
    classText,
    setClassText,
    solutions,
    legacy: parsed.legacy,
    repeated: parsed.repeated,
    problem,
    result,
    error,
    loading: call.loading,
    cancel: call.cancel,
    ready: target.trim() !== "" && solutions.length > 0 && problem === null && !call.loading,
    submit,
  };
}

export type ClassComparison = ReturnType<typeof useClassComparison>;

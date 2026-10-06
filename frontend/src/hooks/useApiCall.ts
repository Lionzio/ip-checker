import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../services/client";
import { errorMessage } from "../ui";

/** O que uma chamada deu: o valor ou a mensagem para a tela. `null`: substituída ou sessão vencida. */
export type CallOutcome<T> = { ok: true; value: T } | { ok: false; message: string; error: unknown };

export const TIMEOUT_MESSAGE = "O servidor não respondeu a tempo. Tente de novo em alguns segundos.";

/**
 * Uma chamada à API do jeito de todas as telas (S26-04): com prazo, cancelando a anterior quando
 * outra começa ou a tela fecha, e com a sessão vencida (401) tratada num lugar só.
 */
export function useApiCall(timeoutMs: number, onUnauthenticated: () => void) {
  const controllerRef = useRef<AbortController | null>(null);
  const [loading, setLoading] = useState(false);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setLoading(false);
  }, []);

  useEffect(
    () => () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
    },
    [],
  );

  const run = useCallback(
    async <T>(call: (signal: AbortSignal) => Promise<T>): Promise<CallOutcome<T> | null> => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs);
      setLoading(true);
      try {
        const value = await call(controller.signal);
        return controllerRef.current === controller ? { ok: true, value } : null;
      } catch (error) {
        // Cancelada, ou substituída por uma chamada mais nova: a tela não muda.
        if (controllerRef.current !== controller) return null;
        if (error instanceof ApiError && error.status === 401) {
          onUnauthenticated();
          return null;
        }
        return { ok: false, message: timedOut ? TIMEOUT_MESSAGE : errorMessage(error), error };
      } finally {
        clearTimeout(timer);
        if (controllerRef.current === controller) {
          controllerRef.current = null;
          setLoading(false);
        }
      }
    },
    [timeoutMs, onUnauthenticated],
  );

  return { run, cancel, loading };
}

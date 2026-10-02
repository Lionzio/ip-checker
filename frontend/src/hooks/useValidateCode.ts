import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type ValidationClient } from "../services/client";
import type { ApiErrorCode, ValidateRequest, ValidateResponse } from "../types/api";

export type ValidationState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; response: ValidateResponse }
  /** Entrada recusada (413/422): o aluno precisa mudar o código ou a lista. */
  | { kind: "rejected"; code: ApiErrorCode; message: string }
  /**
   * Limite de taxa ou sobrecarga (429/503): basta esperar e tentar de novo. `receivedAt` é o
   * instante (Date.now()) em que a resposta chegou, de onde a contagem da espera parte.
   */
  | { kind: "busy"; code: ApiErrorCode; message: string; retryAfterS: number | null; receivedAt: number }
  | { kind: "network"; message: string }
  | { kind: "timeout"; message: string }
  /** A sessão venceu ou foi encerrada (401): a página volta para a tela de entrada. */
  | { kind: "unauthenticated"; message: string };

export const DEFAULT_TIMEOUT_MS = 10_000;

function toErrorState(error: unknown, timedOut: boolean, timeoutMs: number): ValidationState {
  if (timedOut) {
    return {
      kind: "timeout",
      message: `O servidor não respondeu em ${timeoutMs / 1000} segundos.`,
    };
  }
  if (error instanceof ApiError) {
    if (error.status === 401) return { kind: "unauthenticated", message: error.message };
    if (error.status === 429 || error.status === 503) {
      return {
        kind: "busy",
        code: error.code,
        message: error.message,
        retryAfterS: error.retryAfterS,
        receivedAt: Date.now(),
      };
    }
    return { kind: "rejected", code: error.code, message: error.message };
  }
  return {
    kind: "network",
    message: "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.",
  };
}

/** Envia o código para verificação, com tempo limite e cancelamento da requisição anterior. */
export function useValidateCode(client: ValidationClient, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const [state, setState] = useState<ValidationState>({ kind: "idle" });
  const controllerRef = useRef<AbortController | null>(null);
  const lastRequestRef = useRef<ValidateRequest | null>(null);

  useEffect(
    () => () => {
      const controller = controllerRef.current;
      controllerRef.current = null;
      controller?.abort();
    },
    [],
  );

  const validate = useCallback(
    async (request: ValidateRequest) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      lastRequestRef.current = request;
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs);

      setState({ kind: "loading" });
      try {
        const response = await client.validate(request, controller.signal);
        if (controllerRef.current === controller) setState({ kind: "success", response });
      } catch (error) {
        // Uma requisição substituída por outra mais nova não altera o estado.
        if (controllerRef.current === controller) setState(toErrorState(error, timedOut, timeoutMs));
      } finally {
        clearTimeout(timer);
      }
    },
    [client, timeoutMs],
  );

  const retry = useCallback(async () => {
    if (lastRequestRef.current !== null) await validate(lastRequestRef.current);
  }, [validate]);

  return { state, validate, retry };
}

import { useEffect, useState } from "react";
import { ApiError, type ValidationClient } from "../services/client";
import type { ListInfo } from "../types/api";

/**
 * As listas habilitadas, para o seletor de lista (Verificar e Turma). Um 401 leva para Entrar; outra
 * falha vira a mensagem, e `retry` pede de novo (S39-01: antes, cada página tinha a própria cópia).
 */
export function useLists(client: Pick<ValidationClient, "listLists">, onUnauthenticated: () => void) {
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(
      (loaded) => {
        setLists(loaded);
        setError(null);
      },
      (caught: unknown) => {
        if (controller.signal.aborted) return;
        if (caught instanceof ApiError && caught.status === 401) onUnauthenticated();
        else setError("Não foi possível carregar as listas.");
      },
    );
    return () => controller.abort();
  }, [client, onUnauthenticated, attempt]);

  return { lists, error, retry: () => setAttempt((value) => value + 1) };
}

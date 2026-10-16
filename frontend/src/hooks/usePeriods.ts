import { useEffect, useState } from "react";
import { ApiError, type ValidationClient } from "../services/client";
import type { PeriodInfo } from "../types/api";

/**
 * Os períodos carregados no servidor (S43-03): o ativo e até 5 anteriores. Um 401 leva para Entrar;
 * outra falha deixa a lista vazia, e a página segue no período ativo, como antes.
 */
export function usePeriods(client: Pick<ValidationClient, "listPeriods">, onUnauthenticated: () => void) {
  const [periods, setPeriods] = useState<PeriodInfo[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    client.listPeriods(controller.signal).then(setPeriods, (caught: unknown) => {
      if (controller.signal.aborted) return;
      if (caught instanceof ApiError && caught.status === 401) onUnauthenticated();
    });
    return () => controller.abort();
  }, [client, onUnauthenticated]);

  return periods;
}

import { type FormEvent, useEffect, useState } from "react";
import { CodeEditor } from "../components/CodeEditor";
import { ListSelector } from "../components/ListSelector";
import { ResultPanel } from "../components/ResultPanel";
import { useValidateCode } from "../hooks/useValidateCode";
import { ApiError, type ValidationClient } from "../services/client";
import type { ListInfo } from "../types/api";

interface CheckerProps {
  client: ValidationClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

/** Painel principal: verificação das permissões da lista (só com sessão, FR-22). */
export function Checker({ client, onUnauthenticated }: CheckerProps) {
  const [code, setCode] = useState("");
  const [listNumber, setListNumber] = useState<number | null>(null);
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [listsError, setListsError] = useState<string | null>(null);
  const { state, validate, retry } = useValidateCode(client);

  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(setLists, (error: unknown) => {
      if (controller.signal.aborted) return;
      if (error instanceof ApiError && error.status === 401) onUnauthenticated();
      else setListsError("Não foi possível carregar as listas.");
    });
    return () => controller.abort();
  }, [client, onUnauthenticated]);

  useEffect(() => {
    if (state.kind === "unauthenticated") onUnauthenticated();
  }, [state.kind, onUnauthenticated]);

  const loading = state.kind === "loading";
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (listNumber === null) return;
    void validate({ code, list_number: listNumber, question_id: null });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <ListSelector lists={lists} value={listNumber} onChange={setListNumber} disabled={loading} />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          A verificação usa as permissões da lista. As regras específicas de cada questão
          ainda não são consideradas: em caso de divergência, vale o enunciado.
        </p>
        {listsError !== null && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">
            {listsError}
          </p>
        )}
        <CodeEditor value={code} onChange={setCode} disabled={loading} />
        <button
          type="submit"
          disabled={!canVerify}
          className="self-start rounded-md bg-blue-700 px-5 py-2 font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          Verificar
        </button>
      </form>

      <ResultPanel state={state} onRetry={() => void retry()} />
    </div>
  );
}

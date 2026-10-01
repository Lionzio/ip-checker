import { type FormEvent, useEffect, useState } from "react";
import { CodeEditor } from "./components/CodeEditor";
import { ListSelector } from "./components/ListSelector";
import { ResultPanel } from "./components/ResultPanel";
import { useValidateCode } from "./hooks/useValidateCode";
import type { ValidationClient } from "./services/client";
import type { ListInfo } from "./types/api";

interface AppProps {
  client: ValidationClient;
  /** Mostra o aviso de que as respostas são simuladas (cliente simulado). */
  demoMode?: boolean;
}

export function App({ client, demoMode = false }: AppProps) {
  const [code, setCode] = useState("");
  const [listNumber, setListNumber] = useState<number | null>(null);
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [listsError, setListsError] = useState<string | null>(null);
  const { state, validate, retry } = useValidateCode(client);

  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(setLists, () => {
      if (!controller.signal.aborted) setListsError("Não foi possível carregar as listas.");
    });
    return () => controller.abort();
  }, [client]);

  const loading = state.kind === "loading";
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (listNumber === null) return;
    void validate({ code, list_number: listNumber, question_id: null });
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto max-w-6xl">
          <h1 className="text-2xl font-bold">IP-Checker</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Confira se a sua solução respeita as permissões da lista antes de enviar ao Dikastis.
            O código não é executado.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {demoMode && (
          <p
            role="note"
            className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
          >
            Modo demonstração: as respostas são simuladas, sem análise real. Use
            <code className="mx-1"># simular: lento</code> (ou sobrecarga, limite, indisponivel,
            rede) para ver os estados de erro.
          </p>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <form onSubmit={submit} className="flex flex-col gap-4">
            <ListSelector lists={lists} value={listNumber} onChange={setListNumber} disabled={loading} />
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
      </main>
    </div>
  );
}

import { type FormEvent, useEffect, useState } from "react";
import { CodeEditor } from "../components/CodeEditor";
import { type FeedbackForm, FeedbackPanel } from "../components/FeedbackPanel";
import { ListSelector } from "../components/ListSelector";
import { QuestionSelector } from "../components/QuestionSelector";
import { ResultPanel } from "../components/ResultPanel";
import { useValidateCode } from "../hooks/useValidateCode";
import { ApiError, type FeedbackClient, type ValidationClient } from "../services/client";
import type { ListInfo, ValidateRequest } from "../types/api";

interface CheckerProps {
  client: ValidationClient & FeedbackClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

/** Painel principal: verificação das permissões da lista (só com sessão, FR-22). */
export function Checker({ client, onUnauthenticated }: CheckerProps) {
  const [code, setCode] = useState("");
  const [listNumber, setListNumber] = useState<number | null>(null);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [listsError, setListsError] = useState<string | null>(null);
  const { state, validate, retry } = useValidateCode(client);
  // O pedido enviado: é o que o resultado descreve, mesmo que o editor mude depois.
  const [verified, setVerified] = useState<ValidateRequest | null>(null);
  const [feedbackForm, setFeedbackForm] = useState<FeedbackForm>({ student: "", annotation: "" });

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
  const questions = listNumber === null ? null : (lists.find((list) => list.number === listNumber)?.questions ?? []);

  function chooseList(value: number | null) {
    setListNumber(value);
    // As questões são de uma lista só: trocar de lista volta para "sem questão".
    setQuestionId(null);
  }
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (listNumber === null) return;
    const request = { code, list_number: listNumber, question_id: questionId };
    setVerified(request);
    void validate(request);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <ListSelector lists={lists} value={listNumber} onChange={chooseList} disabled={loading} />
        <QuestionSelector questions={questions} value={questionId} onChange={setQuestionId} disabled={loading} />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {questionId === null
            ? "Sem questão, valem só as permissões da lista: se o enunciado liberar ou proibir algo, vale o enunciado."
            : `Valem as permissões da lista e as regras da questão ${questionId}, cadastradas a partir do enunciado.`}
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

      <div className="flex flex-col gap-6">
        <ResultPanel state={state} onRetry={() => void retry()} />
        {state.kind === "success" && verified !== null && (
          <FeedbackPanel
            client={client}
            request={verified}
            verificationId={state.response.request_id}
            status={state.response.status}
            onUnauthenticated={onUnauthenticated}
            form={feedbackForm}
            onFormChange={setFeedbackForm}
          />
        )}
      </div>
    </div>
  );
}

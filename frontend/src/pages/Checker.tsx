import { type FormEvent, useEffect, useRef, useState } from "react";
import { type CodeEditorHandle, CodeEditor } from "../components/CodeEditor";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { GabaritoPanel } from "../components/GabaritoPanel";
import { IndicatorsPanel } from "../components/IndicatorsPanel";
import { ListSelector } from "../components/ListSelector";
import { QuestionSelector } from "../components/QuestionSelector";
import { ResultPanel } from "../components/ResultPanel";
import { Button, ErrorText } from "../components/ui";
import { useDraft } from "../draftContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useValidateCode } from "../hooks/useValidateCode";
import { PAGE_TITLES } from "../labels";
import { ApiError, type FeedbackClient, type ValidationClient } from "../services/client";
import { questionOptions } from "../questions";
import type { ListInfo, ValidateRequest } from "../types/api";

interface CheckerProps {
  client: ValidationClient & FeedbackClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

/**
 * Painel principal: verificação das permissões da lista (só com sessão, FR-22). Feito para corrigir
 * em lote (S26-02): a lista fica lembrada, Ctrl+Enter verifica, o foco vai ao resultado e
 * "Próximo aluno" limpa o código, o nome e a anotação de uma vez.
 */
export function Checker({ client, onUnauthenticated }: CheckerProps) {
  useDocumentTitle(PAGE_TITLES.checker);
  const { draft, setCode, setList, setQuestion, setFeedback, nextStudent } = useDraft();
  const { code, listNumber, questionId } = draft;
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [listsError, setListsError] = useState<string | null>(null);
  const [listsAttempt, setListsAttempt] = useState(0);
  const { state, validate, retry, reset } = useValidateCode(client);
  // O pedido enviado: é o que o resultado descreve, mesmo que o editor mude depois.
  const [verified, setVerified] = useState<ValidateRequest | null>(null);
  const [marked, setMarked] = useState<{ first: number; last: number } | null>(null);
  const [lastFeedback, setLastFeedback] = useState<{ student: string; code: string } | null>(null);
  const editorRef = useRef<CodeEditorHandle>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(
      (loaded) => {
        setLists(loaded);
        setListsError(null);
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) onUnauthenticated();
        else setListsError("Não foi possível carregar as listas.");
      },
    );
    return () => controller.abort();
  }, [client, onUnauthenticated, listsAttempt]);

  useEffect(() => {
    if (state.kind === "unauthenticated") onUnauthenticated();
  }, [state.kind, onUnauthenticated]);

  // Terminada a verificação, o foco e a rolagem vão ao resultado (S26-02).
  useEffect(() => {
    if (state.kind !== "success") return;
    headingRef.current?.focus({ preventScroll: true });
    resultRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [state]);

  const loading = state.kind === "loading";
  const currentList = listNumber === null ? undefined : lists.find((list) => list.number === listNumber);
  const questions = listNumber === null ? null : questionOptions(currentList);
  const registered = questionId !== null && (currentList?.questions ?? []).some((question) => question.id === questionId);
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;
  const stale =
    verified !== null && (verified.code !== code || verified.list_number !== listNumber || verified.question_id !== questionId);

  function verify() {
    if (!canVerify || listNumber === null) return;
    const request = { code, list_number: listNumber, question_id: questionId };
    setVerified(request);
    setMarked(null);
    void validate(request);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    verify();
  }

  function next() {
    nextStudent();
    reset();
    setVerified(null);
    setMarked(null);
    editorRef.current?.focus();
  }

  function selectLines(first: number, last: number) {
    setMarked({ first, last });
    editorRef.current?.selectLines(first, last);
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold">Verificação</h2>
      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={submit} className="flex min-w-0 flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <ListSelector lists={lists} value={listNumber} onChange={setList} disabled={loading} />
            <QuestionSelector questions={questions} value={questionId} onChange={setQuestion} disabled={loading} />
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {questionId === null
              ? "Sem questão, valem só as permissões da lista: se o enunciado liberar ou proibir algo, vale o enunciado."
              : registered
                ? `Valem as permissões da lista e as regras da questão ${questionId}, cadastradas a partir do enunciado.`
                : `A questão ${questionId} não tem regra cadastrada: valem as permissões da lista, e o código é comparado com o gabarito.`}
          </p>
          {listsError !== null && (
            <div className="flex flex-wrap items-center gap-3">
              <ErrorText>{listsError}</ErrorText>
              <Button variant="secondary" onClick={() => setListsAttempt((value) => value + 1)}>
                Tentar novamente
              </Button>
            </div>
          )}
          <CodeEditor
            ref={editorRef}
            value={code}
            onChange={setCode}
            readOnly={loading}
            onSubmitShortcut={verify}
            marked={marked}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={!canVerify}>
              Verificar
            </Button>
            <Button variant="secondary" onClick={next} disabled={code === "" && draft.feedback.student === "" && verified === null}>
              Próximo aluno
            </Button>
          </div>
        </form>

        <div ref={resultRef} className="flex min-w-0 scroll-mt-4 flex-col gap-6">
          <ResultPanel
            state={state}
            onRetry={() => void retry()}
            code={verified?.code}
            stale={stale}
            onSelectLines={selectLines}
            headingRef={headingRef}
          />
          {state.kind === "success" && state.response.gabarito && (
            <GabaritoPanel comparison={state.response.gabarito} onSelectLines={selectLines} />
          )}
          {state.kind === "success" && state.response.indicators && (
            <IndicatorsPanel indicators={state.response.indicators} onSelectLines={selectLines} />
          )}
          {state.kind === "success" && verified !== null && (
            <FeedbackPanel
              client={client}
              request={verified}
              verificationId={state.response.request_id}
              status={state.response.status}
              onUnauthenticated={onUnauthenticated}
              form={draft.feedback}
              onFormChange={setFeedback}
              previous={lastFeedback}
              onGenerated={setLastFeedback}
            />
          )}
        </div>
      </div>
    </div>
  );
}

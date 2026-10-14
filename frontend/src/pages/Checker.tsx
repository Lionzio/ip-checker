import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { type CodeEditorHandle, CodeEditor } from "../components/CodeEditor";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { GabaritoPanel } from "../components/GabaritoPanel";
import { IndicatorsPanel } from "../components/IndicatorsPanel";
import { ListSelector } from "../components/ListSelector";
import { QuestionSelector } from "../components/QuestionSelector";
import { ResultPanel } from "../components/ResultPanel";
import { Button, ErrorText, type TabItem, TabList } from "../components/ui";
import { useDraft } from "../draftContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { NARROW, useMediaQuery } from "../hooks/useMediaQuery";
import { useValidateCode } from "../hooks/useValidateCode";
import { PAGE_TITLES } from "../labels";
import { ApiError, type FeedbackClient, type ValidationClient } from "../services/client";
import { questionOptions } from "../questions";
import type { ListInfo, ValidateRequest } from "../types/api";
import { panelId, tabId } from "../ui";

interface CheckerProps {
  client: ValidationClient & FeedbackClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

type Tab = "resultado" | "indicios" | "feedback";
const TABS = "verificacao";

/**
 * Painel principal: verificação das permissões da lista (só com sessão, FR-22). Feito para corrigir
 * em lote (S26-02): a lista fica lembrada, Ctrl+Enter verifica, o foco vai ao resultado e
 * "Próximo aluno" limpa o código, o nome e a anotação de uma vez. No computador, o editor fica fixo
 * enquanto o resultado rola; no celular, o resultado, os indícios e o feedback viram abas, com um
 * "Voltar ao código" (S37-02).
 */
export function Checker({ client, onUnauthenticated }: CheckerProps) {
  useDocumentTitle(PAGE_TITLES.checker);
  const { draft, setCode, setList, setQuestion, setFeedback, nextStudent } = useDraft();
  const { code, listNumber, questionId } = draft;
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [listsError, setListsError] = useState<string | null>(null);
  const [listsAttempt, setListsAttempt] = useState(0);
  const { state, validate, retry, reset, cancel } = useValidateCode(client);
  // O pedido enviado: é o que o resultado descreve, mesmo que o editor mude depois.
  const [verified, setVerified] = useState<ValidateRequest | null>(null);
  const [marked, setMarked] = useState<{ first: number; last: number } | null>(null);
  const [lastFeedback, setLastFeedback] = useState<{ student: string; code: string } | null>(null);
  const narrow = useMediaQuery(NARROW);
  const [tab, setTab] = useState<Tab>("resultado");
  const editorRef = useRef<CodeEditorHandle>(null);
  const formRef = useRef<HTMLFormElement>(null);
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

  // Terminada a verificação, o foco e a rolagem vão ao resultado (S26-02); a aba já é a do
  // Resultado, porque o Verificar a escolhe antes de enviar (S37-02).
  useEffect(() => {
    if (state.kind !== "success") return;
    headingRef.current?.focus({ preventScroll: true });
    resultRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [state]);

  const loading = state.kind === "loading";
  const currentList = listNumber === null ? undefined : lists.find((list) => list.number === listNumber);
  const questions = listNumber === null ? null : questionOptions(currentList);
  const selected = questionId === null ? undefined : questions?.find((question) => question.id === questionId);
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;
  const stale =
    verified !== null && (verified.code !== code || verified.list_number !== listNumber || verified.question_id !== questionId);

  const success = state.kind === "success";
  const indicators = success && state.response.indicators ? state.response.indicators : null;
  const gabarito = success && state.response.gabarito ? state.response.gabarito : null;
  const tabs: TabItem[] = [
    { id: "resultado", label: "Resultado" },
    ...(indicators !== null ? [{ id: "indicios", label: "Indícios" }] : []),
    ...(success && verified !== null ? [{ id: "feedback", label: "Feedback" }] : []),
  ];
  const activeTab: Tab = tabs.some((item) => item.id === tab) ? tab : "resultado";

  function verify() {
    if (!canVerify || listNumber === null) return;
    const request = { code, list_number: listNumber, question_id: questionId };
    setVerified(request);
    setMarked(null);
    setTab("resultado");
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
    setTab("resultado");
    editorRef.current?.focus();
  }

  function selectLines(first: number, last: number) {
    setMarked({ first, last });
    editorRef.current?.selectLines(first, last);
  }

  function backToCode() {
    editorRef.current?.focus();
    formRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }

  /** No celular, cada painel é uma aba; no computador, todos ficam à vista. */
  function panel(id: Tab, children: ReactNode) {
    if (!narrow) return children;
    return (
      <div
        key={id}
        role="tabpanel"
        id={panelId(TABS, id)}
        aria-labelledby={tabId(TABS, id)}
        hidden={activeTab !== id}
        className="flex flex-col gap-6"
      >
        {children}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold">Verificação</h2>
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <form
          ref={formRef}
          onSubmit={submit}
          className="flex min-w-0 scroll-mt-4 flex-col gap-4 lg:sticky lg:top-4 lg:-mx-0.5 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:px-0.5"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <ListSelector lists={lists} value={listNumber} onChange={setList} disabled={loading} />
            <QuestionSelector questions={questions} value={questionId} onChange={setQuestion} disabled={loading} />
          </div>
          <p id="question-description" className="text-sm text-slate-600 dark:text-slate-300">
            {selected === undefined
              ? "Sem questão, valem só as permissões da lista: se o enunciado liberar ou proibir algo, vale o enunciado."
              : selected.rules
                ? `${selected.id}, "${selected.title}": valem as permissões da lista e as regras da questão ${selected.id}, cadastradas a partir do enunciado.${selected.gabarito ? " O código também é comparado com o gabarito." : ""}`
                : `A questão ${selected.id} não tem regra cadastrada: valem as permissões da lista, e o código é comparado com o gabarito.`}
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
              {loading ? "Verificando…" : "Verificar"}
            </Button>
            {loading && (
              <Button variant="secondary" onClick={cancel}>
                Cancelar
              </Button>
            )}
            <Button variant="secondary" onClick={next} disabled={code === "" && draft.feedback.student === "" && verified === null}>
              Próximo aluno
            </Button>
          </div>
        </form>

        <div ref={resultRef} className="flex min-w-0 scroll-mt-4 flex-col gap-6">
          {narrow && success && <TabList label="Painéis do resultado" items={tabs} value={activeTab} onChange={(id) => setTab(id as Tab)} prefix={TABS} />}
          {panel(
            "resultado",
            <>
              <ResultPanel
                state={state}
                onRetry={() => void retry()}
                code={verified?.code}
                stale={stale}
                onSelectLines={selectLines}
                headingRef={headingRef}
              />
              {gabarito !== null && <GabaritoPanel comparison={gabarito} onSelectLines={selectLines} />}
            </>,
          )}
          {indicators !== null && panel("indicios", <IndicatorsPanel indicators={indicators} onSelectLines={selectLines} />)}
          {success &&
            verified !== null &&
            panel(
              "feedback",
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
              />,
            )}
          {narrow && success && (
            <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-slate-100/95 px-4 py-2 backdrop-blur dark:border-slate-700 dark:bg-slate-950/95">
              <Button variant="secondary" className="w-full" onClick={backToCode}>
                Voltar ao código
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

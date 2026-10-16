import { type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { type CodeEditorHandle, CodeEditor } from "../components/CodeEditor";
import { FeedbackPanel, type FeedbackPanelHandle } from "../components/FeedbackPanel";
import { GabaritoPanel } from "../components/GabaritoPanel";
import { IndicatorsPanel } from "../components/IndicatorsPanel";
import { LoadPyFile } from "../components/LoadPyFile";
import { ReportExport } from "../components/ReportExport";
import { ListSelector } from "../components/ListSelector";
import { PeriodSelector } from "../components/PeriodSelector";
import { QuestionSelector } from "../components/QuestionSelector";
import { ResultPanel } from "../components/ResultPanel";
import { ShortcutsHelp } from "../components/ShortcutsHelp";
import { TabPanel } from "../components/TabPanel";
import { Button, ErrorText, type TabItem, TabList } from "../components/ui";
import { useDraft } from "../draftContext";
import { useCheckerShortcuts } from "../hooks/useCheckerShortcuts";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useLists } from "../hooks/useLists";
import { usePeriods } from "../hooks/usePeriods";
import { NARROW, useMediaQuery } from "../hooks/useMediaQuery";
import { useValidateCode } from "../hooks/useValidateCode";
import { PAGE_TITLES } from "../labels";
import type { FeedbackClient, ValidationClient } from "../services/client";
import { readPythonFile } from "../pyFile";
import { questionOptions } from "../questions";
import type { ValidateRequest } from "../types/api";

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
  const { draft, setCode, setPeriod, setList, setQuestion, setFeedback, nextStudent } = useDraft();
  const { code, period, listNumber, questionId } = draft;
  // O período (S43-03): com um só carregado, o seletor nem aparece, e vale o ativo.
  const periods = usePeriods(client, onUnauthenticated);
  const { lists, error: listsError, retry: retryLists } = useLists(client, onUnauthenticated, period);
  const { state, validate, retry, reset, cancel } = useValidateCode(client);
  // O pedido enviado: é o que o resultado descreve, mesmo que o editor mude depois.
  const [verified, setVerified] = useState<ValidateRequest | null>(null);
  const [marked, setMarked] = useState<{ first: number; last: number } | null>(null);
  const [lastFeedback, setLastFeedback] = useState<{ student: string; code: string } | null>(null);
  const narrow = useMediaQuery(NARROW);
  const [tab, setTab] = useState<Tab>("resultado");
  // O resultado do Carregar .py (S38-03): o nome do arquivo carregado ou o motivo da recusa.
  const [fileNotice, setFileNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const editorRef = useRef<CodeEditorHandle>(null);
  const feedbackRef = useRef<FeedbackPanelHandle>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

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
  const canNext = !(code === "" && draft.feedback.student === "" && verified === null);

  // Atalhos da tela (S37-05): Alt+N e Ctrl+Shift+C, em qualquer lugar da página de verificação.
  useCheckerShortcuts({ canNext, onNext: () => next(), onCopy: () => void feedbackRef.current?.copy() });

  const currentList = listNumber === null ? undefined : lists.find((list) => list.number === listNumber);
  const questions = listNumber === null ? null : questionOptions(currentList);
  const selected = questionId === null ? undefined : questions?.find((question) => question.id === questionId);
  const canVerify = listNumber !== null && code.trim() !== "" && !loading;
  const stale =
    verified !== null &&
    (verified.code !== code ||
      verified.list_number !== listNumber ||
      verified.question_id !== questionId ||
      (verified.period ?? null) !== period);

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
    const request = { code, list_number: listNumber, question_id: questionId, period };
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

  const listTitle = (number: number) => {
    const title = lists.find((list) => list.number === number)?.title;
    return title === undefined ? "" : `: ${title}`;
  };

  function loaded(text: string, name: string) {
    setCode(text);
    setFileNotice({ ok: true, text: `"${name}" carregado no editor.` });
    editorRef.current?.focus();
  }

  function refused(message: string) {
    setFileNotice({ ok: false, text: message });
  }

  // Arrastar um .py para o editor também carrega (S38-03).
  function dragOver(event: DragEvent<HTMLFormElement>) {
    if (!loading && event.dataTransfer.types.includes("Files")) event.preventDefault();
  }

  async function drop(event: DragEvent<HTMLFormElement>) {
    const file = event.dataTransfer.files[0];
    if (loading || file === undefined) return;
    event.preventDefault();
    const result = await readPythonFile(file);
    if (result.ok) loaded(result.text, result.name);
    else refused(result.message);
  }

  function backToCode() {
    editorRef.current?.focus();
    formRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }

  const tabPanel = { narrow, prefix: TABS, active: activeTab };

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold">Verificação</h2>
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <form
          ref={formRef}
          onSubmit={submit}
          onDragOver={dragOver}
          onDrop={(event) => void drop(event)}
          className="flex min-w-0 scroll-mt-4 flex-col gap-4 lg:sticky lg:top-4 lg:-mx-0.5 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:px-0.5"
        >
          <div className={periods.length > 1 ? "grid gap-4 sm:grid-cols-3" : "grid gap-4 sm:grid-cols-2"}>
            <PeriodSelector periods={periods} value={period} onChange={setPeriod} disabled={loading} />
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
              <Button variant="secondary" onClick={retryLists}>
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
            toolbar={<LoadPyFile onLoad={loaded} onError={refused} disabled={loading} />}
          />
          {fileNotice !== null &&
            (fileNotice.ok ? (
              <p role="status" className="text-sm text-slate-700 dark:text-slate-300">
                {fileNotice.text}
              </p>
            ) : (
              <ErrorText>{fileNotice.text}</ErrorText>
            ))}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={!canVerify}>
              {loading ? "Verificando…" : "Verificar"}
            </Button>
            {loading && (
              <Button variant="secondary" onClick={cancel}>
                Cancelar
              </Button>
            )}
            <Button variant="secondary" onClick={next} disabled={!canNext} title="Alt+N">
              Próximo aluno
            </Button>
          </div>
          <ShortcutsHelp />
        </form>

        <div ref={resultRef} className="flex min-w-0 scroll-mt-4 flex-col gap-6">
          {narrow && success && <TabList label="Painéis do resultado" items={tabs} value={activeTab} onChange={(id) => setTab(id as Tab)} prefix={TABS} />}
          <TabPanel {...tabPanel} id="resultado">
            <ResultPanel
              state={state}
              onRetry={() => void retry()}
              code={verified?.code}
              stale={stale}
              onSelectLines={selectLines}
              headingRef={headingRef}
            />
            {success && verified !== null && (
              <ReportExport
                response={state.response}
                list={`Lista ${verified.list_number}${listTitle(verified.list_number)}`}
                listNumber={verified.list_number}
                questionId={verified.question_id ?? null}
              />
            )}
            {gabarito !== null && <GabaritoPanel comparison={gabarito} onSelectLines={selectLines} />}
          </TabPanel>
          {indicators !== null && (
            <TabPanel {...tabPanel} id="indicios">
              <IndicatorsPanel indicators={indicators} onSelectLines={selectLines} />
            </TabPanel>
          )}
          {success && verified !== null && (
            <TabPanel {...tabPanel} id="feedback">
              <FeedbackPanel
                ref={feedbackRef}
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
            </TabPanel>
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

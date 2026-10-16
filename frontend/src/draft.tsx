import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import {
  type Draft,
  DraftContext,
  EMPTY_FEEDBACK,
  type FeedbackForm,
  rememberedList,
  rememberList,
  restoreDraft,
  storeDraft,
} from "./draftContext";

/**
 * O provedor do rascunho (S26-02); fica acima da sessão, para sobreviver a um novo login. Desde a
 * S37-05, o código, a questão, o nome e a anotação também ficam no `sessionStorage` desta aba, para
 * sobreviverem a um F5; Sair os apaga.
 */
export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<Draft>(() => ({
    code: "",
    period: null,
    listNumber: rememberedList(),
    questionId: null,
    feedback: EMPTY_FEEDBACK,
    ...restoreDraft(),
  }));

  useEffect(() => {
    storeDraft(draft);
  }, [draft]);

  const setCode = useCallback((code: string) => setDraft((current) => ({ ...current, code })), []);
  const setPeriod = useCallback(
    (period: string | null) => setDraft((current) => ({ ...current, period, listNumber: null, questionId: null })),
    [],
  );
  const setList = useCallback((listNumber: number | null) => {
    rememberList(listNumber);
    setDraft((current) => ({ ...current, listNumber, questionId: null }));
  }, []);
  const setQuestion = useCallback(
    (questionId: string | null) => setDraft((current) => ({ ...current, questionId })),
    [],
  );
  const setFeedback = useCallback(
    (feedback: FeedbackForm) => setDraft((current) => ({ ...current, feedback })),
    [],
  );
  const nextStudent = useCallback(
    () => setDraft((current) => ({ ...current, code: "", feedback: EMPTY_FEEDBACK })),
    [],
  );
  const clear = useCallback(
    () =>
      setDraft((current) => ({
        code: "",
        period: null,
        listNumber: current.listNumber,
        questionId: null,
        feedback: EMPTY_FEEDBACK,
      })),
    [],
  );

  const value = useMemo(
    () => ({ draft, setCode, setPeriod, setList, setQuestion, setFeedback, nextStudent, clear }),
    [draft, setCode, setPeriod, setList, setQuestion, setFeedback, nextStudent, clear],
  );
  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>;
}

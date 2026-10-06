import { type ReactNode, useCallback, useMemo, useState } from "react";
import {
  type Draft,
  DraftContext,
  EMPTY_FEEDBACK,
  type FeedbackForm,
  rememberedList,
  rememberList,
} from "./draftContext";

/** O provedor do rascunho (S26-02); fica acima da sessão, para sobreviver a um novo login. */
export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<Draft>(() => ({
    code: "",
    listNumber: rememberedList(),
    questionId: null,
    feedback: EMPTY_FEEDBACK,
  }));

  const setCode = useCallback((code: string) => setDraft((current) => ({ ...current, code })), []);
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
        listNumber: current.listNumber,
        questionId: null,
        feedback: EMPTY_FEEDBACK,
      })),
    [],
  );

  const value = useMemo(
    () => ({ draft, setCode, setList, setQuestion, setFeedback, nextStudent, clear }),
    [draft, setCode, setList, setQuestion, setFeedback, nextStudent, clear],
  );
  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>;
}

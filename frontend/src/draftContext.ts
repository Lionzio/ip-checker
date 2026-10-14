/**
 * Rascunho da verificação (S26-02): o código, a lista, a questão, o nome do aluno e a anotação ficam
 * na memória da página, fora da tela, e sobrevivem à navegação e a um novo login depois de a sessão
 * vencer. Sair da conta apaga o rascunho. Nada vai para o servidor: o número da última lista fica
 * neste navegador (`localStorage`) e, desde a S37-05, o resto fica nesta aba (`sessionStorage`),
 * para sobreviver a um F5 e morrer com a aba.
 */
import { createContext, useContext } from "react";

export interface FeedbackForm {
  student: string;
  annotation: string;
}

export interface Draft {
  code: string;
  listNumber: number | null;
  questionId: string | null;
  feedback: FeedbackForm;
}

export interface DraftValue {
  draft: Draft;
  setCode(code: string): void;
  /** Trocar de lista volta para "sem questão": as questões são de uma lista só. */
  setList(listNumber: number | null): void;
  setQuestion(questionId: string | null): void;
  setFeedback(feedback: FeedbackForm): void;
  /** Próximo aluno: limpa o código, o nome e a anotação; a lista e a questão ficam. */
  nextStudent(): void;
  /** Sair: apaga tudo, menos a lista lembrada. */
  clear(): void;
}

export const EMPTY_FEEDBACK: FeedbackForm = { student: "", annotation: "" };

export const DraftContext = createContext<DraftValue | null>(null);

export function useDraft(): DraftValue {
  const value = useContext(DraftContext);
  if (value === null) throw new Error("useDraft fora do DraftProvider");
  return value;
}

const LIST_KEY = "ipc:ultima-lista";

/** A última lista escolhida, lembrada neste navegador; sem armazenamento, nenhuma. */
export function rememberedList(): number | null {
  try {
    const value = Number(window.localStorage.getItem(LIST_KEY));
    return Number.isInteger(value) && value >= 1 && value <= 6 ? value : null;
  } catch {
    return null;
  }
}

export function rememberList(listNumber: number | null) {
  try {
    if (listNumber === null) window.localStorage.removeItem(LIST_KEY);
    else window.localStorage.setItem(LIST_KEY, String(listNumber));
  } catch {
    // Sem armazenamento (janela anônima, bloqueio): a lista só não é lembrada.
  }
}

export const DRAFT_KEY = "ipc:rascunho";

type StoredDraft = Pick<Draft, "code" | "questionId" | "feedback">;

/** O rascunho desta aba, se houver (S37-05): o código, a questão, o nome e a anotação. */
export function restoreDraft(): Partial<StoredDraft> {
  try {
    const raw = window.sessionStorage.getItem(DRAFT_KEY);
    if (raw === null) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    const { code, questionId, feedback } = parsed as Record<string, unknown>;
    const form = typeof feedback === "object" && feedback !== null ? (feedback as Record<string, unknown>) : {};
    return {
      code: typeof code === "string" ? code : "",
      questionId: typeof questionId === "string" ? questionId : null,
      feedback: {
        student: typeof form.student === "string" ? form.student : "",
        annotation: typeof form.annotation === "string" ? form.annotation : "",
      },
    };
  } catch {
    return {};
  }
}

/** Guarda o rascunho nesta aba; vazio, apaga (é o que o Sair faz). */
export function storeDraft(draft: Draft) {
  try {
    const empty = draft.code === "" && draft.questionId === null && draft.feedback.student === "" && draft.feedback.annotation === "";
    if (empty) window.sessionStorage.removeItem(DRAFT_KEY);
    else {
      const stored: StoredDraft = { code: draft.code, questionId: draft.questionId, feedback: draft.feedback };
      window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(stored));
    }
  } catch {
    // Sem armazenamento: o rascunho vive só na memória da página, como antes.
  }
}

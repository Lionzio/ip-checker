/** Classes e mensagens compartilhadas pelas telas de conta (Sprint 14). */
import { ApiError } from "./services/client";

export type Variant = "primary" | "secondary" | "danger";

const BUTTON_BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed sm:min-h-9";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-slate-400 dark:disabled:bg-slate-600",
  secondary:
    "border border-slate-300 hover:bg-slate-100 disabled:opacity-60 dark:border-slate-600 dark:hover:bg-slate-800",
  danger:
    "border border-red-300 text-red-800 hover:bg-red-50 disabled:opacity-60 dark:border-red-700 dark:text-red-200 dark:hover:bg-red-950",
};

export function buttonClass(variant: Variant = "primary", extra = ""): string {
  return `${BUTTON_BASE} ${VARIANTS[variant]} ${extra}`.trim();
}

/** O botão principal de um formulário (S14; desde a S26-01, o mesmo do componente `Button`). */
export const BUTTON = buttonClass("primary");
export const TEXT_LINK = "text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-200";
export const LINK = `text-sm ${TEXT_LINK}`;

export const INPUT =
  "rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-900";

/** A sessão venceu ou foi encerrada (S26-04). Outras 401, como senha atual errada, não contam. */
export function sessionExpired(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401 && error.code === "UNAUTHENTICATED";
}

/** A mensagem da API (FR-25) ou, sem resposta, a de falha de rede. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429 && error.retryAfterS !== null) {
      return `${error.message} Tente de novo em ${error.retryAfterS} s.`;
    }
    return error.message;
  }
  return "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";
}

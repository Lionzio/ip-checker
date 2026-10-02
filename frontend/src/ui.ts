/** Classes e mensagens compartilhadas pelas telas de conta (Sprint 14). */
import { ApiError } from "./services/client";

export const INPUT =
  "rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-900";
export const BUTTON =
  "rounded-md bg-blue-700 px-5 py-2 font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400";
export const LINK = "text-sm text-blue-700 underline dark:text-blue-300";

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

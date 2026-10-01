import type { ApiErrorCode, ListInfo, ValidateRequest, ValidateResponse } from "../types/api";

/** Cliente da API. O MVP usa o cliente simulado; o cliente HTTP real entra na Sprint 9 (S9-02). */
export interface ValidationClient {
  listLists(signal?: AbortSignal): Promise<ListInfo[]>;
  validate(request: ValidateRequest, signal?: AbortSignal): Promise<ValidateResponse>;
}

/** Erro no formato `{ error: { code, message, retry_after_s } }` do contrato (5.2.2). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly retryAfterS: number | null;

  constructor(status: number, code: ApiErrorCode, message: string, retryAfterS: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterS = retryAfterS;
  }
}

/** Contrato da API pública (blueprint, 5.2.2). */

export type Category =
  | "ANULACAO"
  | "PROIBIDO_NA_QUESTAO"
  | "FORA_DA_LISTA"
  | "NAO_CONSTA"
  | "EXIGENCIA";

export interface Violation {
  rule_id: string;
  category: Category;
  /** Linha e coluna começam em 1; a coluna é contada em caracteres. */
  line: number;
  col: number;
  end_line: number;
  end_col: number;
  construct: string;
  allowed_from_list: number | null;
  message: string;
}

export interface SyntaxErrorInfo {
  line: number;
  col: number;
  message: string;
}

export type ValidationStatus = "valid" | "invalid" | "syntax_error";

export type Notice = "QUESTION_RULES_NOT_APPLIED";

export interface ValidateRequest {
  code: string;
  list_number: number;
  question_id: string | null;
}

export interface ValidateResponse {
  request_id: string;
  ruleset_version: string;
  status: ValidationStatus;
  list_number: number;
  question_id: string | null;
  notices: Notice[];
  syntax_error: SyntaxErrorInfo | null;
  violations: Violation[];
}

export interface ListInfo {
  number: number;
  title: string;
}

export type ApiErrorCode =
  | "PAYLOAD_TOO_LARGE"
  | "INVALID_INPUT"
  | "LIST_NOT_ENABLED"
  | "UNKNOWN_QUESTION"
  | "ANALYSIS_LIMIT"
  | "RATE_LIMITED"
  | "OVERLOADED"
  | "ANALYZER_UNAVAILABLE";

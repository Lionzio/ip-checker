import type { ApiErrorCode, Category, Notice } from "./types/api";

export const CATEGORY_LABELS: Record<Category, string> = {
  ANULACAO: "Anulação imediata",
  PROIBIDO_NA_QUESTAO: "Proibido nesta questão",
  FORA_DA_LISTA: "Fora da lista",
  NAO_CONSTA: "Não consta no documento",
  EXIGENCIA: "Exigência não atendida",
};

export const NOTICE_TEXTS: Record<Notice, string> = {
  QUESTION_RULES_NOT_APPLIED:
    "As permissões específicas da questão não foram consideradas. Em caso de divergência, vale o enunciado.",
};

/** Títulos dos estados em que basta esperar e tentar de novo (FR-20: limite de taxa e sobrecarga). */
export const BUSY_TITLES: Partial<Record<ApiErrorCode, string>> = {
  RATE_LIMITED: "Limite de verificações atingido",
  OVERLOADED: "Serviço ocupado",
  ANALYZER_UNAVAILABLE: "Serviço indisponível",
};

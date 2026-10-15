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
    "Nenhuma questão foi escolhida: valeram só as permissões da lista. Em caso de divergência, vale o enunciado.",
  QUESTION_RULES_NOT_REGISTERED:
    "Esta questão não tem regra cadastrada: valeram só as permissões da lista, e o código foi comparado com o gabarito. Em caso de divergência, vale o enunciado.",
};

/** Títulos dos estados em que basta esperar e tentar de novo (FR-20: limite de taxa e sobrecarga). */
export const BUSY_TITLES: Partial<Record<ApiErrorCode, string>> = {
  RATE_LIMITED: "Limite de verificações atingido",
  OVERLOADED: "Serviço ocupado",
  ANALYZER_UNAVAILABLE: "Serviço indisponível",
};

/** Navegação principal (S26-01). */
export const NAV_LABELS = {
  checker: "Verificar",
  plagiarism: "Plágio",
  batch: "Turma",
  admin: "Gerenciar",
  profile: "Perfil",
  signOut: "Sair",
} as const;

/** O `<title>` de cada tela (S26-01). */
export const PAGE_TITLES = {
  landing: "Acesso restrito",
  checker: "Verificação",
  plagiarism: "Plágio",
  batch: "Turma inteira",
  admin: "Gerenciamento",
  profile: "Perfil",
  login: "Entrar",
  register: "Registrar",
  verify: "Confirmar o e-mail",
  forgot: "Esqueci minha senha",
  reset: "Redefinir a senha",
  privacy: "Aviso de privacidade",
  google: "Registrar com o Google",
} as const;

/** Singular e plural de cada categoria, no resumo do relatório (S26-03). */
export const CATEGORY_COUNTS: Record<Category, readonly [string, string]> = {
  ANULACAO: ["anulação imediata", "anulações imediatas"],
  PROIBIDO_NA_QUESTAO: ["proibição da questão", "proibições da questão"],
  EXIGENCIA: ["exigência não atendida", "exigências não atendidas"],
  FORA_DA_LISTA: ["fora da lista", "fora da lista"],
  NAO_CONSTA: ["não consta no documento", "não constam no documento"],
};

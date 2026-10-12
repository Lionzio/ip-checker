import type { ListInfo } from "./types/api";

/** O título de uma questão que só tem gabarito (ADR-11, item 6). */
export const GABARITO_ONLY_TITLE = "sem regra cadastrada (comparação com o gabarito)";

/** Uma questão do seletor: o título fica na descrição abaixo dele, não na opção (S36-05). */
export interface QuestionOption {
  id: string;
  title: string;
  /** Tem regra específica cadastrada (R-01). */
  rules: boolean;
  /** Tem gabarito para comparar (ADR-11). */
  gabarito: boolean;
}

/**
 * As questões do seletor (R-01 e ADR-11): as com regra cadastrada e as que só têm gabarito, em
 * ordem de número.
 */
export function questionOptions(list: ListInfo | undefined): QuestionOption[] {
  if (list === undefined) return [];
  const gabaritos = new Set(list.gabaritos ?? []);
  const registered = (list.questions ?? []).map((question) => ({
    id: question.id,
    title: question.title,
    rules: true,
    gabarito: gabaritos.has(question.id),
  }));
  const known = new Set(registered.map((question) => question.id));
  const onlyGabarito = [...gabaritos]
    .filter((id) => !known.has(id))
    .map((id) => ({ id, title: GABARITO_ONLY_TITLE, rules: false, gabarito: true }));
  const number = (id: string) => Number(id.split("Q")[1]);
  return [...registered, ...onlyGabarito].sort((a, b) => number(a.id) - number(b.id));
}

/** O rótulo curto da opção, que cabe no seletor do computador e do celular (S36-05). */
export function questionLabel(question: QuestionOption): string {
  if (!question.rules) return `${question.id} · só gabarito`;
  return question.gabarito ? `${question.id} · gabarito` : question.id;
}

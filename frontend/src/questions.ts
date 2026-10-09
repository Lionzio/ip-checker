import type { ListInfo, QuestionInfo } from "./types/api";

/** O título que o seletor mostra para uma questão que só tem gabarito (ADR-11, item 6). */
export const GABARITO_ONLY_TITLE = "sem regra cadastrada (comparação com o gabarito)";

/**
 * As questões do seletor (R-01 e ADR-11): as com regra cadastrada, marcando as que têm gabarito, e
 * as que só têm gabarito, em ordem de número.
 */
export function questionOptions(list: ListInfo | undefined): QuestionInfo[] {
  if (list === undefined) return [];
  const gabaritos = new Set(list.gabaritos ?? []);
  const registered = (list.questions ?? []).map((question) => ({
    id: question.id,
    title: gabaritos.has(question.id) ? `${question.title} · com gabarito` : question.title,
  }));
  const known = new Set(registered.map((question) => question.id));
  const onlyGabarito = [...gabaritos]
    .filter((id) => !known.has(id))
    .map((id) => ({ id, title: GABARITO_ONLY_TITLE }));
  const number = (id: string) => Number(id.split("Q")[1]);
  return [...registered, ...onlyGabarito].sort((a, b) => number(a.id) - number(b.id));
}

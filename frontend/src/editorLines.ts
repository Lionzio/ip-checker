/**
 * As linhas tocadas por uma seleção do editor (S36-03): o início da primeira e o fim da última.
 * Uma seleção que termina no começo de uma linha (logo depois de um Enter) não inclui essa linha,
 * como nos editores de código.
 */
export function lineBlock(text: string, start: number, end: number): [number, number] {
  const blockStart = text.lastIndexOf("\n", start - 1) + 1;
  const last = end > start && text[end - 1] === "\n" ? end - 1 : end;
  const next = text.indexOf("\n", last);
  return [blockStart, next === -1 ? text.length : next];
}

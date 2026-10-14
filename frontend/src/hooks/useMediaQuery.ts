import { useEffect, useState } from "react";

/**
 * Se a janela casa com uma media query, acompanhando as mudanças (S37-02). Sem `matchMedia`
 * (testes sem o navegador), responde `false`.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia?.(query).matches ?? false);

  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (media === undefined) return;
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);

  return matches;
}

/** Abaixo do ponto `lg` do Tailwind (64rem): a página empilha as colunas. */
export const NARROW = "(max-width: 63.99rem)";

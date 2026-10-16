import { useEffect } from "react";

/** Dentro de um campo de texto, Ctrl+Shift+C fica com o campo; Alt+N vale em qualquer lugar. */
function inTextField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target.isContentEditable;
}

/** A tecla pelo `code` (a posição física) ou, quando o navegador não o informa, pela letra. */
function isKey(event: KeyboardEvent, code: string, letter: string): boolean {
  return event.code === code || event.key.toLowerCase() === letter;
}

interface Shortcuts {
  /** Alt+N: o próximo aluno, quando há o que limpar. */
  canNext: boolean;
  onNext: () => void;
  /** Ctrl+Shift+C: copia o feedback gerado. */
  onCopy: () => void;
}

/**
 * Os atalhos da tela de verificação (S37-05), em qualquer lugar da página. O ouvinte é refeito a
 * cada renderização, para valer sempre o estado atual da tela.
 */
export function useCheckerShortcuts({ canNext, onNext, onCopy }: Shortcuts) {
  useEffect(() => {
    function keyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) return;
      if (event.altKey && !event.ctrlKey && !event.metaKey && isKey(event, "KeyN", "n")) {
        if (!canNext) return;
        event.preventDefault();
        onNext();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && !event.altKey && isKey(event, "KeyC", "c")) {
        if (inTextField(event.target)) return;
        event.preventDefault();
        onCopy();
      }
    }
    document.addEventListener("keydown", keyDown);
    return () => document.removeEventListener("keydown", keyDown);
  });
}

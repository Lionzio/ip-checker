import { useState } from "react";
import { Disclosure } from "./ui";

/** Os atalhos da tela, na ajuda (S37-05). */
const SHORTCUTS: [string, string][] = [
  ["Ctrl+Enter", "verifica o código do editor"],
  ["Tab e Shift+Tab", "indentam e desindentam as linhas selecionadas no editor"],
  ["Esc e depois Tab", "saem do editor"],
  ["Alt+N", "próximo aluno: limpa o código, o nome e a anotação"],
  ["Ctrl+Shift+C", "copia o feedback gerado"],
];

/** "Atalhos do teclado", abaixo dos botões da verificação. */
export function ShortcutsHelp() {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-sm">
      <Disclosure open={open} onClick={() => setOpen((current) => !current)} className="w-auto" aria-controls="atalhos">
        Atalhos do teclado
      </Disclosure>
      {open && (
        <dl id="atalhos" className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-slate-700 dark:text-slate-200">
          {SHORTCUTS.map(([keys, what]) => (
            <div key={keys} className="contents">
              <dt>
                <kbd className="rounded border border-slate-300 bg-slate-50 px-1.5 font-mono text-xs dark:border-slate-600 dark:bg-slate-800">{keys}</kbd>
              </dt>
              <dd>{what}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

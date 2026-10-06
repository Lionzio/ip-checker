import { type KeyboardEvent, type Ref, useImperativeHandle, useRef, useState } from "react";

/** O que a página pode pedir ao editor (S26-02 e S26-03). */
export interface CodeEditorHandle {
  focus(): void;
  /** Seleciona as linhas (a partir de 1), rola até elas e põe o foco no editor. */
  selectLines(first: number, last: number): void;
  /** Rola até as linhas sem mexer no foco (o outro lado do painel de plágio, S27-03). */
  scrollToLine(line: number): void;
  /** A rolagem sincronizada do painel de plágio (S27-03). */
  setScrollTop(top: number): void;
}

/** Um intervalo de linhas, a partir de 1, inclusivo. */
export interface LineRange {
  first: number;
  last: number;
}

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** Durante a verificação o texto não muda, mas o foco fica no editor (S26-04). */
  readOnly?: boolean;
  /** O nome acessível da área (o painel de plágio tem duas). */
  label?: string;
  placeholder?: string;
  /** Ctrl+Enter (Cmd+Enter no Mac): verificar sem sair do teclado. */
  onSubmitShortcut?: () => void;
  /** Linhas marcadas no gutter: a violação escolhida no relatório ou os trechos em comum. */
  marked?: LineRange | readonly LineRange[] | null;
  /** O trecho em destaque entre os marcados (o par escolhido no painel de plágio). */
  current?: LineRange | null;
  /** Avisa a rolagem, para o painel de plágio rolar o outro código junto. */
  onScrollTop?: (top: number) => void;
  ref?: Ref<CodeEditorHandle>;
}

const INDENT = "    ";
const LINE_HEIGHT_PX = 24;

/** O deslocamento do começo de cada linha no texto. */
function lineStarts(text: string): number[] {
  const starts = [0];
  for (let index = 0; index < text.length; index += 1) {
    if (text[index] === "\n") starts.push(index + 1);
  }
  return starts;
}

/**
 * Área de código com numeração de linhas (S26-02): tabulação de 4, Tab que insere espaços (Esc e
 * depois Tab sai do editor), altura ajustável, Limpar e Colar.
 */
export function CodeEditor({
  value,
  onChange,
  readOnly = false,
  label = "Código Python",
  placeholder = "Cole aqui a sua solução em Python",
  onSubmitShortcut,
  marked = null,
  current = null,
  onScrollTop,
  ref,
}: CodeEditorProps) {
  const gutterRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);
  // Depois de Esc, o próximo Tab sai do editor, como pede o WCAG 2.1.2 (sem armadilha de teclado).
  const escapedRef = useRef(false);
  const [notice, setNotice] = useState<string | null>(null);
  const lineCount = Math.max(value.split("\n").length, 1);
  const ranges: readonly LineRange[] = marked === null ? [] : "first" in marked ? [marked] : marked;
  const inRange = (line: number, range: LineRange | null) => range !== null && line >= range.first && line <= range.last;

  useImperativeHandle(ref, () => ({
    focus: () => areaRef.current?.focus(),
    selectLines(first, last) {
      const area = areaRef.current;
      if (area === null) return;
      const starts = lineStarts(area.value);
      const start = starts[Math.min(first, starts.length) - 1] ?? 0;
      const next = starts[Math.min(last, starts.length - 1)];
      const end = next === undefined || last >= starts.length ? area.value.length : next - 1;
      area.focus();
      area.setSelectionRange(start, end);
      area.scrollTop = Math.max(0, (first - 3) * LINE_HEIGHT_PX);
      if (gutterRef.current) gutterRef.current.scrollTop = area.scrollTop;
    },
    scrollToLine(line) {
      const area = areaRef.current;
      if (area === null) return;
      area.scrollTop = Math.max(0, (line - 3) * LINE_HEIGHT_PX);
      if (gutterRef.current) gutterRef.current.scrollTop = area.scrollTop;
    },
    setScrollTop(top) {
      const area = areaRef.current;
      if (area === null || area.scrollTop === top) return;
      area.scrollTop = top;
      if (gutterRef.current) gutterRef.current.scrollTop = area.scrollTop;
    },
  }));

  function insert(text: string) {
    const area = areaRef.current;
    if (area === null) return;
    // O insertText do navegador mantém o desfazer (Ctrl+Z); sem ele, a troca é feita à mão.
    if (typeof document.execCommand === "function" && document.execCommand("insertText", false, text)) return;
    const { selectionStart, selectionEnd } = area;
    const updated = area.value.slice(0, selectionStart) + text + area.value.slice(selectionEnd);
    onChange(updated);
    requestAnimationFrame(() => area.setSelectionRange(selectionStart + text.length, selectionStart + text.length));
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Escape") {
      escapedRef.current = true;
      return;
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && onSubmitShortcut) {
      event.preventDefault();
      onSubmitShortcut();
      return;
    }
    if (event.key === "Tab" && !event.shiftKey && !escapedRef.current && !readOnly) {
      event.preventDefault();
      insert(INDENT);
    }
    escapedRef.current = false;
  }

  async function paste() {
    setNotice(null);
    try {
      const text = await navigator.clipboard.readText();
      onChange(text);
      areaRef.current?.focus();
    } catch {
      setNotice("O navegador não deixou ler a área de transferência. Cole com Ctrl+V no editor.");
    }
  }

  function clear() {
    onChange("");
    setNotice(null);
    areaRef.current?.focus();
  }

  const hintId = `${label.replace(/\W+/g, "-").toLowerCase()}-dica`;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex h-80 min-h-40 resize-y overflow-hidden rounded-md border border-slate-300 bg-white font-mono text-sm focus-within:ring-2 focus-within:ring-blue-600 dark:border-slate-600 dark:bg-slate-900">
        <div
          ref={gutterRef}
          aria-hidden="true"
          data-testid="line-numbers"
          className="m-0 select-none overflow-hidden border-r border-slate-200 bg-slate-50 py-2 text-right leading-6 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
        >
          {Array.from({ length: lineCount }, (_, index) => {
            const line = index + 1;
            const on = ranges.some((range) => inRange(line, range));
            const active = inRange(line, current);
            const style = active
              ? "bg-amber-300 px-2 font-semibold text-slate-900 dark:bg-amber-600 dark:text-white"
              : on
                ? "bg-amber-100 px-2 font-semibold text-slate-900 dark:bg-amber-900 dark:text-amber-50"
                : "px-2";
            return (
              <div key={line} data-marked={on || active || undefined} data-current={active || undefined} className={style}>
                {line}
              </div>
            );
          })}
        </div>
        <textarea
          ref={areaRef}
          aria-label={label}
          aria-describedby={hintId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={keyDown}
          onScroll={(event) => {
            if (gutterRef.current) gutterRef.current.scrollTop = event.currentTarget.scrollTop;
            onScrollTop?.(event.currentTarget.scrollTop);
          }}
          readOnly={readOnly}
          aria-busy={readOnly || undefined}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="off"
          placeholder={placeholder}
          className="flex-1 resize-none bg-transparent px-3 py-2 leading-6 [tab-size:4] text-slate-900 outline-none dark:text-slate-100"
        />
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <button type="button" onClick={() => void paste()} disabled={readOnly} className="min-h-11 rounded-md px-2 text-blue-700 underline underline-offset-2 disabled:opacity-60 sm:min-h-0 dark:text-blue-300">
          Colar
        </button>
        <button type="button" onClick={clear} disabled={readOnly || value === ""} className="min-h-11 rounded-md px-2 text-blue-700 underline underline-offset-2 disabled:opacity-60 sm:min-h-0 dark:text-blue-300">
          Limpar
        </button>
        <span id={hintId} className="text-slate-600 dark:text-slate-300">
          Tab insere 4 espaços; Esc e depois Tab sai do editor.{onSubmitShortcut ? " Ctrl+Enter verifica." : ""}
        </span>
      </div>
      {notice !== null && (
        <p role="status" className="text-sm text-slate-700 dark:text-slate-300">
          {notice}
        </p>
      )}
    </div>
  );
}

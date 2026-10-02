import { useRef } from "react";

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  /** O nome acessível da área (o painel de plágio tem duas). */
  label?: string;
  placeholder?: string;
}

/** Área de código com numeração de linhas. O CodeMirror entra na Sprint 3. */
export function CodeEditor({
  value,
  onChange,
  disabled = false,
  label = "Código Python",
  placeholder = "Cole aqui a sua solução em Python",
}: CodeEditorProps) {
  const gutterRef = useRef<HTMLPreElement>(null);
  const lineCount = Math.max(value.split("\n").length, 1);
  const lineNumbers = Array.from({ length: lineCount }, (_, index) => index + 1).join("\n");

  return (
    <div className="flex h-80 overflow-hidden rounded-md border border-slate-300 bg-white font-mono text-sm focus-within:ring-2 focus-within:ring-blue-600 dark:border-slate-600 dark:bg-slate-900">
      <pre
        ref={gutterRef}
        aria-hidden="true"
        data-testid="line-numbers"
        className="m-0 select-none overflow-hidden border-r border-slate-200 bg-slate-50 px-2 py-2 text-right leading-6 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
      >
        {lineNumbers}
      </pre>
      <textarea
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onScroll={(event) => {
          if (gutterRef.current) gutterRef.current.scrollTop = event.currentTarget.scrollTop;
        }}
        disabled={disabled}
        spellCheck={false}
        autoCapitalize="off"
        autoCorrect="off"
        wrap="off"
        placeholder={placeholder}
        className="flex-1 resize-none bg-transparent px-3 py-2 leading-6 text-slate-900 outline-none dark:text-slate-100"
      />
    </div>
  );
}

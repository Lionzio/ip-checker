/**
 * Componentes básicos de todas as telas (S26-01; S37-03): botão, link de texto, mensagem de erro,
 * cartão, chip de linha e aviso de erro de sintaxe, com a mesma aparência, o mesmo foco visível e
 * alvos de pelo menos 44 px nas telas de toque. Nenhuma tela escreve a classe de um botão: todas
 * usam estes componentes (o teste `ui.guard.test.ts` confere).
 */
import type { ButtonHTMLAttributes, HTMLAttributes, KeyboardEvent, ReactNode, Ref } from "react";
import { Link, type LinkProps } from "react-router";
import { buttonClass, panelId, type Size, tabId, TEXT_LINK, type Variant } from "../ui";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** `sm` cabe numa linha de tabela; `link` é um botão com cara de link de texto. */
  size?: Size;
  ref?: Ref<HTMLButtonElement>;
}

export function Button({ variant = "primary", size = "md", className = "", type = "button", ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, size, className)} {...props} />;
}

export function TextLink({ className = "", ...props }: LinkProps) {
  return <Link className={`${TEXT_LINK} ${className}`.trim()} {...props} />;
}

/** Um erro que a pessoa precisa ler: anunciado ao leitor de tela, com contraste AA nos dois temas. */
export function ErrorText({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <p id={id} role="alert" className="text-sm text-red-700 dark:text-red-300">
      {children}
    </p>
  );
}

const CARD = "rounded-md border border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";
const CARD_PADDING = { md: "p-4", sm: "p-3", xs: "px-3 py-2", none: "" } as const;

interface CardProps extends HTMLAttributes<HTMLElement> {
  /** O elemento: uma seção com nome (padrão), um item de lista ou uma divisão sem semântica. */
  as?: "section" | "li" | "div";
  padding?: keyof typeof CARD_PADDING;
}

/** A moldura dos painéis (resultado, gabarito, indícios, feedback, plágio) e dos cartões de regra. */
export function Card({ as: Tag = "section", padding = "md", className = "", ...props }: CardProps) {
  return <Tag className={`${CARD} ${CARD_PADDING[padding]} ${className}`.trim()} {...props} />;
}

const CHIP =
  "inline-flex min-h-11 items-center rounded border border-slate-300 px-2 hover:bg-slate-100 aria-pressed:border-amber-500 aria-pressed:bg-amber-100 sm:min-h-7 dark:border-slate-600 dark:hover:bg-slate-800 dark:aria-pressed:bg-amber-900";

interface LineChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Em fonte de código (as linhas do relatório) ou na do texto (os trechos do gabarito). */
  mono?: boolean;
}

/** O botão pequeno "Linha 3, coluna 1" que seleciona um trecho no editor (S26-03). */
export function LineChip({ mono = true, className = "", ...props }: LineChipProps) {
  return <button type="button" className={`${CHIP} ${mono ? "font-mono text-xs" : "text-sm"} ${className}`.trim()} {...props} />;
}

const PILL =
  "inline-flex min-h-11 items-center rounded-full border border-transparent px-3 text-sm font-medium aria-pressed:border-slate-700 aria-pressed:ring-2 aria-pressed:ring-slate-700/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 sm:min-h-7 dark:aria-pressed:border-slate-200";

/** Um contador que filtra ("4 anulações imediatas"): pressionado, ganha a borda e o anel (S37-01). */
export function Chip({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`${PILL} ${className}`.trim()} {...props} />;
}

interface DisclosureProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  open: boolean;
}

/**
 * O cabeçalho de um cartão que abre e fecha: a seta e `aria-expanded` (S37-01). O conteúdo corre
 * como texto, para o cabeçalho fechado ocupar o mínimo de linhas.
 */
export function Disclosure({ open, className = "", children, ...props }: DisclosureProps) {
  return (
    <button
      type="button"
      aria-expanded={open}
      className={`flex w-full cursor-pointer items-start gap-2 rounded text-left text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${className}`.trim()}
      {...props}
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" className="mt-0.5 size-4 shrink-0 text-slate-600 dark:text-slate-300">
        <path d={open ? "M4 6l4 4 4-4" : "M6 4l4 4-4 4"} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="min-w-0 flex-1 leading-6">{children}</span>
    </button>
  );
}

export interface TabItem {
  id: string;
  label: string;
}

interface TabListProps {
  label: string;
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  /** O prefixo dos ids das abas e dos painéis: `${prefix}-aba-${id}` e `${prefix}-painel-${id}`. */
  prefix: string;
}

/**
 * Abas (S37-02): `role="tablist"`, uma aba só no Tab do teclado e as setas, Home e End trocando a
 * aba, que já fica selecionada. Cada painel usa `role="tabpanel"` com o id de `panelId`.
 */
export function TabList({ label, items, value, onChange, prefix }: TabListProps) {
  function keyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: items.length - 1 };
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    const next = items[(target + items.length) % items.length];
    if (next === undefined) return;
    onChange(next.id);
    document.getElementById(tabId(prefix, next.id))?.focus();
  }
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 border-b border-slate-300 dark:border-slate-600">
      {items.map((item, index) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={tabId(prefix, item.id)}
            aria-selected={selected}
            aria-controls={panelId(prefix, item.id)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(event) => keyDown(event, index)}
            className={`-mb-px inline-flex min-h-11 items-center border-b-2 px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
              selected
                ? "border-blue-700 text-blue-800 dark:border-blue-300 dark:text-blue-200"
                : "border-transparent text-slate-700 hover:border-slate-300 dark:text-slate-200"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

interface SyntaxErrorBoxProps {
  title: string;
  line: number;
  col: number;
  message: string;
  /** O título como `h2` que recebe o foco (o resultado da verificação); sem ele, um `h3`. */
  headingRef?: Ref<HTMLHeadingElement>;
  /** `alert` quando o aviso não é anunciado de outro jeito (o painel de plágio). */
  alert?: boolean;
  children?: ReactNode;
}

/** O erro de sintaxe, igual na verificação e no plágio: linha, coluna, mensagem e o que fazer. */
export function SyntaxErrorBox({ title, line, col, message, headingRef, alert = false, children }: SyntaxErrorBoxProps) {
  const heading = "text-lg font-semibold focus:outline-none";
  return (
    <div
      role={alert ? "alert" : undefined}
      className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100"
    >
      {headingRef ? (
        <h2 ref={headingRef} tabIndex={-1} className={heading}>
          {title}
        </h2>
      ) : (
        <h3 className={heading}>{title}</h3>
      )}
      <p className="mt-1">
        Linha {line}, coluna {col}: {message}
      </p>
      {children}
    </div>
  );
}

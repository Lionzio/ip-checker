/**
 * O logotipo (S37-04): um quadrado na cor da marca com duas linhas de código e a marca de
 * verificação. É SVG inline, sem pedido de rede nem biblioteca; o mesmo desenho está em
 * `public/favicon.svg`. Decorativo: o nome do produto vem no texto ao lado.
 */
export function Logo({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false" className={`shrink-0 ${className}`}>
      <rect width="32" height="32" rx="7" className="fill-brand" />
      <path d="M8 11h9M8 16h6" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M13 21l4.5 4.5L26 15" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

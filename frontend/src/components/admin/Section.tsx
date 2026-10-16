import type { ReactNode } from "react";

/** Uma seção do Gerenciar, com a contagem no título e um texto quando está vazia. */
export function Section({ title, empty, count, children }: { title: string; empty: string; count: number; children: ReactNode }) {
  const id = `secao-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h3 id={id} className="text-lg font-semibold">
        {title} <span className="text-sm font-normal text-slate-600 dark:text-slate-300">({count})</span>
      </h3>
      {count === 0 ? <p className="text-sm text-slate-600 dark:text-slate-300">{empty}</p> : children}
    </section>
  );
}

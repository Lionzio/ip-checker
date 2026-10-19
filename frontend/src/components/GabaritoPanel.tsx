import { BAND_STYLES, PERCENT } from "../bands";
import { gabaritoName } from "../labels";
import type { GabaritoComparison } from "../types/api";
import { constructHint } from "../constructTerms";
import { Card, LineChip } from "./ui";

/**
 * Comparação com o gabarito oficial da questão (S32-06; ADR-11, FR-32, US-37): a semelhança, pela
 * mesma medida do painel de plágio, as construções em comum, só no aluno e só no gabarito, e os
 * trechos do aluno que coincidem com o gabarito. Nenhum texto do gabarito chega à página.
 */
interface GabaritoPanelProps {
  comparison: GabaritoComparison;
  /** Clique num trecho: o editor seleciona as linhas, como no relatório (S26-03). */
  onSelectLines?: (first: number, last: number) => void;
}

function Constructs({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="min-w-0">
      <h4 className="text-sm font-semibold">{title}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">{empty}</p>
      ) : (
        <ul className="mt-1 flex flex-wrap gap-1" aria-label={title}>
          {items.map((item) => (
            <li key={item} title={constructHint(item)} className="rounded bg-slate-100 px-2 py-0.5 font-mono text-sm dark:bg-slate-800">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function span(first: number, last: number): string {
  return first === last ? `linha ${first}` : `linhas ${first}–${last}`;
}

export function GabaritoPanel({ comparison, onSelectLines }: GabaritoPanelProps) {
  const compared = comparison.status === "compared" && comparison.similarity !== null && comparison.band !== null;
  return (
    <Card aria-labelledby="gabarito-titulo" className="flex flex-col gap-3">
      <h3 id="gabarito-titulo" className="text-lg font-semibold">
        Comparação com o {gabaritoName(comparison.kind)} · {comparison.question_id}
      </h3>
      {!compared ? (
        <p role="note" className="text-sm text-slate-700 dark:text-slate-200">
          {comparison.message}
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p
              className="text-3xl font-bold"
              aria-label={`Semelhança com o gabarito de ${PERCENT.format(comparison.similarity ?? 0)}%`}
            >
              {PERCENT.format(comparison.similarity ?? 0)}%
            </p>
            {comparison.band !== null && (
              <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BAND_STYLES[comparison.band.id]}`}>
                {comparison.band.label}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300">{comparison.message}</p>
          {comparison.short_code && (
            <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
              Código curto: em questões simples, soluções independentes se parecem com o gabarito.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-3">
            <Constructs title="Em comum" items={comparison.common} empty="Nenhuma construção em comum." />
            <Constructs title="Só no código do aluno" items={comparison.only_student} empty="Nenhuma." />
            <Constructs title="Só no gabarito" items={comparison.only_gabarito} empty="Nenhuma." />
          </div>
          {comparison.student_lines.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold">Trechos do aluno que coincidem com o gabarito</h4>
              <ul className="mt-1 flex flex-wrap gap-1">
                {comparison.student_lines.map(({ first, last }) => (
                  <li key={`${first}-${last}`}>
                    {onSelectLines ? (
                      <LineChip mono={false} onClick={() => onSelectLines(first, last)} aria-label={`${span(first, last)}: selecionar no editor`}>
                        {span(first, last)}
                      </LineChip>
                    ) : (
                      <span className="text-sm">{span(first, last)}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

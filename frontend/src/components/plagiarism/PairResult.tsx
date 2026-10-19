import { BAND_STYLES, PERCENT } from "../../bands";
import { gabaritoName } from "../../labels";
import type { SimilarityBand, SimilarityGabarito, SimilarityMatch, SimilarityResponse } from "../../types/api";
import { Card, LineChip, SyntaxErrorBox } from "../ui";

function lines(first: number, last: number): string {
  return first === last ? `linha ${first}` : `linhas ${first}–${last}`;
}

export function Band({ band }: { band: SimilarityBand }) {
  return <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BAND_STYLES[band.id]}`}>{band.label}</span>;
}

/** O resultado de "Dois códigos": a similaridade, a faixa, as métricas e os trechos em comum (S17-03). */
export function PairResult({
  result,
  matches,
  current,
  onShow,
}: {
  result: SimilarityResponse;
  matches: SimilarityMatch[];
  current: number | null;
  onShow: (index: number) => void;
}) {
  if (result.status === "syntax_error" && result.syntax_error !== null) {
    const problem = result.syntax_error;
    return (
      <SyntaxErrorBox
        title={`O código ${problem.code.toUpperCase()} tem um erro de sintaxe`}
        line={problem.line}
        col={problem.col}
        message={problem.message}
        alert
      >
        <p className="mt-2 text-sm">Os dois códigos precisam ser Python válido para serem comparados.</p>
      </SyntaxErrorBox>
    );
  }
  if (result.similarity === null || result.band === null) return null;
  const metrics = result.metrics;
  return (
    <Card as="div" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-3xl font-bold" aria-label={`Similaridade de ${PERCENT.format(result.similarity)}%`}>
          {PERCENT.format(result.similarity)}%
        </p>
        <Band band={result.band} />
      </div>
      {metrics && (
        <p className="text-sm text-slate-700 dark:text-slate-200">
          Estrutura: {PERCENT.format(metrics.tree_dice)}% · Contenção: {PERCENT.format(metrics.tree_containment)}%
          {metrics.sequence !== null && ` · Sequência: ${PERCENT.format(metrics.sequence)}%`}. A similaridade é a maior
          delas; a contenção alta com estrutura baixa indica código acrescentado a uma cópia.
        </p>
      )}
      {result.short_code && (
        <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
          Um dos códigos é curto: soluções independentes de questões simples tendem a se parecer. Leia os dois antes de
          concluir.
        </p>
      )}
      {matches.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Trechos em comum ({matches.length})</h3>
          <ul className="flex flex-wrap gap-2">
            {matches.map((match, index) => (
              <li key={`${match.a_first}-${match.b_first}`}>
                <LineChip aria-pressed={current === index} onClick={() => onShow(index)}>
                  A: {lines(match.a_first, match.a_last)} ↔ B: {lines(match.b_first, match.b_last)}
                </LineChip>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-sm text-slate-600 dark:text-slate-300">{result.notice}</p>
    </Card>
  );
}

/** A e B comparados com o gabarito e o alerta de possível vazamento (S32-07; ADR-11, item 5). */
export function GabaritoPair({ gabarito }: { gabarito: SimilarityGabarito }) {
  const sides = [
    ["A", gabarito.a],
    ["B", gabarito.b],
  ] as const;
  return (
    <Card aria-label="Comparação com o gabarito" className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">Comparação com o gabarito · {gabarito.question_id}</h3>
      {gabarito.leak_alert && (
        <div
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100"
        >
          <p className="font-semibold">Possível vazamento do gabarito</p>
          <p className="text-sm">{gabarito.message}</p>
        </div>
      )}
      {gabarito.status === "compared" ? (
        <>
          <ul className="flex flex-col gap-2">
            {sides.map(([label, side]) =>
              side ? (
                <li key={label} className="flex flex-wrap items-center gap-3">
                  <span className="font-medium">
                    Código {label} com o {gabaritoName(side.kind)}:
                  </span>
                  <span className="text-xl font-bold">{PERCENT.format(side.similarity)}%</span>
                  <Band band={side.band} />
                </li>
              ) : null,
            )}
          </ul>
          {!gabarito.leak_alert && <p className="text-sm text-slate-600 dark:text-slate-300">{gabarito.message}</p>}
        </>
      ) : (
        <p role="note" className="text-sm text-slate-700 dark:text-slate-200">
          {gabarito.message}
        </p>
      )}
    </Card>
  );
}

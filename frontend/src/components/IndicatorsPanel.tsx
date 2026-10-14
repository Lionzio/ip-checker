import type { Indicator, Indicators } from "../types/api";
import { Card, LineChip } from "./ui";

/**
 * Painel de indícios de uso de IA (S29-03; ADR-08, US-34): só para a equipe, abaixo do resultado.
 * Cada indício vem com o motivo e as linhas; o texto diz que não é prova e sugere perguntas para a
 * conversa com o aluno, que é a única confirmação. Sem indício, o painel nem aparece. Nada daqui
 * vai para o feedback do aluno.
 */
interface IndicatorsPanelProps {
  indicators: Indicators;
  /** Clique numa linha: o editor seleciona o trecho, como no relatório (S26-03). */
  onSelectLines?: (first: number, last: number) => void;
}

const LEVEL_LABELS: Record<NonNullable<Indicators["level"]>, string> = {
  baixo: "Faixa baixa",
  medio: "Faixa média",
  alto: "Faixa alta",
};

const LEVEL_STYLES: Record<NonNullable<Indicators["level"]>, string> = {
  baixo: "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100",
  medio: "bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100",
  alto: "bg-orange-100 text-orange-900 dark:bg-orange-900/50 dark:text-orange-100",
};

const SIGNAL_LABELS: Record<Indicator["signal"], string> = {
  multiplas_violacoes: "Múltiplas violações",
  referencia_ia: "Semelhança com solução de IA",
  gabarito: "Semelhança com o gabarito",
  estilo: "Estilo",
};

/** Linhas mostradas como botões; o resto aparece contado. */
const SHOWN_LINES = 8;

function Lines({ lines, onSelectLines }: { lines: number[]; onSelectLines?: (first: number, last: number) => void }) {
  if (lines.length === 0) return null;
  const shown = lines.slice(0, SHOWN_LINES);
  const rest = lines.length - shown.length;
  return (
    <p className="mt-1 flex flex-wrap items-center gap-1 text-sm text-slate-600 dark:text-slate-300">
      <span>{lines.length === 1 ? "Linha" : "Linhas"}:</span>
      {shown.map((line) =>
        onSelectLines ? (
          <LineChip key={line} mono={false} onClick={() => onSelectLines(line, line)} aria-label={`Linha ${line}: selecionar no editor`}>
            {line}
          </LineChip>
        ) : (
          <span key={line}>{line}</span>
        ),
      )}
      {rest > 0 && <span>e mais {rest}</span>}
    </p>
  );
}

export function IndicatorsPanel({ indicators, onSelectLines }: IndicatorsPanelProps) {
  const weighted = indicators.items.filter((item) => item.level !== null);
  const style = indicators.items.filter((item) => item.level === null);
  return (
    <Card aria-label="Indícios de uso de IA">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Indícios de uso de IA</h2>
        {indicators.level !== null ? (
          <span className={`rounded px-2 py-0.5 text-sm font-medium ${LEVEL_STYLES[indicators.level]}`}>
            {LEVEL_LABELS[indicators.level]}
          </span>
        ) : (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-sm dark:bg-slate-800">Só marcadores de estilo</span>
        )}
      </div>
      <p role="note" className="mt-2 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800">
        {indicators.notice} Só a equipe vê este painel; ele não entra no feedback.
      </p>

      {weighted.length > 0 && (
        <ul className="mt-3 space-y-3">
          {weighted.map((item) => (
            <li key={`${item.signal}-${item.kind}`} className="rounded-md border-l-4 border-l-orange-500 bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="text-sm font-medium">
                {SIGNAL_LABELS[item.signal]}
                {item.level !== null && ` · ${LEVEL_LABELS[item.level].toLowerCase()}`}
              </p>
              <p className="mt-1">{item.reason}</p>
              <Lines lines={item.lines} onSelectLines={onSelectLines} />
            </li>
          ))}
        </ul>
      )}

      {style.length > 0 && (
        <div className="mt-3">
          <h3 className="font-medium">Marcadores de estilo</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Fatos, sem peso na faixa: alguns alunos escrevem assim por conta própria.
          </p>
          <ul className="mt-2 space-y-2">
            {style.map((item) => (
              <li key={item.kind} className="rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
                <p>{item.reason}</p>
                <Lines lines={item.lines} onSelectLines={onSelectLines} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {indicators.questions.length > 0 && (
        <div className="mt-4">
          <h3 className="font-medium">Perguntas para a conversa com o aluno</h3>
          <ol className="mt-1 list-decimal space-y-1 pl-6">
            {indicators.questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}

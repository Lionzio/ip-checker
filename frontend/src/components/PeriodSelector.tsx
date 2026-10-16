import type { PeriodInfo } from "../types/api";

interface PeriodSelectorProps {
  periods: PeriodInfo[];
  /** O período escolhido; `null` é o ativo. */
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

/**
 * Período, antes de Lista e Questão (S43-03, US-39): para corrigir uma lista atrasada com as regras
 * do período dela. Com um período só carregado (o caso até a troca de 2026.2 para 2027.1), não
 * aparece: não há o que escolher.
 */
export function PeriodSelector({ periods, value, onChange, disabled = false }: PeriodSelectorProps) {
  if (periods.length <= 1) return null;
  const active = periods.find((period) => period.active)?.period ?? null;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor="period-selector" className="text-sm font-medium text-slate-700 dark:text-slate-200">
        Período
      </label>
      <select
        id="period-selector"
        value={value ?? active ?? ""}
        onChange={(event) => onChange(event.target.value === active ? null : event.target.value)}
        disabled={disabled}
        className="w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
      >
        {periods.map((period) => (
          <option key={period.period} value={period.period}>
            {period.active ? `${period.period} (ativo)` : period.period}
          </option>
        ))}
      </select>
    </div>
  );
}

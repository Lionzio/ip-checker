import type { ListInfo } from "../types/api";

interface ListSelectorProps {
  lists: ListInfo[];
  value: number | null;
  onChange: (value: number | null) => void;
  disabled?: boolean;
}

export function ListSelector({ lists, value, onChange, disabled = false }: ListSelectorProps) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor="list-selector" className="text-sm font-medium text-slate-700 dark:text-slate-200">
        Lista
      </label>
      <select
        id="list-selector"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
        disabled={disabled}
        className="w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
      >
        <option value="">Escolha a lista</option>
        {lists.map((list) => (
          <option key={list.number} value={list.number}>
            Lista {list.number}: {list.title}
          </option>
        ))}
      </select>
    </div>
  );
}

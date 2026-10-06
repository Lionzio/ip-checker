import type { QuestionInfo } from "../types/api";

interface QuestionSelectorProps {
  /** As questões da lista escolhida; ``null`` enquanto nenhuma lista foi escolhida. */
  questions: QuestionInfo[] | null;
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

/**
 * Questão opcional (R-01, FR-03): as regras dela, cadastradas a partir do enunciado, prevalecem
 * sobre as da lista. Sem questão, valem só as regras da lista.
 */
export function QuestionSelector({ questions, value, onChange, disabled = false }: QuestionSelectorProps) {
  const empty = questions !== null && questions.length === 0;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor="question-selector" className="text-sm font-medium text-slate-700 dark:text-slate-200">
        Questão
      </label>
      <select
        id="question-selector"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
        disabled={disabled || questions === null || empty}
        className="w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 disabled:text-slate-600 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:disabled:text-slate-300"
      >
        {questions === null && <option value="">Escolha a lista primeiro</option>}
        {empty && <option value="">Nenhuma questão com regra específica cadastrada</option>}
        {questions !== null && !empty && (
          <>
            <option value="">Sem questão (só as regras da lista)</option>
            {questions.map((question) => (
              <option key={question.id} value={question.id}>
                {question.id}: {question.title}
              </option>
            ))}
          </>
        )}
      </select>
    </div>
  );
}

import type { Treatment } from "../types/api";

/** Opções do tratamento (FR-26), cada uma com o exemplo do texto do feedback. */
const TREATMENTS: { value: Treatment; label: string; example: string }[] = [
  { value: "masculino", label: "Masculino", example: "“sou o monitor...”" },
  { value: "feminino", label: "Feminino", example: "“sou a monitora...”" },
  { value: "neutro", label: "Neutro", example: "“aqui é ..., da monitoria”" },
];

interface TreatmentFieldProps {
  value: Treatment | null;
  onChange: (value: Treatment) => void;
}

/** Como a pessoa quer ser tratada no feedback. Só ela vê esse dado. */
export function TreatmentField({ value, onChange }: TreatmentFieldProps) {
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="font-medium">Tratamento</legend>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Como você quer ser tratado(a) no texto do feedback. Ninguém mais vê esta escolha.
      </p>
      {TREATMENTS.map((option) => (
        <label key={option.value} className="flex items-center gap-2">
          <input
            type="radio"
            name="treatment"
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
            required
          />
          <span>
            {option.label} <span className="text-slate-600 dark:text-slate-300">{option.example}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

import { useTheme } from "../hooks/useTheme";
import { THEME_LABELS, THEME_OPTIONS } from "../theme";

/** O tema da página, no Perfil (S37-05): claro, escuro ou do sistema, salvo neste navegador. */
export function ThemeField() {
  const [preference, setPreference] = useTheme();
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="font-medium">Tema</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {THEME_OPTIONS.map((option) => (
          <label key={option} className="flex min-h-11 items-center gap-2 sm:min-h-0">
            <input type="radio" name="tema" value={option} checked={preference === option} onChange={() => setPreference(option)} />
            {THEME_LABELS[option]}
          </label>
        ))}
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">Vale só neste navegador; "Do sistema" segue a escolha do seu computador ou celular.</p>
    </fieldset>
  );
}

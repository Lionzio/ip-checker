import { passwordRules } from "../passwordPolicy";

/** Os requisitos da senha, marcados conforme a pessoa digita (FR-23). */
export function PasswordRequirements({ password, id }: { password: string; id: string }) {
  return (
    <ul id={id} aria-label="Requisitos da senha" className="flex flex-col gap-0.5 text-sm">
      {passwordRules(password).map((rule) => (
        <li
          key={rule.label}
          className={rule.met ? "text-green-700 dark:text-green-300" : "text-slate-600 dark:text-slate-300"}
        >
          <span aria-hidden="true">{rule.met ? "✓ " : "• "}</span>
          {rule.label}
          <span className="sr-only">{rule.met ? " (atendido)" : " (falta)"}</span>
        </li>
      ))}
    </ul>
  );
}

import type { AccountStatus, Role } from "../types/api";

/**
 * Etiquetas de cargo (FR-28): professor verde, monitor-chefe azul-claro, monitor roxo,
 * desenvolvedor dourado e contas removidas em cinza. O nome vai sempre escrito, nunca só a cor
 * (NFR-19), e as cores têm contraste AA nos dois temas.
 */
const ROLE_STYLES: Record<Role, string> = {
  desenvolvedor:
    "border-amber-400 bg-amber-100 text-amber-900 dark:border-amber-500 dark:bg-amber-950 dark:text-amber-100",
  professor:
    "border-green-400 bg-green-100 text-green-900 dark:border-green-600 dark:bg-green-950 dark:text-green-100",
  monitor_chefe:
    "border-sky-400 bg-sky-100 text-sky-900 dark:border-sky-600 dark:bg-sky-950 dark:text-sky-100",
  monitor:
    "border-purple-400 bg-purple-100 text-purple-900 dark:border-purple-600 dark:bg-purple-950 dark:text-purple-100",
};
const REMOVED_STYLE =
  "border-slate-400 bg-slate-100 text-slate-800 dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100";
const REMOVED: AccountStatus[] = ["ex_monitor", "conselheiro", "inativo"];

interface RoleBadgeProps {
  role: Role | null;
  status: AccountStatus;
  label: string;
}

export function RoleBadge({ role, status, label }: RoleBadgeProps) {
  const style = REMOVED.includes(status) || role === null ? REMOVED_STYLE : ROLE_STYLES[role];
  return (
    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}

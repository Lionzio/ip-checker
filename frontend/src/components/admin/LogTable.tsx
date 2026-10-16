import type { ManagementLogEntry } from "../../types/api";
import { Card } from "../ui";
import { TABLE, TABLE_HEAD } from "./names";

/** "Pendente → Ativo (Monitor)" ou, na mudança de cargo, "Monitor → Monitor-chefe". */
function change(entry: ManagementLogEntry): string {
  if (entry.action === "alterar_cargo") return `${entry.from_role_label ?? "—"} → ${entry.to_role_label ?? "—"}`;
  const role = entry.to_status === "ativo" && entry.to_role_label !== null ? ` (${entry.to_role_label})` : "";
  return `${entry.from_status_label} → ${entry.to_status_label}${role}`;
}

/** O registro das ações de gerenciamento (S23-03, REC-06), da mais recente para a mais antiga. */
export function LogTable({ entries }: { entries: ManagementLogEntry[] }) {
  return (
    <Card as="div" padding="none" className="overflow-x-auto">
      <table className={`${TABLE} min-w-xl`}>
        <thead className={TABLE_HEAD}>
          <tr>
            <th scope="col" className="px-3 py-2 font-semibold">Quando</th>
            <th scope="col" className="px-3 py-2 font-semibold">Quem</th>
            <th scope="col" className="px-3 py-2 font-semibold">Ação</th>
            <th scope="col" className="px-3 py-2 font-semibold">Mudança</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => (
            <tr key={`${entry.at}-${index}`} className="border-t border-slate-200 align-top dark:border-slate-700">
              <td className="px-3 py-2 whitespace-nowrap">
                <time dateTime={entry.at}>{new Date(entry.at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</time>
              </td>
              <td className="px-3 py-2">
                {entry.actor_name}
                {entry.actor_role_label !== null && (
                  <span className="block text-xs text-slate-600 dark:text-slate-300">{entry.actor_role_label}</span>
                )}
              </td>
              <td className="px-3 py-2">
                {entry.action_label} <span className="font-medium">{entry.target_name}</span>
              </td>
              <td className="px-3 py-2">{change(entry)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

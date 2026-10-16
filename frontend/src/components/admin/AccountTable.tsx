import { useState } from "react";
import type { ManagedAccount, Role } from "../../types/api";
import { RoleBadge } from "../RoleBadge";
import { Button, Card } from "../ui";
import { METHODS, ROLE_NAMES, TABLE, TABLE_HEAD } from "./names";

// Como os botões (S37-03): 44 px nas telas de toque, menor a partir de sm.
const SELECT =
  "min-h-11 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm sm:min-h-8 dark:border-slate-600 dark:bg-slate-900";

export interface Handlers {
  approve: (account: ManagedAccount, role: Role) => void;
  reject: (account: ManagedAccount) => void;
  changeRole: (account: ManagedAccount, role: Role) => void;
  remove: (account: ManagedAccount) => void;
  reactivate: (account: ManagedAccount, role: Role) => void;
}

type Kind = "requests" | "active" | "removed";

/** Os pedidos, os membros ativos ou as contas removidas, com os botões que o cargo permite (S15-03). */
export function AccountTable({
  kind,
  accounts,
  busyId,
  handlers,
}: {
  kind: Kind;
  accounts: ManagedAccount[];
  busyId: string | null;
  handlers: Handlers;
}) {
  if (accounts.length === 0) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Nenhuma conta corresponde à busca.</p>;
  }
  return (
    <Card as="div" padding="none" className="overflow-x-auto">
      <table className={`${TABLE} min-w-2xl`}>
        <thead className={TABLE_HEAD}>
          <tr>
            <th scope="col" className="px-3 py-2 font-semibold">Nome</th>
            <th scope="col" className="px-3 py-2 font-semibold">E-mail</th>
            <th scope="col" className="px-3 py-2 font-semibold">Curso</th>
            {kind === "requests" ? (
              <>
                <th scope="col" className="px-3 py-2 font-semibold">Método</th>
                <th scope="col" className="px-3 py-2 font-semibold">Pedido em</th>
              </>
            ) : (
              <th scope="col" className="px-3 py-2 font-semibold">{kind === "active" ? "Cargo" : "Situação"}</th>
            )}
            <th scope="col" className="px-3 py-2 font-semibold">Ações</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr
              key={account.id}
              aria-busy={busyId === account.id || undefined}
              className="border-t border-slate-200 align-top aria-busy:opacity-60 dark:border-slate-700"
            >
              <th scope="row" className="px-3 py-2 font-medium">{account.name}</th>
              <td className="px-3 py-2 break-all">{account.email}</td>
              <td className="px-3 py-2">{account.course}</td>
              {kind === "requests" ? (
                <>
                  <td className="px-3 py-2">{METHODS[account.signup_method]}</td>
                  <td className="px-3 py-2">{new Date(account.requested_at).toLocaleDateString("pt-BR")}</td>
                </>
              ) : (
                <td className="px-3 py-2">
                  <RoleBadge
                    role={account.role}
                    status={account.status}
                    label={kind === "active" ? (account.role_label ?? account.status_label) : account.status_label}
                  />
                  {kind === "removed" && account.role_label !== null && (
                    <span className="mt-1 block text-xs text-slate-600 dark:text-slate-300">Último cargo: {account.role_label}</span>
                  )}
                </td>
              )}
              <td className="px-3 py-2">
                <Actions account={account} busy={busyId === account.id} handlers={handlers} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Actions({ account, busy, handlers }: { account: ManagedAccount; busy: boolean; handlers: Handlers }) {
  const [chosen, setChosen] = useState<Role | "">("");
  // Depois de cada ação as listas são recarregadas; uma escolha que não vale mais volta à primeira.
  const role = chosen !== "" && account.roles.includes(chosen) ? chosen : (account.roles[0] ?? "");
  const can = (action: ManagedAccount["actions"][number]) => account.actions.includes(action);
  const roleAction = can("aprovar") ? "aprovar" : can("alterar_cargo") ? "alterar_cargo" : can("reativar") ? "reativar" : null;

  if (account.actions.length === 0) {
    return <span className="text-slate-600 dark:text-slate-300">—</span>;
  }

  const roleLabel = { aprovar: "Aprovar", alterar_cargo: "Alterar cargo", reativar: "Reativar" } as const;
  const selectLabel = {
    aprovar: `Cargo para aprovar ${account.name}`,
    alterar_cargo: `Novo cargo de ${account.name}`,
    reativar: `Cargo para reativar ${account.name}`,
  } as const;

  function submitRole() {
    if (role === "" || roleAction === null) return;
    if (roleAction === "aprovar") handlers.approve(account, role);
    else if (roleAction === "alterar_cargo") handlers.changeRole(account, role);
    else handlers.reactivate(account, role);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {roleAction !== null && account.roles.length > 0 && (
        <>
          <select
            aria-label={selectLabel[roleAction]}
            value={role}
            onChange={(event) => setChosen(event.target.value as Role)}
            className={SELECT}
          >
            {account.roles.map((option) => (
              <option key={option} value={option}>
                {ROLE_NAMES[option]}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant={roleAction === "aprovar" ? "primary" : "secondary"}
            disabled={busy || role === ""}
            onClick={submitRole}
            aria-label={`${roleLabel[roleAction]} ${account.name}`}
          >
            {roleLabel[roleAction]}
          </Button>
        </>
      )}
      {can("recusar") && (
        <Button variant="danger" size="sm" disabled={busy} onClick={() => handlers.reject(account)} aria-label={`Recusar ${account.name}`}>
          Recusar
        </Button>
      )}
      {can("remover") && (
        <Button variant="danger" size="sm" disabled={busy} onClick={() => handlers.remove(account)} aria-label={`Remover ${account.name}`}>
          Remover
        </Button>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { RoleBadge } from "../components/RoleBadge";
import type { AdminClient } from "../services/client";
import type { AccountStatus, ManagedAccount, MembersResponse, Role } from "../types/api";
import { errorMessage } from "../ui";

/**
 * Tela de gerenciamento (S15-03, FR-28): fila de pedidos, membros ativos e contas removidas. Cada
 * linha mostra só os botões que quem está logado pode usar; o backend confere de novo.
 */
const ROLE_NAMES: Record<Role, string> = {
  desenvolvedor: "Monitor e desenvolvedor",
  professor: "Professor",
  monitor_chefe: "Monitor-chefe",
  monitor: "Monitor",
};
const STATUS_NAMES: Partial<Record<AccountStatus, string>> = {
  ex_monitor: "Ex-monitor",
  conselheiro: "Conselheiro",
  inativo: "Inativo",
};
const METHODS: Record<ManagedAccount["signup_method"], string> = {
  senha: "E-mail e senha",
  google: "Google",
  seed: "Conta inicial",
};
const SMALL_BUTTON =
  "rounded-md border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:hover:bg-slate-800";
const PRIMARY_BUTTON =
  "rounded-md bg-blue-700 px-3 py-1 text-sm font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400";
const DANGER_BUTTON =
  "rounded-md border border-red-300 px-3 py-1 text-sm text-red-800 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-700 dark:text-red-200 dark:hover:bg-red-950";
const SELECT = "rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-900";

interface Lists {
  requests: ManagedAccount[];
  members: MembersResponse;
}

type Notice = { ok: boolean; text: string } | null;

export function Admin({ client }: { client: AdminClient }) {
  const [lists, setLists] = useState<Lists | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [busy, setBusy] = useState(false);
  // Cada ação recarrega as listas: as ações permitidas mudam com o estado de cada conta.
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((current) => current + 1);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([client.listRequests(controller.signal), client.listMembers(controller.signal)]).then(
      ([requests, members]) => {
        setLists({ requests, members });
        setLoadError(null);
        setBusy(false);
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setLoadError(errorMessage(error));
        setBusy(false);
      },
    );
    return () => controller.abort();
  }, [client, version]);

  async function run(action: () => Promise<void>, success: string) {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ ok: true, text: success });
    } catch (caught) {
      setNotice({ ok: false, text: errorMessage(caught) });
    }
    reload();
  }

  const handlers: Handlers = {
    approve: (account, role) =>
      void run(() => client.approve(account.id, role), `${account.name} foi aprovado(a) como ${ROLE_NAMES[role]}.`),
    reject: (account) => {
      if (!window.confirm(`Recusar o pedido de ${account.name}? A pessoa não terá acesso.`)) return;
      void run(() => client.reject(account.id), `O pedido de ${account.name} foi recusado.`);
    },
    changeRole: (account, role) =>
      void run(() => client.changeRole(account.id, role), `${account.name} agora é ${ROLE_NAMES[role]}.`),
    remove: (account) => {
      const result = account.removal_status !== null ? STATUS_NAMES[account.removal_status] : undefined;
      const question = `Remover ${account.name} da equipe? A conta passa a ${result ?? "removida"}, perde o acesso e as sessões abertas são encerradas.`;
      if (!window.confirm(question)) return;
      void run(() => client.remove(account.id), `${account.name} foi removido(a) da equipe (${result ?? "removida"}).`);
    },
    reactivate: (account, role) =>
      void run(() => client.reactivate(account.id, role), `${account.name} foi reativado(a) como ${ROLE_NAMES[role]}.`),
  };

  return (
    <div className="flex flex-col gap-8 py-4">
      <div>
        <h2 className="text-xl font-semibold">Gerenciamento da equipe</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Aprovação de cadastros, cargos e remoções. Cada linha mostra só o que o seu cargo permite.
        </p>
      </div>
      <div aria-live="polite">
        {notice !== null && (
          <p
            role={notice.ok ? "status" : "alert"}
            className={notice.ok ? "text-sm text-green-800 dark:text-green-300" : "text-sm text-red-700 dark:text-red-300"}
          >
            {notice.text}
          </p>
        )}
      </div>
      {loadError !== null && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p>{loadError}</p>
          <button type="button" className={SMALL_BUTTON} onClick={reload}>
            Tentar novamente
          </button>
        </div>
      )}
      {lists === null && loadError === null && <p className="text-slate-600 dark:text-slate-300">Carregando…</p>}
      {lists !== null && (
        <>
          <Section title="Pedidos pendentes" empty="Nenhum pedido aguardando aprovação." count={lists.requests.length}>
            <AccountTable kind="requests" accounts={lists.requests} busy={busy} handlers={handlers} />
          </Section>
          <Section title="Membros ativos" empty="Nenhum membro ativo." count={lists.members.active.length}>
            <AccountTable kind="active" accounts={lists.members.active} busy={busy} handlers={handlers} />
          </Section>
          <Section
            title="Ex-monitores, conselheiros e inativos"
            empty="Nenhuma conta removida."
            count={lists.members.removed.length}
          >
            <AccountTable kind="removed" accounts={lists.members.removed} busy={busy} handlers={handlers} />
          </Section>
        </>
      )}
    </div>
  );
}

interface Handlers {
  approve: (account: ManagedAccount, role: Role) => void;
  reject: (account: ManagedAccount) => void;
  changeRole: (account: ManagedAccount, role: Role) => void;
  remove: (account: ManagedAccount) => void;
  reactivate: (account: ManagedAccount, role: Role) => void;
}

function Section({ title, empty, count, children }: { title: string; empty: string; count: number; children: React.ReactNode }) {
  const id = `secao-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h3 id={id} className="text-lg font-semibold">
        {title} <span className="text-sm font-normal text-slate-600 dark:text-slate-300">({count})</span>
      </h3>
      {count === 0 ? <p className="text-sm text-slate-600 dark:text-slate-300">{empty}</p> : children}
    </section>
  );
}

type Kind = "requests" | "active" | "removed";

function AccountTable({
  kind,
  accounts,
  busy,
  handlers,
}: {
  kind: Kind;
  accounts: ManagedAccount[];
  busy: boolean;
  handlers: Handlers;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
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
            <tr key={account.id} className="border-t border-slate-200 align-top dark:border-slate-700">
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
                <Actions account={account} busy={busy} handlers={handlers} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
          <button
            type="button"
            className={roleAction === "aprovar" ? PRIMARY_BUTTON : SMALL_BUTTON}
            disabled={busy || role === ""}
            onClick={submitRole}
            aria-label={`${roleLabel[roleAction]} ${account.name}`}
          >
            {roleLabel[roleAction]}
          </button>
        </>
      )}
      {can("recusar") && (
        <button type="button" className={DANGER_BUTTON} disabled={busy} onClick={() => handlers.reject(account)} aria-label={`Recusar ${account.name}`}>
          Recusar
        </button>
      )}
      {can("remover") && (
        <button type="button" className={DANGER_BUTTON} disabled={busy} onClick={() => handlers.remove(account)} aria-label={`Remover ${account.name}`}>
          Remover
        </button>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { RoleBadge } from "../components/RoleBadge";
import { Button, Card } from "../components/ui";
import type { AdminClient } from "../services/client";
import type { AccountStatus, ManagedAccount, ManagementLogEntry, MembersResponse, Role } from "../types/api";
import { errorMessage, INPUT, sessionExpired } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Tela de gerenciamento (S15-03, FR-28): fila de pedidos, membros ativos e contas removidas. Cada
 * linha mostra só os botões que quem está logado pode usar; o backend confere de novo. O registro
 * das ações (S23-03, REC-06) só aparece para o desenvolvedor e os professores.
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
// Como os botões (S37-03): 44 px nas telas de toque, menor a partir de sm.
const SELECT =
  "min-h-11 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm sm:min-h-8 dark:border-slate-600 dark:bg-slate-900";
const TABLE = "w-full text-left text-sm";
const TABLE_HEAD = "bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200";

interface Lists {
  requests: ManagedAccount[];
  members: MembersResponse;
  log: ManagementLogEntry[] | null;
}

type Notice = { ok: boolean; text: string } | null;

/** Quantas ações do registro aparecem de cada vez (S26-04). */
export const LOG_PAGE = 20;

/** Sem acento e em minúsculas: "joao" acha "João". */
function fold(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

interface AdminProps {
  client: AdminClient;
  canViewLog?: boolean;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated?: () => void;
}

export function Admin({ client, canViewLog = false, onUnauthenticated }: AdminProps) {
  useDocumentTitle(PAGE_TITLES.admin);
  const [lists, setLists] = useState<Lists | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  // A conta em que uma ação está em andamento: só a linha dela fica ocupada (S26-04).
  const [busyId, setBusyId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "">("");
  const [logShown, setLogShown] = useState(LOG_PAGE);
  // Cada ação recarrega as listas: as ações permitidas mudam com o estado de cada conta.
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((current) => current + 1);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      client.listRequests(controller.signal),
      client.listMembers(controller.signal),
      canViewLog ? client.managementLog(controller.signal) : Promise.resolve(null),
    ]).then(
      ([requests, members, log]) => {
        setLists({ requests, members, log });
        setLoadError(null);
        setBusyId(null);
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setBusyId(null);
        if (sessionExpired(error) && onUnauthenticated) {
          onUnauthenticated();
          return;
        }
        setLoadError(errorMessage(error));
      },
    );
    return () => controller.abort();
  }, [client, canViewLog, version, onUnauthenticated]);

  async function run(account: ManagedAccount, action: () => Promise<void>, success: string) {
    setBusyId(account.id);
    setNotice(null);
    try {
      await action();
      setNotice({ ok: true, text: success });
    } catch (caught) {
      if (sessionExpired(caught) && onUnauthenticated) {
        onUnauthenticated();
        return;
      }
      setNotice({ ok: false, text: errorMessage(caught) });
    }
    reload();
  }

  const handlers: Handlers = {
    approve: (account, role) =>
      void run(account, () => client.approve(account.id, role), `${account.name} foi aprovado(a) como ${ROLE_NAMES[role]}.`),
    reject: (account) => {
      if (!window.confirm(`Recusar o pedido de ${account.name}? A pessoa não terá acesso.`)) return;
      void run(account, () => client.reject(account.id), `O pedido de ${account.name} foi recusado.`);
    },
    changeRole: (account, role) =>
      void run(account, () => client.changeRole(account.id, role), `${account.name} agora é ${ROLE_NAMES[role]}.`),
    remove: (account) => {
      const result = account.removal_status !== null ? STATUS_NAMES[account.removal_status] : undefined;
      const question = `Remover ${account.name} da equipe? A conta passa a ${result ?? "removida"}, perde o acesso e as sessões abertas são encerradas.`;
      if (!window.confirm(question)) return;
      void run(account, () => client.remove(account.id), `${account.name} foi removido(a) da equipe (${result ?? "removida"}).`);
    },
    reactivate: (account, role) =>
      void run(account, () => client.reactivate(account.id, role), `${account.name} foi reativado(a) como ${ROLE_NAMES[role]}.`),
  };

  // Busca por nome ou e-mail, sem acento; o filtro de cargo vale para os membros e as contas removidas.
  const query = fold(search.trim());
  const matches = (account: ManagedAccount, byRole: boolean) =>
    (query === "" || fold(account.name).includes(query) || fold(account.email).includes(query)) &&
    (!byRole || roleFilter === "" || account.role === roleFilter);

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
          <Button variant="secondary" size="sm" onClick={reload}>
            Tentar novamente
          </Button>
        </div>
      )}
      {lists === null && loadError === null && <p className="text-slate-600 dark:text-slate-300">Carregando…</p>}
      {lists !== null && (
        <>
          <div role="search" className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm sm:max-w-xs">
              <span className="font-medium">Buscar por nome ou e-mail</span>
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} className={INPUT} />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Cargo</span>
              <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value as Role | "")} className={INPUT}>
                <option value="">Todos os cargos</option>
                {(Object.keys(ROLE_NAMES) as Role[]).map((role) => (
                  <option key={role} value={role}>
                    {ROLE_NAMES[role]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Section title="Pedidos pendentes" empty="Nenhum pedido aguardando aprovação." count={lists.requests.length}>
            <AccountTable kind="requests" accounts={lists.requests.filter((a) => matches(a, false))} busyId={busyId} handlers={handlers} />
          </Section>
          <Section title="Membros ativos" empty="Nenhum membro ativo." count={lists.members.active.length}>
            <AccountTable kind="active" accounts={lists.members.active.filter((a) => matches(a, true))} busyId={busyId} handlers={handlers} />
          </Section>
          <Section
            title="Ex-monitores, conselheiros e inativos"
            empty="Nenhuma conta removida."
            count={lists.members.removed.length}
          >
            <AccountTable kind="removed" accounts={lists.members.removed.filter((a) => matches(a, true))} busyId={busyId} handlers={handlers} />
          </Section>
          {lists.log !== null && (
            <Section title="Registro de ações" empty="Nenhuma ação registrada nos últimos 12 meses." count={lists.log.length}>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Quem aprovou, recusou, alterou o cargo, removeu ou reativou cada conta nos últimos 12 meses, da ação mais
                recente para a mais antiga. Só o desenvolvedor e os professores veem este registro.
              </p>
              <LogTable entries={lists.log.slice(0, logShown)} />
              {lists.log.length > logShown && (
                <Button variant="secondary" size="sm" className="self-start" onClick={() => setLogShown((shown) => shown + LOG_PAGE)}>
                  Mostrar mais ({lists.log.length - logShown} restantes)
                </Button>
              )}
            </Section>
          )}
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

/** "Pendente → Ativo (Monitor)" ou, na mudança de cargo, "Monitor → Monitor-chefe". */
function change(entry: ManagementLogEntry): string {
  if (entry.action === "alterar_cargo") return `${entry.from_role_label ?? "—"} → ${entry.to_role_label ?? "—"}`;
  const role = entry.to_status === "ativo" && entry.to_role_label !== null ? ` (${entry.to_role_label})` : "";
  return `${entry.from_status_label} → ${entry.to_status_label}${role}`;
}

function LogTable({ entries }: { entries: ManagementLogEntry[] }) {
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

import { useEffect, useState } from "react";
import { AccountTable, type Handlers } from "../components/admin/AccountTable";
import { LogTable } from "../components/admin/LogTable";
import { ROLE_NAMES, STATUS_NAMES } from "../components/admin/names";
import { Section } from "../components/admin/Section";
import { ListPanel } from "../components/ListPanel";
import { Button } from "../components/ui";
import type { AdminClient } from "../services/client";
import type { ManagedAccount, ManagementLogEntry, MembersResponse, Role } from "../types/api";
import { errorMessage, INPUT, sessionExpired } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Tela de gerenciamento (S15-03, FR-28): fila de pedidos, membros ativos e contas removidas. Cada
 * linha mostra só os botões que quem está logado pode usar; o backend confere de novo. O registro
 * das ações (S23-03, REC-06) só aparece para o desenvolvedor e os professores. As tabelas e as
 * seções moram em `components/admin/` (S39-01).
 */
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
          <ListPanel client={client} onUnauthenticated={onUnauthenticated} />
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

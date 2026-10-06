import { Link, NavLink } from "react-router";
import { NAV_LABELS } from "../labels";
import type { Account } from "../types/api";

interface AppHeaderProps {
  account: Account | null;
  onSignOut?: () => void;
}

// Alvos de 44 px no celular (S26-01); a partir de sm, a altura volta ao tamanho de mesa.
const ITEM =
  "inline-flex min-h-11 items-center rounded-md px-3 text-sm font-medium hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600 sm:min-h-9 dark:hover:bg-slate-800";
const ACTIVE = "bg-slate-100 text-blue-800 dark:bg-slate-800 dark:text-blue-200";

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? `${ITEM} ${ACTIVE}` : ITEM;
}

/**
 * Cabeçalho de todas as telas. Com sessão, a navegação principal (com `aria-current` na tela
 * atual), quem está logado e Sair. No celular, só o nome curto e a navegação, que quebra linha em
 * vez de passar da largura da tela (S26-01).
 */
export function AppHeader({ account, onSignOut }: AppHeaderProps) {
  return (
    <header className="border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <h1 className="text-xl font-bold sm:text-2xl">
            <Link to="/">IP-Checker</Link>
          </h1>
          <p className="hidden text-sm text-slate-600 sm:block dark:text-slate-300">
            Verificação das permissões das listas de Introdução à Programação, sem executar o código.
          </p>
        </div>
        {account !== null && (
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
            <p className="hidden text-sm lg:block">
              <span className="font-medium">{account.name}</span>
              <span className="text-slate-600 dark:text-slate-300"> · {account.role_label}</span>
            </p>
            <nav aria-label="Principal">
              <ul className="flex flex-wrap items-center gap-1">
                <li>
                  <NavLink to="/" end className={navClass}>
                    {NAV_LABELS.checker}
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/plagio" className={navClass}>
                    {NAV_LABELS.plagiarism}
                  </NavLink>
                </li>
                {account.can_manage && (
                  <li>
                    <NavLink to="/gerenciar" className={navClass}>
                      {NAV_LABELS.admin}
                    </NavLink>
                  </li>
                )}
                <li>
                  <NavLink to="/perfil" className={navClass} title={`${account.name} · ${account.role_label}`}>
                    {NAV_LABELS.profile}
                  </NavLink>
                </li>
                <li>
                  <button type="button" onClick={onSignOut} className={`${ITEM} border border-slate-300 dark:border-slate-600`}>
                    {NAV_LABELS.signOut}
                  </button>
                </li>
              </ul>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}

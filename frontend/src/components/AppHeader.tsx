import { Link } from "react-router";
import type { Account } from "../types/api";

interface AppHeaderProps {
  account: Account | null;
  onSignOut?: () => void;
}

/** Cabeçalho de todas as telas; com sessão, mostra quem está logado e o botão Sair. */
export function AppHeader({ account, onSignOut }: AppHeaderProps) {
  return (
    <header className="border-b border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">
            <Link to="/">IP-Checker</Link>
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Verificação das permissões das listas de Introdução à Programação, sem executar o código.
          </p>
        </div>
        {account !== null && (
          <div className="flex items-center gap-3 text-sm">
            <span>
              <span className="font-medium">{account.name}</span>
              <span className="text-slate-600 dark:text-slate-300"> · {account.role_label}</span>
            </span>
            <Link to="/perfil" className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800">
              Perfil
            </Link>
            <button
              type="button"
              onClick={onSignOut}
              className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

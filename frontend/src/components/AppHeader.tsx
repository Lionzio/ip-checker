import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { Link, NavLink } from "react-router";
import { useTheme } from "../hooks/useTheme";
import { NAV_LABELS } from "../labels";
import { THEME_LABELS, THEME_OPTIONS } from "../theme";
import type { Account } from "../types/api";
import { Logo } from "./Logo";
import { Button } from "./ui";

interface AppHeaderProps {
  account: Account | null;
  onSignOut?: () => void;
}

// Alvos de 44 px no celular (S26-01); a partir de sm, a altura volta ao tamanho de mesa.
const ITEM =
  "inline-flex min-h-11 items-center rounded-md px-3 text-sm font-medium hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600 sm:min-h-9 dark:hover:bg-slate-800";
const ACTIVE = "bg-slate-100 text-blue-800 dark:bg-slate-800 dark:text-blue-200";
const MENU_ITEM = `${ITEM} w-full justify-start`;

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? `${ITEM} ${ACTIVE}` : ITEM;
}

/** O primeiro nome, para o botão do menu da conta. */
function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}

/**
 * Cabeçalho de todas as telas (S26-01; S37-04): o logotipo, a navegação principal (com
 * `aria-current` na tela atual) e, com sessão, o menu da conta, aberto pelo primeiro nome, com o
 * nome completo, o cargo, Perfil e Sair. No celular, a navegação quebra linha em vez de passar da
 * largura da tela.
 */
export function AppHeader({ account, onSignOut }: AppHeaderProps) {
  return (
    <header className="border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div className="flex min-w-0 items-center gap-3">
          <Logo />
          <div className="min-w-0">
            <h1 className="text-xl font-bold sm:text-2xl">
              <Link to="/">IP-Checker</Link>
            </h1>
            <p className="hidden text-sm text-slate-600 sm:block dark:text-slate-300">
              Verificação das permissões das listas de Introdução à Programação, sem executar o código.
            </p>
          </div>
        </div>
        {account !== null && (
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
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
              </ul>
            </nav>
            <AccountMenu account={account} onSignOut={onSignOut} />
          </div>
        )}
      </div>
    </header>
  );
}

/**
 * O menu da conta (S37-04): abre pelo clique ou pelo teclado; setas, Esc e clique fora. Traz também
 * o tema (S37-05), como itens de escolha única.
 */
function AccountMenu({ account, onSignOut }: { account: Account; onSignOut?: () => void }) {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useTheme();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    rootRef.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    function pointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", pointerDown);
    return () => document.removeEventListener("pointerdown", pointerDown);
  }, [open]);

  function close(refocus: boolean) {
    setOpen(false);
    if (refocus) buttonRef.current?.focus();
  }

  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      close(true);
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    const items = [...(rootRef.current?.querySelectorAll<HTMLElement>("[role=menuitem], [role=menuitemradio]") ?? [])];
    if (items.length === 0) return;
    event.preventDefault();
    const index = items.indexOf(document.activeElement as HTMLElement);
    const next = event.key === "ArrowDown" ? (index + 1) % items.length : (index - 1 + items.length) % items.length;
    items[next]?.focus();
  }

  return (
    <div ref={rootRef} className="relative" onKeyDown={keyDown}>
      <Button
        ref={buttonRef}
        variant="secondary"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Menu da conta: ${account.name}`}
        onClick={() => setOpen((current) => !current)}
      >
        {firstName(account.name)}
        <svg aria-hidden="true" viewBox="0 0 16 16" className="size-3.5">
          <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </Button>
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-64 rounded-md border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900">
          <p className="px-3 py-2 text-sm">
            <span className="block font-medium">{account.name}</span>
            <span className="text-slate-600 dark:text-slate-300">{account.role_label}</span>
          </p>
          <div role="menu" id={menuId} aria-label={`Conta de ${account.name}`} className="flex flex-col border-t border-slate-200 pt-1 dark:border-slate-700">
            <Link role="menuitem" to="/perfil" className={MENU_ITEM} onClick={() => close(false)}>
              {NAV_LABELS.profile}
            </Link>
            <p className="px-3 pt-2 pb-1 text-xs font-medium text-slate-600 uppercase dark:text-slate-300">Tema</p>
            {THEME_OPTIONS.map((option) => (
              <Button
                key={option}
                role="menuitemradio"
                aria-checked={theme === option}
                variant="link"
                className="justify-start px-3 no-underline aria-checked:font-semibold hover:bg-slate-100 sm:min-h-9 dark:hover:bg-slate-800"
                onClick={() => setTheme(option)}
              >
                <span aria-hidden="true" className="inline-block w-4">
                  {theme === option ? "✓" : ""}
                </span>
                {THEME_LABELS[option]}
              </Button>
            ))}
            <div role="separator" className="my-1 border-t border-slate-200 dark:border-slate-700" />
            <Button
              role="menuitem"
              variant="link"
              className="justify-start px-3 no-underline hover:bg-slate-100 sm:min-h-9 dark:hover:bg-slate-800"
              onClick={() => {
                close(false);
                onSignOut?.();
              }}
            >
              {NAV_LABELS.signOut}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

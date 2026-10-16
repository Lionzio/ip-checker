import type { AccountStatus, ManagedAccount, Role } from "../../types/api";

export const ROLE_NAMES: Record<Role, string> = {
  desenvolvedor: "Monitor e desenvolvedor",
  professor: "Professor",
  monitor_chefe: "Monitor-chefe",
  monitor: "Monitor",
};

export const STATUS_NAMES: Partial<Record<AccountStatus, string>> = {
  ex_monitor: "Ex-monitor",
  conselheiro: "Conselheiro",
  inativo: "Inativo",
};

export const METHODS: Record<ManagedAccount["signup_method"], string> = {
  senha: "E-mail e senha",
  google: "Google",
  seed: "Conta inicial",
};

export const TABLE = "w-full text-left text-sm";
export const TABLE_HEAD = "bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200";

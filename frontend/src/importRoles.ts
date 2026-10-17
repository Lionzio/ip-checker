import type { Account } from "./types/api";

/** Quem cria o token de importação e baixa os enunciados (IMPORT_ROLES na API, S50-04). */
export const IMPORT_ROLES: ReadonlySet<Account["role"]> = new Set(["desenvolvedor", "professor", "monitor_chefe"]);

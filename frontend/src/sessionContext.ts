/** Contexto da sessão da equipe (Sprint 13); o provedor fica em `session.tsx`. */
import { createContext, useContext } from "react";
import type { Account } from "./types/api";

export type SessionState =
  | { status: "loading" }
  /** Sem sessão; `notice` explica por quê, quando ela acabou durante o uso. */
  | { status: "anonymous"; notice: string | null }
  | { status: "signed-in"; account: Account }
  /** O servidor não respondeu ao perguntar pela sessão. */
  | { status: "error"; message: string };

export interface SessionValue {
  state: SessionState;
  /** Entra com nome ou e-mail e senha; a `ApiError` da recusa segue para a tela mostrar. */
  signIn(login: string, password: string): Promise<void>;
  signOut(): Promise<void>;
  /** A API respondeu 401 durante o uso: a sessão venceu ou foi encerrada. */
  expire(): void;
  retry(): void;
}

export const SessionContext = createContext<SessionValue | null>(null);

export const EXPIRED_NOTICE = "A sua sessão terminou. Entre de novo para continuar.";

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (value === null) throw new Error("useSession fora do SessionProvider");
  return value;
}

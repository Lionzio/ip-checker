/**
 * Sessão da equipe (Sprint 13, FR-22). O cookie da sessão é HttpOnly: a página não o lê, só pergunta
 * à API quem está logado (`/api/v1/auth/me`) ao abrir e depois de entrar ou sair.
 */
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, type AuthClient } from "./services/client";
import { EXPIRED_NOTICE, SessionContext, type SessionState } from "./sessionContext";

export function SessionProvider({ client, children }: { client: AuthClient; children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    client.me(controller.signal).then(
      (account) => setState({ status: "signed-in", account }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "anonymous", notice: null });
        } else {
          setState({
            status: "error",
            message: "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.",
          });
        }
      },
    );
    return () => controller.abort();
  }, [client, attempt]);

  const signIn = useCallback(
    async (login: string, password: string) => {
      const account = await client.login(login, password);
      setState({ status: "signed-in", account });
    },
    [client],
  );

  const signOut = useCallback(async () => {
    try {
      await client.logout();
    } finally {
      setState({ status: "anonymous", notice: null });
    }
  }, [client]);

  const expire = useCallback(() => setState({ status: "anonymous", notice: EXPIRED_NOTICE }), []);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((value) => value + 1);
  }, []);

  const value = useMemo(
    () => ({ state, signIn, signOut, expire, retry }),
    [state, signIn, signOut, expire, retry],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

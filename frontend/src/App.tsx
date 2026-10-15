import { lazy, Suspense, useCallback, useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router";
import { AppFooter } from "./components/AppFooter";
import { AppHeader } from "./components/AppHeader";
import { Button } from "./components/ui";
import { DraftProvider } from "./draft";
import { useDraft } from "./draftContext";
import { useThemeEffect } from "./hooks/useTheme";
import { Admin } from "./pages/Admin";
import { Checker } from "./pages/Checker";
import { GoogleComplete } from "./pages/GoogleComplete";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Plagiarism } from "./pages/Plagiarism";
import { Privacy } from "./pages/Privacy";
import { ForgotPassword } from "./pages/ForgotPassword";
import { Profile } from "./pages/Profile";
import { Register } from "./pages/Register";
import { ResetPassword } from "./pages/ResetPassword";
import { Verify } from "./pages/Verify";
import type { ApiClient } from "./services/client";
import { SessionProvider } from "./session";
import { useSession } from "./sessionContext";

/** A Turma (S40-01) é carregada só quando aberta, para não pesar no primeiro carregamento (NFR-03). */
const ClassBatch = lazy(() => import("./pages/ClassBatch").then((module) => ({ default: module.ClassBatch })));

interface AppProps {
  client: ApiClient;
  /** Mostra o aviso de que as respostas são simuladas (cliente simulado). */
  demoMode?: boolean;
}

/** A página inteira. O roteador fica no `main.tsx`, para os testes usarem um em memória. */
export function App({ client, demoMode = false }: AppProps) {
  return (
    // O rascunho fica acima da sessão: sobrevive a um novo login depois de ela vencer (S26-02).
    <DraftProvider>
      <SessionProvider client={client}>
        <Shell client={client} demoMode={demoMode} />
      </SessionProvider>
    </DraftProvider>
  );
}

/** As telas abertas sem sessão: nelas, uma sessão vencida não leva a Entrar. */
const PUBLIC_PATHS = new Set(["/entrar", "/registrar", "/verificar", "/esqueci-senha", "/redefinir-senha", "/privacidade", "/google/concluir"]);

function Shell({ client, demoMode }: Required<AppProps>) {
  const { state, signIn, signOut, expire, retry, setAccount } = useSession();
  const { clear } = useDraft();
  useThemeEffect();
  const navigate = useNavigate();
  const location = useLocation();
  const account = state.status === "signed-in" ? state.account : null;
  // De onde a sessão vencida tirou a pessoa: depois de entrar de novo, ela volta para lá.
  const from = (location.state as { from?: string } | null)?.from;
  const pathRef = useRef(location.pathname);
  useEffect(() => {
    pathRef.current = location.pathname;
  }, [location.pathname]);

  async function enter(login: string, password: string) {
    await signIn(login, password);
    void navigate(from !== undefined && !PUBLIC_PATHS.has(from) ? from : "/");
  }

  function leave() {
    // Sair apaga o rascunho (código, nome e anotação): o próximo a usar o computador não os vê.
    clear();
    void signOut().finally(() => void navigate("/"));
  }

  // Uma 401 em qualquer tela (S26-04): a sessão acaba e a pessoa vai a Entrar, com o aviso.
  const expireToLogin = useCallback(() => {
    const path = pathRef.current;
    expire();
    if (!PUBLIC_PATHS.has(path)) void navigate("/entrar", { replace: true, state: { from: path } });
  }, [expire, navigate]);

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <AppHeader account={account} onSignOut={leave} />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {demoMode && (
          <p
            role="note"
            className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
          >
            Modo demonstração: as respostas são simuladas, sem análise real, e qualquer nome e
            senha entram. Use
            <code className="mx-1"># simular: lento</code> (ou sobrecarga, limite, indisponivel,
            rede) para ver os estados de erro.
          </p>
        )}

        {state.status === "loading" && <p className="text-slate-600 dark:text-slate-300">Carregando…</p>}
        {state.status === "error" && (
          <div role="alert" className="flex flex-col items-start gap-3">
            <p>{state.message}</p>
            <Button onClick={retry}>Tentar novamente</Button>
          </div>
        )}
        {(state.status === "anonymous" || state.status === "signed-in") && (
          <Routes>
            <Route
              path="/"
              element={
                state.status === "signed-in" ? (
                  <Checker client={client} onUnauthenticated={expireToLogin} />
                ) : (
                  <Landing notice={state.notice} />
                )
              }
            />
            <Route
              path="/entrar"
              element={
                state.status === "signed-in" ? (
                  <Navigate to="/" replace />
                ) : (
                  <Login client={client} onSignIn={enter} notice={state.notice} />
                )
              }
            />
            <Route
              path="/registrar"
              element={state.status === "signed-in" ? <Navigate to="/" replace /> : <Register client={client} />}
            />
            <Route path="/verificar" element={<Verify client={client} />} />
            {/* Esqueci minha senha (S24-04): abertas, porque quem esqueceu a senha não tem sessão. */}
            <Route path="/esqueci-senha" element={<ForgotPassword client={client} />} />
            <Route path="/redefinir-senha" element={<ResetPassword client={client} />} />
            <Route path="/privacidade" element={<Privacy />} />
            <Route
              path="/google/concluir"
              element={state.status === "signed-in" ? <Navigate to="/" replace /> : <GoogleComplete client={client} />}
            />
            <Route
              path="/perfil"
              element={
                state.status === "signed-in" ? (
                  <Profile client={client} account={state.account} onUpdated={setAccount} onUnauthenticated={expireToLogin} />
                ) : (
                  <Navigate to="/entrar" replace />
                )
              }
            />
            <Route
              path="/plagio"
              element={
                state.status === "signed-in" ? (
                  <Plagiarism client={client} onUnauthenticated={expireToLogin} />
                ) : (
                  <Navigate to="/entrar" replace />
                )
              }
            />
            <Route
              path="/turma"
              element={
                state.status === "signed-in" ? (
                  <Suspense fallback={<p role="status" className="py-4 text-sm">Carregando…</p>}>
                    <ClassBatch client={client} onUnauthenticated={expireToLogin} />
                  </Suspense>
                ) : (
                  <Navigate to="/entrar" replace />
                )
              }
            />
            <Route
              path="/gerenciar"
              element={
                state.status === "signed-in" && state.account.can_manage ? (
                  <Admin client={client} canViewLog={state.account.can_view_log} onUnauthenticated={expireToLogin} />
                ) : (
                  <Navigate to={state.status === "signed-in" ? "/" : "/entrar"} replace />
                )
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
      <AppFooter />
    </div>
  );
}

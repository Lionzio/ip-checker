import { Navigate, Route, Routes, useNavigate } from "react-router";
import { AppFooter } from "./components/AppFooter";
import { AppHeader } from "./components/AppHeader";
import { Checker } from "./pages/Checker";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Profile } from "./pages/Profile";
import { Register } from "./pages/Register";
import { Verify } from "./pages/Verify";
import type { ApiClient } from "./services/client";
import { SessionProvider } from "./session";
import { useSession } from "./sessionContext";

interface AppProps {
  client: ApiClient;
  /** Mostra o aviso de que as respostas são simuladas (cliente simulado). */
  demoMode?: boolean;
}

/** A página inteira. O roteador fica no `main.tsx`, para os testes usarem um em memória. */
export function App({ client, demoMode = false }: AppProps) {
  return (
    <SessionProvider client={client}>
      <Shell client={client} demoMode={demoMode} />
    </SessionProvider>
  );
}

function Shell({ client, demoMode }: Required<AppProps>) {
  const { state, signIn, signOut, expire, retry, setAccount } = useSession();
  const navigate = useNavigate();
  const account = state.status === "signed-in" ? state.account : null;

  async function enter(login: string, password: string) {
    await signIn(login, password);
    void navigate("/");
  }

  function leave() {
    void signOut().finally(() => void navigate("/"));
  }

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
            <button
              type="button"
              onClick={retry}
              className="rounded-md bg-blue-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-800"
            >
              Tentar novamente
            </button>
          </div>
        )}
        {(state.status === "anonymous" || state.status === "signed-in") && (
          <Routes>
            <Route
              path="/"
              element={
                state.status === "signed-in" ? (
                  <Checker client={client} onUnauthenticated={expire} />
                ) : (
                  <Landing notice={state.notice} />
                )
              }
            />
            <Route
              path="/entrar"
              element={state.status === "signed-in" ? <Navigate to="/" replace /> : <Login onSignIn={enter} />}
            />
            <Route
              path="/registrar"
              element={state.status === "signed-in" ? <Navigate to="/" replace /> : <Register client={client} />}
            />
            <Route path="/verificar" element={<Verify client={client} />} />
            <Route
              path="/perfil"
              element={
                state.status === "signed-in" ? (
                  <Profile client={client} account={state.account} onUpdated={setAccount} />
                ) : (
                  <Navigate to="/entrar" replace />
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

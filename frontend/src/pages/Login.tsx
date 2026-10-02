import { type FormEvent, useState } from "react";
import { Link } from "react-router";
import { ApiError } from "../services/client";

interface LoginProps {
  onSignIn: (login: string, password: string) => Promise<void>;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    // A API já manda a mensagem certa para cada caso (FR-25): credenciais inválidas, domínio,
    // cadastro aguardando, recusado ou removido, e a espera depois de muitas tentativas.
    if (error.retryAfterS !== null && error.status === 429) {
      return `${error.message} Tente de novo em ${error.retryAfterS} s.`;
    }
    return error.message;
  }
  return "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";
}

/** Entrar com nome ou e-mail institucional e senha (FR-25). O Google entra na Sprint 16. */
export function Login({ onSignIn }: LoginProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      await onSignIn(login, password);
    } catch (caught) {
      setError(messageFor(caught));
      setSending(false);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Entrar</h2>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Nome ou e-mail institucional</span>
        <input
          name="login"
          autoComplete="username"
          required
          value={login}
          onChange={(event) => setLogin(event.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Senha</span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
        />
      </label>
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={sending}
          className="rounded-md bg-blue-700 px-5 py-2 font-medium text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          Entrar
        </button>
        <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
          Voltar
        </Link>
      </div>
    </form>
  );
}

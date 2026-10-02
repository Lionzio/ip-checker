import { type FormEvent, useState } from "react";
import { Link } from "react-router";
import { BUTTON, errorMessage, INPUT } from "../ui";

interface LoginProps {
  onSignIn: (login: string, password: string) => Promise<void>;
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
      // A API manda a mensagem certa para cada caso (FR-25).
      setError(errorMessage(caught));
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
          className={INPUT}
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
          className={INPUT}
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
          className={BUTTON}
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

import { type FormEvent, useState } from "react";
import { Link } from "react-router";
import type { AuthClient } from "../services/client";
import { BUTTON, errorMessage, INPUT } from "../ui";

/**
 * "Esqueci minha senha" (S24-04, Q-19 b): pede o link de redefinição. A resposta é sempre a
 * mesma, exista a conta ou não, para a página não revelar quem tem conta.
 */
export function ForgotPassword({ client }: { client: AuthClient }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      await client.forgotPassword(email.trim());
      setSent(true);
    } catch (caught) {
      setError(errorMessage(caught));
    }
    setSending(false);
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Esqueci minha senha</h2>
      {sent ? (
        <p role="status">
          Se houver uma conta com {email.trim()}, enviamos para ele um link para escolher uma senha nova. O link vale
          por 1 hora. Confira também a caixa de spam.
        </p>
      ) : (
        <>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Informe o e-mail institucional da sua conta. Enviaremos um link para você escolher uma senha nova.
          </p>
          <label className="flex flex-col gap-1">
            <span className="font-medium">E-mail institucional</span>
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={INPUT}
            />
          </label>
          <button type="submit" disabled={sending} className={`${BUTTON} self-start`}>
            Enviar o link
          </button>
        </>
      )}
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Link to="/entrar" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar para Entrar
      </Link>
    </form>
  );
}

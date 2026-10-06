import { type FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { PasswordRequirements } from "../components/PasswordRequirements";
import { passwordAccepted } from "../passwordPolicy";
import type { AuthClient } from "../services/client";
import { BUTTON, errorMessage, INPUT } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Página do link de "esqueci minha senha" (S24-04). Como na verificação, abrir o link não gasta
 * nada: só o envio do formulário, um POST, usa o token. Definir a senha encerra as sessões.
 */
export function ResetPassword({ client }: { client: AuthClient }) {
  useDocumentTitle(PAGE_TITLES.reset);
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const mismatch = confirmation !== "" && confirmation !== password;
  const ready = passwordAccepted(password) && confirmation === password;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) return;
    setState("sending");
    setError(null);
    try {
      await client.resetPassword(token, password);
      setState("done");
    } catch (caught) {
      setError(errorMessage(caught));
      setState("idle");
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Escolher uma senha nova</h2>
      {state === "done" ? (
        <p role="status">
          Senha nova definida. As sessões abertas da sua conta foram encerradas;{" "}
          <Link to="/entrar" className="text-blue-700 underline dark:text-blue-300">
            entre com a senha nova
          </Link>
          .
        </p>
      ) : token === "" ? (
        <p role="alert">Este endereço não traz o código do link. Abra o link do e-mail de novo ou peça outro.</p>
      ) : (
        <>
          <label className="flex flex-col gap-1">
            <span className="font-medium">Senha nova</span>
            <input
              name="new-password"
              type="password"
              autoComplete="new-password"
              required
              aria-describedby="requisitos-senha"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={INPUT}
            />
          </label>
          <PasswordRequirements id="requisitos-senha" password={password} />
          <label className="flex flex-col gap-1">
            <span className="font-medium">Repita a senha nova</span>
            <input
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              aria-invalid={mismatch}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              className={INPUT}
            />
          </label>
          {mismatch && <p className="text-sm text-red-700 dark:text-red-300">As duas senhas não são iguais.</p>}
          <button type="submit" disabled={!ready || state === "sending"} className={`${BUTTON} self-start`}>
            Definir a senha nova
          </button>
        </>
      )}
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Link to="/esqueci-senha" className="text-sm text-blue-700 underline dark:text-blue-300">
        Pedir outro link
      </Link>
    </form>
  );
}

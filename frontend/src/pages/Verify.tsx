import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import type { AuthClient } from "../services/client";
import { Button } from "../components/ui";
import { errorMessage } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Página do link do e-mail (S14-02). Abrir o link não confirma nada: o antivírus do e-mail costuma
 * abrir os links que recebe. Só o botão, que faz um POST, gasta o token (ameaça 21).
 */
export function Verify({ client }: { client: AuthClient }) {
  useDocumentTitle(PAGE_TITLES.verify);
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setState("sending");
    setError(null);
    try {
      await client.verifyEmail(token);
      setState("done");
    } catch (caught) {
      setError(errorMessage(caught));
      setState("idle");
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Confirmar o e-mail</h2>
      {state === "done" ? (
        <p role="status">
          E-mail confirmado. Agora o seu cadastro aguarda a aprovação de um monitor-chefe, de um
          professor ou do desenvolvedor; depois dela, é só entrar.
        </p>
      ) : token === "" ? (
        <p role="alert">Este endereço não traz o código de verificação. Abra o link do e-mail de novo.</p>
      ) : (
        <>
          <p>Confirme que este e-mail é seu para mandar o cadastro para a aprovação.</p>
          <Button onClick={() => void confirm()} disabled={state === "sending"} className="self-start">
            Confirmar meu e-mail
          </Button>
        </>
      )}
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Ir para o início
      </Link>
    </div>
  );
}

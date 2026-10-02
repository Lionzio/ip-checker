import { useEffect, useState } from "react";
import { GOOGLE_START } from "../google";
import type { AuthClient } from "../services/client";

/**
 * "Entrar com o Google" (FR-24), só quando o servidor tem o Google configurado. É um link, não um
 * botão de formulário: a navegação vai ao backend, que segue para o Google.
 */
export function GoogleButton({ client, label }: { client: AuthClient; label: string }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    client.options(controller.signal).then(
      (options) => setEnabled(options.google),
      () => setEnabled(false),
    );
    return () => controller.abort();
  }, [client]);

  if (!enabled) return null;
  return (
    <div className="flex flex-col gap-3">
      <a
        href={GOOGLE_START}
        className="flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-2 font-medium text-slate-900 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
      >
        <span aria-hidden="true" className="font-bold text-blue-700 dark:text-blue-300">
          G
        </span>
        {label}
      </a>
      <p className="text-center text-sm text-slate-600 dark:text-slate-300">ou</p>
    </div>
  );
}

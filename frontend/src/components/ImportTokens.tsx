import { type FormEvent, useEffect, useState } from "react";
import type { ImportTokenClient } from "../services/client";
import type { ImportTokenCreated, ImportTokenInfo } from "../types/api";
import { errorMessage, INPUT, sessionExpired } from "../ui";
import { Button } from "./ui";

interface ImportTokensProps {
  client: ImportTokenClient;
  onUnauthenticated?: () => void;
}

const DATE = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "America/Recife" });

function situation(token: ImportTokenInfo): string {
  if (token.revoked_at !== null) return `revogado em ${DATE.format(new Date(token.revoked_at))}`;
  if (!token.active) return `venceu em ${DATE.format(new Date(token.expires_at))}`;
  const used = token.last_used_at === null ? "nunca usado" : `usado em ${DATE.format(new Date(token.last_used_at))}`;
  return `vale até ${DATE.format(new Date(token.expires_at))} · ${used}`;
}

/**
 * O token de importação da extensão do Dikastis (S50-04): só a chefia e o desenvolvedor criam. O
 * valor aparece uma vez, logo depois de criar; a API guarda só o hash.
 */
export function ImportTokens({ client, onUnauthenticated }: ImportTokensProps) {
  const [tokens, setTokens] = useState<ImportTokenInfo[] | null>(null);
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState<ImportTokenCreated | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    client.listImportTokens(controller.signal).then(setTokens, (caught: unknown) => {
      if (controller.signal.aborted) return;
      if (sessionExpired(caught) && onUnauthenticated) onUnauthenticated();
      else setMessage({ ok: false, text: errorMessage(caught) });
    });
    return () => controller.abort();
  }, [client, onUnauthenticated]);

  async function act(action: () => Promise<void>) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      setTokens(await client.listImportTokens());
    } catch (caught) {
      if (sessionExpired(caught) && onUnauthenticated) {
        onUnauthenticated();
        return;
      }
      setMessage({ ok: false, text: errorMessage(caught) });
    } finally {
      setBusy(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void act(async () => {
      setCreated(await client.createImportToken(label.trim()));
      setLabel("");
    });
  }

  function revoke(token: ImportTokenInfo) {
    void act(async () => {
      await client.revokeImportToken(token.id);
      if (created?.id === token.id) setCreated(null);
      setMessage({ ok: true, text: `Token “${token.label}” revogado.` });
    });
  }

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setMessage({ ok: true, text: "Token copiado. Cole no popup da extensão." });
    } catch {
      setMessage({ ok: false, text: "Não foi possível copiar: selecione o token e copie à mão." });
    }
  }

  const active = tokens?.filter((token) => token.active) ?? [];
  return (
    <section aria-labelledby="titulo-token" className="flex flex-col gap-4">
      <h2 id="titulo-token" className="text-xl font-semibold">
        Token de importação
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        A extensão do Dikastis usa este token para enviar as listas ao IP-Checker. Ele vale 90 dias, aparece só uma vez e
        pode ser revogado a qualquer momento. Até 3 ativos.
      </p>
      {created !== null && (
        <div role="status" className="flex flex-col gap-2 rounded-md border border-amber-400 bg-amber-50 p-3 text-sm dark:border-amber-600 dark:bg-amber-950">
          <p className="font-medium">Copie agora: o token não será mostrado de novo.</p>
          <code className="font-mono break-all select-all">{created.token}</code>
          <div>
            <Button size="sm" variant="secondary" onClick={() => void copy(created.token)}>
              Copiar
            </Button>
          </div>
        </div>
      )}
      <form onSubmit={create} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1">
          <span className="font-medium">Onde vai ficar</span>
          <input
            name="label"
            required
            maxLength={60}
            placeholder="Chrome do notebook"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            className={INPUT}
          />
        </label>
        <Button type="submit" disabled={busy || active.length >= 3 || label.trim() === ""}>
          Criar token
        </Button>
      </form>
      {message !== null && (
        <p role={message.ok ? "status" : "alert"} className={`text-sm ${message.ok ? "text-green-800 dark:text-green-300" : "text-red-700 dark:text-red-300"}`}>
          {message.text}
        </p>
      )}
      {tokens !== null && tokens.length > 0 && (
        <ul className="flex flex-col gap-2 text-sm" aria-label="Seus tokens de importação">
          {tokens.map((token) => (
            <li key={token.id} className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700">
              <span>
                <span className="font-medium">{token.label}</span>
                <span className="block text-slate-600 dark:text-slate-300">{situation(token)}</span>
              </span>
              {token.active && (
                <Button size="sm" variant="secondary" onClick={() => revoke(token)} disabled={busy}>
                  Revogar
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

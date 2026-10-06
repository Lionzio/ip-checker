import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router";
import { PrivacyNotice } from "../components/PrivacyNotice";
import { TreatmentField } from "../components/TreatmentField";
import type { AuthClient } from "../services/client";
import type { GooglePending, Treatment } from "../types/api";
import { BUTTON, errorMessage, INPUT } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/**
 * Formulário complementar do Google (S16-01, FR-24): nome (sugerido pelo Google, editável e
 * único), curso e tratamento, sem senha. Ao enviar, o cadastro vai direto para a aprovação.
 */
export function GoogleComplete({ client }: { client: AuthClient }) {
  useDocumentTitle(PAGE_TITLES.google);
  const [pending, setPending] = useState<GooglePending | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [course, setCourse] = useState("");
  const [treatment, setTreatment] = useState<Treatment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    client.googlePending(controller.signal).then(
      (found) => {
        setPending(found);
        setName(found.name);
      },
      (caught: unknown) => {
        if (!controller.signal.aborted) setLoadError(errorMessage(caught));
      },
    );
    return () => controller.abort();
  }, [client]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (treatment === null) return;
    setSending(true);
    setError(null);
    try {
      setSentTo(await client.completeGoogle({ name, course, treatment }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSending(false);
    }
  }

  if (sentTo !== null) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
        <h2 className="text-xl font-semibold">Cadastro enviado</h2>
        <p role="status">
          O cadastro de <strong>{sentTo}</strong> foi enviado e aguarda a aprovação de um
          monitor-chefe, de um professor ou do desenvolvedor. Depois dela, é só entrar com o Google.
        </p>
        <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
          Voltar ao início
        </Link>
      </div>
    );
  }

  if (loadError !== null) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
        <h2 className="text-xl font-semibold">Registrar com o Google</h2>
        <p role="alert">{loadError}</p>
        <Link to="/entrar" className="text-sm text-blue-700 underline dark:text-blue-300">
          Ir para Entrar
        </Link>
      </div>
    );
  }

  if (pending === null) return <p className="py-10 text-slate-600 dark:text-slate-300">Carregando…</p>;

  const ready = name.trim() !== "" && course.trim() !== "" && treatment !== null;
  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Registrar com o Google</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        O Google confirmou o e-mail <strong>{pending.email}</strong>. Complete os dados abaixo; o
        pedido vai para a aprovação de um monitor-chefe, de um professor ou do desenvolvedor.
      </p>
      <div className="flex flex-col gap-1">
        <label className="flex flex-col gap-1">
          <span className="font-medium">Nome</span>
          <input name="name" autoComplete="name" required maxLength={120} aria-describedby="dica-nome-google" value={name} onChange={(e) => setName(e.target.value)} className={INPUT} />
        </label>
        <span id="dica-nome-google" className="text-sm text-slate-600 dark:text-slate-300">
          Sugerido pelo Google; pode mudar. É único e também serve para entrar.
        </span>
      </div>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Curso</span>
        <input name="course" required maxLength={120} value={course} onChange={(e) => setCourse(e.target.value)} className={INPUT} />
      </label>
      <TreatmentField value={treatment} onChange={setTreatment} />
      <PrivacyNotice />
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <button type="submit" disabled={sending || !ready} className={`${BUTTON} self-start`}>
        Enviar cadastro
      </button>
    </form>
  );
}

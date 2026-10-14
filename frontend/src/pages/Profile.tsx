import { type FormEvent, useState } from "react";
import { Link } from "react-router";
import { PasswordRequirements } from "../components/PasswordRequirements";
import { ThemeField } from "../components/ThemeField";
import { TreatmentField } from "../components/TreatmentField";
import { passwordAccepted } from "../passwordPolicy";
import type { AuthClient } from "../services/client";
import type { Account, Treatment } from "../types/api";
import { Button } from "../components/ui";
import { errorMessage, INPUT, sessionExpired } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

interface ProfileProps {
  client: AuthClient;
  account: Account;
  onUpdated: (account: Account) => void;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated?: () => void;
}

/** Perfil (FR-26): nome, curso, tratamento, senha e o tema da página (S37-05). O cargo não se altera por aqui. */
export function Profile({ client, account, onUpdated, onUnauthenticated }: ProfileProps) {
  useDocumentTitle(PAGE_TITLES.profile);
  return (
    <div className="mx-auto flex max-w-md flex-col gap-10 py-10">
      <ProfileForm client={client} account={account} onUpdated={onUpdated} onUnauthenticated={onUnauthenticated} />
      <PasswordForm
        client={client}
        hasPassword={account.has_password}
        onChanged={() => onUpdated({ ...account, has_password: true })}
        onUnauthenticated={onUnauthenticated}
      />
      <section aria-labelledby="titulo-aparencia" className="flex flex-col gap-4">
        <h2 id="titulo-aparencia" className="text-xl font-semibold">
          Aparência
        </h2>
        <ThemeField />
      </section>
      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar ao painel
      </Link>
    </div>
  );
}

function ProfileForm({ client, account, onUpdated, onUnauthenticated }: ProfileProps) {
  const [name, setName] = useState(account.name);
  const [course, setCourse] = useState(account.course);
  const [treatment, setTreatment] = useState<Treatment>(account.treatment);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      onUpdated(await client.updateProfile({ name, course, treatment }));
      setMessage({ ok: true, text: "Perfil salvo." });
    } catch (caught) {
      if (sessionExpired(caught) && onUnauthenticated) {
        onUnauthenticated();
        return;
      }
      setMessage({ ok: false, text: errorMessage(caught) });
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-4" aria-labelledby="titulo-perfil">
      <h2 id="titulo-perfil" className="text-xl font-semibold">
        Perfil
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {account.email} · {account.role_label}. O cargo é definido por quem aprova os cadastros.
      </p>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Nome</span>
        <input name="name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} className={INPUT} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Curso</span>
        <input name="course" required maxLength={120} value={course} onChange={(e) => setCourse(e.target.value)} className={INPUT} />
      </label>
      <TreatmentField value={treatment} onChange={setTreatment} />
      {message !== null && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? "text-sm text-green-700 dark:text-green-300" : "text-sm text-red-700 dark:text-red-300"}>
          {message.text}
        </p>
      )}
      <Button type="submit" className="self-start">
        Salvar perfil
      </Button>
    </form>
  );
}

function PasswordForm({
  client,
  hasPassword,
  onChanged,
  onUnauthenticated,
}: {
  client: AuthClient;
  hasPassword: boolean;
  onChanged: () => void;
  onUnauthenticated?: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const matches = next === repeat;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!matches) return;
    setMessage(null);
    try {
      await client.changePassword(hasPassword ? current : null, next);
      setCurrent("");
      setNext("");
      setRepeat("");
      onChanged();
      setMessage({ ok: true, text: "Senha alterada. As outras sessões desta conta foram encerradas." });
    } catch (caught) {
      if (sessionExpired(caught) && onUnauthenticated) {
        onUnauthenticated();
        return;
      }
      setMessage({ ok: false, text: errorMessage(caught) });
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-4" aria-labelledby="titulo-senha">
      <h2 id="titulo-senha" className="text-xl font-semibold">
        {hasPassword ? "Alterar a senha" : "Definir uma senha"}
      </h2>
      {!hasPassword && (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          A sua conta foi criada pelo Google. Com uma senha, você também pode entrar com nome ou e-mail.
        </p>
      )}
      {hasPassword && (
        <label className="flex flex-col gap-1">
          <span className="font-medium">Senha atual</span>
          <input name="current-password" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} className={INPUT} />
        </label>
      )}
      <label className="flex flex-col gap-1">
        <span className="font-medium">Nova senha</span>
        <input name="new-password" type="password" autoComplete="new-password" required aria-describedby="requisitos-nova-senha" value={next} onChange={(e) => setNext(e.target.value)} className={INPUT} />
      </label>
      <PasswordRequirements id="requisitos-nova-senha" password={next} />
      <label className="flex flex-col gap-1">
        <span className="font-medium">Repita a nova senha</span>
        <input name="repeat-password" type="password" autoComplete="new-password" required value={repeat} onChange={(e) => setRepeat(e.target.value)} className={INPUT} />
      </label>
      {!matches && repeat !== "" && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          As duas senhas novas não são iguais.
        </p>
      )}
      {message !== null && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? "text-sm text-green-700 dark:text-green-300" : "text-sm text-red-700 dark:text-red-300"}>
          {message.text}
        </p>
      )}
      <Button type="submit" disabled={!matches || !passwordAccepted(next)} className="self-start">
        {hasPassword ? "Alterar a senha" : "Definir a senha"}
      </Button>
    </form>
  );
}

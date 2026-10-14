import { type FormEvent, useState } from "react";
import { Link } from "react-router";
import { GoogleButton } from "../components/GoogleButton";
import { PasswordRequirements } from "../components/PasswordRequirements";
import { PrivacyNotice } from "../components/PrivacyNotice";
import { TreatmentField } from "../components/TreatmentField";
import { passwordAccepted } from "../passwordPolicy";
import type { AuthClient } from "../services/client";
import type { Treatment } from "../types/api";
import { Button } from "../components/ui";
import { errorMessage, INPUT } from "../ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

const COURSES = [
  "Ciência da Computação",
  "Engenharia da Computação",
  "Sistemas de Informação",
  "Inteligência Artificial",
];

/** Registro por e-mail institucional e senha (FR-23), ou pelo Google (FR-24, S16-01). */
export function Register({ client }: { client: AuthClient }) {
  useDocumentTitle(PAGE_TITLES.register);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [course, setCourse] = useState("");
  const [treatment, setTreatment] = useState<Treatment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (treatment === null) return;
    setSending(true);
    setError(null);
    try {
      setSentTo(await client.register({ name, email, password, course, treatment }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSending(false);
    }
  }

  if (sentTo !== null) return <CheckYourEmail client={client} email={sentTo} />;

  const ready = name.trim() !== "" && course.trim() !== "" && treatment !== null && passwordAccepted(password);
  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Registrar</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Para a equipe da disciplina. Depois de confirmar o e-mail, o pedido vai para a aprovação de
        um monitor-chefe, de um professor ou do desenvolvedor.
      </p>
      <GoogleButton client={client} label="Registrar com o Google" />
      <div className="flex flex-col gap-1">
        <label className="flex flex-col gap-1">
          <span className="font-medium">Nome</span>
          <input name="name" autoComplete="name" required maxLength={120} aria-describedby="dica-nome" value={name} onChange={(e) => setName(e.target.value)} className={INPUT} />
        </label>
        <span id="dica-nome" className="text-sm text-slate-600 dark:text-slate-300">
          Único; também serve para entrar.
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <label className="flex flex-col gap-1">
          <span className="font-medium">E-mail institucional</span>
          <input name="email" type="email" autoComplete="email" required aria-describedby="dica-email" value={email} onChange={(e) => setEmail(e.target.value)} className={INPUT} />
        </label>
        <span id="dica-email" className="text-sm text-slate-600 dark:text-slate-300">
          Só @cin.ufpe.br ou @ufpe.br. Prefira o @cin.ufpe.br.
        </span>
      </div>
      <label className="flex flex-col gap-1">
        <span className="font-medium">Senha</span>
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          required
          aria-describedby="requisitos-senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={INPUT}
        />
      </label>
      <PasswordRequirements id="requisitos-senha" password={password} />
      <label className="flex flex-col gap-1">
        <span className="font-medium">Curso</span>
        <input name="course" list="cursos" required maxLength={120} value={course} onChange={(e) => setCourse(e.target.value)} className={INPUT} />
        <datalist id="cursos">
          {COURSES.map((option) => (
            <option key={option} value={option} />
          ))}
        </datalist>
      </label>
      <TreatmentField value={treatment} onChange={setTreatment} />
      <PrivacyNotice />
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <div className="flex items-center gap-4">
        <Button type="submit" disabled={sending || !ready}>
          Registrar
        </Button>
        <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
          Voltar
        </Link>
      </div>
    </form>
  );
}

function CheckYourEmail({ client, email }: { client: AuthClient; email: string }) {
  const [notice, setNotice] = useState<string | null>(null);

  async function resend() {
    try {
      await client.resendVerification(email);
      setNotice("Se o cadastro ainda espera a confirmação, enviamos um novo link.");
    } catch (caught) {
      setNotice(errorMessage(caught));
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Confirme o seu e-mail</h2>
      <p>
        Enviamos um link para <strong>{email}</strong>. Abra a mensagem e clique em “Clique aqui
        para verificar seu acesso.”. O link vale por 24 horas e só uma vez.
      </p>
      <Button variant="link" className="self-start" onClick={() => void resend()}>
        Não recebi: enviar de novo
      </Button>
      {notice !== null && <p role="status" className="text-sm">{notice}</p>}
      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar ao início
      </Link>
    </div>
  );
}

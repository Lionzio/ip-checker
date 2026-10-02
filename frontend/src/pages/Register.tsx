import { Link } from "react-router";

/** O cadastro por e-mail e senha chega na Sprint 14 (FR-23); o pelo Google, na Sprint 16. */
export function Register() {
  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
      <h2 className="text-xl font-semibold">Registrar</h2>
      <p className="text-slate-700 dark:text-slate-300">
        O cadastro de novos membros da equipe ainda não está disponível. Quando abrir, ele vai
        pedir o e-mail institucional (@cin.ufpe.br ou @ufpe.br) e passar pela aprovação de um
        monitor-chefe, de um professor ou do desenvolvedor.
      </p>
      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar
      </Link>
    </div>
  );
}

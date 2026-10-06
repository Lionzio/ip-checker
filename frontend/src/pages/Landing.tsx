import { Link } from "react-router";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/** Sem sessão, a página só oferece Registrar e Entrar (FR-22). */
export function Landing({ notice }: { notice: string | null }) {
  useDocumentTitle(PAGE_TITLES.landing);
  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-10">
      {notice !== null && (
        <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
          {notice}
        </p>
      )}
      <h2 className="text-xl font-semibold">Acesso restrito à equipe da disciplina</h2>
      <p className="text-slate-700 dark:text-slate-300">
        O IP-Checker é usado por professores, monitores-chefe e monitores na correção. Entre com a
        sua conta ou peça o seu cadastro com o e-mail institucional.
      </p>
      <div className="flex gap-3">
        <Link
          to="/registrar"
          className="rounded-md border border-blue-700 px-5 py-2 font-medium text-blue-700 hover:bg-blue-50 dark:border-blue-400 dark:text-blue-300 dark:hover:bg-slate-800"
        >
          Registrar
        </Link>
        <Link
          to="/entrar"
          className="rounded-md bg-blue-700 px-5 py-2 font-medium text-white hover:bg-blue-800"
        >
          Entrar
        </Link>
      </div>
    </div>
  );
}

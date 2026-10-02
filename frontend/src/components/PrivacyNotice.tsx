import { Link } from "react-router";

/** O resumo do aviso de privacidade, nos dois registros (S19-02, Q-19 d). */
export function PrivacyNotice() {
  return (
    <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
      Guardamos o seu nome, e-mail, curso e tratamento para dar acesso à equipe e montar o feedback; a
      senha, só como resumo criptográfico. O tratamento só você vê. Detalhes no{" "}
      <Link to="/privacidade" className="text-blue-700 underline dark:text-blue-300">
        aviso de privacidade
      </Link>
      .
    </p>
  );
}

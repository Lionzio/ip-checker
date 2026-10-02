/** Créditos da plataforma, pedidos pelo autor (02/10/2026). */
export function AppFooter() {
  const link = "underline hover:text-slate-900 dark:hover:text-white";
  return (
    <footer className="border-t border-slate-200 px-4 py-4 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300">
      <p className="mx-auto max-w-6xl">
        Desenvolvido por Vinícius Leôncio (Lionzio) para a disciplina de Introdução a Programação
        (IP).{" "}
        <a className={link} href="https://github.com/Lionzio" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        {" · "}
        <a
          className={link}
          href="https://www.linkedin.com/in/vin%C3%ADcius-le%C3%B4ncio-3226a9366/"
          target="_blank"
          rel="noopener noreferrer"
        >
          LinkedIn
        </a>
      </p>
    </footer>
  );
}

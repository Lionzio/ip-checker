import { Logo } from "../components/Logo";
import { ButtonLink, Card } from "../components/ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";

/** O que a ferramenta faz, em três blocos (S37-04). */
const FEATURES = [
  {
    title: "Verificar",
    text: "Cole a solução do aluno e veja o que a lista permite ou proíbe, com a linha de cada violação. O código não é executado nem guardado.",
  },
  {
    title: "Plágio",
    text: "Compare duas soluções, ou uma contra a turma inteira: a semelhança resiste a nomes trocados, linhas reordenadas e formas equivalentes.",
  },
  {
    title: "Feedback",
    text: "Monte o retorno para o aluno a partir do resultado, com o nome dele e a sua anotação, pronto para colar no Dikastis.",
  },
];

/** Sem sessão, a página só oferece Registrar e Entrar (FR-22). */
export function Landing({ notice }: { notice: string | null }) {
  useDocumentTitle(PAGE_TITLES.landing);
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 py-10">
      {notice !== null && (
        <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
          {notice}
        </p>
      )}
      <div className="flex flex-col gap-4">
        <Logo className="size-12" />
        <h2 className="text-2xl font-semibold">Acesso restrito à equipe da disciplina</h2>
        <p className="max-w-prose text-slate-700 dark:text-slate-300">
          O IP-Checker é usado por professores, monitores-chefe e monitores na correção. Entre com a
          sua conta ou peça o seu cadastro com o e-mail institucional.
        </p>
        <div className="flex flex-wrap gap-3">
          <ButtonLink to="/entrar">Entrar</ButtonLink>
          <ButtonLink to="/registrar" variant="secondary">
            Registrar
          </ButtonLink>
        </div>
      </div>
      <ul aria-label="O que o IP-Checker faz" className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map((feature) => (
          <Card as="li" key={feature.title}>
            <h3 className="font-semibold">{feature.title}</h3>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{feature.text}</p>
          </Card>
        ))}
      </ul>
    </div>
  );
}

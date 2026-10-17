import { useEffect, useState } from "react";
import { Link } from "react-router";
import { PeriodSelector } from "../components/PeriodSelector";
import { Button, Card, ErrorText } from "../components/ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { usePeriods } from "../hooks/usePeriods";
import { IMPORT_ROLES } from "../importRoles";
import { PAGE_TITLES } from "../labels";
import type { ApiClient } from "../services/client";
import type { Account, CatalogListInfo, CatalogQuestionInfo, CatalogResponse } from "../types/api";
import { errorMessage, sessionExpired } from "../ui";

interface ListsProps {
  client: Pick<ApiClient, "listPeriods" | "catalog" | "statementsZip">;
  account: Account;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

const KIND_LABELS: Record<CatalogListInfo["kind"], string> = { lista: "Lista", prova: "Prova", treino: "Treino" };

const DATE = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", timeZone: "America/Recife" });
const DATE_TIME = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Recife",
});

function listName(item: CatalogListInfo): string {
  const name = item.number === null ? "Lista de Treinamento" : `${KIND_LABELS[item.kind]} ${item.number}`;
  return item.title !== name && !item.title.startsWith(`${name} `) ? `${name}: ${item.title}` : item.title;
}

function period(item: CatalogListInfo): string | null {
  if (item.starts_at === null && item.ends_at === null) return null;
  if (item.starts_at !== null && item.ends_at !== null) {
    return `de ${DATE.format(new Date(item.starts_at))} a ${DATE.format(new Date(item.ends_at))}`;
  }
  return item.starts_at !== null ? `desde ${DATE.format(new Date(item.starts_at))}` : `até ${DATE.format(new Date(item.ends_at ?? ""))}`;
}

function Stage({ done, label, missing }: { done: boolean; label: string; missing: string }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
        done
          ? "bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200"
          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
      }`}
    >
      {done ? `✓ ${label}` : missing}
    </span>
  );
}

function QuestionRow({ question }: { question: CatalogQuestionInfo }) {
  return (
    <tr className="border-t border-slate-200 align-top dark:border-slate-700">
      <th scope="row" className="px-3 py-2 font-mono font-medium whitespace-nowrap">
        {question.question_id}
      </th>
      <td className="px-3 py-2">
        {question.title}
        {question.missing_since !== null && (
          <span className="block text-xs text-amber-900 dark:text-amber-200">Não encontrada na última sincronização.</span>
        )}
      </td>
      <td className="px-3 py-2 text-center">{question.version}</td>
      <td className="px-3 py-2">
        <div className="flex flex-wrap gap-1">
          <Stage done label="enunciado" missing="sem enunciado" />
          <Stage done={question.has_rules} label="regras" missing="sem regras próprias" />
          <Stage done={question.has_gabarito} label="gabarito" missing="sem gabarito" />
        </div>
      </td>
    </tr>
  );
}

function ListSection({ item }: { item: CatalogListInfo }) {
  const name = listName(item);
  const when = period(item);
  return (
    <Card aria-label={name} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h3 className="text-lg font-semibold">{name}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {[when, item.classes.length > 0 ? `turmas: ${item.classes.join(", ")}` : null].filter(Boolean).join(" · ")}
        </p>
        {item.missing_since !== null && (
          <p className="text-sm text-amber-900 dark:text-amber-200">Não encontrada no Dikastis na última sincronização.</p>
        )}
      </div>
      {item.questions.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">Sem questões no padrão 26.2L1Q1.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-xl text-left text-sm">
            <thead className="text-xs text-slate-600 uppercase dark:text-slate-300">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Questão
                </th>
                <th scope="col" className="px-3 py-2">
                  Título
                </th>
                <th scope="col" className="px-3 py-2 text-center">
                  Versão
                </th>
                <th scope="col" className="px-3 py-2">
                  Etapa 1
                </th>
              </tr>
            </thead>
            <tbody>
              {item.questions.map((question) => (
                <QuestionRow key={question.question_id} question={question} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

/**
 * As listas do período (S50-06, US-48): o que a extensão do Dikastis já trouxe, com o estado da
 * etapa 1 de cada questão (enunciado, regras, gabarito). Só a chefia baixa os enunciados.
 */
export function Lists({ client, account, onUnauthenticated }: ListsProps) {
  useDocumentTitle(PAGE_TITLES.lists);
  const periods = usePeriods(client, onUnauthenticated);
  const [chosen, setChosen] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const current = chosen ?? periods.find((item) => item.active)?.period ?? null;

  useEffect(() => {
    if (current === null) return;
    const controller = new AbortController();
    client.catalog(current, controller.signal).then(
      (found) => {
        setCatalog(found);
        setError(null);
      },
      (caught: unknown) => {
        if (controller.signal.aborted) return;
        if (sessionExpired(caught)) {
          onUnauthenticated();
          return;
        }
        setError(errorMessage(caught));
      },
    );
    return () => controller.abort();
  }, [client, current, onUnauthenticated]);

  async function download() {
    if (current === null) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await client.statementsZip(current);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `enunciados-${current}.zip`;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      if (sessionExpired(caught)) {
        onUnauthenticated();
        return;
      }
      setError(errorMessage(caught));
    } finally {
      setDownloading(false);
    }
  }

  const shown = catalog !== null && catalog.period === current ? catalog : null;
  const leadership = IMPORT_ROLES.has(account.role);
  const hasLists = shown !== null && shown.lists.length > 0;
  return (
    <div className="flex flex-col gap-6 py-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{PAGE_TITLES.lists}</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            As listas e questões do Dikastis, trazidas pela extensão do IP-Checker.
            {shown?.last_sync && ` Última sincronização: ${DATE_TIME.format(new Date(shown.last_sync))}.`}
          </p>
        </div>
        {leadership && hasLists && (
          <Button variant="secondary" onClick={() => void download()} disabled={downloading}>
            {downloading ? "Preparando…" : "Baixar enunciados (.zip)"}
          </Button>
        )}
      </div>
      <div className="max-w-xs">
        <PeriodSelector periods={periods} value={chosen} onChange={setChosen} />
      </div>
      {error !== null && <ErrorText>{error}</ErrorText>}
      {shown === null && error === null && (
        <p role="status" className="text-sm text-slate-600 dark:text-slate-300">
          Carregando as listas…
        </p>
      )}
      {shown !== null && !hasLists && (
        <Card aria-label="Sem listas ainda" className="flex flex-col gap-2 text-sm">
          <p className="font-medium">O período {shown.period} ainda não tem listas no IP-Checker.</p>
          <p>
            Quem cuida da sincronização instala a extensão do Dikastis (guia da equipe, seção “Listas do período e a extensão
            do Dikastis”), cria o token de importação no{" "}
            {leadership ? (
              <Link to="/perfil" className="text-blue-700 underline dark:text-blue-300">
                Perfil
              </Link>
            ) : (
              "Perfil"
            )}{" "}
            e clica em “Verificar agora” com o Dikastis aberto.
          </p>
        </Card>
      )}
      {shown?.lists.map((item) => (
        <ListSection key={`${item.kind}-${item.number ?? 0}`} item={item} />
      ))}
    </div>
  );
}

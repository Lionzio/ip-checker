import { useEffect, useState } from "react";
import type { AdminClient } from "../services/client";
import type { ListPanel as Panel } from "../types/api";
import { errorMessage, sessionExpired } from "../ui";
import { Card, ErrorText } from "./ui";

interface ListPanelProps {
  client: AdminClient;
  onUnauthenticated?: () => void;
}

const LISTS = [1, 2, 3, 4, 5, 6];
const PERCENT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/**
 * Painel por lista (S40-03, US-16): as regras mais violadas numa lista do período ativo, para a
 * chefia decidir o que reforçar em aula. Só contagens anônimas da telemetria: nenhum aluno, conta,
 * código ou nome aparece aqui.
 */
export function ListPanel({ client, onUnauthenticated }: ListPanelProps) {
  const [listNumber, setListNumber] = useState(1);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    client.listPanel(listNumber, null, controller.signal).then(
      (loaded) => {
        setPanel(loaded);
        setError(null);
      },
      (caught: unknown) => {
        if (controller.signal.aborted) return;
        if (sessionExpired(caught) && onUnauthenticated) {
          onUnauthenticated();
          return;
        }
        setPanel(null);
        setError(errorMessage(caught));
      },
    );
    return () => controller.abort();
  }, [client, listNumber, onUnauthenticated]);

  const syntaxPct = panel !== null && panel.events > 0 ? (100 * panel.syntax_errors) / panel.events : null;
  return (
    <section aria-labelledby="painel-lista" className="flex flex-col gap-2">
      <h3 id="painel-lista" className="text-lg font-semibold">
        Painel por lista
      </h3>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        As regras mais violadas no período, só com contagens anônimas: nenhum aluno, conta ou código aparece aqui.
      </p>
      <label className="flex flex-col gap-1 self-start text-sm">
        <span className="font-medium">Lista do painel</span>
        <select
          value={listNumber}
          onChange={(event) => setListNumber(Number(event.target.value))}
          className="min-h-11 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm sm:min-h-8 dark:border-slate-600 dark:bg-slate-900"
        >
          {LISTS.map((number) => (
            <option key={number} value={number}>
              Lista {number}
            </option>
          ))}
        </select>
      </label>
      {error !== null && <ErrorText>{error}</ErrorText>}
      {panel !== null && (
        <>
          <p className="text-sm">
            {panel.semester === "" ? "Sem período ativo." : `Período ${panel.semester}: `}
            {panel.events === 1 ? "1 verificação" : `${panel.events} verificações`}
            {syntaxPct !== null && `, ${PERCENT.format(syntaxPct)}% com erro de sintaxe`}
            {panel.adoption_pct !== null && `; ${PERCENT.format(panel.adoption_pct)}% da equipe já usou esta lista`}.
          </p>
          {panel.top_rules.length === 0 ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">Nenhuma violação registrada nesta lista ainda.</p>
          ) : (
            <Card as="div" padding="none" className="overflow-x-auto">
              <table className="w-full min-w-md text-left text-sm">
                <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  <tr>
                    <th scope="col" className="px-3 py-2 font-semibold">Regra</th>
                    <th scope="col" className="px-3 py-2 text-right font-semibold">Verificações</th>
                    <th scope="col" className="px-3 py-2 text-right font-semibold">Ocorrências</th>
                  </tr>
                </thead>
                <tbody>
                  {panel.top_rules.map((rule) => (
                    <tr key={rule.rule_id} className="border-t border-slate-200 dark:border-slate-700">
                      <th scope="row" className="px-3 py-2 font-medium">{rule.rule_id}</th>
                      <td className="px-3 py-2 text-right tabular-nums">{rule.events}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{rule.occurrences}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </section>
  );
}

import { PERCENT } from "../../bands";
import type { SimilarityClassResponse } from "../../types/api";
import { Button, Card, SyntaxErrorBox } from "../ui";
import { Band } from "./PairResult";

/** O resultado de "Contra a turma": as soluções da mais parecida para a menos (S27-02). */
export function ClassResult({ response, onSideBySide }: { response: SimilarityClassResponse; onSideBySide: (label: string) => void }) {
  if (response.status === "syntax_error" && response.syntax_error) {
    const problem = response.syntax_error;
    return (
      <SyntaxErrorBox
        title="A solução comparada tem um erro de sintaxe"
        line={problem.line}
        col={problem.col}
        message={problem.message}
        alert
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-slate-700 dark:text-slate-200">
        Da mais parecida para a menos. Cada trecho pesa pela raridade na turma: o que todos escrevem quase não conta.
      </p>
      <Card as="div" padding="none" className="overflow-x-auto">
        <table className="w-full min-w-md text-left text-sm">
          <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">Solução</th>
              <th scope="col" className="px-3 py-2 font-semibold">Similaridade</th>
              <th scope="col" className="px-3 py-2 font-semibold">Faixa</th>
              <th scope="col" className="px-3 py-2 font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody>
            {response.results.map((item, index) => (
              <tr key={`${item.label}-${index}`} className="border-t border-slate-200 align-top dark:border-slate-700">
                <th scope="row" className="px-3 py-2 font-medium">{item.label}</th>
                {item.status === "compared" && item.similarity !== null && item.band !== null ? (
                  <>
                    <td className="px-3 py-2">
                      {PERCENT.format(item.similarity)}%
                      {item.short_code && <span className="block text-xs text-amber-900 dark:text-amber-200">Código curto</span>}
                    </td>
                    <td className="px-3 py-2">
                      <Band band={item.band} />
                    </td>
                    <td className="px-3 py-2">
                      <Button variant="link" onClick={() => onSideBySide(item.label)} aria-label={`Comparar lado a lado com ${item.label}`}>
                        Comparar lado a lado
                      </Button>
                    </td>
                  </>
                ) : (
                  <td colSpan={3} className="px-3 py-2 text-red-700 dark:text-red-300">
                    {item.syntax_error
                      ? `Erro de sintaxe na linha ${item.syntax_error.line}, coluna ${item.syntax_error.col}: ${item.syntax_error.message}`
                      : item.message}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-sm text-slate-600 dark:text-slate-300">{response.notice}</p>
    </div>
  );
}

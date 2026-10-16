import type { PairComparison } from "../../hooks/usePairComparison";
import type { PeriodInfo } from "../../types/api";
import { INPUT } from "../../ui";
import { CodeEditor } from "../CodeEditor";
import { PeriodSelector } from "../PeriodSelector";
import { Button, ErrorText } from "../ui";
import { GabaritoPair, PairResult } from "./PairResult";

interface PairModeProps {
  pair: PairComparison;
  /** As questões com gabarito (ADR-11, item 5): sem elas, o seletor nem aparece. */
  withGabarito: { id: string; list: number }[];
  /** Os períodos carregados (S43-03): com mais de um, o gabarito pode ser de um anterior. */
  periods: PeriodInfo[];
}

/** "Dois códigos" (S17-03, FR-29): lado a lado, com os trechos em comum realçados. */
export function PairMode({ pair, withGabarito, periods }: PairModeProps) {
  const { chosen, compared, editorA, editorB, sync } = pair;
  const empty = pair.codeA === "" && pair.codeB === "";
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void pair.compare();
      }}
      className="flex flex-col gap-4"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Código A</h3>
          <CodeEditor
            ref={editorA}
            value={pair.codeA}
            onChange={pair.setCodeA}
            readOnly={pair.loading}
            label="Código A"
            placeholder="Cole aqui a primeira solução"
            marked={pair.marksA}
            current={chosen ? { first: chosen.a_first, last: chosen.a_last } : null}
            onScrollTop={(top) => sync && editorB.current?.setScrollTop(top)}
          />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Código B</h3>
          <CodeEditor
            ref={editorB}
            value={pair.codeB}
            onChange={pair.setCodeB}
            readOnly={pair.loading}
            label="Código B"
            placeholder="Cole aqui a segunda solução"
            marked={pair.marksB}
            current={chosen ? { first: chosen.b_first, last: chosen.b_last } : null}
            onScrollTop={(top) => sync && editorA.current?.setScrollTop(top)}
          />
        </div>
      </div>
      {periods.length > 1 && (
        <div className="max-w-md">
          <PeriodSelector periods={periods} value={pair.period} onChange={pair.setPeriod} disabled={pair.loading} />
        </div>
      )}
      {withGabarito.length > 0 && (
        <div className="flex max-w-md min-w-0 flex-col gap-1">
          <label htmlFor="gabarito-questao" className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Questão (para comparar também com o gabarito)
          </label>
          <select
            id="gabarito-questao"
            value={pair.questionId ?? ""}
            onChange={(event) => pair.setQuestionId(event.target.value === "" ? null : event.target.value)}
            disabled={pair.loading}
            className={INPUT}
          >
            <option value="">Sem questão (só A com B)</option>
            {withGabarito.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} (Lista {item.list})
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={!pair.ready}>
          {pair.loading ? "Verificando…" : "Verificar"}
        </Button>
        {pair.loading && (
          <Button variant="secondary" onClick={pair.cancel}>
            Cancelar
          </Button>
        )}
        <Button variant="secondary" onClick={pair.swap} disabled={pair.loading || empty}>
          Trocar A e B
        </Button>
        <Button variant="secondary" onClick={pair.clear} disabled={pair.loading || empty}>
          Limpar os dois
        </Button>
        <label className="flex min-h-11 items-center gap-2 text-sm sm:min-h-0">
          <input type="checkbox" checked={sync} onChange={(event) => pair.setSync(event.target.checked)} />
          Rolar os dois códigos juntos
        </label>
      </div>
      <section aria-live="polite" aria-label="Resultado da comparação" className="flex flex-col gap-3">
        {pair.error !== null && <ErrorText>{pair.error}</ErrorText>}
        {compared !== null && !pair.fresh && (
          <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
            Os códigos mudaram desde a comparação: verifique de novo para ver os trechos em comum.
          </p>
        )}
        {compared !== null && <PairResult result={compared.result} matches={pair.matches} current={pair.current} onShow={pair.show} />}
        {compared !== null && compared.result.gabarito && <GabaritoPair gabarito={compared.result.gabarito} />}
      </section>
    </form>
  );
}

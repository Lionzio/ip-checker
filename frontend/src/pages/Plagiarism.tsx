import { type FormEvent, useEffect, useRef, useState } from "react";
import { BAND_STYLES, PERCENT } from "../bands";
import { type CodeEditorHandle, CodeEditor, type LineRange } from "../components/CodeEditor";
import { Button, Card, ErrorText, LineChip, SyntaxErrorBox } from "../components/ui";
import { useApiCall } from "../hooks/useApiCall";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PAGE_TITLES } from "../labels";
import { classBytes, MAX_CLASS, MAX_CLASS_BYTES, parseClass } from "../plagiarismClass";
import { ApiError, type PlagiarismClient, type ValidationClient } from "../services/client";
import type {
  ListInfo,
  SimilarityBand,
  SimilarityClassResponse,
  SimilarityGabarito,
  SimilarityMatch,
  SimilarityResponse,
} from "../types/api";
import { INPUT } from "../ui";

/**
 * Painel de plágio (S17-03, FR-29; S27-02 e S27-03): duas soluções lado a lado (empilhadas em telas
 * estreitas) com os trechos em comum realçados, ou uma solução contra a turma, em que o que todos
 * escrevem quase não conta. A comparação roda no analisador isolado, e nada é guardado.
 */
/** A comparação de dois códigos de 50 KB leva menos de 1 s; o resto cobre a fila e a rede. */
export const PLAGIARISM_TIMEOUT_MS = 15_000;
/** Contra a turma, o analisador tem até 10 s. */
export const CLASS_TIMEOUT_MS = 20_000;

type Mode = "pair" | "class";

interface PlagiarismProps {
  /** As listas dão as questões com gabarito (S32-07). */
  client: PlagiarismClient & Pick<ValidationClient, "listLists">;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

interface Compared {
  codeA: string;
  codeB: string;
  result: SimilarityResponse;
}

function lines(first: number, last: number): string {
  return first === last ? `linha ${first}` : `linhas ${first}–${last}`;
}

export function Plagiarism({ client, onUnauthenticated }: PlagiarismProps) {
  useDocumentTitle(PAGE_TITLES.plagiarism);
  const [mode, setMode] = useState<Mode>("pair");
  const [codeA, setCodeA] = useState("");
  const [codeB, setCodeB] = useState("");
  const [compared, setCompared] = useState<Compared | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<number | null>(null);
  const [sync, setSync] = useState(true);
  const [lists, setLists] = useState<ListInfo[]>([]);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const pair = useApiCall(PLAGIARISM_TIMEOUT_MS, onUnauthenticated);
  const editorA = useRef<CodeEditorHandle>(null);
  const editorB = useRef<CodeEditorHandle>(null);

  const [target, setTarget] = useState("");
  const [classText, setClassText] = useState("");
  const [classResult, setClassResult] = useState<{ response: SimilarityClassResponse; codes: Map<string, string> } | null>(null);
  const [classError, setClassError] = useState<string | null>(null);
  const group = useApiCall(CLASS_TIMEOUT_MS, onUnauthenticated);

  // As questões com gabarito (ADR-11, item 5): sem elas, o seletor nem aparece.
  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(setLists, (error: unknown) => {
      if (!controller.signal.aborted && error instanceof ApiError && error.status === 401) onUnauthenticated();
    });
    return () => controller.abort();
  }, [client, onUnauthenticated]);
  const withGabarito = lists.flatMap((list) => (list.gabaritos ?? []).map((id) => ({ id, list: list.number })));

  // Os trechos só valem para os códigos que foram comparados.
  const fresh = compared !== null && compared.codeA === codeA && compared.codeB === codeB;
  const matches: SimilarityMatch[] = fresh ? (compared.result.matches ?? []) : [];
  const chosen = current !== null ? matches[current] : undefined;

  async function comparePair(first = codeA, second = codeB) {
    setError(null);
    setCompared(null);
    setCurrent(null);
    const outcome = await pair.run((signal) => client.compare(first, second, signal, questionId));
    if (outcome === null) return;
    if (outcome.ok) setCompared({ codeA: first, codeB: second, result: outcome.value });
    else setError(outcome.message);
  }

  function submitPair(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void comparePair();
  }

  function swap() {
    setCodeA(codeB);
    setCodeB(codeA);
    setCurrent(null);
    if (compared !== null) {
      const result = compared.result;
      setCompared({
        codeA: compared.codeB,
        codeB: compared.codeA,
        result: {
          ...result,
          matches: (result.matches ?? []).map((m) => ({ a_first: m.b_first, a_last: m.b_last, b_first: m.a_first, b_last: m.a_last })),
          gabarito: result.gabarito ? { ...result.gabarito, a: result.gabarito.b, b: result.gabarito.a } : result.gabarito,
        },
      });
    }
  }

  function clearPair() {
    setCodeA("");
    setCodeB("");
    setCompared(null);
    setError(null);
    setCurrent(null);
    editorA.current?.focus();
  }

  function show(index: number) {
    const match = matches[index];
    if (match === undefined) return;
    setCurrent(index);
    editorA.current?.scrollToLine(match.a_first);
    editorB.current?.scrollToLine(match.b_first);
  }

  const { solutions, legacy: legacyClass, repeated } = parseClass(classText);
  const bytes = classBytes(target, solutions);
  const classProblem =
    solutions.length > MAX_CLASS
      ? `São ${solutions.length} soluções; o limite é ${MAX_CLASS}.`
      : bytes > MAX_CLASS_BYTES
        ? "As soluções passam de 120 KB juntas: compare a turma em partes."
        : null;

  async function submitClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClassError(null);
    setClassResult(null);
    const sent = solutions;
    const outcome = await group.run((signal) => client.compareClass(target, sent, signal));
    if (outcome === null) return;
    if (outcome.ok) setClassResult({ response: outcome.value, codes: new Map(sent.map((item) => [item.label, item.code])) });
    else setClassError(outcome.message);
  }

  function sideBySide(label: string) {
    const code = classResult?.codes.get(label);
    if (code === undefined) return;
    setMode("pair");
    setCodeA(target);
    setCodeB(code);
    void comparePair(target, code);
  }

  const marksA: LineRange[] = matches.map((m) => ({ first: m.a_first, last: m.a_last }));
  const marksB: LineRange[] = matches.map((m) => ({ first: m.b_first, last: m.b_last }));
  const readyPair = codeA.trim() !== "" && codeB.trim() !== "" && !pair.loading;
  const readyClass = target.trim() !== "" && solutions.length > 0 && classProblem === null && !group.loading;

  return (
    <div className="flex flex-col gap-4 py-4">
      <div>
        <h2 className="text-xl font-semibold">Plágio</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          A comparação resiste a nomes trocados, espaços, comentários, linhas reordenadas e formas equivalentes (como
          trocar um for por um while), e nada é guardado.
        </p>
      </div>
      <div role="group" aria-label="Tipo de comparação" className="flex flex-wrap gap-2">
        <Button variant={mode === "pair" ? "primary" : "secondary"} aria-pressed={mode === "pair"} onClick={() => setMode("pair")}>
          Dois códigos
        </Button>
        <Button variant={mode === "class" ? "primary" : "secondary"} aria-pressed={mode === "class"} onClick={() => setMode("class")}>
          Contra a turma
        </Button>
      </div>

      {mode === "pair" ? (
        <form onSubmit={submitPair} className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="font-medium">Código A</h3>
              <CodeEditor
                ref={editorA}
                value={codeA}
                onChange={setCodeA}
                readOnly={pair.loading}
                label="Código A"
                placeholder="Cole aqui a primeira solução"
                marked={marksA}
                current={chosen ? { first: chosen.a_first, last: chosen.a_last } : null}
                onScrollTop={(top) => sync && editorB.current?.setScrollTop(top)}
              />
            </div>
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="font-medium">Código B</h3>
              <CodeEditor
                ref={editorB}
                value={codeB}
                onChange={setCodeB}
                readOnly={pair.loading}
                label="Código B"
                placeholder="Cole aqui a segunda solução"
                marked={marksB}
                current={chosen ? { first: chosen.b_first, last: chosen.b_last } : null}
                onScrollTop={(top) => sync && editorA.current?.setScrollTop(top)}
              />
            </div>
          </div>
          {withGabarito.length > 0 && (
            <div className="flex max-w-md min-w-0 flex-col gap-1">
              <label htmlFor="gabarito-questao" className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Questão (para comparar também com o gabarito)
              </label>
              <select
                id="gabarito-questao"
                value={questionId ?? ""}
                onChange={(event) => setQuestionId(event.target.value === "" ? null : event.target.value)}
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
            <Button type="submit" disabled={!readyPair}>
              {pair.loading ? "Verificando…" : "Verificar"}
            </Button>
            {pair.loading && (
              <Button variant="secondary" onClick={pair.cancel}>
                Cancelar
              </Button>
            )}
            <Button variant="secondary" onClick={swap} disabled={pair.loading || (codeA === "" && codeB === "")}>
              Trocar A e B
            </Button>
            <Button variant="secondary" onClick={clearPair} disabled={pair.loading || (codeA === "" && codeB === "")}>
              Limpar os dois
            </Button>
            <label className="flex min-h-11 items-center gap-2 text-sm sm:min-h-0">
              <input type="checkbox" checked={sync} onChange={(event) => setSync(event.target.checked)} />
              Rolar os dois códigos juntos
            </label>
          </div>
          <section aria-live="polite" aria-label="Resultado da comparação" className="flex flex-col gap-3">
            {error !== null && <ErrorText>{error}</ErrorText>}
            {compared !== null && !fresh && (
              <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
                Os códigos mudaram desde a comparação: verifique de novo para ver os trechos em comum.
              </p>
            )}
            {compared !== null && <PairResult result={compared.result} matches={matches} current={current} onShow={show} />}
            {compared !== null && compared.result.gabarito && <GabaritoPair gabarito={compared.result.gabarito} />}
          </section>
        </form>
      ) : (
        <form onSubmit={(event) => void submitClass(event)} className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="font-medium">Solução comparada</h3>
              <CodeEditor
                value={target}
                onChange={setTarget}
                readOnly={group.loading}
                label="Solução comparada"
                placeholder="Cole aqui a solução que você quer comparar com a turma"
              />
            </div>
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="font-medium">Soluções da turma</h3>
              <CodeEditor
                value={classText}
                onChange={setClassText}
                readOnly={group.loading}
                label="Soluções da turma"
                placeholder={"=== Ana\nn = int(input())\n...\n=== Bruno\n..."}
                describedBy="turma-dica"
              />
              <p id="turma-dica" className="text-sm text-slate-600 dark:text-slate-300">
                Cada solução começa por uma linha <code>=== nome</code>. Até {MAX_CLASS} soluções, somando até 120 KB.{" "}
                {solutions.length === 1 ? "1 solução." : `${solutions.length} soluções.`}
              </p>
              {legacyClass && (
                <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
                  As soluções foram separadas pelo formato antigo <code>### nome</code>. Prefira <code>=== nome</code>: um
                  comentário que começa com <code>###</code> dentro do código parte a solução em duas.
                </p>
              )}
              {repeated.length > 0 && (
                <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
                  {repeated.length === 1 ? "Este nome aparece" : "Estes nomes aparecem"} mais de uma vez:{" "}
                  {repeated.join(", ")}. As repetições ganharam um número, como "{repeated[0]} (2)", para que cada
                  solução abra o próprio código.
                </p>
              )}
              {classProblem !== null && <ErrorText>{classProblem}</ErrorText>}
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={!readyClass}>
              {group.loading ? "Comparando…" : "Comparar com a turma"}
            </Button>
            {group.loading && (
              <Button variant="secondary" onClick={group.cancel}>
                Cancelar
              </Button>
            )}
          </div>
          <section aria-live="polite" aria-label="Resultado contra a turma" className="flex flex-col gap-3">
            {classError !== null && <ErrorText>{classError}</ErrorText>}
            {classResult !== null && <ClassResult response={classResult.response} onSideBySide={sideBySide} />}
          </section>
        </form>
      )}
    </div>
  );
}

/** A e B comparados com o gabarito e o alerta de possível vazamento (S32-07; ADR-11, item 5). */
function GabaritoPair({ gabarito }: { gabarito: SimilarityGabarito }) {
  const sides = [
    ["A", gabarito.a],
    ["B", gabarito.b],
  ] as const;
  return (
    <Card aria-label="Comparação com o gabarito" className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">Comparação com o gabarito · {gabarito.question_id}</h3>
      {gabarito.leak_alert && (
        <div
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100"
        >
          <p className="font-semibold">Possível vazamento do gabarito</p>
          <p className="text-sm">{gabarito.message}</p>
        </div>
      )}
      {gabarito.status === "compared" ? (
        <>
          <ul className="flex flex-col gap-2">
            {sides.map(([label, side]) =>
              side ? (
                <li key={label} className="flex flex-wrap items-center gap-3">
                  <span className="font-medium">Código {label} com o gabarito:</span>
                  <span className="text-xl font-bold">{PERCENT.format(side.similarity)}%</span>
                  <Band band={side.band} />
                </li>
              ) : null,
            )}
          </ul>
          {!gabarito.leak_alert && <p className="text-sm text-slate-600 dark:text-slate-300">{gabarito.message}</p>}
        </>
      ) : (
        <p role="note" className="text-sm text-slate-700 dark:text-slate-200">
          {gabarito.message}
        </p>
      )}
    </Card>
  );
}

function Band({ band }: { band: SimilarityBand }) {
  return <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BAND_STYLES[band.id]}`}>{band.label}</span>;
}

function PairResult({
  result,
  matches,
  current,
  onShow,
}: {
  result: SimilarityResponse;
  matches: SimilarityMatch[];
  current: number | null;
  onShow: (index: number) => void;
}) {
  if (result.status === "syntax_error" && result.syntax_error !== null) {
    const problem = result.syntax_error;
    return (
      <SyntaxErrorBox
        title={`O código ${problem.code.toUpperCase()} tem um erro de sintaxe`}
        line={problem.line}
        col={problem.col}
        message={problem.message}
        alert
      >
        <p className="mt-2 text-sm">Os dois códigos precisam ser Python válido para serem comparados.</p>
      </SyntaxErrorBox>
    );
  }
  if (result.similarity === null || result.band === null) return null;
  const metrics = result.metrics;
  return (
    <Card as="div" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-3xl font-bold" aria-label={`Similaridade de ${PERCENT.format(result.similarity)}%`}>
          {PERCENT.format(result.similarity)}%
        </p>
        <Band band={result.band} />
      </div>
      {metrics && (
        <p className="text-sm text-slate-700 dark:text-slate-200">
          Estrutura: {PERCENT.format(metrics.tree_dice)}% · Contenção: {PERCENT.format(metrics.tree_containment)}%
          {metrics.sequence !== null && ` · Sequência: ${PERCENT.format(metrics.sequence)}%`}. A similaridade é a maior
          delas; a contenção alta com estrutura baixa indica código acrescentado a uma cópia.
        </p>
      )}
      {result.short_code && (
        <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
          Um dos códigos é curto: soluções independentes de questões simples tendem a se parecer. Leia os dois antes de
          concluir.
        </p>
      )}
      {matches.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Trechos em comum ({matches.length})</h3>
          <ul className="flex flex-wrap gap-2">
            {matches.map((match, index) => (
              <li key={`${match.a_first}-${match.b_first}`}>
                <LineChip aria-pressed={current === index} onClick={() => onShow(index)}>
                  A: {lines(match.a_first, match.a_last)} ↔ B: {lines(match.b_first, match.b_last)}
                </LineChip>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-sm text-slate-600 dark:text-slate-300">{result.notice}</p>
    </Card>
  );
}

function ClassResult({ response, onSideBySide }: { response: SimilarityClassResponse; onSideBySide: (label: string) => void }) {
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

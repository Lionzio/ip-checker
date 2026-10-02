import { type FormEvent, useState } from "react";
import { CodeEditor } from "../components/CodeEditor";
import { ApiError, type PlagiarismClient } from "../services/client";
import type { SimilarityBand, SimilarityResponse } from "../types/api";
import { BUTTON, errorMessage } from "../ui";

/**
 * Painel de plágio (S17-03, FR-29): duas soluções lado a lado (empilhadas em telas estreitas),
 * Verificar, a porcentagem e a faixa com cor e nome escrito. A comparação roda no analisador
 * isolado, e nada é guardado.
 */
const BAND_STYLES: Record<SimilarityBand["id"], string> = {
  plagio: "border-red-400 bg-red-100 text-red-900 dark:border-red-500 dark:bg-red-950 dark:text-red-100",
  altas_chances:
    "border-orange-400 bg-orange-100 text-orange-900 dark:border-orange-500 dark:bg-orange-950 dark:text-orange-100",
  requer_atencao:
    "border-amber-400 bg-amber-100 text-amber-900 dark:border-amber-500 dark:bg-amber-950 dark:text-amber-100",
  ligeiramente_suspeito:
    "border-sky-400 bg-sky-100 text-sky-900 dark:border-sky-500 dark:bg-sky-950 dark:text-sky-100",
  sem_suspeitas:
    "border-green-400 bg-green-100 text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-100",
};

const PERCENT = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

interface PlagiarismProps {
  client: PlagiarismClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

export function Plagiarism({ client, onUnauthenticated }: PlagiarismProps) {
  const [codeA, setCodeA] = useState("");
  const [codeB, setCodeB] = useState("");
  const [result, setResult] = useState<SimilarityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await client.compare(codeA, codeB));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        onUnauthenticated();
        return;
      }
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  const ready = codeA.trim() !== "" && codeB.trim() !== "" && !loading;
  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-4 py-4">
      <div>
        <h2 className="text-xl font-semibold">Plágio</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Cole a solução de cada aluno. A comparação resiste a nomes trocados, espaços, comentários e
          trechos reordenados, e nada é guardado.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Código A</h3>
          <CodeEditor value={codeA} onChange={setCodeA} disabled={loading} label="Código A" placeholder="Cole aqui a primeira solução" />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Código B</h3>
          <CodeEditor value={codeB} onChange={setCodeB} disabled={loading} label="Código B" placeholder="Cole aqui a segunda solução" />
        </div>
      </div>
      <button type="submit" disabled={!ready} className={`${BUTTON} self-start`}>
        {loading ? "Verificando…" : "Verificar"}
      </button>
      <section aria-live="polite" aria-label="Resultado da comparação" className="flex flex-col gap-3">
        {error !== null && (
          <p role="alert" className="text-red-700 dark:text-red-300">
            {error}
          </p>
        )}
        {result !== null && <Result result={result} />}
      </section>
    </form>
  );
}

function Result({ result }: { result: SimilarityResponse }) {
  if (result.status === "syntax_error" && result.syntax_error !== null) {
    const problem = result.syntax_error;
    return (
      <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100">
        <p className="font-semibold">O código {problem.code.toUpperCase()} tem um erro de sintaxe</p>
        <p>
          Linha {problem.line}, coluna {problem.col}: {problem.message}
        </p>
        <p className="text-sm">Os dois códigos precisam ser Python válido para serem comparados.</p>
      </div>
    );
  }
  if (result.similarity === null || result.band === null) return null;
  return (
    <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-3xl font-bold" aria-label={`Similaridade de ${PERCENT.format(result.similarity)}%`}>
          {PERCENT.format(result.similarity)}%
        </p>
        <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BAND_STYLES[result.band.id]}`}>
          {result.band.label}
        </span>
      </div>
      {result.short_code && (
        <p role="note" className="text-sm text-amber-900 dark:text-amber-200">
          Um dos códigos é curto: soluções independentes de questões simples tendem a se parecer.
          Leia os dois antes de concluir.
        </p>
      )}
      <p className="text-sm text-slate-600 dark:text-slate-300">{result.notice}</p>
    </div>
  );
}

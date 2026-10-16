import { lazy, Suspense, useEffect, useState } from "react";
import { ClassMode } from "../components/plagiarism/ClassMode";
import { PairMode } from "../components/plagiarism/PairMode";
import { Button } from "../components/ui";
import { useClassComparison } from "../hooks/useClassComparison";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { usePairComparison } from "../hooks/usePairComparison";
import { PAGE_TITLES } from "../labels";
import { ApiError, type PlagiarismClient, type ValidationClient } from "../services/client";
import type { ListInfo } from "../types/api";

export { CLASS_TIMEOUT_MS } from "../hooks/useClassComparison";
export { PLAGIARISM_TIMEOUT_MS } from "../hooks/usePairComparison";

/** O todos contra todos (S40-02) é carregado só quando escolhido (NFR-03). */
const ClassMatrix = lazy(() => import("../components/ClassMatrix").then((module) => ({ default: module.ClassMatrix })));

type Mode = "pair" | "class" | "matrix";

interface PlagiarismProps {
  /** As listas dão as questões com gabarito (S32-07). */
  client: PlagiarismClient & Pick<ValidationClient, "listLists">;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

const MODES: { mode: Mode; label: string }[] = [
  { mode: "pair", label: "Dois códigos" },
  { mode: "class", label: "Contra a turma" },
  { mode: "matrix", label: "Todos contra todos" },
];

/**
 * Painel de plágio (S17-03, FR-29; S27-02, S27-03 e S40-02): duas soluções lado a lado (empilhadas
 * em telas estreitas) com os trechos em comum realçados, uma solução contra a turma, em que o que
 * todos escrevem quase não conta, ou a turma toda, cada uma contra as outras. A comparação roda no
 * analisador isolado, e nada é guardado. Cada modo mora no próprio arquivo (S39-01); o estado dos
 * dois primeiros fica aqui, para o que foi colado sobreviver à troca de modo.
 */
export function Plagiarism({ client, onUnauthenticated }: PlagiarismProps) {
  useDocumentTitle(PAGE_TITLES.plagiarism);
  const [mode, setMode] = useState<Mode>("pair");
  const [lists, setLists] = useState<ListInfo[]>([]);
  const pair = usePairComparison(client, onUnauthenticated);
  const group = useClassComparison(client, onUnauthenticated);

  // As questões com gabarito (ADR-11, item 5): sem elas, o seletor nem aparece.
  useEffect(() => {
    const controller = new AbortController();
    client.listLists(controller.signal).then(setLists, (error: unknown) => {
      if (!controller.signal.aborted && error instanceof ApiError && error.status === 401) onUnauthenticated();
    });
    return () => controller.abort();
  }, [client, onUnauthenticated]);
  const withGabarito = lists.flatMap((list) => (list.gabaritos ?? []).map((id) => ({ id, list: list.number })));

  // Dos outros modos para os dois códigos lado a lado, já comparados (S27-03 e S40-02).
  function sideBySide(first: string, second: string) {
    setMode("pair");
    pair.compareThese(first, second);
  }

  function classSideBySide(label: string) {
    const code = group.result?.codes.get(label);
    if (code !== undefined) sideBySide(group.target, code);
  }

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
        {MODES.map((item) => (
          <Button
            key={item.mode}
            variant={mode === item.mode ? "primary" : "secondary"}
            aria-pressed={mode === item.mode}
            onClick={() => setMode(item.mode)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {mode === "pair" ? (
        <PairMode pair={pair} withGabarito={withGabarito} />
      ) : mode === "class" ? (
        <ClassMode group={group} onSideBySide={classSideBySide} />
      ) : (
        <Suspense fallback={<p role="status" className="text-sm">Carregando…</p>}>
          <ClassMatrix client={client} onUnauthenticated={onUnauthenticated} onSideBySide={sideBySide} />
        </Suspense>
      )}
    </div>
  );
}

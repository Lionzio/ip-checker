import { type DragEvent, useEffect, useRef, useState } from "react";
import { BATCH_COLUMNS, BATCH_STATUS, batchCsv, studentOf, summary } from "../classBatch";
import { type ClassFile, chunks, MAX_FILES, readClassFiles } from "../classFiles";
import { ListSelector } from "../components/ListSelector";
import { PeriodSelector } from "../components/PeriodSelector";
import { QuestionSelector } from "../components/QuestionSelector";
import { Button, Card, ErrorText } from "../components/ui";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useLists } from "../hooks/useLists";
import { usePeriods } from "../hooks/usePeriods";
import { PAGE_TITLES } from "../labels";
import { questionOptions } from "../questions";
import { ApiError, type ValidationClient } from "../services/client";
import type { BatchResult } from "../types/api";

interface ClassBatchProps {
  client: ValidationClient;
  /** A API respondeu 401: a sessão venceu ou foi encerrada. */
  onUnauthenticated: () => void;
}

/** Quantas vezes uma parte é reenviada depois de um 429 ou 503 com espera (S40-01). */
const MAX_RETRIES = 5;

type Progress = { done: number; total: number; waitingS: number | null };

const STATUS_STYLES: Record<BatchResult["status"], string> = {
  valid: "text-green-800 dark:text-green-300",
  invalid: "text-red-800 dark:text-red-300",
  syntax_error: "text-amber-900 dark:text-amber-200",
  rejected: "text-slate-700 dark:text-slate-300",
};

/**
 * A turma inteira (S40-01, US-33): os `.py` de uma lista, soltos ou num `.zip`, conferidos de uma
 * vez. A página lê os arquivos, manda à API em partes (até 20 arquivos e abaixo de 128 KB), espera
 * quando o servidor pede e mostra uma linha por aluno, que pode virar um CSV. Nada é guardado.
 */
export function ClassBatch({ client, onUnauthenticated }: ClassBatchProps) {
  useDocumentTitle(PAGE_TITLES.batch);
  const periods = usePeriods(client, onUnauthenticated);
  const [period, setPeriod] = useState<string | null>(null);
  const { lists, error: listsError } = useLists(client, onUnauthenticated, period);
  const [listNumber, setListNumber] = useState<number | null>(null);
  const [questionId, setQuestionId] = useState<string | null>(null);
  const [files, setFiles] = useState<ClassFile[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<{ list: string; questionId: string | null } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const running = progress !== null;
  const currentList = listNumber === null ? undefined : lists.find((list) => list.number === listNumber);
  const questions = listNumber === null ? null : questionOptions(currentList);

  async function chosen(list: File[]) {
    if (list.length === 0) return;
    const read = await readClassFiles(list);
    setFiles(read.files);
    setSkipped(read.skipped);
    setResults([]);
    setChecked(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function dragOver(event: DragEvent<HTMLDivElement>) {
    if (!running && event.dataTransfer.types.includes("Files")) event.preventDefault();
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    if (running) return;
    event.preventDefault();
    void chosen([...event.dataTransfer.files]);
  }

  async function wait(seconds: number, signal: AbortSignal) {
    for (let left = seconds; left > 0; left -= 1) {
      if (signal.aborted) return;
      setProgress((current) => (current === null ? null : { ...current, waitingS: left }));
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    setProgress((current) => (current === null ? null : { ...current, waitingS: null }));
  }

  async function run() {
    if (listNumber === null || files.length === 0) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    const label = `Lista ${listNumber}${currentList ? `: ${currentList.title}` : ""}${period ? ` (${period})` : ""}`;
    setResults([]);
    setError(null);
    setChecked({ list: label, questionId });
    setProgress({ done: 0, total: files.length, waitingS: null });
    const collected: BatchResult[] = [];
    try {
      for (const part of chunks(files)) {
        for (let attempt = 0; ; attempt += 1) {
          try {
            const response = await client.validateBatch(
              { list_number: listNumber, question_id: questionId, period, files: part },
              controller.signal,
            );
            collected.push(...response.results);
            setResults([...collected]);
            setProgress({ done: collected.length, total: files.length, waitingS: null });
            break;
          } catch (caught) {
            if (controller.signal.aborted) return;
            if (caught instanceof ApiError && caught.status === 401) {
              onUnauthenticated();
              return;
            }
            const busy = caught instanceof ApiError && (caught.status === 429 || caught.status === 503);
            if (!busy || attempt >= MAX_RETRIES) throw caught;
            await wait(caught.retryAfterS ?? 5, controller.signal);
            if (controller.signal.aborted) return;
          }
        }
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? `${caught.message} ${collected.length} de ${files.length} arquivos foram conferidos.`
          : "Não foi possível falar com o servidor. Os resultados já recebidos continuam abaixo.",
      );
    } finally {
      controllerRef.current = null;
      setProgress(null);
    }
  }

  function cancel() {
    controllerRef.current?.abort();
    setProgress(null);
    setError(`Correção cancelada: ${results.length} de ${files.length} arquivos foram conferidos.`);
  }

  function downloadCsv() {
    if (checked === null) return;
    const url = URL.createObjectURL(new Blob([batchCsv(results, checked)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `ip-checker-turma-${checked.questionId ?? `lista-${listNumber ?? ""}`}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const counts = summary(results);
  const sorted = [...results].sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
  return (
    <div className="flex flex-col gap-4 py-4">
      <div>
        <h2 className="text-xl font-semibold">Turma inteira</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Os <code>.py</code> de uma lista, soltos ou num <code>.zip</code> (até {MAX_FILES} arquivos, 50 KB cada e
          2 MB no total), conferidos de uma vez. O nome do arquivo identifica o aluno. Nada é guardado.
        </p>
      </div>
      <div className={periods.length > 1 ? "grid gap-4 sm:grid-cols-3" : "grid gap-4 sm:grid-cols-2"}>
        <PeriodSelector
          periods={periods}
          value={period}
          onChange={(value) => {
            setPeriod(value);
            setListNumber(null);
            setQuestionId(null);
          }}
          disabled={running}
        />
        <ListSelector
          lists={lists}
          value={listNumber}
          onChange={(value) => {
            setListNumber(value);
            setQuestionId(null);
          }}
          disabled={running}
        />
        <QuestionSelector questions={questions} value={questionId} onChange={setQuestionId} disabled={running} />
      </div>
      <div
        onDragOver={dragOver}
        onDrop={drop}
        className="flex flex-col items-start gap-2 rounded-md border-2 border-dashed border-slate-300 p-4 dark:border-slate-600"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".py,.zip,text/x-python,application/zip"
          aria-label="Arquivos da turma (.py ou .zip)"
          className="sr-only"
          tabIndex={-1}
          onChange={(event) => void chosen([...(event.target.files ?? [])])}
        />
        <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={running}>
          Escolher arquivos
        </Button>
        <p className="text-sm text-slate-600 dark:text-slate-300">Ou arraste os arquivos ou o .zip para cá.</p>
        {files.length > 0 && (
          <p role="status" className="text-sm font-medium">
            {files.length === 1 ? "1 arquivo pronto." : `${files.length} arquivos prontos.`}
          </p>
        )}
        {skipped.length > 0 && (
          <details className="text-sm text-amber-900 dark:text-amber-200">
            <summary className="cursor-pointer">
              {skipped.length === 1 ? "1 arquivo ficou de fora" : `${skipped.length} arquivos ficaram de fora`}
            </summary>
            <ul className="mt-1 list-disc pl-5">
              {skipped.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => void run()} disabled={running || listNumber === null || files.length === 0}>
          {running ? "Corrigindo…" : "Corrigir a turma"}
        </Button>
        {running && (
          <Button variant="secondary" onClick={cancel}>
            Cancelar
          </Button>
        )}
        {progress !== null && (
          <span role="status" className="text-sm">
            {progress.waitingS !== null
              ? `O servidor pediu uma pausa: continua em ${progress.waitingS} s (${progress.done} de ${progress.total}).`
              : `${progress.done} de ${progress.total} arquivos conferidos.`}
          </span>
        )}
      </div>
      {progress !== null && (
        <progress className="h-2 w-full" max={progress.total} value={progress.done} aria-label="Andamento da correção" />
      )}
      {listsError !== null && <ErrorText>{listsError}</ErrorText>}
      {error !== null && <ErrorText>{error}</ErrorText>}
      {results.length > 0 && (
        <section aria-label="Resultado da turma" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm">
              {counts.valid} válidas, {counts.invalid} com violações, {counts.syntax_error} com erro de sintaxe
              {counts.rejected > 0 && `, ${counts.rejected} recusadas`}.
            </p>
            <Button variant="secondary" size="sm" onClick={downloadCsv} disabled={running}>
              Baixar CSV
            </Button>
          </div>
          <Card as="div" padding="none" className="overflow-x-auto">
            <table className="w-full min-w-3xl text-left text-sm">
              <thead className="bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <tr>
                  <th scope="col" className="px-3 py-2 font-semibold">Aluno</th>
                  <th scope="col" className="px-3 py-2 font-semibold">Status</th>
                  {BATCH_COLUMNS.map((column) => (
                    <th key={column.category} scope="col" className="px-3 py-2 text-right font-semibold">
                      {column.label}
                    </th>
                  ))}
                  <th scope="col" className="px-3 py-2 font-semibold">Regras</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Gabarito</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((result) => (
                  <tr key={result.name} className="border-t border-slate-200 align-top dark:border-slate-700">
                    <th scope="row" className="px-3 py-2 font-medium">{studentOf(result.name)}</th>
                    <td className={`px-3 py-2 ${STATUS_STYLES[result.status]}`}>
                      {BATCH_STATUS[result.status]}
                      {result.syntax_error && (
                        <span className="block text-xs">
                          linha {result.syntax_error.line}: {result.syntax_error.message}
                        </span>
                      )}
                      {result.message && <span className="block text-xs">{result.message}</span>}
                    </td>
                    {BATCH_COLUMNS.map((column) => (
                      <td key={column.category} className="px-3 py-2 text-right tabular-nums">
                        {result.counts[column.category] ?? 0}
                      </td>
                    ))}
                    <td className="px-3 py-2 font-mono text-xs">{result.rule_ids.join(" ")}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {result.gabarito_similarity === null || result.gabarito_similarity === undefined
                        ? "—"
                        : `${result.gabarito_similarity.toLocaleString("pt-BR")}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </section>
      )}
    </div>
  );
}

import { type FormEvent, useEffect, useRef, useState } from "react";
import type { FeedbackForm } from "../draftContext";
import { useApiCall } from "../hooks/useApiCall";
import type { FeedbackClient } from "../services/client";
import type { FeedbackResponse, ValidateRequest, ValidationStatus } from "../types/api";
import { BUTTON, INPUT } from "../ui";

/** O servidor tem até 28 s para as IAs; o resto cobre a análise e a rede. */
export const FEEDBACK_TIMEOUT_MS = 40_000;

interface FeedbackPanelProps {
  client: FeedbackClient;
  /** O código e a lista que foram verificados: o feedback é sobre eles, não sobre o editor. */
  request: ValidateRequest;
  /** Identifica a verificação: um texto gerado antes de verificar de novo some. */
  verificationId: string;
  status: ValidationStatus;
  onUnauthenticated: () => void;
  /** Nome e anotação ficam com o verificador: sobrevivem a uma nova verificação do mesmo aluno. */
  form: FeedbackForm;
  onFormChange: (form: FeedbackForm) => void;
  /** O último feedback gerado na página: para avisar quando o código mudou e o nome não (S26-02). */
  previous?: { student: string; code: string } | null;
  onGenerated?: (generated: { student: string; code: string }) => void;
}

interface Generated {
  verificationId: string;
  text: string;
  source: FeedbackResponse["source"];
}

const SOURCE_NOTES: Record<FeedbackResponse["source"], string> = {
  llm: "Escrito com IA a partir do resultado do IP-Checker. Revise antes de copiar.",
  template:
    "Montado sem IA, por modelos de texto (nenhuma IA está configurada ou nenhuma respondeu a tempo). Revise antes de copiar.",
};

/**
 * Feedback para o aluno (S19-01, FR-30): Nome do aluno, Anotação, Gerar feedback, o texto num campo
 * editável e Copiar. O texto aparece num campo de texto, nunca como HTML.
 */
export function FeedbackPanel({
  client,
  request,
  verificationId,
  status,
  onUnauthenticated,
  form,
  onFormChange,
  previous = null,
  onGenerated,
}: FeedbackPanelProps) {
  const { student, annotation } = form;
  const [generated, setGenerated] = useState<Generated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const { run, cancel, loading } = useApiCall(FEEDBACK_TIMEOUT_MS, onUnauthenticated);
  const copyRef = useRef<HTMLButtonElement>(null);

  const current = generated !== null && generated.verificationId === verificationId ? generated : null;
  // O nome é o do feedback anterior, mas o código é outro: provavelmente é outro aluno (S26-02).
  const sameName =
    previous !== null && student.trim() !== "" && student.trim() === previous.student && request.code !== previous.code;

  // Gerado o texto, o foco vai a Copiar: o próximo passo é colá-lo no Dikastis (S26-02).
  useEffect(() => {
    if (current !== null) copyRef.current?.focus();
  }, [current?.verificationId, current?.source]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCopied(null);
    const name = student.trim();
    const outcome = await run((signal) =>
      client.feedback(
        {
          code: request.code,
          list_number: request.list_number,
          question_id: request.question_id ?? null,
          student_name: name,
          annotation: annotation.trim() === "" ? null : annotation,
        },
        signal,
      ),
    );
    if (outcome === null) return;
    if (!outcome.ok) {
      setError(outcome.message);
      return;
    }
    setGenerated({ verificationId, text: outcome.value.text, source: outcome.value.source });
    onGenerated?.({ student: name, code: request.code });
  }

  async function copy() {
    if (current === null) return;
    try {
      await navigator.clipboard.writeText(current.text);
      setCopied("Copiado.");
    } catch {
      setCopied("Não foi possível copiar. Selecione o texto e copie com Ctrl+C.");
    }
  }

  return (
    <section
      aria-labelledby="titulo-feedback"
      className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-4 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
    >
      <h2 id="titulo-feedback" className="text-lg font-semibold">
        Feedback para o aluno
      </h2>
      {status === "syntax_error" ? (
        <p className="text-sm text-slate-700 dark:text-slate-300">
          Com erro de sintaxe, as permissões não foram verificadas, então não há feedback. Corrija o código e
          verifique de novo.
        </p>
      ) : (
        <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="font-medium">Nome do aluno</span>
            <input
              name="student"
              required
              maxLength={120}
              autoComplete="off"
              value={student}
              onChange={(event) => onFormChange({ ...form, student: event.target.value })}
              className={INPUT}
            />
          </label>
          <div className="flex flex-col gap-1">
            <label className="flex flex-col gap-1">
              <span className="font-medium">Anotação importante (opcional)</span>
              <textarea
                name="annotation"
                rows={3}
                maxLength={1000}
                aria-describedby="dica-anotacao"
                value={annotation}
                onChange={(event) => onFormChange({ ...form, annotation: event.target.value })}
                className={INPUT}
              />
            </label>
            <span id="dica-anotacao" className="text-sm text-slate-600 dark:text-slate-300">
              Observações e dicas para o aluno. O nome dele nunca é enviado a uma IA.
            </span>
          </div>
          {sameName && (
            <p role="note" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
              O código mudou, mas o nome do aluno é o mesmo do último feedback ({previous?.student}). Confira o
              nome antes de gerar.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={loading || student.trim().length < 2} className={BUTTON}>
              {loading ? "Gerando…" : "Gerar feedback"}
            </button>
            {loading && (
              <button
                type="button"
                onClick={cancel}
                className="inline-flex min-h-11 items-center rounded-md border border-slate-300 px-4 text-sm font-medium hover:bg-slate-100 sm:min-h-9 dark:border-slate-600 dark:hover:bg-slate-800"
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      )}
      {error !== null && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      {current !== null && (
        <div className="flex flex-col gap-2">
          <label className="flex flex-col gap-1">
            <span className="font-medium">Texto do feedback</span>
            <textarea
              name="feedback"
              rows={8}
              value={current.text}
              onChange={(event) => setGenerated({ ...current, text: event.target.value })}
              className={INPUT}
            />
          </label>
          <p className="text-sm text-slate-600 dark:text-slate-300">{SOURCE_NOTES[current.source]}</p>
          <div className="flex items-center gap-3">
            <button
              ref={copyRef}
              type="button"
              onClick={() => void copy()}
              className="inline-flex min-h-11 items-center rounded-md border border-slate-300 px-4 text-sm font-medium hover:bg-slate-100 sm:min-h-9 dark:border-slate-600 dark:hover:bg-slate-800"
            >
              Copiar
            </button>
            <span role="status" className="text-sm">
              {copied}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

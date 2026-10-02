import { type FormEvent, useState } from "react";
import { ApiError, type FeedbackClient } from "../services/client";
import type { FeedbackResponse, ValidateRequest, ValidationStatus } from "../types/api";
import { BUTTON, errorMessage, INPUT } from "../ui";

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
}

export interface FeedbackForm {
  student: string;
  annotation: string;
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
}: FeedbackPanelProps) {
  const { student, annotation } = form;
  const [generated, setGenerated] = useState<Generated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const current = generated !== null && generated.verificationId === verificationId ? generated : null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setCopied(null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FEEDBACK_TIMEOUT_MS);
    try {
      const response = await client.feedback(
        {
          code: request.code,
          list_number: request.list_number,
          student_name: student.trim(),
          annotation: annotation.trim() === "" ? null : annotation,
        },
        controller.signal,
      );
      setGenerated({ verificationId, text: response.text, source: response.source });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        onUnauthenticated();
        return;
      }
      setError(
        controller.signal.aborted
          ? "O servidor não respondeu a tempo. Tente de novo em alguns segundos."
          : errorMessage(caught),
      );
    } finally {
      clearTimeout(timer);
      setLoading(false);
    }
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
          <button type="submit" disabled={loading || student.trim().length < 2} className={`${BUTTON} self-start`}>
            {loading ? "Gerando…" : "Gerar feedback"}
          </button>
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
              type="button"
              onClick={() => void copy()}
              className="rounded-md border border-slate-300 px-4 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
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

import { useEffect, useState } from "react";
import type { ValidationState } from "../hooks/useValidateCode";
import { BUSY_TITLES, CATEGORY_LABELS, NOTICE_TEXTS } from "../labels";
import type { ValidateResponse, Violation } from "../types/api";

interface ResultPanelProps {
  state: ValidationState;
  onRetry: () => void;
}

const CATEGORY_STYLES: Record<Violation["category"], string> = {
  ANULACAO: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
  PROIBIDO_NA_QUESTAO: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
  FORA_DA_LISTA: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
  NAO_CONSTA: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
  EXIGENCIA: "bg-purple-100 text-purple-900 dark:bg-purple-900/40 dark:text-purple-100",
};

function RetryButton({ onRetry, disabled = false }: { onRetry: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onRetry}
      disabled={disabled}
      className="mt-3 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
    >
      Tentar novamente
    </button>
  );
}

function Notices({ response }: { response: ValidateResponse }) {
  if (response.notices.length === 0) return null;
  return (
    <ul className="mt-3 space-y-1 text-sm text-slate-600 dark:text-slate-300">
      {response.notices.map((notice) => (
        <li key={notice}>{NOTICE_TEXTS[notice]}</li>
      ))}
    </ul>
  );
}

function SuccessResult({ response }: { response: ValidateResponse }) {
  if (response.status === "syntax_error" && response.syntax_error !== null) {
    const { line, col, message } = response.syntax_error;
    return (
      <div>
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">Erro de sintaxe</h2>
        <p className="mt-1">
          Linha {line}, coluna {col}: {message}
        </p>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Corrija a sintaxe: as permissões só são verificadas depois.
        </p>
      </div>
    );
  }

  if (response.status === "valid") {
    return (
      <div>
        <h2 className="text-lg font-semibold text-green-700 dark:text-green-300">
          Nenhuma violação encontrada
        </h2>
        <Notices response={response} />
        <p className="mt-3 text-xs text-slate-500">Regras {response.ruleset_version}</p>
      </div>
    );
  }

  const count = response.violations.length;
  return (
    <div>
      <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">
        {count === 1 ? "1 violação encontrada" : `${count} violações encontradas`}
      </h2>
      <ul className="mt-3 space-y-2">
        {response.violations.map((violation) => (
          <li
            key={`${violation.rule_id}-${violation.line}-${violation.col}`}
            className="rounded-md border border-slate-200 p-3 dark:border-slate-700"
          >
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className={`rounded px-2 py-0.5 font-medium ${CATEGORY_STYLES[violation.category]}`}>
                {CATEGORY_LABELS[violation.category]}
              </span>
              <span className="font-mono text-slate-600 dark:text-slate-300">
                {/* Uma exigência (R-02) fala da solução inteira, não de um trecho. */}
                {violation.category === "EXIGENCIA"
                  ? "Solução inteira"
                  : `Linha ${violation.line}, coluna ${violation.col}`}
              </span>
              <span className="text-slate-500">{violation.rule_id}</span>
            </div>
            <p className="mt-1">{violation.message}</p>
          </li>
        ))}
      </ul>
      {response.truncated && (
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          Mostrando as {count} primeiras violações. Corrija estas e verifique de novo.
        </p>
      )}
      <Notices response={response} />
      <p className="mt-3 text-xs text-slate-500">Regras {response.ruleset_version}</p>
    </div>
  );
}

type BusyState = Extract<ValidationState, { kind: "busy" }>;

/** Limite de taxa ou sobrecarga (US-18): mostra a espera pedida pelo servidor, em contagem regressiva. */
function BusyResult({ state, onRetry }: { state: BusyState; onRetry: () => void }) {
  const deadline = state.retryAfterS === null ? null : state.receivedAt + state.retryAfterS * 1000;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (deadline === null) return;
    const timer = setInterval(() => {
      setNow(Date.now());
      if (Date.now() >= deadline) clearInterval(timer);
    }, 250);
    return () => clearInterval(timer);
  }, [deadline]);

  const remaining = deadline === null ? 0 : Math.max(0, Math.ceil((deadline - now) / 1000));
  return (
    <div>
      <h2 className="text-lg font-semibold">{BUSY_TITLES[state.code] ?? "Serviço ocupado"}</h2>
      <p className="mt-1">{state.message}</p>
      {deadline !== null && (
        // Sem aria-live: um leitor de tela não deve anunciar cada segundo da contagem.
        <p className="mt-1 text-sm" aria-live="off">
          {remaining > 0
            ? `Tente novamente em ${remaining} ${remaining === 1 ? "segundo" : "segundos"}.`
            : "Já pode tentar novamente."}
        </p>
      )}
      <RetryButton onRetry={onRetry} disabled={remaining > 0} />
    </div>
  );
}

function Content({ state, onRetry }: ResultPanelProps) {
  switch (state.kind) {
    case "idle":
      return (
        <p className="text-slate-600 dark:text-slate-300">
          Cole o código, escolha a lista e clique em Verificar.
        </p>
      );
    case "loading":
      return <p className="text-slate-600 dark:text-slate-300">Verificando…</p>;
    case "success":
      return <SuccessResult response={state.response} />;
    case "rejected":
      return (
        <div>
          <h2 className="text-lg font-semibold">
            {state.code === "PAYLOAD_TOO_LARGE" ? "O código excede 50 KB" : "O código não pôde ser verificado"}
          </h2>
          <p className="mt-1">{state.message}</p>
        </div>
      );
    case "busy":
      // A chave recria a contagem a cada nova resposta 429 ou 503.
      return <BusyResult key={state.receivedAt} state={state} onRetry={onRetry} />;
    case "network":
    case "timeout":
      return (
        <div>
          <h2 className="text-lg font-semibold">Sem resposta do servidor</h2>
          <p className="mt-1">{state.message}</p>
          <RetryButton onRetry={onRetry} />
        </div>
      );
  }
}

export function ResultPanel({ state, onRetry }: ResultPanelProps) {
  return (
    <section
      aria-label="Resultado da verificação"
      aria-live="polite"
      aria-busy={state.kind === "loading"}
      className="rounded-md border border-slate-200 bg-white p-4 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
    >
      <Content state={state} onRetry={onRetry} />
    </section>
  );
}

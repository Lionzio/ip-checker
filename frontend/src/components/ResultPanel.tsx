import { type Ref, useEffect, useState } from "react";
import type { ValidationState } from "../hooks/useValidateCode";
import { BUSY_TITLES, CATEGORY_LABELS, NOTICE_TEXTS } from "../labels";
import { announcement, groupViolations, type RuleGroup, summarize } from "../report";
import type { Category, ValidateResponse } from "../types/api";
import { Button, Card, LineChip, SyntaxErrorBox } from "./ui";

interface ResultPanelProps {
  state: ValidationState;
  onRetry: () => void;
  /** O código que foi verificado: de onde saem os trechos de cada violação (S26-03). */
  code?: string;
  /** O editor mudou depois da verificação: o resultado pode não valer mais. */
  stale?: boolean;
  /** Clique numa linha do relatório: o editor seleciona o trecho (S26-03). */
  onSelectLines?: (first: number, last: number) => void;
  /** O título do resultado, que recebe o foco quando a verificação termina (S26-02). */
  headingRef?: Ref<HTMLHeadingElement>;
}

// Uma cor por categoria: a anulação (vermelho) nunca se confunde com o fora da lista (âmbar).
const CATEGORY_STYLES: Record<Category, string> = {
  ANULACAO: "bg-red-100 text-red-900 dark:bg-red-900/50 dark:text-red-100",
  PROIBIDO_NA_QUESTAO: "bg-fuchsia-100 text-fuchsia-900 dark:bg-fuchsia-900/50 dark:text-fuchsia-100",
  EXIGENCIA: "bg-purple-100 text-purple-900 dark:bg-purple-900/50 dark:text-purple-100",
  FORA_DA_LISTA: "bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100",
  NAO_CONSTA: "bg-sky-100 text-sky-900 dark:bg-sky-900/50 dark:text-sky-100",
};

const CARD_BORDERS: Record<Category, string> = {
  ANULACAO: "border-l-red-600",
  PROIBIDO_NA_QUESTAO: "border-l-fuchsia-600",
  EXIGENCIA: "border-l-purple-600",
  FORA_DA_LISTA: "border-l-amber-500",
  NAO_CONSTA: "border-l-sky-600",
};

const HEADING = "text-lg font-semibold focus:outline-none";

function RetryButton({ onRetry, disabled = false }: { onRetry: () => void; disabled?: boolean }) {
  return (
    <Button variant="secondary" size="sm" onClick={onRetry} disabled={disabled} className="mt-3">
      Tentar novamente
    </Button>
  );
}

/** Os avisos (como o das regras de questão) aparecem uma vez só, no fim do relatório. */
function Notices({ response }: { response: ValidateResponse }) {
  if (response.notices.length === 0) return null;
  return (
    <ul className="mt-3 space-y-1 text-sm text-slate-600 dark:text-slate-300">
      {[...new Set(response.notices)].map((notice) => (
        <li key={notice}>{NOTICE_TEXTS[notice]}</li>
      ))}
    </ul>
  );
}

function Snippet({ code, line }: { code: string | undefined; line: number }) {
  const text = code?.split("\n")[line - 1]?.trim();
  if (text === undefined || text === "") return null;
  return (
    <pre className="mt-2 overflow-x-auto rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-100">
      <code>
        <span className="mr-2 text-slate-600 select-none dark:text-slate-300" aria-hidden="true">
          {line}
        </span>
        {text}
      </code>
    </pre>
  );
}

function RuleCard({
  group,
  code,
  onSelectLines,
}: {
  group: RuleGroup;
  code: string | undefined;
  onSelectLines?: (first: number, last: number) => void;
}) {
  // Uma exigência (R-02, R-68) fala da solução inteira, não de um trecho.
  const whole = group.category === "EXIGENCIA";
  const first = group.occurrences[0];
  return (
    <Card as="li" padding="sm" className={`border-l-4 ${CARD_BORDERS[group.category]}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className={`rounded px-2 py-0.5 font-medium ${CATEGORY_STYLES[group.category]}`}>
          {CATEGORY_LABELS[group.category]}
        </span>
        <span className="text-slate-600 dark:text-slate-300">{group.ruleId}</span>
        {whole && <span className="font-mono text-slate-600 dark:text-slate-300">Solução inteira</span>}
      </div>
      <p className="mt-1">{group.message}</p>
      {!whole && (
        <>
          <div className="mt-2 flex flex-wrap gap-1">
            {group.occurrences.map((item) => {
              const where = `Linha ${item.line}, coluna ${item.col}`;
              return onSelectLines ? (
                <LineChip
                  key={`${item.line}-${item.col}`}
                  onClick={() => onSelectLines(item.line, Math.max(item.line, item.end_line))}
                  aria-label={`${where}: selecionar no editor`}
                >
                  {where}
                </LineChip>
              ) : (
                <span key={`${item.line}-${item.col}`} className="font-mono text-xs text-slate-600 dark:text-slate-300">
                  {where}
                </span>
              );
            })}
          </div>
          {first !== undefined && <Snippet code={code} line={first.line} />}
        </>
      )}
    </Card>
  );
}

function SuccessResult({
  response,
  code,
  onSelectLines,
  headingRef,
}: {
  response: ValidateResponse;
  code: string | undefined;
  onSelectLines?: (first: number, last: number) => void;
  headingRef?: Ref<HTMLHeadingElement>;
}) {
  if (response.status === "syntax_error" && response.syntax_error !== null) {
    const { line, col, message } = response.syntax_error;
    return (
      <SyntaxErrorBox title="Erro de sintaxe" line={line} col={col} message={message} headingRef={headingRef}>
        {onSelectLines && (
          <LineChip mono={false} onClick={() => onSelectLines(line, line)} className="mt-2">
            Mostrar a linha {line} no editor
          </LineChip>
        )}
        <p className="mt-2 text-sm">Corrija a sintaxe: as permissões só são verificadas depois.</p>
      </SyntaxErrorBox>
    );
  }

  if (response.status === "valid") {
    return (
      <div>
        <h2 ref={headingRef} tabIndex={-1} className={`${HEADING} text-green-700 dark:text-green-300`}>
          Nenhuma violação encontrada
        </h2>
        <Notices response={response} />
        <RulesLine response={response} />
      </div>
    );
  }

  const count = response.violations.length;
  const groups = groupViolations(response.violations);
  return (
    <div>
      <h2 ref={headingRef} tabIndex={-1} className={`${HEADING} text-red-700 dark:text-red-300`}>
        {count === 1 ? "1 violação encontrada" : `${count} violações encontradas`}
      </h2>
      <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{summarize(response.violations)}</p>
      <ul className="mt-3 space-y-2">
        {groups.map((group) => (
          <RuleCard key={`${group.category}-${group.ruleId}-${group.message}`} group={group} code={code} onSelectLines={onSelectLines} />
        ))}
      </ul>
      {response.truncated && (
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          Mostrando as {count} primeiras violações. Corrija estas e verifique de novo.
        </p>
      )}
      <Notices response={response} />
      <RulesLine response={response} />
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
      <h2 className={HEADING}>{BUSY_TITLES[state.code] ?? "Serviço ocupado"}</h2>
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

function Content({ state, onRetry, code, onSelectLines, headingRef }: ResultPanelProps) {
  switch (state.kind) {
    case "idle":
      return <p className="text-slate-600 dark:text-slate-300">Cole o código, escolha a lista e clique em Verificar.</p>;
    case "loading":
      return <p className="text-slate-600 dark:text-slate-300">Verificando…</p>;
    case "success":
      return <SuccessResult response={state.response} code={code} onSelectLines={onSelectLines} headingRef={headingRef} />;
    case "rejected":
      return (
        <div>
          <h2 className={HEADING}>
            {state.code === "PAYLOAD_TOO_LARGE" ? "O código excede 50 KB" : "O código não pôde ser verificado"}
          </h2>
          <p className="mt-1">{state.message}</p>
        </div>
      );
    case "busy":
      // A chave recria a contagem a cada nova resposta 429 ou 503.
      return <BusyResult key={state.receivedAt} state={state} onRetry={onRetry} />;
    case "unauthenticated":
      return (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          A sua sessão terminou. Entre de novo para continuar.
        </p>
      );
    case "network":
    case "timeout":
      return (
        <div>
          <h2 className={HEADING}>Sem resposta do servidor</h2>
          <p className="mt-1">{state.message}</p>
          <RetryButton onRetry={onRetry} />
        </div>
      );
  }
}

export function ResultPanel(props: ResultPanelProps) {
  const { state, stale = false } = props;
  return (
    <Card aria-label="Resultado da verificação" aria-busy={state.kind === "loading"}>
      {/* Só o resumo vai para o leitor de tela; o relatório fica para ler no próprio ritmo. */}
      <p className="sr-only" aria-live="polite">
        {announcement(state)}
      </p>
      {stale && state.kind === "success" && (
        <p role="note" className="mb-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
          O código mudou desde a verificação: este resultado é do código anterior. Verifique de novo.
        </p>
      )}
      <Content {...props} />
    </Card>
  );
}

/** A versão das regras e, se houver, a questão cujas regras valeram (R-01). */
function RulesLine({ response }: { response: ValidateResponse }) {
  return (
    <p className="mt-3 text-xs text-slate-600 dark:text-slate-300">
      Regras {response.ruleset_version}
      {response.question_id !== null && ` · questão ${response.question_id}`}
    </p>
  );
}

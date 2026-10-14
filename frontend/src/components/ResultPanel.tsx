import { type Ref, useEffect, useId, useState } from "react";
import type { ValidationState } from "../hooks/useValidateCode";
import { BUSY_TITLES, CATEGORY_LABELS, NOTICE_TEXTS } from "../labels";
import { announcement, categoryCounts, groupViolations, type RuleGroup, snippetLines } from "../report";
import type { Category, ValidateResponse } from "../types/api";
import { Button, Card, Chip, Disclosure, LineChip, SyntaxErrorBox } from "./ui";

/** Até este número de regras, os cartões nascem abertos; acima, fechados (S37-01). */
export const OPEN_BY_DEFAULT = 5;

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

/** O trecho do código com a linha da violação em destaque (S26-03; o contexto desde a S37-01). */
function Snippet({ code, first, last }: { code: string | undefined; first: number; last: number }) {
  if (code === undefined) return null;
  const lines = snippetLines(code, first, last);
  if (lines.every((item) => item.text === "")) return null;
  return (
    <pre className="mt-2 overflow-x-auto rounded bg-slate-100 py-1 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-100">
      <code>
        {lines.map((item) => (
          <span
            key={item.line}
            data-marked={item.marked || undefined}
            className={`block px-2 ${item.marked ? "bg-amber-100 font-semibold dark:bg-amber-900/60" : ""}`}
          >
            <span className="mr-3 inline-block w-6 text-right text-slate-600 select-none dark:text-slate-300" aria-hidden="true">
              {item.line}
            </span>
            {item.text}
          </span>
        ))}
      </code>
    </pre>
  );
}

/**
 * Um cartão por regra (S37-01): a categoria, a regra e a mensagem sempre à vista; as linhas e o
 * trecho abrem e fecham. Uma exigência (R-02, R-68) fala da solução inteira e não tem o que abrir.
 */
function RuleCard({
  group,
  code,
  open,
  onToggle,
  onSelectLines,
}: {
  group: RuleGroup;
  code: string | undefined;
  open: boolean;
  onToggle: () => void;
  onSelectLines?: (first: number, last: number) => void;
}) {
  const bodyId = useId();
  const whole = group.category === "EXIGENCIA";
  const first = group.occurrences[0];
  const count = group.occurrences.length;
  const header = (
    <>
      <span className={`rounded px-2 py-0.5 text-sm font-medium ${CATEGORY_STYLES[group.category]}`}>{CATEGORY_LABELS[group.category]}</span>
      <span className="text-sm text-slate-600 dark:text-slate-300">{group.ruleId}</span>
      {whole ? (
        <span className="font-mono text-sm text-slate-600 dark:text-slate-300">Solução inteira</span>
      ) : (
        <span className="text-sm text-slate-600 dark:text-slate-300">{count === 1 ? "1 linha" : `${count} linhas`}</span>
      )}
      <span className="basis-full">{group.message}</span>
    </>
  );
  return (
    <Card as="li" padding="xs" className={`border-l-4 ${CARD_BORDERS[group.category]}`}>
      {whole ? (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">{header}</div>
      ) : (
        <Disclosure open={open} aria-controls={bodyId} onClick={onToggle}>
          {header}
        </Disclosure>
      )}
      {!whole && open && (
        <div id={bodyId}>
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
          {first !== undefined && <Snippet code={code} first={first.line} last={first.end_line} />}
        </div>
      )}
    </Card>
  );
}

const groupKey = (group: RuleGroup) => `${group.category}-${group.ruleId}-${group.message}`;

/**
 * O relatório das violações (S37-01): os contadores por categoria filtram os cartões; cada regra
 * é um cartão que abre e fecha, aberto por padrão até OPEN_BY_DEFAULT regras.
 */
function ViolationsReport({
  response,
  code,
  onSelectLines,
}: {
  response: ValidateResponse;
  code: string | undefined;
  onSelectLines?: (first: number, last: number) => void;
}) {
  const groups = groupViolations(response.violations);
  const counts = categoryCounts(response.violations);
  const [filter, setFilter] = useState<Category | null>(null);
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(groups.length <= OPEN_BY_DEFAULT ? groups.map(groupKey) : []),
  );
  const shown = groups.filter((group) => filter === null || group.category === filter);
  const collapsible = shown.filter((group) => group.category !== "EXIGENCIA");
  const allOpen = collapsible.every((group) => open.has(groupKey(group)));

  function toggle(key: string) {
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function setAll(value: boolean) {
    setOpen((current) => {
      const next = new Set(current);
      for (const group of collapsible) {
        if (value) next.add(groupKey(group));
        else next.delete(groupKey(group));
      }
      return next;
    });
  }

  return (
    <>
      <div role="group" aria-label="Filtrar por categoria" className="mt-2 flex flex-wrap items-center gap-2">
        {counts.map((item) => (
          <Chip
            key={item.category}
            aria-pressed={filter === item.category}
            onClick={() => setFilter(filter === item.category ? null : item.category)}
            className={CATEGORY_STYLES[item.category]}
          >
            {item.label}
          </Chip>
        ))}
        {filter !== null && (
          <Button variant="link" onClick={() => setFilter(null)}>
            Todas
          </Button>
        )}
      </div>
      {collapsible.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-x-3">
          <Button variant="link" onClick={() => setAll(!allOpen)}>
            {allOpen ? "Fechar todos" : "Abrir todos"}
          </Button>
        </div>
      )}
      <ul aria-label="Regras violadas" className="mt-2 space-y-1.5">
        {shown.map((group) => (
          <RuleCard
            key={groupKey(group)}
            group={group}
            code={code}
            open={open.has(groupKey(group))}
            onToggle={() => toggle(groupKey(group))}
            onSelectLines={onSelectLines}
          />
        ))}
      </ul>
    </>
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
  return (
    <div>
      <h2 ref={headingRef} tabIndex={-1} className={`${HEADING} text-red-700 dark:text-red-300`}>
        {count === 1 ? "1 violação encontrada" : `${count} violações encontradas`}
      </h2>
      {/* A chave recomeça o filtro e os cartões a cada verificação. */}
      <ViolationsReport key={response.request_id} response={response} code={code} onSelectLines={onSelectLines} />
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

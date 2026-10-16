import type { ClassComparison } from "../../hooks/useClassComparison";
import { MAX_CLASS } from "../../plagiarismClass";
import { CodeEditor } from "../CodeEditor";
import { Button, ErrorText } from "../ui";
import { ClassResult } from "./ClassResult";

interface ClassModeProps {
  group: ClassComparison;
  /** "Comparar lado a lado": leva a solução comparada e a da turma para "Dois códigos". */
  onSideBySide: (label: string) => void;
}

/** "Contra a turma" (S27-02): uma solução contra até 100 da turma, com o peso pela raridade. */
export function ClassMode({ group, onSideBySide }: ClassModeProps) {
  const { solutions, repeated } = group;
  return (
    <form onSubmit={(event) => void group.submit(event)} className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Solução comparada</h3>
          <CodeEditor
            value={group.target}
            onChange={group.setTarget}
            readOnly={group.loading}
            label="Solução comparada"
            placeholder="Cole aqui a solução que você quer comparar com a turma"
          />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="font-medium">Soluções da turma</h3>
          <CodeEditor
            value={group.classText}
            onChange={group.setClassText}
            readOnly={group.loading}
            label="Soluções da turma"
            placeholder={"=== Ana\nn = int(input())\n...\n=== Bruno\n..."}
            describedBy="turma-dica"
          />
          <p id="turma-dica" className="text-sm text-slate-600 dark:text-slate-300">
            Cada solução começa por uma linha <code>=== nome</code>. Até {MAX_CLASS} soluções, somando até 120 KB.{" "}
            {solutions.length === 1 ? "1 solução." : `${solutions.length} soluções.`}
          </p>
          {group.legacy && (
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
          {group.problem !== null && <ErrorText>{group.problem}</ErrorText>}
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={!group.ready}>
          {group.loading ? "Comparando…" : "Comparar com a turma"}
        </Button>
        {group.loading && (
          <Button variant="secondary" onClick={group.cancel}>
            Cancelar
          </Button>
        )}
      </div>
      <section aria-live="polite" aria-label="Resultado contra a turma" className="flex flex-col gap-3">
        {group.error !== null && <ErrorText>{group.error}</ErrorText>}
        {group.result !== null && <ClassResult response={group.result.response} onSideBySide={onSideBySide} />}
      </section>
    </form>
  );
}

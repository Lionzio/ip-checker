import { useState } from "react";
import { reportFileName, reportText } from "../report";
import type { ValidateResponse } from "../types/api";
import { Button } from "./ui";

interface ReportExportProps {
  response: ValidateResponse;
  /** "Lista 1: Comandos condicionais". */
  list: string;
  listNumber: number;
  questionId: string | null;
}

/**
 * Exportar o resultado (S38-03): copiar como texto ou baixar um .txt, com a lista, a questão, as
 * regras e as linhas, sem o código. Nada vai ao servidor: o arquivo é montado no navegador.
 */
export function ReportExport({ response, list, listNumber, questionId }: ReportExportProps) {
  const [status, setStatus] = useState<string | null>(null);
  const text = () => reportText(response, { list, questionId });

  async function copy() {
    try {
      await navigator.clipboard.writeText(text());
      setStatus("Relatório copiado.");
    } catch {
      setStatus("Não foi possível copiar. Use Baixar .txt.");
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([text()], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = reportFileName(listNumber, questionId);
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("Relatório baixado.");
  }

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Exportar o resultado">
      <Button variant="secondary" size="sm" onClick={() => void copy()}>
        Copiar o relatório
      </Button>
      <Button variant="secondary" size="sm" onClick={download}>
        Baixar .txt
      </Button>
      <span role="status" className="text-sm text-slate-600 dark:text-slate-300">
        {status}
      </span>
    </div>
  );
}

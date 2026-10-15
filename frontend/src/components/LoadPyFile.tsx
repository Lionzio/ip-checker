import { useRef } from "react";
import { readPythonFile } from "../pyFile";
import { Button } from "./ui";

interface LoadPyFileProps {
  /** O texto do arquivo vai para o editor. */
  onLoad: (text: string, name: string) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}

/** "Carregar .py" (S38-03): escolhe um arquivo do computador; arrastar para o editor também vale. */
export function LoadPyFile({ onLoad, onError, disabled = false }: LoadPyFileProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  async function chosen(files: FileList | null) {
    const file = files?.[0];
    if (file === undefined) return;
    const result = await readPythonFile(file);
    if (result.ok) onLoad(result.text, result.name);
    else onError(result.message);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".py,text/x-python,text/plain"
        aria-label="Arquivo .py para carregar no editor"
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => void chosen(event.target.files)}
      />
      <Button variant="link" onClick={() => inputRef.current?.click()} disabled={disabled}>
        Carregar .py
      </Button>
    </>
  );
}

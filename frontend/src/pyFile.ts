/**
 * Carregar um `.py` no editor (S38-03): só texto UTF-8 de até 50 KB, o mesmo limite da API
 * (FR-04). O arquivo é lido no navegador e vai para o editor; nada é enviado nem guardado até a
 * pessoa clicar em Verificar.
 */
export const MAX_FILE_BYTES = 51_200;

export type PyFileResult = { ok: true; text: string; name: string } | { ok: false; message: string };

const KB = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export async function readPythonFile(file: File): Promise<PyFileResult> {
  if (!/\.py$/i.test(file.name)) {
    return { ok: false, message: `"${file.name}" não é um arquivo .py.` };
  }
  if (file.size > MAX_FILE_BYTES) {
    return {
      ok: false,
      message: `"${file.name}" tem ${KB.format(file.size / 1024)} KB; o limite é 50 KB.`,
    };
  }
  const bytes = new Uint8Array(await file.arrayBuffer());
  let text: string;
  try {
    // Sem o BOM do UTF-8, que alguns editores do Windows põem no começo do arquivo.
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(bytes);
  } catch {
    return {
      ok: false,
      message: `"${file.name}" não está em UTF-8. Salve o arquivo como UTF-8 no seu editor e tente de novo.`,
    };
  }
  if (text.includes("\u0000")) {
    return { ok: false, message: `"${file.name}" não parece ser um arquivo de texto.` };
  }
  return { ok: true, text: text.replace(/\r\n?/g, "\n"), name: file.name };
}

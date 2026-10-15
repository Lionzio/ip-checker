/**
 * Os arquivos da turma (S40-01): vários `.py` ou um `.zip`, lidos no navegador. Nada vai ao
 * servidor nesta etapa; a página só manda à API os códigos que passaram dos limites, em partes.
 *
 * O `.zip` é lido aqui, e não na API, para que o servidor nunca descompacte nada (zip bomb): o
 * diretório central diz o tamanho de cada arquivo, e a descompressão para assim que passa dele ou
 * dos limites, mesmo que o diretório minta.
 */
import { MAX_FILE_BYTES } from "./pyFile";

export const MAX_FILES = 100;
export const MAX_TOTAL_BYTES = 2 * 1024 * 1024;
/** Um `.zip` maior que isto nem é aberto: os 2 MB descompactados cabem com folga. */
export const MAX_ZIP_BYTES = 4 * 1024 * 1024;

export interface ClassFile {
  /** O nome do arquivo, sem pastas: é como o aluno aparece na tabela. */
  name: string;
  code: string;
}

export interface ClassFiles {
  files: ClassFile[];
  /** O que ficou de fora e por quê, um aviso por arquivo (ou um só para o `.zip` inteiro). */
  skipped: string[];
}

const decoder = () => new TextDecoder("utf-8", { fatal: true, ignoreBOM: false });

function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

/** Lê os arquivos escolhidos (ou arrastados) e aplica os limites do lote. */
export async function readClassFiles(chosen: File[]): Promise<ClassFiles> {
  const files: ClassFile[] = [];
  const skipped: string[] = [];
  let total = 0;

  function add(name: string, bytes: Uint8Array) {
    if (files.length >= MAX_FILES) {
      skipped.push(`"${name}": a turma passa de ${MAX_FILES} arquivos.`);
      return;
    }
    if (bytes.length > MAX_FILE_BYTES) {
      skipped.push(`"${name}": passa de 50 KB.`);
      return;
    }
    if (total + bytes.length > MAX_TOTAL_BYTES) {
      skipped.push(`"${name}": a turma passa de 2 MB.`);
      return;
    }
    let code: string;
    try {
      code = decoder().decode(bytes);
    } catch {
      skipped.push(`"${name}": não está em UTF-8.`);
      return;
    }
    if (code.includes("\u0000")) {
      skipped.push(`"${name}": não é um arquivo de texto.`);
      return;
    }
    total += bytes.length;
    files.push({ name, code: code.replace(/\r\n?/g, "\n") });
  }

  for (const file of chosen) {
    if (/\.zip$/i.test(file.name)) {
      if (file.size > MAX_ZIP_BYTES) {
        skipped.push(`"${file.name}": o .zip passa de 4 MB.`);
        continue;
      }
      try {
        for (const entry of await unzip(new Uint8Array(await file.arrayBuffer()), file.name)) {
          if (entry.skipped !== undefined) skipped.push(entry.skipped);
          else add(entry.name, entry.bytes);
        }
      } catch (error) {
        skipped.push(`"${file.name}": ${error instanceof Error ? error.message : "não foi possível abrir o .zip."}`);
      }
    } else if (/\.py$/i.test(file.name)) {
      if (file.size > MAX_FILE_BYTES) skipped.push(`"${file.name}": passa de 50 KB.`);
      else add(file.name, new Uint8Array(await file.arrayBuffer()));
    } else {
      skipped.push(`"${file.name}": não é .py nem .zip.`);
    }
  }
  // Nomes repetidos (a mesma pasta em dois .zip) ganham um número, como no "Contra a turma".
  const seen = new Map<string, number>();
  for (const file of files) {
    const count = (seen.get(file.name) ?? 0) + 1;
    seen.set(file.name, count);
    if (count > 1) file.name = `${file.name} (${count})`;
  }
  return { files, skipped };
}

type ZipEntry = { name: string; bytes: Uint8Array; skipped?: undefined } | { skipped: string };

const EOCD = 0x06054b50;
const CENTRAL = 0x02014b50;
const LOCAL = 0x04034b50;

/** Lê os `.py` de um `.zip` (sem ZIP64 nem criptografia), parando em qualquer limite. */
export async function unzip(data: Uint8Array, zipName = "o .zip"): Promise<ZipEntry[]> {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  let end = -1;
  for (let at = data.length - 22; at >= Math.max(0, data.length - 22 - 65_535); at -= 1) {
    if (view.getUint32(at, true) === EOCD) {
      end = at;
      break;
    }
  }
  if (end < 0) throw new Error("não é um .zip válido.");
  const count = view.getUint16(end + 10, true);
  let at = view.getUint32(end + 16, true);
  const entries: ZipEntry[] = [];
  let declaredTotal = 0;
  for (let index = 0; index < count; index += 1) {
    if (at + 46 > data.length || view.getUint32(at, true) !== CENTRAL) throw new Error("o .zip está corrompido.");
    const flags = view.getUint16(at + 8, true);
    const method = view.getUint16(at + 10, true);
    const compressed = view.getUint32(at + 20, true);
    const size = view.getUint32(at + 24, true);
    const nameLength = view.getUint16(at + 28, true);
    const extraLength = view.getUint16(at + 30, true);
    const commentLength = view.getUint16(at + 32, true);
    const local = view.getUint32(at + 42, true);
    const path = new TextDecoder().decode(data.subarray(at + 46, at + 46 + nameLength));
    at += 46 + nameLength + extraLength + commentLength;

    const name = baseName(path);
    if (path.endsWith("/") || path.includes("__MACOSX") || name.startsWith(".")) continue;
    if (!/\.py$/i.test(name)) {
      entries.push({ skipped: `"${name}" (em ${zipName}): não é .py.` });
      continue;
    }
    if (flags & 1) {
      entries.push({ skipped: `"${name}" (em ${zipName}): está criptografado.` });
      continue;
    }
    if (size > MAX_FILE_BYTES) {
      entries.push({ skipped: `"${name}": passa de 50 KB.` });
      continue;
    }
    declaredTotal += size;
    if (declaredTotal > MAX_TOTAL_BYTES) {
      entries.push({ skipped: `"${name}": a turma passa de 2 MB.` });
      continue;
    }
    if (local + 30 > data.length || view.getUint32(local, true) !== LOCAL) throw new Error("o .zip está corrompido.");
    const start = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
    const raw = data.subarray(start, start + compressed);
    if (method === 0) {
      entries.push({ name, bytes: raw.subarray(0, size) });
    } else if (method === 8) {
      const bytes = await inflate(raw, size);
      entries.push(bytes === null ? { skipped: `"${name}": o conteúdo não bate com o tamanho declarado.` } : { name, bytes });
    } else {
      entries.push({ skipped: `"${name}" (em ${zipName}): compressão não suportada.` });
    }
  }
  return entries;
}

/** Descompacta (deflate) parando assim que passa do tamanho declarado: nunca guarda mais que ele. */
async function inflate(raw: Uint8Array, declared: number): Promise<Uint8Array | null> {
  const source = new ReadableStream<BufferSource>({
    start(controller) {
      controller.enqueue(raw as Uint8Array<ArrayBuffer>);
      controller.close();
    },
  });
  const stream = source.pipeThrough(new DecompressionStream("deflate-raw"));
  const reader = stream.getReader();
  const out = new Uint8Array(declared);
  let filled = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (filled + value.length > declared) {
        await reader.cancel();
        return null;
      }
      out.set(value, filled);
      filled += value.length;
    }
  } catch {
    return null;
  }
  return filled === declared ? out : null;
}

/** Divide a turma em partes de até 20 arquivos e até ~110 KB, abaixo da barreira de 128 KB. */
export function chunks(files: ClassFile[], maxFiles = 20, maxBytes = 110 * 1024): ClassFile[][] {
  const parts: ClassFile[][] = [];
  let current: ClassFile[] = [];
  let bytes = 0;
  const encoder = new TextEncoder();
  for (const file of files) {
    // O JSON escapa aspas, barras e quebras: o dobro do tamanho cobre o pior caso comum.
    const size = encoder.encode(file.code).length * 2 + encoder.encode(file.name).length + 64;
    if (current.length > 0 && (current.length >= maxFiles || bytes + size > maxBytes)) {
      parts.push(current);
      current = [];
      bytes = 0;
    }
    current.push(file);
    bytes += size;
  }
  if (current.length > 0) parts.push(current);
  return parts;
}

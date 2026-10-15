import { describe, expect, it } from "vitest";
import { chunks, MAX_FILES, readClassFiles, unzip } from "./classFiles";

/** Monta um .zip com entradas guardadas (método 0) ou comprimidas (8), como os do Windows. */
async function zip(entries: { name: string; text: string; deflate?: boolean; lieSize?: number }[]): Promise<Uint8Array> {
  const encoder = new TextEncoder();
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;
  for (const entry of entries) {
    const name = encoder.encode(entry.name);
    const raw = encoder.encode(entry.text);
    const body = entry.deflate
      ? new Uint8Array(
          await new Response(
            new ReadableStream<BufferSource>({
              start(controller) {
                controller.enqueue(raw);
                controller.close();
              },
            }).pipeThrough(new CompressionStream("deflate-raw")),
          ).arrayBuffer(),
        )
      : raw;
    const size = entry.lieSize ?? raw.length;
    const local = new Uint8Array(30 + name.length + body.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(8, entry.deflate ? 8 : 0, true);
    lv.setUint32(18, body.length, true);
    lv.setUint32(22, size, true);
    lv.setUint16(26, name.length, true);
    local.set(name, 30);
    local.set(body, 30 + name.length);
    const central = new Uint8Array(46 + name.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(10, entry.deflate ? 8 : 0, true);
    cv.setUint32(20, body.length, true);
    cv.setUint32(24, size, true);
    cv.setUint16(28, name.length, true);
    cv.setUint32(42, offset, true);
    central.set(name, 46);
    locals.push(local);
    centrals.push(central);
    offset += local.length;
  }
  const centralSize = centrals.reduce((sum, item) => sum + item.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, entries.length, true);
  ev.setUint16(10, entries.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);
  const all = [...locals, ...centrals, end];
  const out = new Uint8Array(all.reduce((sum, item) => sum + item.length, 0));
  let at = 0;
  for (const item of all) {
    out.set(item, at);
    at += item.length;
  }
  return out;
}

const file = (content: BlobPart | Uint8Array, name: string) => new File([content as BlobPart], name);

describe("Arquivos da turma (S40-01)", () => {
  it("lê .py soltos e os .py de um .zip, guardados ou comprimidos, sem as pastas", async () => {
    const archive = await zip([
      { name: "turma/ana.py", text: "x = 1\n" },
      { name: "turma/bruno.py", text: "print('olá')\r\n".repeat(50), deflate: true },
      { name: "turma/", text: "" },
      { name: "__MACOSX/turma/._ana.py", text: "lixo" },
      { name: "turma/notas.txt", text: "não é código" },
    ]);

    const result = await readClassFiles([file(archive, "lista3.zip"), file("y = 2\n", "carla.py")]);

    expect(result.files.map((item) => item.name)).toEqual(["ana.py", "bruno.py", "carla.py"]);
    expect(result.files[1]?.code).toBe("print('olá')\n".repeat(50));
    expect(result.skipped).toEqual(['"notas.txt" (em lista3.zip): não é .py.']);
  });

  it("um .zip que mente o tamanho (zip bomb) é recusado sem descompactar além do declarado", async () => {
    const bomb = await zip([{ name: "bomba.py", text: "x = 1\n".repeat(20_000), deflate: true, lieSize: 100 }]);

    const entries = await unzip(bomb);

    expect(entries).toEqual([{ skipped: '"bomba.py": o conteúdo não bate com o tamanho declarado.' }]);
  });

  it("aplica os limites de 50 KB por arquivo, 100 arquivos e UTF-8", async () => {
    const many = Array.from({ length: MAX_FILES + 2 }, (_, index) => file(`x = ${index}\n`, `a${index}.py`));
    const result = await readClassFiles([
      ...many,
      file("x".repeat(51_201), "grande.py"),
      file(new Uint8Array([0x78, 0xe9]), "latin1.py"),
      file("foto", "foto.png"),
    ]);

    expect(result.files).toHaveLength(MAX_FILES);
    expect(result.skipped).toContain('"a100.py": a turma passa de 100 arquivos.');
    expect(result.skipped).toContain('"grande.py": passa de 50 KB.');
    expect(result.skipped).toContain('"latin1.py": a turma passa de 100 arquivos.');
    expect(result.skipped).toContain('"foto.png": não é .py nem .zip.');
  });

  it("recusa arquivo que não é UTF-8 e numera nomes repetidos", async () => {
    const result = await readClassFiles([
      file(new Uint8Array([0x78, 0xe9]), "latin1.py"),
      file("x = 1\n", "ana.py"),
      file("x = 2\n", "ana.py"),
    ]);

    expect(result.skipped).toEqual(['"latin1.py": não está em UTF-8.']);
    expect(result.files.map((item) => item.name)).toEqual(["ana.py", "ana.py (2)"]);
  });

  it("um arquivo que não é .zip de verdade vira aviso, não erro", async () => {
    const result = await readClassFiles([file("não sou zip", "falso.zip")]);

    expect(result.files).toEqual([]);
    expect(result.skipped).toEqual(['"falso.zip": não é um .zip válido.']);
  });

  it("divide a turma em partes de até 20 arquivos e abaixo de 128 KB", () => {
    const small = Array.from({ length: 45 }, (_, index) => ({ name: `${index}.py`, code: "x = 1\n" }));
    expect(chunks(small).map((part) => part.length)).toEqual([20, 20, 5]);

    const big = Array.from({ length: 3 }, (_, index) => ({ name: `${index}.py`, code: "x".repeat(40_000) }));
    expect(chunks(big).map((part) => part.length)).toEqual([1, 1, 1]);
  });
});

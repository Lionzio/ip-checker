import { describe, expect, it } from "vitest";
import { MAX_FILE_BYTES, readPythonFile } from "./pyFile";

const file = (content: BlobPart, name = "solucao.py") => new File([content], name);

describe("Carregar .py (S38-03)", () => {
  it("lê um .py em UTF-8, com acentos, e troca as quebras do Windows", async () => {
    expect(await readPythonFile(file("nome = input()\r\nprint('olá')\r\n"))).toEqual({
      ok: true,
      text: "nome = input()\nprint('olá')\n",
      name: "solucao.py",
    });
  });

  it("tira o BOM do UTF-8", async () => {
    const result = await readPythonFile(file(new Uint8Array([0xef, 0xbb, 0xbf, 0x78, 0x0a])));
    expect(result).toMatchObject({ ok: true, text: "x\n" });
  });

  it("recusa arquivo maior que 50 KB", async () => {
    const result = await readPythonFile(file("x".repeat(MAX_FILE_BYTES + 1)));
    expect(result).toEqual({ ok: false, message: '"solucao.py" tem 50 KB; o limite é 50 KB.' });
  });

  it("aceita exatamente 50 KB", async () => {
    expect((await readPythonFile(file("x".repeat(MAX_FILE_BYTES)))).ok).toBe(true);
  });

  it("recusa encoding que não é UTF-8", async () => {
    const latin1 = new Uint8Array([0x70, 0x72, 0x69, 0x6e, 0x74, 0x28, 0x27, 0xe9, 0x27, 0x29]);
    const result = await readPythonFile(file(latin1));
    expect(result).toMatchObject({ ok: false, message: expect.stringContaining("não está em UTF-8") });
  });

  it("recusa o que não é .py e o que não é texto", async () => {
    expect(await readPythonFile(file("x", "foto.png"))).toMatchObject({ ok: false, message: expect.stringContaining("não é um arquivo .py") });
    expect(await readPythonFile(file(new Uint8Array([0x78, 0x00, 0x79])))).toMatchObject({ ok: false, message: expect.stringContaining("texto") });
  });
});

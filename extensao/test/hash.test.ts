import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { hashDoConteudo, jsonCanonico, normalizarTexto } from "../src/catalogo/hash";

interface Vetor {
  nome: string;
  questao: {
    title: string;
    description: string;
    input_description: string;
    output_description: string;
    samples: { input: string; output: string }[];
  };
  hash: string;
}

const vetores = (
  JSON.parse(readFileSync(new URL("./vetores-hash.json", import.meta.url), "utf8")) as {
    vetores: Vetor[];
  }
).vetores;

describe("o hash do enunciado (o mesmo da API)", () => {
  it.each(vetores.map((v) => [v.nome, v] as const))("%s", async (_nome, vetor) => {
    expect(await hashDoConteudo(vetor.questao)).toBe(vetor.hash);
  });

  it("tem os casos que importam para as duas linguagens", () => {
    expect(vetores.length).toBeGreaterThanOrEqual(8);
  });
});

describe("a normalização", () => {
  it("troca CRLF e CR por LF e tira os espaços do fim das linhas e das pontas", () => {
    expect(normalizarTexto(" a  \r\nb\t\r c \n")).toBe("a\nb\n c");
  });

  it("junta os acentos em NFC", () => {
    expect(normalizarTexto("número")).toBe("número");
  });

  it("não tira o espaço inquebrável, que o Python também não tira", () => {
    expect(normalizarTexto(" x ")).toBe(" x ");
  });

  it("não trata U+2028 como quebra de linha", () => {
    expect(normalizarTexto("a  b")).toBe("a  b");
  });

  it("escreve o JSON com as chaves em ordem e os acentos sem escape", () => {
    expect(
      jsonCanonico({
        title: "T ",
        description: "Dê",
        input_description: "E",
        output_description: "S",
        samples: [{ input: "1\n", output: "2" }],
      }),
    ).toBe(
      '{"description":"Dê","input_description":"E","output_description":"S",' +
        '"samples":[{"input":"1","output":"2"}],"title":"T"}',
    );
  });
});

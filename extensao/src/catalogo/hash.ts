// O hash do enunciado (S50-03): a mesma regra de backend/src/ipc_api/importing/hashing.py, com os
// mesmos casos (test/vetores-hash.json). A API recalcula e recusa o que não bate.
//
// Cada texto em NFC, com \r\n e \r trocados por \n, os espaços e tabs do fim de cada linha
// removidos e o texto sem espaço, tab ou quebra de linha nas pontas (só esses três: o trim() do
// JavaScript tiraria outros). Depois, o JSON com as chaves em ordem e sem espaços, em UTF-8, e o
// SHA-256 em hexadecimal.

export interface TextosDaQuestao {
  title: string;
  description: string;
  input_description: string;
  output_description: string;
  samples: { input: string; output: string }[];
}

export function normalizarTexto(texto: string): string {
  return (
    texto
      .normalize("NFC")
      .replace(/\r\n?/g, "\n")
      // Sem a flag m: o $ do JavaScript com m também casaria antes de U+2028 e U+2029.
      .replace(/[ \t]+(?=\n|$)/g, "")
      .replace(/^[ \t\n]+|[ \t\n]+$/g, "")
  );
}

/** O JSON canônico: as chaves em ordem alfabética, como o sort_keys do Python. */
export function jsonCanonico(q: TextosDaQuestao): string {
  return JSON.stringify({
    description: normalizarTexto(q.description),
    input_description: normalizarTexto(q.input_description),
    output_description: normalizarTexto(q.output_description),
    samples: q.samples.map((s) => ({
      input: normalizarTexto(s.input),
      output: normalizarTexto(s.output),
    })),
    title: normalizarTexto(q.title),
  });
}

export async function hashDoConteudo(q: TextosDaQuestao): Promise<string> {
  const bytes = new TextEncoder().encode(jsonCanonico(q));
  const resumo = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(resumo)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

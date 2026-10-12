/**
 * O termo técnico de cada construção que o motor mostra em português (S36-04). A página exibe o
 * nome em português e deixa o termo do Python na dica, para quem quiser procurar a documentação.
 * Os nomes vêm de `backend/src/ipc_analyzer/engine/display.py`; um nome sem termo aqui fica sem dica.
 */
export const CONSTRUCT_TERMS: Readonly<Record<string, string>> = {
  atribuição: "Assign",
  "atribuição composta (+=, -=...)": "AugAssign",
  "atribuição com anotação de tipo": "AnnAssign",
  "conta aritmética": "BinOp",
  "operador lógico (and, or)": "BoolOp",
  comparação: "Compare",
  "operador unário (-, not)": "UnaryOp",
  "f-string": "JoinedStr",
  "valor dentro de f-string": "FormattedValue",
  "operador ternário": "IfExp",
  indexação: "Subscript",
  fatiamento: "Slice",
  lista: "List",
  tupla: "Tuple",
  dicionário: "Dict",
  "expressão geradora": "GeneratorExp",
  "chamada de função": "Call",
  "retorno de vários valores": "Return (tupla)",
  "desempacotamento no for": "For (vários alvos)",
  recursão: "chamada recursiva",
};

export function constructHint(name: string): string | undefined {
  const term = CONSTRUCT_TERMS[name];
  return term === undefined ? undefined : `Termo técnico: ${term}`;
}

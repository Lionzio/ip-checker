// Respostas sintéticas do Dikastis, montadas a partir de docs/api-dikastis.md: só os formatos
// são os de lá; ids, nomes e textos são inventados. Nenhum dado de aluno (os "members" da turma
// existem só para provar que a extensão os ignora).

export const ORG = "ORG-IP";
/** Um texto que nunca pode sair do script da página: o de um caso oculto. */
export const CASO_OCULTO = "CANARIO-CASO-OCULTO-7f3a";

export const organizacao = {
  id: ORG,
  name: "Introdução à Programação",
  teams: [
    { id: "TURMA-SI", name: "IP SI UFPE 2026.2" },
    { id: "TURMA-EC", name: "IP EC UFPE 2026.2 " },
    { id: "TURMA-VELHA", name: "IP SI UFPE 2025.1" },
    { id: "TURMA-SEM-PERIODO", name: "Monitoria" },
  ],
};

function turma(id: string, prefixo: string) {
  return {
    id,
    name: `IP ${prefixo} UFPE 2026.2`,
    members: [{ id: "PESSOA-1", name: "Pessoa Inventada", email: "pessoa@exemplo.invalid" }],
    tasks: [
      { id: `${prefixo}-L1`, title: "Lista 1" },
      { id: `${prefixo}-L2`, title: "Lista 2 - Laços" },
      { id: `${prefixo}-TR`, title: "Lista de Treinamento" },
      { id: `${prefixo}-AV`, title: "Avisos da disciplina" },
    ],
  };
}

export const turmas = { "TURMA-SI": turma("TURMA-SI", "SI"), "TURMA-EC": turma("TURMA-EC", "EC") };

function problemaDaTarefa(id: string, title: string, order: string) {
  return { order, weight: 1, problem: { id, title } };
}

function tarefa(title: string, problemas: ReturnType<typeof problemaDaTarefa>[]) {
  return {
    id: "ignorado",
    title,
    beginTime: "2026-10-01T03:00:00.000Z",
    endTime: "2026-10-08T02:59:00.000Z",
    description: "Texto da tarefa (não usado).",
    problems: problemas,
  };
}

const lista1 = () =>
  tarefa("Lista 1", [
    problemaDaTarefa("PROB-L1Q1", "26.2L1Q1 - Questão 1", "A"),
    problemaDaTarefa("PROB-L1Q2", "26.2L1Q2 -⏳Questão 2", "B"),
    problemaDaTarefa("PROB-VELHO", "20.2L1Q01 - Questão de outro período", "C"),
  ]);

export const tarefas: Record<string, unknown> = {
  "SI-L1": lista1(),
  // A outra turma tem a própria tarefa, com os mesmos problemas.
  "EC-L1": lista1(),
  "SI-L2": tarefa("Lista 2 - Laços", [
    problemaDaTarefa("PROB-L2Q1", "26.2L2Q1👮 Questão 3", "A"),
  ]),
  // Na EC, a L2-Q1 é outra cópia do problema (outro id), com o mesmo título.
  "EC-L2": tarefa("Lista 2 - Laços", [
    problemaDaTarefa("PROB-L2Q1-EC", "26.2L2Q1👮 Questão 3", "A"),
  ]),
  "SI-TR": tarefa("Lista de Treinamento", [
    problemaDaTarefa("PROB-TREINO", "Aquecimento", "A"),
  ]),
  "EC-TR": tarefa("Lista de Treinamento", []),
};

function problema(title: string, descricao: string) {
  return {
    id: "ignorado",
    title,
    description: descricao,
    inputDescription: "Um inteiro N.",
    outputDescription: "O mesmo N.",
    timeLimit: 1,
    memoryLimit: 256,
    testCases: [
      { displayId: 1, input: "1\n", output: "1\n", isSample: true },
      { displayId: 2, input: CASO_OCULTO, output: CASO_OCULTO, isSample: false },
      { displayId: 3, input: "2", output: "2", isSample: true },
    ],
  };
}

export const problemas: Record<string, unknown> = {
  "PROB-L1Q1": problema("26.2L1Q1 - Questão 1", "Leia N e imprima N."),
  "PROB-L1Q2": problema("26.2L1Q2 -⏳Questão 2", "Leia N e imprima o dobro de N."),
  "PROB-L2Q1": problema("26.2L2Q1👮 Questão 3", "Leia N e imprima N vezes."),
  "PROB-L2Q1-EC": problema("26.2L2Q1👮 Questão 3", "Cópia da EC."),
};

/** As rotas do Dikastis falso, por caminho. */
export function rotasDoDikastis(
  mudar: { problemas?: Record<string, unknown> } = {},
): Record<string, unknown> {
  const rotas: Record<string, unknown> = { [`/api/organizations/${ORG}`]: organizacao };
  for (const [id, corpo] of Object.entries(turmas)) rotas[`/api/teams/${id}`] = corpo;
  for (const [id, corpo] of Object.entries(tarefas)) rotas[`/api/tasks/${id}`] = corpo;
  for (const [id, corpo] of Object.entries({ ...problemas, ...mudar.problemas })) {
    rotas[`/api/problems/${id}`] = corpo;
  }
  return rotas;
}

/** Os títulos das 28 questões de 2026.2 (L1 a L4), só no formato: "26.2L1Q1 - Questão 1". */
export const TITULOS_2026_2 = [7, 7, 7, 7].flatMap((quantas, i) =>
  Array.from({ length: quantas }, (_, j) => `26.2L${i + 1}Q${j + 1} - Questão ${j + 1}`),
);

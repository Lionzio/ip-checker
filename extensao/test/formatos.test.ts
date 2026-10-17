import { describe, expect, it } from "vitest";

import { FormatoDesconhecido } from "../src/dikastis/erros";
import {
  validarOrganizacao,
  validarProblema,
  validarTarefa,
  validarTurma,
} from "../src/dikastis/formatos";
import { CASO_OCULTO, organizacao, problemas, tarefas, turmas } from "./respostas/dikastis";

const erro = (f: () => unknown) => {
  try {
    f();
  } catch (e) {
    return e as FormatoDesconhecido;
  }
  throw new Error("não lançou");
};

describe("os formatos do Dikastis", () => {
  it("lê as turmas da organização", () => {
    expect(validarOrganizacao(organizacao, "/api/organizations/X")[0]).toEqual({
      id: "TURMA-SI",
      nome: "IP SI UFPE 2026.2",
    });
  });

  it("lê as tarefas da turma e ignora os membros", () => {
    const lidas = validarTurma(turmas["TURMA-SI"], "/api/teams/X");

    expect(lidas.map((t) => t.titulo)).toEqual([
      "Lista 1",
      "Lista 2 - Laços",
      "Lista de Treinamento",
      "Avisos da disciplina",
    ]);
    expect(JSON.stringify(lidas)).not.toContain("Pessoa Inventada");
  });

  it("lê a tarefa com as datas em ISO e os problemas", () => {
    const tarefa = validarTarefa(tarefas["SI-L1"], "/api/tasks/X");

    expect(tarefa.inicio).toBe("2026-10-01T03:00:00.000Z");
    expect(tarefa.problemas[0]).toEqual({ id: "PROB-L1Q1", titulo: "26.2L1Q1 - Questão 1" });
    expect(validarTarefa({ title: "T", problems: [] }, "/x")).toMatchObject({
      inicio: null,
      fim: null,
    });
  });

  it("lê o problema só com os casos de exemplo", () => {
    const problema = validarProblema(problemas["PROB-L1Q1"], "/api/problems/X");

    expect(problema.exemplos).toEqual([
      { entrada: "1\n", saida: "1\n" },
      { entrada: "2", saida: "2" },
    ]);
    expect(JSON.stringify(problema)).not.toContain(CASO_OCULTO);
    expect(problema.limiteTempo).toBe(1);
  });

  it("aceita descrições nulas e o limite de tempo ausente", () => {
    const problema = validarProblema(
      { title: "T", description: null, testCases: [] },
      "/api/problems/X",
    );

    expect(problema).toMatchObject({ descricao: "", descricaoEntrada: "", limiteTempo: null });
  });

  it.each([
    [() => validarOrganizacao([], "/api/organizations/X"), "(resposta)", "um objeto"],
    [() => validarOrganizacao({ turmas: [] }, "/api/organizations/X"), "teams", "uma lista"],
    [() => validarOrganizacao({ teams: [{ id: 1, name: "x" }] }, "/o"), "teams[0].id", "um texto"],
    [() => validarTurma({ tasks: [null] }, "/t"), "tasks[0]", "um objeto"],
    [() => validarTarefa({ title: "T", beginTime: "ontem", problems: [] }, "/t"), "beginTime", "uma data"],
    [() => validarTarefa({ title: "T", problems: [{ problem: "x" }] }, "/t"), "problems[0].problem", "um objeto"],
    [() => validarProblema({ title: "T", testCases: [{ input: "1" }] }, "/p"), "testCases[0].isSample", "verdadeiro ou falso"],
    [() => validarProblema({ title: "T", timeLimit: "1s", testCases: [] }, "/p"), "timeLimit", "um número"],
    [() => validarProblema({ title: "T", description: 3, testCases: [] }, "/p"), "description", "um texto"],
    [() => validarProblema({ title: "T", testCases: [{ isSample: true, input: 1 }] }, "/p"), "testCases[0].input", "um texto"],
  ])("um campo mudado para limpo: %#", (f, campo, esperado) => {
    const e = erro(f);

    expect(e).toBeInstanceOf(FormatoDesconhecido);
    expect([e.campo, e.esperado]).toEqual([campo, esperado]);
    expect(e.message).toContain("Nada foi enviado");
  });
});

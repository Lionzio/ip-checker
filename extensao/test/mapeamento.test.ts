import { describe, expect, it } from "vitest";

import {
  cursoDaTurma,
  limiteEmMs,
  periodoAPartirDe,
  periodoDaTurma,
  questaoDoTitulo,
  tipoDaTarefa,
  tituloSemPrefixo,
} from "../src/catalogo/mapeamento";
import { TITULOS_2026_2 } from "./respostas/dikastis";

describe("as turmas", () => {
  it("tiram o período do fim do nome", () => {
    expect(periodoDaTurma("IP SI UFPE 2026.2")).toBe("2026.2");
    expect(periodoDaTurma("IP EC UFPE 2027.1  ")).toBe("2027.1");
    expect(periodoDaTurma("IP 2026.2 SI")).toBeNull();
    expect(periodoDaTurma("Monitoria")).toBeNull();
  });

  it("só entram de 2026.2 em diante", () => {
    expect(periodoAPartirDe("2026.2", "2026.2")).toBe(true);
    expect(periodoAPartirDe("2027.1", "2026.2")).toBe(true);
    expect(periodoAPartirDe("2026.1", "2026.2")).toBe(false);
  });

  it.each([
    ["IP SI UFPE 2026.2", "SI"],
    ["IP EC UFPE 2026.2", "EC"],
    ["IP CC/IA UFPE 2026.2", "CC/IA"],
    ["IP CC / IA UFPE 2026.2", "CC/IA"],
    ["IP IA UFPE 2026.2", "CC/IA"],
    ["IP CC UFPE 2026.2", "CC"],
    ["IP UFPE 2026.2", "outro"],
    ["IP SISTEMAS 2026.2", "outro"],
  ])("%s é do curso %s", (nome, curso) => {
    expect(cursoDaTurma(nome)).toBe(curso);
  });
});

describe("as tarefas", () => {
  it.each([
    ["Lista de Treinamento", { tipo: "treino", numero: null }],
    ["lista de treinamento 2", { tipo: "treino", numero: null }],
    ["Lista 1", { tipo: "lista", numero: 1 }],
    ["Lista 12 - Recursão", { tipo: "lista", numero: 12 }],
    ["Prova 2", { tipo: "prova", numero: 2 }],
    ["Lista 21", null],
    ["Lista 0", null],
    ["Listão", null],
    ["Avisos", null],
  ])("%s", (titulo, esperado) => {
    expect(tipoDaTarefa(titulo)).toEqual(esperado);
  });
});

describe("as questões", () => {
  it.each([
    ["26.2L1Q1 - Eco", "2026.2", "L1-Q1"],
    ["26.2L3Q8👮 Polícia", "2026.2", "L3-Q8"],
    ["26.2L2Q6 -⏳Tempo", "2026.2", "L2-Q6"],
    ["20.2L1Q01 - Antiga", "2020.2", "L1-Q1"],
    ["26.2 L4 Q10 - Espaços", "2026.2", "L4-Q10"],
    ["26.2P1Q2 - Prova", "2026.2", "P1-Q2"],
  ])("%s → %s %s", (titulo, periodo, id) => {
    expect(questaoDoTitulo(titulo)).toEqual({ periodo, id });
  });

  it("recusam o que não segue o padrão", () => {
    for (const titulo of ["Aquecimento", "26.3L1Q1", "26.2L0Q1", "26.2L1Q0", "L1Q1 - x"]) {
      expect(questaoDoTitulo(titulo)).toBeNull();
    }
  });

  it("as 28 questões de 2026.2 viram L1-Q1 a L4-Q7, sem repetir", () => {
    const ids = TITULOS_2026_2.map((t) => questaoDoTitulo(t)?.id);

    expect(new Set(ids).size).toBe(28);
    expect(ids.slice(0, 2)).toEqual(["L1-Q1", "L1-Q2"]);
    expect(ids.at(-1)).toBe("L4-Q7");
  });

  it("perdem o prefixo no título", () => {
    expect(tituloSemPrefixo("26.2L1Q1 - Eco")).toBe("Eco");
    expect(tituloSemPrefixo("26.2L2Q6 -⏳Tempo")).toBe("⏳Tempo");
    expect(tituloSemPrefixo("26.2L3Q8👮 Polícia")).toBe("👮 Polícia");
    expect(tituloSemPrefixo("26.2L1Q1")).toBe("26.2L1Q1");
    expect(tituloSemPrefixo("Sem prefixo")).toBe("Sem prefixo");
  });
});

describe("o limite de tempo", () => {
  it("até 60 é em segundos; acima, em milissegundos", () => {
    expect(limiteEmMs(1)).toBe(1000);
    expect(limiteEmMs(2.5)).toBe(2500);
    expect(limiteEmMs(1500)).toBe(1500);
    expect(limiteEmMs(null)).toBeNull();
    expect(limiteEmMs(-1)).toBeNull();
    expect(limiteEmMs(10_000_000)).toBeNull();
  });
});

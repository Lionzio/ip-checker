import { describe, expect, it } from "vitest";

import { SemTurmas, lerCatalogo } from "../src/catalogo/descoberta";
import { ClienteDikastis } from "../src/dikastis/cliente";
import { FormatoDesconhecido } from "../src/dikastis/erros";
import { RelogioFalso, fetchFalso } from "./apoio";
import { CASO_OCULTO, ORG, organizacao, rotasDoDikastis } from "./respostas/dikastis";

function dikastis(rotas = rotasDoDikastis()) {
  const relogio = new RelogioFalso();
  const fetch = fetchFalso(rotas, relogio);
  const cliente = new ClienteDikastis({ token: "tk", fetch, relogio });
  return { cliente, fetch, relogio };
}

describe("a descoberta no Dikastis", () => {
  it("lê as turmas do período, as listas e as questões", async () => {
    const { cliente } = dikastis();

    const catalogo = await lerCatalogo(cliente, { organizacao: ORG });

    expect(catalogo.periodo).toBe("2026.2");
    expect(catalogo.turmas).toEqual([
      { id: "TURMA-SI", nome: "IP SI UFPE 2026.2", curso: "SI" },
      { id: "TURMA-EC", nome: "IP EC UFPE 2026.2", curso: "EC" },
    ]);
    expect(catalogo.listas.map((l) => [l.turmaId, l.tipo, l.numero])).toEqual([
      ["TURMA-SI", "lista", 1],
      ["TURMA-SI", "lista", 2],
      ["TURMA-SI", "treino", null],
      ["TURMA-EC", "lista", 1],
      ["TURMA-EC", "lista", 2],
      ["TURMA-EC", "treino", null],
    ]);
    expect(catalogo.questoes.map((q) => [q.questaoId, q.titulo, q.limiteTempoMs])).toEqual([
      ["L1-Q1", "Questão 1", 1000],
      ["L1-Q2", "⏳Questão 2", 1000],
      ["L2-Q1", "👮 Questão 3", 1000],
    ]);
    // Período antigo, sem período; "Avisos" nas duas turmas; o de 2020.2 nas duas Listas 1 e o
    // "Aquecimento" do treino.
    expect(catalogo.ignorados).toEqual({ turmas: 2, tarefas: 2, problemas: 3 });
  });

  it("lê cada problema uma vez, mesmo em várias turmas, e ignora a cópia da outra turma", async () => {
    const { cliente, fetch } = dikastis();

    const catalogo = await lerCatalogo(cliente, { organizacao: ORG });

    const lidos = fetch.pedidos.filter((p) => p.url.includes("/problems/")).map((p) => p.url);
    expect(lidos).toHaveLength(3);
    expect(lidos.some((u) => u.endsWith("PROB-L2Q1-EC"))).toBe(false);
    const l2DaEc = catalogo.listas.find((l) => l.turmaId === "TURMA-EC" && l.numero === 2);
    expect(l2DaEc?.questoes.map((q) => q.problemaId)).toEqual(["PROB-L2Q1"]);
  });

  it("nunca pede placar, submissões ou pessoas", async () => {
    const { cliente, fetch } = dikastis();

    await lerCatalogo(cliente, { organizacao: ORG });

    for (const pedido of fetch.pedidos) {
      expect(pedido.url).toMatch(/\/api\/(organizations|teams|tasks|problems)\/[\w-]+$/);
    }
  });

  it("não deixa sair nenhum caso oculto nem dado de pessoa", async () => {
    const { cliente } = dikastis();

    const texto = JSON.stringify(await lerCatalogo(cliente, { organizacao: ORG }));

    expect(texto).not.toContain(CASO_OCULTO);
    expect(texto).not.toContain("Pessoa Inventada");
    expect(texto).not.toContain("exemplo.invalid");
  });

  it("os casos de exemplo e o hash vêm de cada questão", async () => {
    const { cliente } = dikastis();

    const [primeira] = (await lerCatalogo(cliente, { organizacao: ORG })).questoes;

    expect(primeira?.exemplos).toEqual([
      { entrada: "1\n", saida: "1\n" },
      { entrada: "2", saida: "2" },
    ]);
    expect(primeira?.hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it("um enunciado diferente dá outro hash", async () => {
    const antes = (await lerCatalogo(dikastis().cliente, { organizacao: ORG })).questoes[0];
    const mudado = rotasDoDikastis({
      problemas: {
        "PROB-L1Q1": {
          title: "26.2L1Q1 - Questão 1",
          description: "Leia N e imprima N + 1.",
          testCases: [],
        },
      },
    });

    const depois = (await lerCatalogo(dikastis(mudado).cliente, { organizacao: ORG })).questoes[0];

    expect(depois?.hash).not.toBe(antes?.hash);
  });

  it("fica no período mais recente quando há dois", async () => {
    const rotas = rotasDoDikastis();
    rotas[`/api/organizations/${ORG}`] = {
      teams: [...organizacao.teams, { id: "TURMA-NOVA", name: "IP SI UFPE 2027.1" }],
    };
    rotas["/api/teams/TURMA-NOVA"] = { tasks: [] };

    const catalogo = await lerCatalogo(dikastis(rotas).cliente, { organizacao: ORG });

    expect(catalogo.periodo).toBe("2027.1");
    expect(catalogo.turmas.map((t) => t.id)).toEqual(["TURMA-NOVA"]);
    expect(catalogo.questoes).toEqual([]);
  });

  it("sem turma do período, para com uma mensagem clara", async () => {
    const rotas = { [`/api/organizations/${ORG}`]: { teams: [{ id: "V", name: "IP 2025.2" }] } };

    await expect(lerCatalogo(dikastis(rotas).cliente, { organizacao: ORG })).rejects.toThrow(
      SemTurmas,
    );
  });

  it("um formato mudado para a leitura inteira", async () => {
    const rotas = rotasDoDikastis({ problemas: { "PROB-L1Q2": { title: "x" } } });

    await expect(lerCatalogo(dikastis(rotas).cliente, { organizacao: ORG })).rejects.toThrow(
      FormatoDesconhecido,
    );
  });
});

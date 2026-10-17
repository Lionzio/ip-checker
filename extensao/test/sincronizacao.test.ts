import { describe, expect, it } from "vitest";

import { type Catalogo, lerCatalogo } from "../src/catalogo/descoberta";
import { ClienteDikastis } from "../src/dikastis/cliente";
import {
  ClienteIpChecker,
  IpCheckerIndisponivel,
  RecusadoPeloIpChecker,
  TokenRecusado,
} from "../src/ipchecker/cliente";
import { dividirEmPartes, montarManifesto, questaoParaApi } from "../src/sincronizacao/manifesto";
import { NadaParaEnviar, Sincronizacao } from "../src/sincronizacao/sincronizar";
import { IpCheckerFalso, RelogioFalso, fetchFalso, json } from "./apoio";
import { CASO_OCULTO, ORG, rotasDoDikastis } from "./respostas/dikastis";

const ENDERECO = "https://ip-checker.exemplo.invalid";
const TOKEN = "ipc_imp_token-de-teste-com-tamanho";

async function catalogo(mudar: Parameters<typeof rotasDoDikastis>[0] = {}): Promise<Catalogo> {
  const relogio = new RelogioFalso();
  const fetch = fetchFalso(rotasDoDikastis(mudar), relogio);
  return lerCatalogo(new ClienteDikastis({ token: "tk", fetch, relogio }), { organizacao: ORG });
}

function montar(servidor = new IpCheckerFalso()) {
  const fetch = fetchFalso(servidor.rotas());
  const cliente = new ClienteIpChecker({ endereco: `${ENDERECO}/`, token: TOKEN, fetch });
  const sincronizacao = new Sincronizacao(
    async () => cliente,
    () => new Date("2026-10-16T12:00:00Z"),
  );
  return { servidor, fetch, sincronizacao };
}

describe("a sincronização", () => {
  it("verifica, envia só o que falta e, na segunda vez, não acha nada novo", async () => {
    const { servidor, sincronizacao } = montar();
    const lido = await catalogo();

    const resumo = await sincronizacao.verificar("manual", async () => lido);

    expect(resumo).toEqual({
      periodo: "2026.2",
      listas: 3,
      questoes: 3,
      novasOuAlteradas: 3,
      iguais: 0,
      sumidas: 0,
      ignorados: { turmas: 2, tarefas: 2, problemas: 3 },
      em: "2026-10-16T12:00:00.000Z",
    });
    expect(servidor.manifestos[0]?.mode).toBe("manual");
    expect(await sincronizacao.enviar(async () => lido)).toEqual({
      criadas: 3,
      atualizadas: 0,
      iguais: 0,
      partes: 1,
    });
    expect(sincronizacao.pendentes()).toBe(0);

    const segunda = await sincronizacao.verificar("semi", async () => lido);

    expect([segunda.novasOuAlteradas, segunda.iguais, segunda.sumidas]).toEqual([0, 3, 0]);
    await expect(sincronizacao.enviar(async () => lido)).rejects.toThrow(NadaParaEnviar);
  });

  it("um enunciado alterado vai sozinho, e o que sumiu aparece", async () => {
    const { servidor, sincronizacao } = montar();
    const lido = await catalogo();
    await sincronizacao.enviar(async () => lido);
    const mudado = await catalogo({
      problemas: {
        "PROB-L1Q1": { title: "26.2L1Q1 - Questão 1", description: "Nova versão.", testCases: [] },
      },
    });
    mudado.listas = mudado.listas.filter((l) => l.numero !== 2);
    mudado.questoes = mudado.questoes.filter((q) => q.questaoId !== "L2-Q1");

    const resumo = await sincronizacao.verificar("manual", async () => mudado);
    const envio = await sincronizacao.enviar(async () => mudado);

    expect([resumo.novasOuAlteradas, resumo.sumidas]).toEqual([1, 1]);
    expect(envio).toMatchObject({ criadas: 0, atualizadas: 1 });
    expect(servidor.partes.at(-1)?.map((q) => q.question_id)).toEqual(["L1-Q1"]);
  });

  it("envia sem verificar antes quando ainda não há rodada", async () => {
    const { servidor, sincronizacao } = montar();
    const lido = await catalogo();

    expect((await sincronizacao.enviar(async () => lido)).criadas).toBe(3);
    expect(servidor.manifestos).toHaveLength(1);
  });

  it("retoma de onde parou quando uma parte falha", async () => {
    const servidor = new IpCheckerFalso();
    const { sincronizacao } = montar(servidor);
    const lido = await catalogo();
    // Partes de uma questão cada: a segunda falha uma vez.
    lido.questoes.forEach((q) => (q.descricao = "x".repeat(60_000)));
    servidor.falhar = { parte: 2, status: 503 };

    await expect(sincronizacao.enviar(async () => lido)).rejects.toThrow(IpCheckerIndisponivel);
    expect(sincronizacao.pendentes()).toBe(2);

    const envio = await sincronizacao.enviar(async () => lido);

    expect(envio).toMatchObject({ criadas: 2, partes: 2 });
    expect(servidor.questoes.size).toBe(3);
    expect(servidor.manifestos).toHaveLength(1);
  });

  it("uma rodada recusada (422) obriga a verificar de novo", async () => {
    const servidor = new IpCheckerFalso();
    const { sincronizacao } = montar(servidor);
    const lido = await catalogo();
    await sincronizacao.verificar("manual", async () => lido);
    servidor.rodadas.clear();

    await expect(sincronizacao.enviar(async () => lido)).rejects.toThrow(RecusadoPeloIpChecker);
    expect(sincronizacao.pendentes()).toBe(0);
    expect((await sincronizacao.enviar(async () => lido)).criadas).toBe(3);
  });

  it("o que vai ao IP-Checker não tem caso oculto", async () => {
    const { fetch, sincronizacao } = montar();
    const lido = await catalogo();

    await sincronizacao.enviar(async () => lido);

    expect(JSON.stringify(fetch.pedidos.map((p) => p.corpo))).not.toContain(CASO_OCULTO);
  });
});

describe("o manifesto e as partes", () => {
  it("o manifesto segue o contrato da API", async () => {
    const lido = await catalogo();

    const manifesto = montarManifesto(lido, "semi");

    expect(manifesto.classes[0]).toEqual({
      dikastis_org_id: "TURMA-SI",
      name: "IP SI UFPE 2026.2",
      course: "SI",
    });
    expect(manifesto.lists[0]).toMatchObject({
      dikastis_task_id: "SI-L1",
      class_org_id: "TURMA-SI",
      kind: "lista",
      number: 1,
      starts_at: "2026-10-01T03:00:00.000Z",
    });
    expect(manifesto.lists[0]?.questions[0]).toEqual({
      dikastis_problem_id: "PROB-L1Q1",
      question_id: "L1-Q1",
      content_hash: lido.questoes[0]?.hash,
    });
  });

  it("as partes respeitam o tamanho e o número de questões", async () => {
    const lido = await catalogo();
    const questoes = Array.from({ length: 130 }, (_, i) => ({
      ...questaoParaApi(lido.questoes[0]!),
      question_id: `L1-Q${(i % 99) + 1}`,
    }));

    const porNumero = dividirEmPartes(questoes, 10_000_000, 60);
    const porTamanho = dividirEmPartes(questoes, 2_000, 60);

    expect(porNumero.map((p) => p.length)).toEqual([60, 60, 10]);
    expect(porTamanho.every((p) => new TextEncoder().encode(JSON.stringify(p)).length < 2_000)).toBe(
      true,
    );
    expect(dividirEmPartes([])).toEqual([]);
  });
});

describe("o cliente do IP-Checker", () => {
  const corpo = { period: "2026.2", mode: "manual" as const, classes: [], lists: [] };

  it("manda o token, sem cookies, para o endereço sem a barra do fim", async () => {
    const { fetch, sincronizacao } = montar();

    await sincronizacao.verificar("manual", () => catalogo());

    const [pedido] = fetch.pedidos;
    expect(pedido?.url).toBe(`${ENDERECO}/api/v1/import/catalog/manifest`);
    expect(pedido?.metodo).toBe("POST");
    expect(pedido?.credentials).toBe("omit");
    expect(pedido?.cabecalhos["Authorization"]).toBe(`Bearer ${TOKEN}`);
  });

  it.each([
    [401, {}, TokenRecusado, "recusou o token"],
    [503, {}, IpCheckerIndisponivel, "indisponível (erro 503)"],
    [429, { error: { code: "RATE_LIMITED", retry_after_s: 12 } }, RecusadoPeloIpChecker, "espere 12 s"],
    [429, "não é JSON", RecusadoPeloIpChecker, "espere 60 s"],
    [422, { error: { code: "INVALID_INPUT", message: "O hash não confere." } }, RecusadoPeloIpChecker, "O hash não confere."],
    [413, { error: {} }, RecusadoPeloIpChecker, "recusou o pedido (413)"],
  ])("%i vira um erro claro", async (status, resposta, tipo, mensagem) => {
    const fetch = fetchFalso({
      "/api/v1/import/catalog/manifest": () =>
        typeof resposta === "string" ? new Response(resposta, { status }) : json(resposta, status),
    });
    const cliente = new ClienteIpChecker({ endereco: ENDERECO, token: TOKEN, fetch });

    const erro = await cliente.manifesto(corpo).catch((e: unknown) => e);

    expect(erro).toBeInstanceOf(tipo);
    expect((erro as Error).message).toContain(mensagem);
  });

  it("sem resposta, o IP-Checker está indisponível", async () => {
    const fetch = (async () => {
      throw new TypeError("rede");
    }) as typeof globalThis.fetch;
    const cliente = new ClienteIpChecker({ endereco: ENDERECO, token: TOKEN, fetch });

    await expect(cliente.manifesto(corpo)).rejects.toThrow("sem resposta");
  });
});

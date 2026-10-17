import { describe, expect, it } from "vitest";

import { CHAVE_TOKEN, ClienteDikastis, lerToken } from "../src/dikastis/cliente";
import { ErroDikastis, FormatoDesconhecido, SemSessao } from "../src/dikastis/erros";
import { validarTurma } from "../src/dikastis/formatos";
import { RelogioFalso, fetchFalso, json } from "./apoio";

const armazenamento = (valor: string | null) => ({ getItem: () => valor });
const jwt = (exp: number) =>
  ["e30", btoa(JSON.stringify({ exp })).replace(/=+$/, ""), "assinatura"].join(".");
const TURMA = { tasks: [] };

function cliente(rotas: Record<string, unknown>) {
  const relogio = new RelogioFalso();
  const fetch = fetchFalso(rotas, relogio);
  return { relogio, fetch, cliente: new ClienteDikastis({ token: "tk", fetch, relogio }) };
}

describe("o token da sessão do Dikastis", () => {
  it("vem do localStorage da página, com ou sem aspas", () => {
    expect(lerToken(armazenamento("abc"), 0)).toBe("abc");
    expect(lerToken(armazenamento('"abc"'), 0)).toBe("abc");
    expect(CHAVE_TOKEN).toBe("@Dikastis:token");
  });

  it("sem token, com token vazio ou com aspas quebradas é SemSessao", () => {
    for (const valor of [null, "", "  ", '"abc']) {
      expect(() => lerToken(armazenamento(valor), 0)).toThrow(SemSessao);
    }
  });

  it("um JWT vencido é SemSessao; um válido passa", () => {
    const agora = 1_800_000_000_000;

    expect(() => lerToken(armazenamento(jwt(agora / 1000 - 1)), agora)).toThrow(SemSessao);
    expect(lerToken(armazenamento(jwt(agora / 1000 + 60)), agora)).toContain(".");
    expect(lerToken(armazenamento("a.!!!.c"), agora)).toBe("a.!!!.c");
  });
});

describe("o cliente do Dikastis", () => {
  it("manda o token como Bearer e confere o formato", async () => {
    const { cliente: c, fetch } = cliente({ "/api/teams/T": TURMA });

    expect(await c.get("teams/T", validarTurma)).toEqual([]);
    expect(fetch.pedidos[0]?.url).toBe("https://dikastis.com.br/api/teams/T");
    expect(fetch.pedidos[0]?.cabecalhos["Authorization"]).toBe("Bearer tk");
  });

  it("faz no máximo 2 pedidos por segundo, mesmo com pedidos simultâneos", async () => {
    const { cliente: c, fetch, relogio } = cliente({ "/api/teams/T": TURMA });
    const inicio = relogio.agora();

    await Promise.all([1, 2, 3, 4].map(() => c.get("teams/T", validarTurma)));

    expect(fetch.pedidos.map((p) => p.em - inicio)).toEqual([0, 500, 1000, 1500]);
  });

  it("repete um 429 e um 5xx com espera de 2 s e 4 s", async () => {
    let vez = 0;
    const { cliente: c, relogio } = cliente({
      "/api/teams/T": () => json({}, [429, 503][vez++] ?? 200),
    });

    expect(await c.get("teams/T", (d) => d)).toEqual({});
    expect(relogio.esperas.filter((ms) => ms >= 2000)).toEqual([2000, 4000]);
  });

  it("desiste depois de 3 repetições", async () => {
    const { cliente: c } = cliente({ "/api/teams/T": () => json({}, 500) });

    await expect(c.get("teams/T", validarTurma)).rejects.toThrow(ErroDikastis);
    expect(c.pedidos).toBe(4);
  });

  it("repete quando o Dikastis não responde", async () => {
    let vez = 0;
    const relogio = new RelogioFalso();
    const fetch = (async () => {
      if (vez++ === 0) throw new TypeError("rede");
      return json(TURMA);
    }) as typeof globalThis.fetch;

    const c = new ClienteDikastis({ token: "tk", fetch, relogio });

    expect(await c.get("teams/T", validarTurma)).toEqual([]);
  });

  it("não repete um 403 nem um 404", async () => {
    const { cliente: c } = cliente({ "/api/teams/T": () => json({}, 403) });

    await expect(c.get("teams/T", validarTurma)).rejects.toThrow("respondeu 403");
    await expect(c.get("teams/X", validarTurma)).rejects.toThrow("respondeu 404");
    expect(c.pedidos).toBe(2);
  });

  it("401 é SemSessao", async () => {
    const { cliente: c } = cliente({ "/api/teams/T": () => json({}, 401) });

    await expect(c.get("teams/T", validarTurma)).rejects.toThrow(SemSessao);
  });

  it("uma resposta que não é JSON é formato desconhecido", async () => {
    const { cliente: c } = cliente({ "/api/teams/T": () => new Response("<html>") });

    await expect(c.get("teams/T", validarTurma)).rejects.toThrow(FormatoDesconhecido);
  });

  it("o erro sem resposta diz que o Dikastis não respondeu", () => {
    expect(new ErroDikastis("/api/x", null).message).toContain("não respondeu");
  });
});

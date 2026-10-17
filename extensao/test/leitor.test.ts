import { describe, expect, it, vi } from "vitest";

import { ORGANIZACAO_IP } from "../src/config";
import { responderLeitura } from "../src/content/leitor";
import { RelogioFalso, fetchFalso } from "./apoio";
import { ORG, organizacao, rotasDoDikastis } from "./respostas/dikastis";

const TOKEN_DA_PAGINA = "token-da-sessao-do-dikastis-123";

function rotasDaOrganizacaoReal() {
  const rotas = rotasDoDikastis();
  delete rotas[`/api/organizations/${ORG}`];
  rotas[`/api/organizations/${ORGANIZACAO_IP}`] = organizacao;
  return rotas;
}

describe("o script da página", () => {
  it("lê o catálogo com o token da página e devolve só o catálogo", async () => {
    const relogio = new RelogioFalso();
    const fetch = fetchFalso(rotasDaOrganizacaoReal(), relogio);
    const armazenamento = { getItem: vi.fn(() => TOKEN_DA_PAGINA) };

    const resposta = await responderLeitura({ armazenamento, fetch, relogio });

    expect(resposta.ok).toBe(true);
    expect(armazenamento.getItem).toHaveBeenCalledWith("@Dikastis:token");
    expect(fetch.pedidos[0]?.cabecalhos["Authorization"]).toBe(`Bearer ${TOKEN_DA_PAGINA}`);
    expect(JSON.stringify(resposta)).not.toContain(TOKEN_DA_PAGINA);
  });

  it("sem sessão, devolve o erro serializado", async () => {
    const resposta = await responderLeitura({ armazenamento: { getItem: () => null } });

    expect(resposta).toEqual({
      ok: false,
      erro: { nome: "SemSessao", mensagem: expect.stringContaining("entre na sua conta") },
    });
  });

  it("dois pedidos seguidos dividem a mesma leitura", async () => {
    const relogio = new RelogioFalso();
    const fetch = fetchFalso(rotasDaOrganizacaoReal(), relogio);
    const ambiente = { armazenamento: { getItem: () => TOKEN_DA_PAGINA }, fetch, relogio };

    const [a, b] = await Promise.all([responderLeitura(ambiente), responderLeitura(ambiente)]);

    expect(a).toBe(b);
    expect(fetch.pedidos.filter((p) => p.url.includes("/organizations/"))).toHaveLength(1);
  });
});

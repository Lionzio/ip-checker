import { describe, expect, it } from "vitest";

import { type Ambiente, type Guardado, Servico, mascarar, textoDoSelo } from "../src/background/servico";
import { type Catalogo, lerCatalogo } from "../src/catalogo/descoberta";
import { INTERVALO_SEMI_MS } from "../src/config";
import { ClienteDikastis } from "../src/dikastis/cliente";
import { SemSessao } from "../src/dikastis/erros";
import { IpCheckerFalso, RelogioFalso, fetchFalso } from "./apoio";
import { ORG, rotasDoDikastis } from "./respostas/dikastis";

const TOKEN = "ipc_imp_abcdefghijklmnopqrstuvwxyz";
const MINUTO = 60_000;

async function catalogo(): Promise<Catalogo> {
  const relogio = new RelogioFalso();
  const fetch = fetchFalso(rotasDoDikastis(), relogio);
  return lerCatalogo(new ClienteDikastis({ token: "tk", fetch, relogio }), { organizacao: ORG });
}

class AmbienteFalso implements Ambiente {
  guardado: Guardado = { token: TOKEN };
  selos: string[] = [];
  leituras = 0;
  abas: (number | undefined)[] = [];
  tempo = Date.parse("2026-10-16T12:00:00Z");
  servidor = new IpCheckerFalso();
  fetch = fetchFalso(this.servidor.rotas());
  falharLeitura: Error | null = null;
  private lido: Promise<Catalogo> | null = null;

  async ler() {
    return { ...this.guardado };
  }
  async gravar(parcial: Guardado) {
    this.guardado = { ...this.guardado, ...parcial };
  }
  async lerCatalogo(abaId?: number) {
    this.leituras++;
    this.abas.push(abaId);
    if (this.falharLeitura) throw this.falharLeitura;
    this.lido ??= catalogo();
    return structuredClone(await this.lido);
  }
  async selo(texto: string) {
    this.selos.push(texto);
  }
  agora() {
    return this.tempo;
  }
}

describe("o modo semi-automático (S50-07)", () => {
  it("duas aberturas em 10 minutos fazem uma verificação; com 31 minutos, duas", async () => {
    const ambiente = new AmbienteFalso();
    const servico = new Servico(ambiente);

    await servico.atender({ tipo: "dikastis-aberto" }, 7);
    ambiente.tempo += 10 * MINUTO;
    await servico.atender({ tipo: "dikastis-aberto" }, 7);

    expect(ambiente.leituras).toBe(1);
    expect(ambiente.abas).toEqual([7]);
    expect(ambiente.servidor.manifestos.map((m) => m.mode)).toEqual(["semi"]);

    ambiente.tempo += 21 * MINUTO;
    await servico.atender({ tipo: "dikastis-aberto" }, 7);

    expect(ambiente.leituras).toBe(2);
  });

  it("o selo mostra as novidades e some depois do envio", async () => {
    const ambiente = new AmbienteFalso();
    const servico = new Servico(ambiente);

    await servico.atender({ tipo: "dikastis-aberto" }, 1);
    expect(ambiente.selos.at(-1)).toBe("3");

    const resposta = await servico.atender({ tipo: "enviar" });

    expect(resposta).toMatchObject({ ok: true, envio: { criadas: 3 } });
    expect(ambiente.selos.at(-1)).toBe("");
  });

  it("não roda sem token nem com o modo desligado", async () => {
    for (const guardado of [{}, { token: TOKEN, semiAutomatico: false }]) {
      const ambiente = new AmbienteFalso();
      ambiente.guardado = guardado;

      await new Servico(ambiente).atender({ tipo: "dikastis-aberto" }, 1);

      expect(ambiente.leituras).toBe(0);
    }
  });

  it("uma falha espera os 30 minutos e não derruba nada", async () => {
    const ambiente = new AmbienteFalso();
    ambiente.falharLeitura = new SemSessao();
    const servico = new Servico(ambiente);

    expect(await servico.atender({ tipo: "dikastis-aberto" }, 1)).toBeNull();
    ambiente.tempo += INTERVALO_SEMI_MS - 1;
    await servico.atender({ tipo: "dikastis-aberto" }, 1);

    expect(ambiente.leituras).toBe(1);
  });
});

describe("o service worker", () => {
  it("o estado mostra o token só mascarado", async () => {
    const ambiente = new AmbienteFalso();

    const resposta = await new Servico(ambiente).atender({ tipo: "estado" });

    expect(resposta).toMatchObject({
      ok: true,
      estado: {
        endereco: "https://ip-checker-red-phi.vercel.app",
        token: "ipc_imp_…wxyz",
        semiAutomatico: true,
        resumo: null,
        pendentes: 0,
      },
    });
    expect(JSON.stringify(resposta)).not.toContain(TOKEN);
  });

  it("verificar grava o resumo (só contagens) e a data", async () => {
    const ambiente = new AmbienteFalso();

    const resposta = await new Servico(ambiente).atender({ tipo: "verificar" });

    expect(resposta).toMatchObject({ ok: true, estado: { pendentes: 3 } });
    expect(ambiente.guardado.resumo?.novasOuAlteradas).toBe(3);
    expect(ambiente.guardado.ultimaVerificacao).toBe(ambiente.tempo);
    expect(JSON.stringify(ambiente.guardado)).not.toContain("Leia N");
    expect(ambiente.servidor.manifestos[0]?.mode).toBe("manual");
  });

  it("duas verificações ao mesmo tempo leem o Dikastis uma vez", async () => {
    const ambiente = new AmbienteFalso();
    const servico = new Servico(ambiente);

    await Promise.all([servico.atender({ tipo: "verificar" }), servico.atender({ tipo: "verificar" })]);

    expect(ambiente.leituras).toBe(1);
  });

  it("sem token, pede o token", async () => {
    const ambiente = new AmbienteFalso();
    ambiente.guardado = {};

    const resposta = await new Servico(ambiente).atender({ tipo: "verificar" });

    expect(resposta).toMatchObject({ ok: false, erro: { nome: "SemToken" } });
  });

  it("um erro do Dikastis chega ao popup com o nome e a mensagem", async () => {
    const ambiente = new AmbienteFalso();
    ambiente.falharLeitura = new SemSessao();

    const resposta = await new Servico(ambiente).atender({ tipo: "verificar" });

    expect(resposta).toMatchObject({
      ok: false,
      erro: { nome: "SemSessao", mensagem: expect.stringContaining("Sem sessão") },
      estado: { token: "ipc_imp_…wxyz" },
    });
  });

  it("o selo e a máscara", () => {
    expect([textoDoSelo(0), textoDoSelo(5), textoDoSelo(150)]).toEqual(["", "5", "99+"]);
    expect(mascarar("ipc_imp_x")).toBe("ipc_imp_…");
  });
});

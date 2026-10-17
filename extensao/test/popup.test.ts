// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Estado, Pedido, Resposta } from "../src/mensagens";
import {
  type ApiDoPopup,
  conferirEndereco,
  iniciarPopup,
  textoDoEnvio,
  textoDoResumo,
} from "../src/popup/popup";
import type { Resumo } from "../src/sincronizacao/sincronizar";

// No jsdom, o URL global é o do navegador: o caminho vem do Node.
const html = readFileSync(resolve(import.meta.dirname, "../src/popup/popup.html"), "utf8");
const TOKEN = "ipc_imp_abcdefghijklmnopqrstuvwxyz0123";

const RESUMO: Resumo = {
  periodo: "2026.2",
  listas: 4,
  questoes: 28,
  novasOuAlteradas: 28,
  iguais: 0,
  sumidas: 0,
  ignorados: { turmas: 0, tarefas: 0, problemas: 0 },
  em: "2026-10-16T15:30:00.000Z",
};

function estado(mudar: Partial<Estado> = {}): Estado {
  return {
    endereco: "https://ip-checker-red-phi.vercel.app",
    token: "ipc_imp_…0123",
    semiAutomatico: true,
    resumo: null,
    pendentes: 0,
    ...mudar,
  };
}

function api(respostas: Partial<Record<Pedido["tipo"], Resposta>> = {}) {
  const pedidos: Pedido[] = [];
  const falsa: ApiDoPopup & { pedidos: Pedido[] } = {
    pedidos,
    pedir: vi.fn(async (pedido: Pedido) => {
      pedidos.push(pedido);
      return respostas[pedido.tipo] ?? { ok: true as const, estado: estado() };
    }),
    gravar: vi.fn(async () => undefined),
    permitir: vi.fn(async () => true),
  };
  return falsa;
}

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const esperar = () => new Promise((fim) => setTimeout(fim, 0));

beforeEach(() => {
  const lido = new DOMParser().parseFromString(html, "text/html");
  document.body.replaceChildren(...lido.body.childNodes);
});

describe("o popup", () => {
  it("mostra o estado: resumo, endereço, token mascarado e Enviar desligado sem novidades", async () => {
    await iniciarPopup(document, api());

    expect($("resumo").textContent).toBe("Ainda sem verificação.");
    expect($<HTMLInputElement>("endereco").value).toBe("https://ip-checker-red-phi.vercel.app");
    expect($("token-atual").textContent).toContain("ipc_imp_…0123");
    expect($<HTMLButtonElement>("enviar").disabled).toBe(true);
    expect($<HTMLDetailsElement>("ajustes").open).toBe(false);
  });

  it("sem token, abre os ajustes", async () => {
    await iniciarPopup(document, api({ estado: { ok: true, estado: estado({ token: null }) } }));

    expect($<HTMLDetailsElement>("ajustes").open).toBe(true);
    expect($("token-atual").textContent).toContain("Crie o token");
  });

  it("Verificar agora mostra as novidades e liga o Enviar", async () => {
    const falsa = api({
      verificar: { ok: true, estado: estado({ resumo: RESUMO, pendentes: 28 }) },
    });
    await iniciarPopup(document, falsa);

    $("verificar").click();
    await esperar();

    expect(falsa.pedidos.map((p) => p.tipo)).toEqual(["estado", "verificar"]);
    expect($("resumo").textContent).toContain("4 listas, 28 questões; 28 questões novas ou alteradas");
    expect($<HTMLButtonElement>("enviar").disabled).toBe(false);
  });

  it("Enviar mostra o resultado", async () => {
    const falsa = api({
      estado: { ok: true, estado: estado({ resumo: RESUMO }) },
      enviar: {
        ok: true,
        estado: estado(),
        envio: { criadas: 27, atualizadas: 1, iguais: 0, partes: 1 },
      },
    });
    await iniciarPopup(document, falsa);

    $("enviar").click();
    await esperar();

    expect($("situacao").textContent).toBe("Enviado: 27 questões novas, 1 alterada.");
  });

  it("um erro aparece como erro", async () => {
    const falsa = api({
      verificar: {
        ok: false,
        erro: { nome: "SemSessao", mensagem: "Sem sessão no Dikastis." },
        estado: estado(),
      },
    });
    await iniciarPopup(document, falsa);

    $("verificar").click();
    await esperar();

    expect($("situacao").textContent).toBe("Sem sessão no Dikastis.");
    expect($("situacao").classList.contains("erro")).toBe(true);
  });

  it("uma extensão que não responde vira um aviso", async () => {
    const falsa = api();
    await iniciarPopup(document, falsa);
    falsa.pedir = vi.fn(async () => {
      throw new Error("sem resposta");
    });

    $("verificar").click();
    await esperar();

    expect($("situacao").textContent).toContain("não respondeu");
  });

  it("salva o token novo e o modo, e limpa o campo", async () => {
    const falsa = api();
    await iniciarPopup(document, falsa);
    $<HTMLInputElement>("token").value = ` ${TOKEN} `;
    $<HTMLInputElement>("semi").checked = false;

    $<HTMLFormElement>("formulario").requestSubmit();
    await esperar();

    expect(falsa.gravar).toHaveBeenCalledWith({
      endereco: "https://ip-checker-red-phi.vercel.app",
      semiAutomatico: false,
      token: TOKEN,
    });
    expect($<HTMLInputElement>("token").value).toBe("");
    expect($("situacao").textContent).toBe("Ajustes salvos.");
  });

  it("recusa um token que não é de importação e um endereço de fora", async () => {
    const falsa = api();
    await iniciarPopup(document, falsa);

    $<HTMLInputElement>("token").value = "senha123";
    $<HTMLFormElement>("formulario").requestSubmit();
    await esperar();
    expect($("situacao").textContent).toContain("ipc_imp_");

    $<HTMLInputElement>("token").value = "";
    $<HTMLInputElement>("endereco").value = "https://outro.exemplo.invalid";
    $<HTMLFormElement>("formulario").requestSubmit();
    await esperar();
    expect($("situacao").textContent).toContain("Use o endereço do piloto");
    expect(falsa.gravar).not.toHaveBeenCalled();
  });

  it("um endereço local pede a permissão do Chrome", async () => {
    const falsa = api();
    falsa.permitir = vi.fn(async () => false);
    await iniciarPopup(document, falsa);
    $<HTMLInputElement>("endereco").value = "http://127.0.0.1:8180/";

    $<HTMLFormElement>("formulario").requestSubmit();
    await esperar();

    expect(falsa.permitir).toHaveBeenCalledWith("http://127.0.0.1:8180/*");
    expect($("situacao").textContent).toContain("Sem a permissão");
    expect(falsa.gravar).not.toHaveBeenCalled();
  });
});

describe("os textos do popup", () => {
  it("o resumo sem novidades diz nada novo", () => {
    const texto = textoDoResumo({ ...RESUMO, novasOuAlteradas: 0, iguais: 28 });

    expect(texto).toMatch(/^2026\.2: 4 listas, 28 questões; nada novo\. Verificado em /);
  });

  it("o singular e as sumidas", () => {
    expect(textoDoResumo({ ...RESUMO, listas: 1, questoes: 1, novasOuAlteradas: 1, sumidas: 2 })).toContain(
      "1 lista, 1 questão; 1 questão nova ou alterada, 2 sumidas",
    );
    expect(textoDoEnvio({ criadas: 1, atualizadas: 0, iguais: 0, partes: 1 })).toBe(
      "Enviado: 1 questão nova, 0 alteradas.",
    );
  });

  it("os endereços aceitos", () => {
    expect(conferirEndereco("https://ip-checker-red-phi.vercel.app/")).toEqual({
      ok: true,
      endereco: "https://ip-checker-red-phi.vercel.app",
      local: false,
    });
    expect(conferirEndereco("http://localhost:5180")).toMatchObject({ ok: true, local: true });
    expect(conferirEndereco("não é endereço")).toEqual({ ok: false, motivo: "Endereço inválido." });
  });
});

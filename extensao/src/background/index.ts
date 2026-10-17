// O service worker: liga o Servico às APIs do Chrome (mensagens, armazenamento, abas, selo).

import { DIKASTIS } from "../config";
import type { Catalogo } from "../catalogo/descoberta";
import type { Pedido, PedidoDeLeitura, RespostaDeLeitura } from "../mensagens";
import { type Guardado, Servico } from "./servico";

class SemAbaDoDikastis extends Error {
  constructor() {
    super("Abra o Dikastis numa aba, entre na sua conta e tente de novo.");
    this.name = "SemAbaDoDikastis";
  }
}

class AbaSemExtensao extends Error {
  constructor() {
    super("Recarregue a aba do Dikastis (ela foi aberta antes da extensão) e tente de novo.");
    this.name = "AbaSemExtensao";
  }
}

async function lerCatalogo(abaId?: number): Promise<Catalogo> {
  let alvo = abaId;
  if (alvo === undefined) {
    const abas = await chrome.tabs.query({ url: `${DIKASTIS}/*` });
    alvo = abas.find((aba) => aba.active)?.id ?? abas[0]?.id;
  }
  if (alvo === undefined) throw new SemAbaDoDikastis();
  let resposta: RespostaDeLeitura | undefined;
  try {
    const pedido: PedidoDeLeitura = { tipo: "ler-catalogo" };
    resposta = await chrome.tabs.sendMessage<PedidoDeLeitura, RespostaDeLeitura>(alvo, pedido);
  } catch {
    throw new AbaSemExtensao();
  }
  if (resposta === undefined) throw new AbaSemExtensao();
  if (!resposta.ok) {
    const erro = new Error(resposta.erro.mensagem);
    erro.name = resposta.erro.nome;
    throw erro;
  }
  return resposta.catalogo;
}

const servico = new Servico({
  ler: async () => (await chrome.storage.local.get(null)) as Guardado,
  gravar: (parcial) => chrome.storage.local.set(parcial),
  lerCatalogo,
  selo: async (texto) => {
    await chrome.action.setBadgeBackgroundColor({ color: "#1d4ed8" });
    await chrome.action.setBadgeText({ text: texto });
  },
  agora: () => Date.now(),
});

chrome.runtime.onMessage.addListener((pedido: Pedido, remetente, responder) => {
  // Só a própria extensão fala com o service worker (o popup e o script da página).
  if (remetente.id !== chrome.runtime.id) return false;
  void servico.atender(pedido, remetente.tab?.id).then((resposta) => responder(resposta));
  return true;
});

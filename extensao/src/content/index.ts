// O script da página no dikastis.com.br: avisa o service worker que o Dikastis abriu (o modo
// semi-automático, S50-07) e atende o pedido de leitura do catálogo.

import type { Pedido, PedidoDeLeitura } from "../mensagens";
import { responderLeitura } from "./leitor";

chrome.runtime.onMessage.addListener((pedido: PedidoDeLeitura, remetente, responder) => {
  if (remetente.id !== chrome.runtime.id || pedido?.tipo !== "ler-catalogo") return false;
  void responderLeitura({ armazenamento: window.localStorage }).then(responder);
  return true;
});

const aviso: Pedido = { tipo: "dikastis-aberto" };
// Sem o service worker (extensão recarregada), o aviso só se perde.
chrome.runtime.sendMessage(aviso).catch(() => undefined);

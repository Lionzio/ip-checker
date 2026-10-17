// As mensagens entre o popup, o service worker e o script da página.

import type { Catalogo } from "./catalogo/descoberta";
import type { Resumo, ResultadoEnvio } from "./sincronizacao/sincronizar";

/** Do popup (ou do script da página) para o service worker. */
export type Pedido =
  | { tipo: "estado" }
  | { tipo: "verificar" }
  | { tipo: "enviar" }
  | { tipo: "dikastis-aberto" };

export interface ErroSerializado {
  nome: string;
  mensagem: string;
}

export interface Estado {
  endereco: string;
  /** O token mascarado (ipc_imp_…abcd), nunca o valor. */
  token: string | null;
  semiAutomatico: boolean;
  resumo: Resumo | null;
  pendentes: number;
}

export type Resposta =
  | { ok: true; estado: Estado; envio?: ResultadoEnvio }
  | { ok: false; erro: ErroSerializado; estado?: Estado };

/** Do service worker para o script da página. */
export interface PedidoDeLeitura {
  tipo: "ler-catalogo";
}

export type RespostaDeLeitura =
  | { ok: true; catalogo: Catalogo }
  | { ok: false; erro: ErroSerializado };

export function serializarErro(erro: unknown): ErroSerializado {
  if (erro instanceof Error) return { nome: erro.name, mensagem: erro.message };
  return { nome: "Error", mensagem: "Erro inesperado na extensão." };
}

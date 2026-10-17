// O script da página, sem as APIs do Chrome: lê o token do Dikastis no localStorage da própria
// página, monta o catálogo e devolve ao service worker só o catálogo (nunca o token).

import { lerCatalogo } from "../catalogo/descoberta";
import { ClienteDikastis, type Relogio, lerToken, relogioReal } from "../dikastis/cliente";
import { type RespostaDeLeitura, serializarErro } from "../mensagens";

export interface AmbienteDaPagina {
  armazenamento: Pick<Storage, "getItem">;
  fetch?: typeof fetch;
  relogio?: Relogio;
}

/** Uma leitura por vez: dois pedidos seguidos dividem a mesma (e o mesmo ritmo de 2/s). */
let emAndamento: Promise<RespostaDeLeitura> | null = null;

export function responderLeitura(ambiente: AmbienteDaPagina): Promise<RespostaDeLeitura> {
  emAndamento ??= ler(ambiente).finally(() => {
    emAndamento = null;
  });
  return emAndamento;
}

async function ler(ambiente: AmbienteDaPagina): Promise<RespostaDeLeitura> {
  const relogio = ambiente.relogio ?? relogioReal;
  try {
    const token = lerToken(ambiente.armazenamento, relogio.agora());
    const cliente = new ClienteDikastis({ token, fetch: ambiente.fetch, relogio });
    return { ok: true, catalogo: await lerCatalogo(cliente) };
  } catch (erro) {
    return { ok: false, erro: serializarErro(erro) };
  }
}

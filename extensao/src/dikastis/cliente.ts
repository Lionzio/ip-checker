// O cliente da API do Dikastis (S50-02): o único lugar que fala com o Dikastis. Roda no script da
// página (mesma origem), com o token que o próprio Dikastis guarda no localStorage. O token nunca
// sai do script da página: não vai ao service worker, ao IP-Checker nem ao console.

import { DIKASTIS, ESPERAS_DIKASTIS_MS, INTERVALO_DIKASTIS_MS } from "../config";
import { ErroDikastis, FormatoDesconhecido, SemSessao } from "./erros";
import type { Validador } from "./formatos";

/** A chave em que o Dikastis guarda o token da sessão. */
export const CHAVE_TOKEN = "@Dikastis:token";

export interface Relogio {
  agora(): number;
  esperar(ms: number): Promise<void>;
}

export const relogioReal: Relogio = {
  agora: () => Date.now(),
  esperar: (ms) => new Promise((fim) => setTimeout(fim, ms)),
};

/** O token da sessão do Dikastis, ou SemSessao se não houver ou se já venceu. */
export function lerToken(armazenamento: Pick<Storage, "getItem">, agora: number): string {
  let token = armazenamento.getItem(CHAVE_TOKEN);
  if (token?.startsWith('"')) {
    try {
      token = JSON.parse(token) as string;
    } catch {
      token = null;
    }
  }
  if (typeof token !== "string" || token.trim() === "") throw new SemSessao();
  const vence = vencimento(token);
  if (vence !== null && vence <= agora) throw new SemSessao();
  return token;
}

/** O ``exp`` de um JWT em milissegundos, ou null se o token não for um JWT legível. */
function vencimento(token: string): number | null {
  const partes = token.split(".");
  if (partes.length !== 3 || !partes[1]) return null;
  try {
    const base64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");
    const carga = JSON.parse(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="))) as {
      exp?: unknown;
    };
    return typeof carga.exp === "number" ? carga.exp * 1000 : null;
  } catch {
    return null;
  }
}

export interface OpcoesCliente {
  token: string;
  fetch?: typeof fetch;
  relogio?: Relogio;
  base?: string;
}

export class ClienteDikastis {
  private readonly token: string;
  private readonly fetch: typeof fetch;
  private readonly relogio: Relogio;
  private readonly base: string;
  private proximo = 0;
  /** Quantos pedidos foram feitos (para o resumo e os testes). */
  pedidos = 0;

  constructor(opcoes: OpcoesCliente) {
    this.token = opcoes.token;
    this.fetch = opcoes.fetch ?? globalThis.fetch.bind(globalThis);
    this.relogio = opcoes.relogio ?? relogioReal;
    this.base = opcoes.base ?? DIKASTIS;
  }

  /** GET em /api/<caminho>, no ritmo de 2 por segundo, com o formato conferido. */
  async get<T>(caminho: string, validar: Validador<T>): Promise<T> {
    const endereco = `/api/${caminho}`;
    for (let tentativa = 0; ; tentativa++) {
      await this.vez();
      let resposta: Response | null;
      try {
        this.pedidos++;
        resposta = await this.fetch(`${this.base}${endereco}`, {
          headers: { Authorization: `Bearer ${this.token}`, Accept: "application/json" },
        });
      } catch {
        resposta = null;
      }
      if (resposta?.ok) {
        let dado: unknown;
        try {
          dado = await resposta.json();
        } catch {
          throw new FormatoDesconhecido(endereco, "(resposta)", "JSON");
        }
        return validar(dado, endereco);
      }
      if (resposta?.status === 401) throw new SemSessao();
      const repete = resposta === null || resposta.status === 429 || resposta.status >= 500;
      const espera = ESPERAS_DIKASTIS_MS[tentativa];
      if (!repete || espera === undefined) {
        throw new ErroDikastis(endereco, resposta?.status ?? null);
      }
      await this.relogio.esperar(espera);
    }
  }

  /** Espera a vez do próximo pedido: no máximo um a cada 500 ms, mesmo com pedidos simultâneos. */
  private async vez(): Promise<void> {
    const agora = this.relogio.agora();
    const inicio = Math.max(agora, this.proximo);
    this.proximo = inicio + INTERVALO_DIKASTIS_MS;
    if (inicio > agora) await this.relogio.esperar(inicio - agora);
  }
}

// O service worker (S50-03, S50-07), sem as APIs do Chrome: elas entram por ``Ambiente``, para os
// testes trocarem por versões falsas. Guarda no chrome.storage.local só o endereço, o token, a
// escolha do modo semi-automático, a data da última verificação e o resumo (contagens).

import { ENDERECO_PADRAO, INTERVALO_SEMI_MS } from "../config";
import type { Catalogo } from "../catalogo/descoberta";
import { ClienteIpChecker } from "../ipchecker/cliente";
import { type Estado, type Pedido, type Resposta, serializarErro } from "../mensagens";
import { type Modo, type Resumo, Sincronizacao } from "../sincronizacao/sincronizar";

export interface Guardado {
  endereco?: string;
  token?: string;
  semiAutomatico?: boolean;
  /** Milissegundos desde 1970 da última verificação (de qualquer modo). */
  ultimaVerificacao?: number;
  resumo?: Resumo;
}

export interface Ambiente {
  ler(): Promise<Guardado>;
  gravar(parcial: Guardado): Promise<void>;
  /** Pede o catálogo ao script da página (na aba indicada ou numa aba aberta do Dikastis). */
  lerCatalogo(abaId?: number): Promise<Catalogo>;
  selo(texto: string): Promise<void>;
  agora(): number;
  fetch?: typeof fetch;
}

export class SemToken extends Error {
  constructor() {
    super("Cole o token de importação (criado no Perfil do IP-Checker) e salve.");
    this.name = "SemToken";
  }
}

export function mascarar(token: string): string {
  return token.length <= 12 ? "ipc_imp_…" : `${token.slice(0, 8)}…${token.slice(-4)}`;
}

export function textoDoSelo(novidades: number): string {
  if (novidades <= 0) return "";
  return novidades > 99 ? "99+" : String(novidades);
}

export class Servico {
  readonly sincronizacao: Sincronizacao;
  /** Uma verificação por vez: a segunda espera a primeira (o selo e o popup veem a mesma). */
  private emAndamento: Promise<Resumo> | null = null;

  constructor(private readonly ambiente: Ambiente) {
    this.sincronizacao = new Sincronizacao(async () => {
      const guardado = await this.ambiente.ler();
      if (!guardado.token) throw new SemToken();
      return new ClienteIpChecker({
        endereco: guardado.endereco ?? ENDERECO_PADRAO,
        token: guardado.token,
        fetch: this.ambiente.fetch,
      });
    }, () => new Date(this.ambiente.agora()));
  }

  async atender(pedido: Pedido, abaId?: number): Promise<Resposta | null> {
    try {
      switch (pedido.tipo) {
        case "estado":
          return { ok: true, estado: await this.estado() };
        case "verificar":
          await this.verificar("manual");
          return { ok: true, estado: await this.estado() };
        case "enviar": {
          const envio = await this.sincronizacao.enviar(() => this.ambiente.lerCatalogo());
          await this.atualizarSelo();
          return { ok: true, estado: await this.estado(), envio };
        }
        case "dikastis-aberto":
          await this.semiAutomatico(abaId);
          return null;
      }
    } catch (erro) {
      return { ok: false, erro: serializarErro(erro), estado: await this.estado() };
    }
  }

  /** S50-07: ao abrir o Dikastis, verifica (só o manifesto) no máximo a cada 30 minutos. */
  private async semiAutomatico(abaId?: number): Promise<void> {
    const guardado = await this.ambiente.ler();
    if (guardado.semiAutomatico === false || !guardado.token) return;
    const ultima = guardado.ultimaVerificacao ?? 0;
    if (this.ambiente.agora() - ultima < INTERVALO_SEMI_MS) return;
    try {
      await this.verificar("semi", abaId);
    } catch (erro) {
      // Sem popup aberto, o erro fica no console do service worker (sem dados).
      console.warn("IP-Checker: verificação automática falhou:", serializarErro(erro).nome);
    }
  }

  private async verificar(modo: Modo, abaId?: number): Promise<Resumo> {
    if (this.emAndamento !== null) return this.emAndamento;
    this.emAndamento = (async () => {
      // A data vai antes da leitura: uma falha também espera os 30 minutos do semi-automático.
      await this.ambiente.gravar({ ultimaVerificacao: this.ambiente.agora() });
      const resumo = await this.sincronizacao.verificar(modo, () =>
        this.ambiente.lerCatalogo(abaId),
      );
      await this.ambiente.gravar({ resumo });
      await this.atualizarSelo();
      return resumo;
    })();
    try {
      return await this.emAndamento;
    } finally {
      this.emAndamento = null;
    }
  }

  private async atualizarSelo(): Promise<void> {
    await this.ambiente.selo(textoDoSelo(this.sincronizacao.pendentes()));
  }

  private async estado(): Promise<Estado> {
    const guardado = await this.ambiente.ler();
    return {
      endereco: guardado.endereco ?? ENDERECO_PADRAO,
      token: guardado.token ? mascarar(guardado.token) : null,
      semiAutomatico: guardado.semiAutomatico !== false,
      resumo: guardado.resumo ?? null,
      pendentes: this.sincronizacao.pendentes(),
    };
  }
}

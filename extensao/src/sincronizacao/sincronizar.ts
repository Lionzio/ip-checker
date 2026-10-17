// A sincronização (S50-03, S50-05): "Verificar" lê o Dikastis e manda só o manifesto; "Enviar"
// manda, em partes, só as questões novas ou alteradas que o IP-Checker pediu. A rodada (o run_id,
// o que falta e o que já foi) fica só na memória do service worker: se uma parte falhar, o próximo
// "Enviar" continua de onde parou. O enunciado nunca vai para o chrome.storage.

import type { Catalogo } from "../catalogo/descoberta";
import { type ClienteIpChecker, RecusadoPeloIpChecker } from "../ipchecker/cliente";
import { dividirEmPartes, montarManifesto, questaoParaApi } from "./manifesto";

export type Modo = "manual" | "semi";

export interface Resumo {
  periodo: string;
  /** Listas e provas do período (a mesma lista em várias turmas conta uma vez). */
  listas: number;
  questoes: number;
  novasOuAlteradas: number;
  iguais: number;
  sumidas: number;
  ignorados: Catalogo["ignorados"];
  /** Quando a verificação terminou (ISO 8601). */
  em: string;
}

export interface ResultadoEnvio {
  criadas: number;
  atualizadas: number;
  iguais: number;
  partes: number;
}

interface Rodada {
  runId: string;
  catalogo: Catalogo;
  pendentes: Set<string>;
}

export class NadaParaEnviar extends Error {
  constructor() {
    super("Nada para enviar: verifique de novo para ver se há novidades.");
    this.name = "NadaParaEnviar";
  }
}

export class Sincronizacao {
  private rodada: Rodada | null = null;

  constructor(
    private readonly cliente: () => Promise<ClienteIpChecker>,
    private readonly agora: () => Date = () => new Date(),
  ) {}

  /** Lê o Dikastis e manda o manifesto; devolve o resumo das novidades. */
  async verificar(modo: Modo, ler: () => Promise<Catalogo>): Promise<Resumo> {
    const catalogo = await ler();
    const ipchecker = await this.cliente();
    const resultado = await ipchecker.manifesto(montarManifesto(catalogo, modo));
    this.rodada = { runId: resultado.run_id, catalogo, pendentes: new Set(resultado.need) };
    const listas = new Set(catalogo.listas.map((l) => `${l.tipo}:${l.numero ?? 0}`));
    return {
      periodo: catalogo.periodo,
      listas: listas.size,
      questoes: catalogo.questoes.length,
      novasOuAlteradas: resultado.need.length,
      iguais: resultado.unchanged,
      sumidas: resultado.missing.length,
      ignorados: catalogo.ignorados,
      em: this.agora().toISOString(),
    };
  }

  /** O que a última verificação achou e ainda não foi enviado. */
  pendentes(): number {
    return this.rodada?.pendentes.size ?? 0;
  }

  /** Manda as questões que faltam, em partes; sem rodada, verifica antes. */
  async enviar(ler: () => Promise<Catalogo>): Promise<ResultadoEnvio> {
    if (this.rodada === null) await this.verificar("manual", ler);
    const rodada = this.rodada as Rodada;
    const questoes = rodada.catalogo.questoes.filter((q) => rodada.pendentes.has(q.problemaId));
    if (questoes.length === 0) throw new NadaParaEnviar();
    const ipchecker = await this.cliente();
    const total: ResultadoEnvio = { criadas: 0, atualizadas: 0, iguais: 0, partes: 0 };
    for (const parte of dividirEmPartes(questoes.map(questaoParaApi))) {
      let resultado;
      try {
        resultado = await ipchecker.questoes({
          run_id: rodada.runId,
          period: rodada.catalogo.periodo,
          questions: parte,
        });
      } catch (erro) {
        // A rodada sumiu ou não confere mais: a próxima vez começa de novo, com outra verificação.
        if (erro instanceof RecusadoPeloIpChecker && erro.status === 422) this.rodada = null;
        throw erro;
      }
      for (const q of parte) rodada.pendentes.delete(q.dikastis_problem_id);
      total.criadas += resultado.created;
      total.atualizadas += resultado.updated;
      total.iguais += resultado.unchanged;
      total.partes++;
    }
    return total;
  }
}

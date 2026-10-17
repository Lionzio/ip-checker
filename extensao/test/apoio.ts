// Apoio dos testes: um relógio falso, um Dikastis falso (com as respostas sintéticas de
// respostas/dikastis.ts) e um IP-Checker falso com as regras do manifesto da API.

import type { Relogio } from "../src/dikastis/cliente";
import type {
  ManifestoApi,
  QuestaoApi,
  ResultadoManifesto,
  ResultadoQuestoes,
} from "../src/ipchecker/cliente";

export class RelogioFalso implements Relogio {
  esperas: number[] = [];
  constructor(public tempo = 1_000_000) {}
  agora(): number {
    return this.tempo;
  }
  private fila: { fim: number; acordar: () => void }[] = [];
  private agendado = false;

  /**
   * Esperas simultâneas se sobrepõem, como no relógio de verdade: cada uma acorda na sua vez,
   * na ordem do fim, e o que vem depois dela roda antes de o relógio andar de novo.
   */
  esperar(ms: number): Promise<void> {
    this.esperas.push(ms);
    return new Promise((acordar) => {
      this.fila.push({ fim: this.tempo + ms, acordar });
      this.agendar();
    });
  }

  private agendar(): void {
    if (this.agendado) return;
    this.agendado = true;
    setTimeout(() => {
      this.agendado = false;
      this.fila.sort((a, b) => a.fim - b.fim);
      const proxima = this.fila.shift();
      if (proxima === undefined) return;
      this.tempo = Math.max(this.tempo, proxima.fim);
      proxima.acordar();
      if (this.fila.length > 0) this.agendar();
    }, 0);
  }
}

export function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export interface Pedido {
  url: string;
  metodo: string;
  cabecalhos: Record<string, string>;
  corpo: unknown;
  credentials: RequestCredentials | undefined;
  em: number;
}

/** Um fetch que responde por caminho (sem a origem) e registra cada pedido. */
export function fetchFalso(
  rotas: Record<string, unknown | ((pedido: Pedido) => Response)>,
  relogio?: RelogioFalso,
): typeof fetch & { pedidos: Pedido[] } {
  const pedidos: Pedido[] = [];
  const falso = async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const url = String(entrada);
    const pedido: Pedido = {
      url,
      metodo: init?.method ?? "GET",
      cabecalhos: { ...(init?.headers as Record<string, string> | undefined) },
      corpo: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
      credentials: init?.credentials,
      em: relogio?.agora() ?? 0,
    };
    pedidos.push(pedido);
    const caminho = new URL(url).pathname;
    const rota = rotas[caminho];
    if (rota === undefined) return json({ message: "não encontrado" }, 404);
    if (typeof rota === "function") return (rota as (p: Pedido) => Response)(pedido);
    return json(rota);
  };
  return Object.assign(falso as typeof fetch, { pedidos });
}

/** O IP-Checker falso: as mesmas regras do MemoryCatalogStore (S50-05), em miniatura. */
export class IpCheckerFalso {
  hashes = new Map<string, string>();
  questoes = new Map<string, QuestaoApi>();
  rodadas = new Set<string>();
  manifestos: ManifestoApi[] = [];
  partes: QuestaoApi[][] = [];
  /** Falha (com este status) a parte de número indicado (contando de 1), uma vez. */
  falhar: { parte: number; status: number } | null = null;
  private contador = 0;

  manifesto(corpo: ManifestoApi): ResultadoManifesto {
    this.manifestos.push(corpo);
    const vistas = new Map<string, { problema: string; hash: string }>();
    for (const lista of corpo.lists) {
      for (const q of lista.questions) {
        if (!vistas.has(q.question_id)) {
          vistas.set(q.question_id, { problema: q.dikastis_problem_id, hash: q.content_hash });
        }
      }
    }
    const need = [...vistas.entries()]
      .filter(([id, v]) => this.hashes.get(id) !== v.hash)
      .map(([, v]) => v.problema);
    const runId = `rodada-${++this.contador}`;
    this.rodadas.add(runId);
    return {
      run_id: runId,
      need,
      unchanged: vistas.size - need.length,
      missing: [...this.hashes.keys()].filter((id) => !vistas.has(id)).sort(),
    };
  }

  questoesDaParte(corpo: { run_id: string; questions: QuestaoApi[] }): ResultadoQuestoes {
    const resultado = { created: 0, updated: 0, unchanged: 0 };
    for (const q of corpo.questions) {
      const anterior = this.hashes.get(q.question_id);
      if (anterior === q.content_hash) resultado.unchanged++;
      else if (anterior === undefined) resultado.created++;
      else resultado.updated++;
      this.hashes.set(q.question_id, q.content_hash);
      this.questoes.set(q.question_id, q);
    }
    return resultado;
  }

  /** As rotas para o fetchFalso. */
  rotas(): Record<string, (pedido: Pedido) => Response> {
    return {
      "/api/v1/import/catalog/manifest": (p) => json(this.manifesto(p.corpo as ManifestoApi)),
      "/api/v1/import/catalog/questions": (p) => {
        const corpo = p.corpo as { run_id: string; questions: QuestaoApi[] };
        if (!this.rodadas.has(corpo.run_id)) {
          return json({ error: { code: "INVALID_INPUT", message: "Rodada desconhecida." } }, 422);
        }
        this.partes.push(corpo.questions);
        if (this.falhar?.parte === this.partes.length) {
          const status = this.falhar.status;
          this.falhar = null;
          this.partes.pop();
          return json({ error: { code: "DATABASE_UNAVAILABLE", message: "fora" } }, status);
        }
        return json(this.questoesDaParte(corpo));
      },
    };
  }
}

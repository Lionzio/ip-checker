// O cliente das rotas /api/v1/import/* do IP-Checker (S50-04, S50-05). Roda no service worker,
// com o token de importação e sem cookies (credentials: "omit"). O Chrome manda a origem
// chrome-extension://<id>, a única aceita nessas rotas além da própria página.

export interface ClasseApi {
  dikastis_org_id: string;
  name: string;
  course: string;
}

export interface ListaApi {
  dikastis_task_id: string;
  class_org_id: string;
  kind: string;
  number: number | null;
  title: string;
  starts_at: string | null;
  ends_at: string | null;
  questions: { dikastis_problem_id: string; question_id: string; content_hash: string }[];
}

export interface ManifestoApi {
  period: string;
  mode: "manual" | "semi";
  classes: ClasseApi[];
  lists: ListaApi[];
}

export interface ResultadoManifesto {
  run_id: string;
  need: string[];
  unchanged: number;
  missing: string[];
}

export interface QuestaoApi {
  question_id: string;
  dikastis_problem_id: string;
  list_kind: string;
  list_number: number | null;
  title: string;
  description: string;
  input_description: string;
  output_description: string;
  samples: { input: string; output: string }[];
  time_limit_ms: number | null;
  content_hash: string;
}

export interface ResultadoQuestoes {
  created: number;
  updated: number;
  unchanged: number;
}

/** O token de importação foi recusado (vencido, revogado, de outra conta ou digitado errado). */
export class TokenRecusado extends Error {
  constructor() {
    super("O IP-Checker recusou o token de importação: crie outro no Perfil e cole aqui.");
    this.name = "TokenRecusado";
  }
}

/** O IP-Checker não respondeu ou está fora do ar. */
export class IpCheckerIndisponivel extends Error {
  constructor(detalhe: string) {
    super(`O IP-Checker está indisponível (${detalhe}); tente de novo em alguns minutos.`);
    this.name = "IpCheckerIndisponivel";
  }
}

/** O IP-Checker recusou o pedido (formato, limite ou rodada desconhecida). */
export class RecusadoPeloIpChecker extends Error {
  constructor(
    readonly status: number,
    readonly codigo: string,
    mensagem: string,
  ) {
    super(mensagem);
    this.name = "RecusadoPeloIpChecker";
  }
}

export interface OpcoesIpChecker {
  endereco: string;
  token: string;
  fetch?: typeof fetch;
}

export class ClienteIpChecker {
  private readonly endereco: string;
  private readonly token: string;
  private readonly fetch: typeof fetch;

  constructor(opcoes: OpcoesIpChecker) {
    this.endereco = opcoes.endereco.replace(/\/+$/, "");
    this.token = opcoes.token;
    this.fetch = opcoes.fetch ?? globalThis.fetch.bind(globalThis);
  }

  manifesto(corpo: ManifestoApi): Promise<ResultadoManifesto> {
    return this.pedir<ResultadoManifesto>("POST", "/api/v1/import/catalog/manifest", corpo);
  }

  questoes(corpo: {
    run_id: string;
    period: string;
    questions: QuestaoApi[];
  }): Promise<ResultadoQuestoes> {
    return this.pedir<ResultadoQuestoes>("PUT", "/api/v1/import/catalog/questions", corpo);
  }

  private async pedir<T>(metodo: string, caminho: string, corpo: unknown): Promise<T> {
    let resposta: Response;
    try {
      resposta = await this.fetch(`${this.endereco}${caminho}`, {
        method: metodo,
        credentials: "omit",
        headers: {
          Authorization: `Bearer ${this.token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(corpo),
      });
    } catch {
      throw new IpCheckerIndisponivel("sem resposta");
    }
    if (resposta.ok) return (await resposta.json()) as T;
    if (resposta.status === 401) throw new TokenRecusado();
    const erro = await lerErro(resposta);
    if (resposta.status >= 500) throw new IpCheckerIndisponivel(`erro ${resposta.status}`);
    if (resposta.status === 429) {
      const espera = erro.espera ?? 60;
      throw new RecusadoPeloIpChecker(
        429,
        erro.codigo,
        `Muitas sincronizações seguidas: espere ${espera} s e tente de novo.`,
      );
    }
    throw new RecusadoPeloIpChecker(resposta.status, erro.codigo, erro.mensagem);
  }
}

async function lerErro(
  resposta: Response,
): Promise<{ codigo: string; mensagem: string; espera: number | null }> {
  try {
    const corpo = (await resposta.json()) as {
      error?: { code?: unknown; message?: unknown; retry_after_s?: unknown };
    };
    const erro = corpo.error ?? {};
    return {
      codigo: typeof erro.code === "string" ? erro.code : "DESCONHECIDO",
      mensagem:
        typeof erro.message === "string"
          ? erro.message
          : `O IP-Checker recusou o pedido (${resposta.status}).`,
      espera: typeof erro.retry_after_s === "number" ? erro.retry_after_s : null,
    };
  } catch {
    return {
      codigo: "DESCONHECIDO",
      mensagem: `O IP-Checker recusou o pedido (${resposta.status}).`,
      espera: null,
    };
  }
}

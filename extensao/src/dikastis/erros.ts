// Os erros do adaptador do Dikastis (S50-02). As mensagens vão para o popup; nenhuma traz o token
// nem texto de enunciado.

/** Sem sessão no Dikastis: o token não existe ou venceu. */
export class SemSessao extends Error {
  constructor() {
    super("Sem sessão no Dikastis: entre na sua conta numa aba do Dikastis e tente de novo.");
    this.name = "SemSessao";
  }
}

/**
 * Uma resposta do Dikastis veio num formato que a extensão não conhece. A sincronização para
 * inteira e nada é enviado ao IP-Checker (NFR-34).
 */
export class FormatoDesconhecido extends Error {
  constructor(
    readonly endereco: string,
    readonly campo: string,
    readonly esperado: string,
  ) {
    super(
      `O formato do Dikastis mudou em ${endereco}: o campo "${campo}" deveria ser ${esperado}. ` +
        "Nada foi enviado; avise o desenvolvedor para atualizar a extensão.",
    );
    this.name = "FormatoDesconhecido";
  }
}

/** O Dikastis respondeu com erro (ou não respondeu) depois das repetições. */
export class ErroDikastis extends Error {
  constructor(
    readonly endereco: string,
    readonly status: number | null,
  ) {
    super(
      status === null
        ? `O Dikastis não respondeu em ${endereco}; confira a conexão e tente de novo.`
        : `O Dikastis respondeu ${status} em ${endereco}; tente de novo mais tarde.`,
    );
    this.name = "ErroDikastis";
  }
}

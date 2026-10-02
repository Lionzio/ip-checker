/**
 * Entrada pelo Google (S16-01, FR-24). O botão é um link comum: o navegador vai ao backend, que
 * redireciona para o Google e, na volta, para a página certa. Quando o Google recusa, a API manda
 * só um código em `/entrar?google=...`, e a mensagem fica aqui.
 */
export const GOOGLE_START = "/api/v1/auth/google/start";

const REASONS: Record<string, string> = {
  cancelado: "A entrada pelo Google foi cancelada.",
  estado: "A entrada pelo Google expirou ou foi aberta em outra aba. Tente de novo.",
  dominio:
    "Só e-mails @cin.ufpe.br e @ufpe.br têm acesso ao IP-Checker. Escolha a sua conta Google institucional.",
  email_nao_verificado: "O Google não confirmou este e-mail. Use a sua conta Google institucional.",
  outra_conta: "Este e-mail já está ligado a outra conta Google. Entre com ela ou com a sua senha.",
  token: "O Google não confirmou a entrada. Tente de novo.",
  indisponivel: "Não foi possível entrar pelo Google agora. Tente de novo em instantes ou entre com a senha.",
  ACCOUNT_PENDING_VERIFICATION: "Confirme o seu e-mail pelo link que enviamos antes de entrar.",
  ACCOUNT_PENDING_APPROVAL:
    "O seu cadastro está aguardando a aprovação de um monitor-chefe, de um professor ou do desenvolvedor.",
  ACCOUNT_REJECTED: "O seu cadastro foi recusado.",
  ACCOUNT_REMOVED: "Esta conta foi removida da equipe e não tem mais acesso.",
};

/** A mensagem de um código de `?google=`; um código desconhecido recebe uma mensagem genérica. */
export function googleMessage(reason: string | null): string | null {
  if (reason === null || reason === "") return null;
  return REASONS[reason] ?? "Não foi possível entrar pelo Google. Tente de novo.";
}

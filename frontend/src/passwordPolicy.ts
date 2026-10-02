/**
 * Política de senha (FR-23), a mesma do backend (`ipc_api/accounts/passwords.py`): pelo menos 9
 * caracteres, 1 letra maiúscula e 1 caractere especial (nem letra, nem número, nem espaço). A
 * página mostra cada requisito enquanto a pessoa digita; quem decide é o backend.
 */

export interface PasswordRule {
  label: string;
  met: boolean;
}

const MIN_LENGTH = 9;
const MAX_LENGTH = 128;

export function passwordRules(password: string): PasswordRule[] {
  const characters = Array.from(password);
  return [
    { label: `Pelo menos ${MIN_LENGTH} caracteres`, met: characters.length >= MIN_LENGTH && characters.length <= MAX_LENGTH },
    { label: "Pelo menos 1 letra maiúscula", met: characters.some((char) => char !== char.toLowerCase()) },
    {
      label: "Pelo menos 1 caractere especial (como ! ? - _ @ #)",
      met: characters.some((char) => !/[\p{L}\p{N}\s]/u.test(char)),
    },
  ];
}

export function passwordAccepted(password: string): boolean {
  return passwordRules(password).every((rule) => rule.met);
}

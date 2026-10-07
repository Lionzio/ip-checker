import { readFileSync } from "node:fs";

/**
 * Uma conta por projeto (S28-04): os projetos "conta", "feedback" e "limite" trocam a senha, o
 * tratamento ou gastam o limite de 30 verificações por minuto da conta (P-11 h). Com a própria
 * conta, nenhum deles atrapalha os outros, e a pausa de 61 s para a janela do limite virar deixou
 * de existir. As contas são criadas pelo `accounts.setup.ts`; as senhas são desta execução e ficam
 * só em `e2e/.auth/` (fora do Git).
 */
export const PROJECT_ACCOUNTS = ["conta", "feedback", "limite"] as const;
export type ProjectAccount = (typeof PROJECT_ACCOUNTS)[number];

export interface Credentials {
  login: string;
  password: string;
  name: string;
}

export const storageFor = (project: ProjectAccount) => `e2e/.auth/${project}.json`;
export const credentialsFor = (project: ProjectAccount) => `e2e/.auth/${project}.credenciais.json`;

/** Login, senha e nome da conta do projeto, criada pelo `accounts.setup.ts`. */
export function accountOf(project: ProjectAccount): Credentials {
  return JSON.parse(readFileSync(credentialsFor(project), "utf-8")) as Credentials;
}

import { mkdirSync, writeFileSync } from "node:fs";
import { expect, type Page, test as setup } from "@playwright/test";
import { STORAGE_STATE } from "../playwright.config";
import { type Credentials, credentialsFor, PROJECT_ACCOUNTS, type ProjectAccount, storageFor } from "./accounts";
import { verificationLink } from "./mailpit";
import { pageFetch } from "./pageFetch";

/**
 * Cria a conta de cada projeto de `accounts.ts` pelo caminho de verdade: registro, e-mail no
 * Mailpit, confirmação, aprovação pelo desenvolvedor e login.
 */

/**
 * As chamadas sem sessão (registro, confirmação e login) dividem o limite de 30 por minuto por IP
 * com o projeto principal, que acabou de rodar: com 429, espera o `retry_after_s` da API e tenta de
 * novo, em vez de uma pausa fixa.
 */
async function anonymous(page: Page, path: string, body: unknown): Promise<{ status: number; body: unknown }> {
  for (let attempt = 1; ; attempt += 1) {
    const response = await pageFetch(page, path, { method: "POST", body });
    if (response.status !== 429 || attempt === 3) return response;
    const wait = (response.body as { error?: { retry_after_s?: number } }).error?.retry_after_s ?? 10;
    await page.waitForTimeout((wait + 1) * 1000);
  }
}
async function created(page: Page, project: ProjectAccount): Promise<Credentials> {
  const suffix = `${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
  const account: Credentials = {
    login: `e2e.${project}.${suffix}@cin.ufpe.br`,
    password: `E2e-${suffix}!x`,
    name: `E2E ${project} ${suffix}`,
  };
  const registered = await anonymous(page, "/api/v1/auth/register", {
    name: account.name,
    email: account.login,
    password: account.password,
    course: "Ciência da Computação",
    treatment: "neutro",
  });
  expect(registered.status, JSON.stringify(registered.body)).toBe(201);
  const link = await verificationLink(page.request, account.login);
  const verified = await anonymous(page, "/api/v1/auth/verify", { token: link.searchParams.get("token") });
  expect(verified.status, JSON.stringify(verified.body)).toBe(200);
  return account;
}

setup("cria uma conta ativa para cada projeto que mexe na própria conta", async ({ browser }) => {
  setup.setTimeout(240_000);
  const developer = await (await browser.newContext({ storageState: STORAGE_STATE })).newPage();
  await developer.goto("/");
  mkdirSync("e2e/.auth", { recursive: true });

  for (const project of PROJECT_ACCOUNTS) {
    const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
    const page = await context.newPage();
    await page.goto("/");
    const account = await created(page, project);

    const requests = await pageFetch(developer, "/api/v1/admin/requests");
    const items = (requests.body as { items: { id: string; email: string }[] }).items;
    const pending = items.find((item) => item.email === account.login);
    expect(pending, `o pedido de ${account.login} está na fila`).toBeTruthy();
    const approved = await pageFetch(developer, `/api/v1/admin/requests/${pending?.id}/approve`, {
      method: "POST",
      body: { role: "monitor" },
    });
    expect(approved.status).toBe(204);

    const signedIn = await anonymous(page, "/api/v1/auth/login", {
      login: account.login,
      password: account.password,
    });
    expect(signedIn.status).toBe(200);
    await context.storageState({ path: storageFor(project) });
    writeFileSync(credentialsFor(project), JSON.stringify(account));
    await context.close();
  }
});

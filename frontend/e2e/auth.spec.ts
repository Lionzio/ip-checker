import { expect, test } from "@playwright/test";
import { pageFetch } from "./pageFetch";

/**
 * Acesso restrito à equipe (S13-03, FR-22): sem sessão, só Registrar e Entrar, e a API não devolve
 * nada. Estes testes começam sem o cookie guardado pelo projeto "login".
 */
test.use({ storageState: { cookies: [], origins: [] } });

test("sem login, a página só mostra Registrar e Entrar", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Registrar" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Entrar" })).toBeVisible();
  await expect(page.getByLabel("Código Python")).toHaveCount(0);
  await expect(page.getByRole("option")).toHaveCount(0);
});

test("sem login, a API responde 401 e nenhum dado", async ({ request }) => {
  const lists = await request.get("/api/v1/lists");
  const validate = await request.post("/api/v1/validate", { data: { code: "x = 1\n", list_number: 1 } });

  for (const response of [lists, validate]) {
    expect(response.status()).toBe(401);
    expect(await response.json()).toEqual({
      error: {
        code: "UNAUTHENTICATED",
        message: "Entre com a sua conta da equipe para usar o IP-Checker.",
        retry_after_s: null,
      },
    });
  }
});

test("senha errada mostra a mensagem única de credenciais inválidas", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(process.env.E2E_LOGIN ?? "");
  await page.getByLabel("Senha").fill("Senha-errada-1");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page.getByRole("alert")).toContainText("Nome, e-mail ou senha incorretos.");
  await expect(page.getByLabel("Código Python")).toHaveCount(0);
});

test("e-mail fora dos domínios aceitos é recusado", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill("aluno@gmail.com");
  await page.getByLabel("Senha").fill("Qualquer-1");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page.getByRole("alert")).toContainText("Só e-mails @cin.ufpe.br e @ufpe.br");
});

test("o cookie da sessão é HttpOnly, Secure e SameSite=Lax", async ({ page }) => {
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(process.env.E2E_LOGIN ?? "");
  await page.getByLabel("Senha").fill(process.env.E2E_PASSWORD ?? "");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("button", { name: "Sair" })).toBeVisible();

  const [cookie] = await page.context().cookies();
  expect(cookie?.name).toBe("__Host-ipc_session");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.secure).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  // O JavaScript da página não enxerga o cookie.
  expect(await page.evaluate(() => document.cookie)).toBe("");
});

test("sair encerra a sessão e volta para o início", async ({ page }) => {
  // Uma sessão própria: sair com a sessão guardada derrubaria a dos outros testes.
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(process.env.E2E_NAME ?? "");
  await page.getByLabel("Senha").fill(process.env.E2E_PASSWORD ?? "");
  await page.getByRole("button", { name: "Entrar" }).click();
  const header = page.getByRole("banner");
  await expect(header).toContainText(process.env.E2E_NAME ?? "");
  await expect(header).toContainText("Monitor e desenvolvedor");

  expect((await pageFetch(page, "/api/v1/auth/me")).status).toBe(200);

  await page.getByRole("button", { name: "Sair" }).click();

  await expect(page.getByRole("link", { name: "Entrar" })).toBeVisible();
  expect((await pageFetch(page, "/api/v1/auth/me")).status).toBe(401);
});

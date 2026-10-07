import { type Browser, expect, type Page, test } from "@playwright/test";
import { accountOf } from "./accounts";
import { pageFetch } from "./pageFetch";

/**
 * Perfil e troca de senha (S14-03, FR-26) com a conta do projeto "conta" (S28-04), que é só dele:
 * a troca de senha encerra as outras sessões da conta sem atrapalhar os demais projetos.
 */
async function signIn(browser: Browser, password: string): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(accountOf("conta").login);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  return page;
}

async function changePassword(page: Page, current: string, next: string) {
  await page.goto("/perfil");
  await page.getByLabel("Senha atual", { exact: true }).fill(current);
  await page.getByLabel("Nova senha", { exact: true }).fill(next);
  await page.getByLabel("Repita a nova senha", { exact: true }).fill(next);
  await page.getByRole("button", { name: "Alterar a senha" }).click();
  await expect(page.getByRole("status")).toContainText("Senha alterada");
}

test("edita curso e tratamento no perfil, e a mudança fica salva", async ({ page }) => {
  await page.goto("/");
  const me = await pageFetch(page, "/api/v1/auth/me");
  expect(me.status).toBe(200);
  const before = me.body as { course: string; treatment: string };
  const course = before.course === "Ciência da Computação" ? "Engenharia da Computação" : "Ciência da Computação";

  await page.getByRole("link", { name: "Perfil" }).click();
  await expect(page.getByLabel("Nome", { exact: true })).not.toHaveValue("");
  await page.getByLabel("Curso", { exact: true }).fill(course);
  await page.getByLabel(/Neutro/).check();
  await page.getByRole("button", { name: "Salvar perfil" }).click();
  await expect(page.getByRole("status")).toHaveText("Perfil salvo.");

  await page.reload();
  await expect(page.getByLabel("Curso", { exact: true })).toHaveValue(course);
  await expect(page.getByLabel(/Neutro/)).toBeChecked();

  const restored = await pageFetch(page, "/api/v1/profile", {
    method: "PATCH",
    body: { course: before.course, treatment: before.treatment },
  });
  expect(restored.status).toBe(200);
});

test("troca a senha, encerra as outras sessões e mantém a atual", async ({ page, browser }) => {
  const temporary = `Temp-${Date.now()}!x`;
  const { password } = accountOf("conta");
  const other = await signIn(browser, password);
  await expect(other.getByRole("button", { name: "Sair" })).toBeVisible();

  // A senha atual errada é recusada e não troca nada.
  await page.goto("/perfil");
  await page.getByLabel("Senha atual", { exact: true }).fill("Errada-de-proposito-1");
  await page.getByLabel("Nova senha", { exact: true }).fill(temporary);
  await page.getByLabel("Repita a nova senha", { exact: true }).fill(temporary);
  await page.getByRole("button", { name: "Alterar a senha" }).click();
  await expect(page.getByRole("alert")).toHaveText("A senha atual está incorreta.");

  await changePassword(page, password, temporary);
  try {
    expect((await pageFetch(other, "/api/v1/auth/me")).status).toBe(401);
    expect((await pageFetch(page, "/api/v1/auth/me")).status).toBe(200);

    const withOld = await signIn(browser, password);
    await expect(withOld.getByRole("alert")).toContainText("Nome, e-mail ou senha incorretos.");
    const withNew = await signIn(browser, temporary);
    await expect(withNew.getByRole("button", { name: "Sair" })).toBeVisible();
  } finally {
    // Devolve a senha original pela sessão guardada, para a próxima execução local.
    await changePassword(page, temporary, password);
  }
  await other.context().close();
});

import { expect, test as setup } from "@playwright/test";
import { STORAGE_STATE } from "../playwright.config";

/** Entra pela tela com a conta do desenvolvedor e guarda o cookie para os demais testes. */
setup("entrar como desenvolvedor", async ({ page }) => {
  const password = process.env.E2E_PASSWORD;
  expect(password, "defina E2E_PASSWORD ou IPC_DEV_INITIAL_PASSWORD em deploy/.env").toBeTruthy();

  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(process.env.E2E_LOGIN ?? "");
  await page.getByLabel("Senha").fill(password ?? "");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page.getByLabel("Código Python")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sair" })).toBeVisible();
  await page.context().storageState({ path: STORAGE_STATE });
});

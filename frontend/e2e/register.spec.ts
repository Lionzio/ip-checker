import { expect, test } from "@playwright/test";
import { resetLink, verificationLink } from "./mailpit";

/**
 * Registro por e-mail e senha (S14-01, S14-02, FR-23): o formulário, o e-mail que chega ao Mailpit
 * do compose, a confirmação pelo botão da página do link e o cadastro parado na aprovação.
 */
test.use({ storageState: { cookies: [], origins: [] } });

test("registra, confirma o e-mail pelo link e espera a aprovação", async ({ page, request }) => {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const email = `e2e.${stamp}@cin.ufpe.br`;
  const name = `Pessoa E2E ${stamp}`;
  const password = `E2e-${stamp}!`;

  await page.goto("/");
  await page.getByRole("link", { name: "Registrar" }).click();
  await page.getByLabel("Nome", { exact: true }).fill(name);
  await page.getByLabel("E-mail institucional", { exact: true }).fill(email.toUpperCase());
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByLabel("Curso", { exact: true }).fill("Ciência da Computação");
  await page.getByLabel(/Feminino/).check();
  await page.getByRole("button", { name: "Registrar" }).click();

  await expect(page.getByRole("heading", { name: "Confirme o seu e-mail" })).toBeVisible();
  await expect(page.getByText(email, { exact: true })).toBeVisible();

  const link = await verificationLink(request, email);
  // Abrir o link não confirma nada: só o botão faz o POST (ameaça 21).
  await page.goto(link.pathname + link.search);
  const confirm = page.getByRole("button", { name: "Confirmar meu e-mail" });
  await expect(confirm).toBeVisible();
  await confirm.click();
  await expect(page.getByRole("status")).toContainText("E-mail confirmado");

  // O link é de uso único.
  await page.goto(link.pathname + link.search);
  await page.getByRole("button", { name: "Confirmar meu e-mail" }).click();
  await expect(page.getByRole("alert")).toContainText("já foi usado ou venceu");

  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(name);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toContainText("aguardando a aprovação");
});

test("esqueci minha senha: o link do e-mail define a senha nova (S24-04)", async ({ page, request }) => {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const email = `e2e.senha.${stamp}@cin.ufpe.br`;
  const name = `Pessoa Senha ${stamp}`;

  // Um cadastro confirmado, ainda na fila de aprovação.
  await page.goto("/registrar");
  await page.getByLabel("Nome", { exact: true }).fill(name);
  await page.getByLabel("E-mail institucional", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(`Antiga-${stamp}!`);
  await page.getByLabel("Curso", { exact: true }).fill("Ciência da Computação");
  await page.getByLabel(/Neutro/).check();
  await page.getByRole("button", { name: "Registrar" }).click();
  const verify = await verificationLink(request, email);
  await page.goto(verify.pathname + verify.search);
  await page.getByRole("button", { name: "Confirmar meu e-mail" }).click();
  await expect(page.getByRole("status")).toContainText("E-mail confirmado");

  await page.goto("/entrar");
  await page.getByRole("link", { name: "Esqueci minha senha" }).click();
  // Espera a tela nova: sem isso, o e-mail podia cair no "Nome ou e-mail institucional" de Entrar.
  await expect(page.getByRole("heading", { name: "Esqueci minha senha" })).toBeVisible();
  await page.getByLabel("E-mail institucional", { exact: true }).fill(email);
  await page.getByRole("button", { name: "Enviar o link" }).click();
  await expect(page.getByRole("status")).toContainText(`Se houver uma conta com ${email}`);

  const link = await resetLink(request, email);
  await page.goto(link.pathname + link.search);
  await page.getByLabel("Senha nova", { exact: true }).fill(`Nova-${stamp}!`);
  await page.getByLabel("Repita a senha nova").fill(`Nova-${stamp}!`);
  await page.getByRole("button", { name: "Definir a senha nova" }).click();
  await expect(page.getByRole("status")).toContainText("Senha nova definida.");

  // A senha nova é a que vale: o cadastro aparece como aguardando a aprovação.
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(`Nova-${stamp}!`);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toContainText("aguardando a aprovação");
});

test("o nome de outra conta não pode ser repetido", async ({ page }) => {
  await page.goto("/registrar");
  await page.getByLabel("Nome", { exact: true }).fill(process.env.E2E_NAME ?? "");
  await page.getByLabel("E-mail institucional", { exact: true }).fill(`e2e.nome.${Date.now()}@ufpe.br`);
  await page.getByLabel("Senha", { exact: true }).fill("Nome-repetido-1");
  await page.getByLabel("Curso", { exact: true }).fill("Ciência da Computação");
  await page.getByLabel(/Neutro/).check();
  await page.getByRole("button", { name: "Registrar" }).click();

  await expect(page.getByRole("alert")).toContainText("nome já é usado");
});

test("o e-mail do link de verificação vence ou é inválido", async ({ page }) => {
  await page.goto(`/verificar?token=${"A".repeat(43)}`);
  await page.getByRole("button", { name: "Confirmar meu e-mail" }).click();

  await expect(page.getByRole("alert")).toContainText("já foi usado ou venceu");
});

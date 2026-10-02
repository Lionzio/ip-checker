import { expect, type APIRequestContext, test } from "@playwright/test";

/**
 * Registro por e-mail e senha (S14-01, S14-02, FR-23): o formulário, o e-mail que chega ao Mailpit
 * do compose, a confirmação pelo botão da página do link e o cadastro parado na aprovação.
 */
test.use({ storageState: { cookies: [], origins: [] } });

const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://127.0.0.1:8125";

interface MailpitSummary {
  ID: string;
}

/** O link do e-mail de verificação mandado para `to`, esperando a mensagem chegar. */
async function verificationLink(request: APIRequestContext, to: string): Promise<URL> {
  let id: string | undefined;
  await expect
    .poll(
      async () => {
        const search = await request.get(`${MAILPIT}/api/v1/search`, { params: { query: `to:"${to}"` } });
        const body = (await search.json()) as { messages: MailpitSummary[] };
        id = body.messages[0]?.ID;
        return id;
      },
      { message: `o e-mail para ${to} não chegou ao Mailpit`, timeout: 15_000 },
    )
    .toBeTruthy();
  const message = (await (await request.get(`${MAILPIT}/api/v1/message/${id}`)).json()) as {
    Subject: string;
    HTML: string;
    Text: string;
  };
  expect(message.Subject).toBe("Confirme o seu cadastro no IP-Checker");
  expect(message.HTML).toContain("Clique aqui para verificar seu acesso.");
  const href = /href="([^"]+\/verificar\?token=[A-Za-z0-9_-]{43})"/.exec(message.HTML)?.[1];
  expect(href, "o HTML do e-mail traz o link de verificação").toBeTruthy();
  return new URL((href ?? "").replaceAll("&amp;", "&"));
}

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

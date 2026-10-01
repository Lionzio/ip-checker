import { expect, type Page, test } from "@playwright/test";

/**
 * Marco 1 (Sprint 9): com o compose no ar, o aluno cola o código, escolhe a Lista 1 e vê o
 * resultado do motor de verdade. Nada aqui é simulado.
 */

async function verify(page: Page, code: string) {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill(code);
  await page.getByRole("button", { name: "Verificar" }).click();
}

const result = (page: Page) => page.getByRole("region", { name: "Resultado da verificação" });

test("a página carrega as listas da API real, sem o aviso de demonstração", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("option", { name: "Lista 1: Comandos condicionais" })).toBeAttached();
  await expect(page.getByRole("note")).toHaveCount(0);
});

test("código válido na Lista 1 mostra sucesso", async ({ page }) => {
  await verify(page, "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelse:\n    print('Reprovado')\n");

  await expect(result(page).getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();
  await expect(result(page)).toContainText("Regras 2026.2.0");
});

test("for na Lista 1 mostra a R-34 na linha 2", async ({ page }) => {
  await verify(page, "n = int(input())\nfor i in range(n):\n    print(i)\n");

  const panel = result(page);
  await expect(panel.getByRole("heading", { name: "2 violações encontradas" })).toBeVisible();
  const r34 = panel.getByRole("listitem").filter({ hasText: "R-34" });
  await expect(r34).toContainText("Fora da lista");
  await expect(r34).toContainText("Linha 2, coluna 1");
  await expect(r34).toContainText("a partir da Lista 2");
});

test("erro de sintaxe mostra linha e coluna", async ({ page }) => {
  await verify(page, "x = int(input())\nif x > 0\n    print(x)\n");

  await expect(result(page).getByRole("heading", { name: "Erro de sintaxe" })).toBeVisible();
  await expect(result(page)).toContainText("Linha 2, coluna 9: faltou ':'");
});

test("as proibições gerais anulam a questão", async ({ page }) => {
  await verify(page, "try:\n    x = int(input())\nexcept ValueError:\n    x = 0\n");

  await expect(result(page).getByRole("listitem").filter({ hasText: "R-06" })).toContainText("Anulação imediata");
});

test("a 11ª verificação da sessão em um minuto mostra o limite e o tempo de espera", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill("x = 1\n");
  const verifyButton = page.getByRole("button", { name: "Verificar" });
  const clientIds = new Set<string | undefined>();

  for (let attempt = 1; attempt <= 10; attempt += 1) {
    const answered = page.waitForResponse((response) => response.url().endsWith("/api/v1/validate"));
    await verifyButton.click();
    const response = await answered;
    expect(response.status(), `verificação ${attempt}`).toBe(200);
    clientIds.add(response.request().headers()["x-client-id"]);
  }
  // A sessão inteira usa um único identificador anônimo.
  expect(clientIds.size).toBe(1);
  expect([...clientIds][0]).toMatch(/^[0-9a-f-]{36}$/);

  const limited = page.waitForResponse((response) => response.url().endsWith("/api/v1/validate"));
  await verifyButton.click();
  expect((await limited).status()).toBe(429);

  const panel = result(page);
  await expect(panel.getByRole("heading", { name: "Limite de verificações atingido" })).toBeVisible();
  await expect(panel).toContainText("Você fez muitas verificações em pouco tempo.");
  await expect(panel).toContainText(/Tente novamente em \d+ segundos\./);
  await expect(panel.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
});

test("a borda envia os cabeçalhos de segurança", async ({ page }) => {
  const response = await page.goto("/");
  const headers = response?.headers() ?? {};

  expect(headers["content-security-policy"]).toContain("script-src 'self'");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("no-referrer");
  expect(headers["server"]).toBeUndefined();
});

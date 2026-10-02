import { expect, test } from "@playwright/test";

/**
 * Limite de taxa por conta (S13-02; antes, por X-Client-Id anônimo): roda por último (projeto
 * "limite"), porque todos os testes usam a conta do desenvolvedor e dividem os 30 por minuto.
 */
test("acima de 30 verificações por minuto da mesma conta, a página mostra o limite e a espera", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill("x = 1\nif x:\n    print(x)\n");
  const verifyButton = page.getByRole("button", { name: "Verificar" });
  const statuses: number[] = [];

  for (let attempt = 1; attempt <= 40 && !statuses.includes(429); attempt += 1) {
    const answered = page.waitForResponse((response) => response.url().endsWith("/api/v1/validate"));
    await verifyButton.click();
    const response = await answered;
    statuses.push(response.status());
    // A sessão vai no cookie; o identificador anônimo antigo não existe mais.
    expect(response.request().headers()["x-client-id"]).toBeUndefined();
    if (response.status() === 200) {
      await expect(page.getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();
    }
  }

  expect(statuses.at(-1)).toBe(429);
  expect(statuses.slice(0, -1).every((status) => status === 200)).toBe(true);
  const panel = page.getByRole("region", { name: "Resultado da verificação" });
  await expect(panel.getByRole("heading", { name: "Limite de verificações atingido" })).toBeVisible();
  await expect(panel).toContainText("Você fez muitas requisições em pouco tempo.");
  await expect(panel).toContainText(/Tente novamente em \d+ segundos\./);
  await expect(panel.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
});

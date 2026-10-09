import { expect, test } from "@playwright/test";

/**
 * Comparação com o gabarito (Sprint 32, ADR-11): o compose monta os gabaritos sintéticos de
 * `e2e/gabaritos-sinteticos` na API, que só tem o da L1-Q1 de 2026.2. Nenhum gabarito oficial entra
 * aqui, e nenhum texto do gabarito chega à página.
 */

/** Uma cópia do gabarito sintético com os nomes trocados. */
const COPY = `n = int(input())
total = 0
i = 0
while i < n:
    v = int(input())
    if v % 2 == 0:
        total = total + v
    i = i + 1
if total > 100:
    print("muito", total)
else:
    print("pouco", total)
`;

test("a questão só com gabarito usa as regras da lista e mostra a comparação", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Questão").selectOption("L1-Q1");
  await page.getByLabel("Código Python").fill(COPY);
  await page.getByRole("button", { name: "Verificar" }).click();

  const panel = page.getByRole("region", { name: "Comparação com o gabarito · L1-Q1" });
  await expect(panel).toBeVisible();
  await expect(panel.getByLabel(/Semelhança com o gabarito de (9\d|100),\d%/)).toBeVisible();
  await expect(panel.getByRole("list", { name: "Em comum" })).toContainText("while");
  // O aviso de que a questão não tem regra cadastrada (ADR-11, item 6).
  await expect(page.getByText(/não tem regra cadastrada/).first()).toBeVisible();
  // Nada do gabarito sintético aparece além do que o aluno escreveu.
  await expect(page.getByText("Gabarito SINTÉTICO")).toHaveCount(0);
});

test("no plágio, duas cópias do gabarito disparam o alerta de possível vazamento", async ({ page }) => {
  await page.goto("/plagio");
  await page.getByLabel("Questão (para comparar também com o gabarito)").selectOption("L1-Q1");
  await page.getByLabel("Código A").fill(COPY);
  await page.getByLabel("Código B").fill(COPY.replaceAll("total", "soma"));
  await page.getByRole("button", { name: "Verificar" }).click();

  await expect(page.getByRole("alert")).toContainText("Possível vazamento do gabarito");
  await expect(page.getByText("Código A com o gabarito:")).toBeVisible();
});

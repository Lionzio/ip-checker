import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

/**
 * Painel de plágio (S17-03; FR-29, US-31) com o analisador de verdade: uma cópia com as variáveis
 * renomeadas aparece como "Plágio", soluções diferentes não, e a tela passa no axe.
 */
const ORIGINAL = [
  "nota = float(input())",
  "frequencia = float(input())",
  "if frequencia < 75:",
  '    print("reprovado por falta")',
  "elif nota >= 7:",
  '    print("aprovado")',
  "else:",
  '    print("final")',
  "",
].join("\n");

async function compare(page: Page, a: string, b: string) {
  await page.goto("/");
  await page.getByRole("link", { name: "Plágio" }).click();
  await page.getByLabel("Código A").fill(a);
  await page.getByLabel("Código B").fill(b);
  await page.getByRole("button", { name: "Verificar" }).click();
  return page.getByRole("region", { name: "Resultado da comparação" });
}

test("uma cópia com as variáveis renomeadas aparece como Plágio", async ({ page }) => {
  const copy = ORIGINAL.replaceAll("nota", "media").replaceAll("frequencia", "presenca");

  const result = await compare(page, ORIGINAL, copy);

  await expect(result).toContainText("100,0%");
  await expect(result).toContainText("Plágio");
  await expect(result).toContainText("a decisão final sobre plágio é sempre da equipe");

  const scan = await new AxeBuilder({ page }).include("main").analyze();
  const serious = scan.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""));
  expect(serious.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
});

test("soluções diferentes não parecem plágio", async ({ page }) => {
  const other = ["a = int(input())", "b = int(input())", "print(max(a, b))", ""].join("\n");

  const result = await compare(page, ORIGINAL, other);

  await expect(result).toContainText("Sem suspeitas");
});

test("o erro de sintaxe aponta o código e a linha", async ({ page }) => {
  const result = await compare(page, ORIGINAL, "if x\n    y = 1\n");

  await expect(result.getByRole("alert")).toContainText("O código B tem um erro de sintaxe");
  await expect(result.getByRole("alert")).toContainText("Linha 1");
});

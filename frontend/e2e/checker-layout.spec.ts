import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

/**
 * A tela de verificação com sete violações (S37-01 e S37-02): no computador, os cartões fechados
 * cabem na primeira tela de 1280×900 e o editor fica fixo; no celular, o resultado cabe em duas
 * telas de 375×812, vem em abas e tem o "Voltar ao código". Roda no projeto "feedback": cada
 * teste gasta uma verificação da conta dele.
 */

/** Lista 1: sete violações em sete regras (import, for, range, None, break, try e .sqrt()). */
const SEVEN = [
  "import math",
  "n = int(input())",
  "for i in range(n):",
  "    if i is None:",
  "        break",
  "try:",
  "    print(math.sqrt(n))",
  "except:",
  "    print(0)",
  "",
].join("\n");

const result = (page: Page) => page.getByRole("region", { name: "Resultado da verificação" });

async function verifySeven(page: Page) {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill(SEVEN);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(result(page).getByRole("heading", { name: "7 violações encontradas" })).toBeVisible();
}

async function noSeriousViolations(page: Page) {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    const scan = await new AxeBuilder({ page }).include("header").include("main").analyze();
    const serious = scan.violations.filter((item) => item.impact === "serious" || item.impact === "critical");
    expect(serious.map((item) => `${colorScheme}: ${item.id}`)).toEqual([]);
  }
}

test.describe("no computador", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("sete violações cabem na primeira tela com os cartões fechados, e o editor fica fixo", async ({ page }) => {
    await verifySeven(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    const region = result(page);

    // Acima de 5 regras, os cartões nascem fechados (S37-01).
    await expect(region.getByRole("button", { expanded: false })).toHaveCount(7);
    const box = await region.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y + box!.height).toBeLessThanOrEqual(900);

    // A coluna do editor fica fixa enquanto o resultado rola (S37-02).
    const form = page.locator("form").filter({ has: page.getByLabel("Código Python") });
    expect(await form.evaluate((element) => getComputedStyle(element).position)).toBe("sticky");
    await expect(page.getByRole("tablist")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Voltar ao código" })).toHaveCount(0);

    await noSeriousViolations(page);
  });
});

test.describe("no celular", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("o resultado cabe em duas telas, em abas, com Voltar ao código", async ({ page }) => {
    await verifySeven(page);
    const tabs = page.getByRole("tablist", { name: "Painéis do resultado" });
    await expect(tabs.getByRole("tab", { name: "Resultado" })).toHaveAttribute("aria-selected", "true");
    await expect(tabs.getByRole("tab", { name: "Feedback" })).toBeVisible();

    const panel = page.getByRole("tabpanel", { name: "Resultado" });
    const box = await panel.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeLessThanOrEqual(2 * 812);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);

    await tabs.getByRole("tab", { name: "Feedback" }).click();
    await expect(page.getByRole("heading", { name: "Feedback para o aluno" })).toBeVisible();
    await expect(result(page)).toBeHidden();

    await page.getByRole("button", { name: "Voltar ao código" }).click();
    await expect(page.getByLabel("Código Python")).toBeFocused();

    await tabs.getByRole("tab", { name: "Resultado" }).click();
    await noSeriousViolations(page);
  });
});

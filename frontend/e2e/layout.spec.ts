import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

/**
 * Celular e temas (S26-01): nenhuma tela passa de 375 px, a navegação marca a tela atual e o axe não
 * acha violações graves nem no tema claro nem no escuro. Não verifica código: não gasta o limite.
 */

const SCREENS = ["/", "/plagio", "/perfil", "/gerenciar", "/privacidade"];

async function width(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth);
}

test.describe("no celular", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  for (const path of SCREENS) {
    test(`${path} cabe em 375 px`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("navigation", { name: "Principal" })).toBeVisible();

      expect(await width(page)).toBeLessThanOrEqual(375);
    });
  }

  test("a navegação tem alvos de 44 px e marca a tela atual", async ({ page }) => {
    await page.goto("/plagio");
    const nav = page.getByRole("navigation", { name: "Principal" });

    await expect(nav.getByRole("link", { name: "Plágio" })).toHaveAttribute("aria-current", "page");
    for (const item of await nav.locator("a, button").all()) {
      expect((await item.boundingBox())?.height).toBeGreaterThanOrEqual(44);
    }
  });
});

for (const colorScheme of ["light", "dark"] as const) {
  test(`axe sem violações graves no tema ${colorScheme === "light" ? "claro" : "escuro"}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme });
    for (const path of ["/", "/plagio", "/gerenciar"]) {
      await page.goto(path);
      await expect(page.getByRole("navigation", { name: "Principal" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2 }).first()).toBeVisible();

      const scan = await new AxeBuilder({ page }).include("header").include("main").analyze();
      const serious = scan.violations.filter((item) => item.impact === "serious" || item.impact === "critical");
      expect(serious.map((item) => `${path}: ${item.id}`)).toEqual([]);
    }
  });
}

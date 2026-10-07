import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

/**
 * Indícios de uso de IA (S29; ADR-08, US-34) com o motor de verdade. No compose, os indícios ficam
 * ligados (IPC_AI_INDICATORS=1); no piloto, desligados até a política ser aprovada (S29-04), e este
 * teste não roda lá. Roda no projeto "feedback", com a conta só dele: não gasta o limite por conta
 * do projeto principal.
 */
const SUSPICIOUS = "for i in range(5):\n    if i == 1:\n        break\n    if i == 2:\n        continue\n    pass\n";
const CLEAN = "x = int(input())\nif x > 0:\n    print(x)\n";

async function verify(page: Page, code: string, list: string) {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption(list);
  await page.getByLabel("Código Python").fill(code);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page.getByRole("region", { name: "Resultado da verificação" }).getByRole("heading", { level: 2 })).toBeVisible();
}

const panel = (page: Page) => page.getByRole("region", { name: "Indícios de uso de IA" });

test("break, continue e pass juntos mostram o indício alto, com as linhas e as perguntas", async ({ page }) => {
  await verify(page, SUSPICIOUS, "2");

  await expect(panel(page)).toBeVisible();
  await expect(panel(page).getByText("Faixa alta", { exact: true })).toBeVisible();
  await expect(panel(page)).toContainText("'break', 'continue' e 'pass'");
  await expect(panel(page).getByRole("note")).toContainText("não são prova");
  await expect(panel(page).getByRole("heading", { name: "Perguntas para a conversa com o aluno" })).toBeVisible();

  await panel(page).getByRole("button", { name: "Linha 5: selecionar no editor" }).click();
  const selected = await page
    .getByLabel("Código Python")
    .evaluate((area: HTMLTextAreaElement) => area.value.slice(area.selectionStart, area.selectionEnd));
  expect(selected).toBe("        continue");

  const scan = await new AxeBuilder({ page }).include("main").analyze();
  const serious = scan.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""));
  expect(serious.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
});

test("uma solução limpa não mostra indício nenhum", async ({ page }) => {
  await verify(page, CLEAN, "1");

  await expect(page.getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();
  await expect(panel(page)).toHaveCount(0);
});

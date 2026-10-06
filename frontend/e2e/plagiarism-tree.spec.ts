import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

/**
 * Plágio por árvore canonizada (S27; ADR-07) com o analisador de verdade. Roda no projeto
 * "feedback", depois da janela do limite por conta.
 */

const ORIGINAL = [
  "def media(notas):",
  "    soma = 0",
  "    quantidade = 0",
  "    for nota in notas:",
  "        soma += nota",
  "        quantidade += 1",
  "    return soma / quantidade",
  "",
  "valores = [float(x) for x in input().split()]",
  "print(media(valores))",
  "",
].join("\n");

// A mesma solução com as funções e linhas em outra ordem, nomes trocados e o for virando while.
const DISGUISED = [
  "entrada = [float(t) for t in input().split()]",
  "",
  "def calcula(lista):",
  "    n = 0",
  "    total = 0",
  "    i = 0",
  "    while i < len(lista):",
  "        total = total + lista[i]",
  "        n = n + 1",
  "        i += 1",
  "    return total / n",
  "",
  "print(calcula(entrada))",
  "",
].join("\n");

async function open(page: Page) {
  await page.goto("/plagio");
  await expect(page.getByRole("heading", { name: "Plágio" })).toBeVisible();
}

function marked(page: Page, label: string) {
  return page.locator("div", { has: page.getByLabel(label, { exact: true }) }).last().getByTestId("line-numbers");
}

test("a cópia reordenada e reescrita mostra os trechos correspondentes nos dois lados", async ({ page }) => {
  await open(page);
  await page.getByLabel("Código A", { exact: true }).fill(ORIGINAL);
  await page.getByLabel("Código B", { exact: true }).fill(DISGUISED);
  await page.getByRole("button", { name: "Verificar" }).click();

  const result = page.getByRole("region", { name: "Resultado da comparação" });
  await expect(result).toContainText("Plágio");
  await expect(result).toContainText(/Estrutura: 100,0%/);
  const pair = result.getByRole("button", { name: "A: linhas 1–7 ↔ B: linhas 3–11" });
  await expect(pair).toBeVisible();

  await pair.click();
  await expect(pair).toHaveAttribute("aria-pressed", "true");
  await expect(marked(page, "Código A").locator("[data-current]")).toHaveText(["1", "2", "3", "4", "5", "6", "7"]);
  await expect(marked(page, "Código B").locator("[data-current]")).toHaveCount(9);

  const scan = await new AxeBuilder({ page }).include("main").analyze();
  const serious = scan.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""));
  expect(serious.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
});

test("contra a turma, o que todos escrevem não conta, e a cópia vem primeiro", async ({ page }) => {
  const common = "valor = int(input())\nprint(valor * 2 + 1)\n";
  const target = `${common}if valor > 10:\n    print('grande')\n`;
  const others = Array.from({ length: 6 }, (_, index) => `### Aluno ${index + 2}\n${common}for i in range(${index + 2}):\n    print(i * ${index + 2})\n`);
  others.push(`### Cópia\n${target.replaceAll("valor", "numero").replace("grande", "enorme")}`);

  await open(page);
  await page.getByRole("button", { name: "Contra a turma" }).click();
  await page.getByLabel("Solução comparada", { exact: true }).fill(target);
  await page.getByLabel("Soluções da turma").fill(others.join(""));
  await page.getByRole("button", { name: "Comparar com a turma" }).click();

  const rows = page.getByRole("region", { name: "Resultado contra a turma" }).getByRole("row");
  await expect(rows).toHaveCount(8);
  await expect(rows.nth(1)).toContainText("Cópia");
  await expect(rows.nth(1)).toContainText("Plágio");
  await expect(rows.nth(2)).toContainText("Sem suspeitas");
});

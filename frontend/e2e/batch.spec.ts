import { expect, type Page, test } from "@playwright/test";

/**
 * Correção em lote (S26-02 e S26-03), contra a API e o motor de verdade. Roda no projeto
 * "feedback", depois da janela do limite por conta: cada aluno gasta uma verificação e um feedback.
 */

const STUDENTS = [
  { name: "Ana Souza", code: "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\n" },
  { name: "Bruno Lima", code: "n = int(input())\nif n % 2 == 0:\n    print('par')\nelse:\n    print('ímpar')\n" },
  { name: "Carla Dias", code: "x = int(input())\nfor i in range(x):\n    print(i)\n" },
];

const result = (page: Page) => page.getByRole("region", { name: "Resultado da verificação" });

test("três alunos seguidos, em até 4 ações cada, sem o nome do anterior no feedback", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  const editor = page.getByLabel("Código Python");
  const seen: string[] = [];

  for (const student of STUDENTS) {
    // 1. Colar o código.
    await editor.fill(student.code);
    // 2. Ctrl+Enter: verifica, e o foco vai ao título do resultado.
    await editor.press("Control+Enter");
    await expect(result(page).getByRole("heading", { name: /violaç/ })).toBeFocused();
    // 3. O nome do aluno e Enter: gera o feedback, e o foco vai a Copiar.
    const name = page.getByLabel("Nome do aluno");
    await expect(name).toHaveValue("");
    await name.fill(student.name);
    await name.press("Enter");
    const text = page.getByLabel("Texto do feedback");
    await expect(text).toHaveValue(new RegExp(`^Olá, ${student.name},`));
    for (const previous of seen) await expect(text).not.toHaveValue(new RegExp(previous));
    await expect(page.getByRole("button", { name: "Copiar" })).toBeFocused();
    // 4. Próximo aluno: código, nome e resultado limpos, a lista fica, e o foco volta ao editor.
    await page.getByRole("button", { name: "Próximo aluno" }).click();
    await expect(editor).toHaveValue("");
    await expect(editor).toBeFocused();
    await expect(page.getByLabel("Lista")).toHaveValue("1");
    seen.push(student.name);
  }
});

test("clicar numa violação seleciona o trecho certo no editor", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill("n = int(input())\nif n > 0:\n    print(n)\nfor i in range(n):\n    print(i)\n");
  await page.getByRole("button", { name: "Verificar" }).click();

  const card = result(page).getByRole("listitem").filter({ hasText: "R-34" });
  await expect(card).toContainText("for i in range(n):");
  await card.getByRole("button", { name: "Linha 4, coluna 1: selecionar no editor" }).click();

  const selected = await page
    .getByLabel("Código Python")
    .evaluate((area: HTMLTextAreaElement) => area.value.slice(area.selectionStart, area.selectionEnd));
  // O motor aponta o for inteiro, do cabeçalho ao fim do corpo: o editor seleciona e marca o trecho.
  expect(selected).toBe("for i in range(n):\n    print(i)");
  await expect(page.getByLabel("Código Python")).toBeFocused();
  await expect(page.getByTestId("line-numbers").locator("[data-marked]")).toHaveText(["4", "5"]);
});

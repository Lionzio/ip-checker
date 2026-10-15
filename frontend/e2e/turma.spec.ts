import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { pageFetch } from "./pageFetch";

/**
 * A turma inteira (Sprint 40), contra a API e o motor de verdade. Roda no projeto "feedback", com a
 * conta de monitor: o lote inteiro conta 1 no limite por conta, e o todos contra todos também.
 */

const SAME = "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelse:\n    print('Reprovado')\n";

/** Dez alunos: oito válidos e diferentes entre si, um com `for` (fora da Lista 1) e um com erro de sintaxe. */
const FILES = [
  ...Array.from({ length: 8 }, (_, index) => ({
    name: `aluno${index + 1}.py`,
    code: `x${index} = int(input())\nif x${index} > ${index}:\n    print(x${index} * ${index + 2})\n`,
  })),
  { name: "aluno9.py", code: "n = int(input())\nfor i in range(n):\n    print(i)\n" },
  { name: "aluno10.py", code: "x = (1\n" },
];

test("corrige 10 arquivos de uma vez e exporta o CSV sem código (S40-01)", async ({ page }) => {
  await page.goto("/turma");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Arquivos da turma (.py ou .zip)").setInputFiles(
    FILES.map((file) => ({ name: file.name, mimeType: "text/x-python", buffer: Buffer.from(file.code) })),
  );
  await expect(page.getByText("10 arquivos prontos.")).toBeVisible();

  await page.getByRole("button", { name: "Corrigir a turma" }).click();
  const result = page.getByRole("region", { name: "Resultado da turma" });
  await expect(result).toContainText("8 válidas, 1 com violações, 1 com erro de sintaxe");
  await expect(result.getByRole("row").filter({ hasText: "aluno9" })).toContainText("R-34");

  const download = page.waitForEvent("download");
  await result.getByRole("button", { name: "Baixar CSV" }).click();
  const csv = readFileSync(await (await download).path(), "utf-8");
  expect(csv.trim().split("\r\n")).toHaveLength(11);
  for (const file of FILES) expect(csv).not.toContain(file.code.split("\n")[0]);
});

test("o todos contra todos acha o grupo de cópias (S40-02)", async ({ page }) => {
  await page.goto("/plagio");
  await page.getByRole("button", { name: "Todos contra todos" }).click();
  const others = FILES.slice(0, 4).map((file, index) => `=== Outro ${index + 1}\n${file.code}`);
  await page
    .getByLabel("Soluções da turma para todos contra todos")
    .fill([`=== Ana\n${SAME}`, ...others, `=== Bia\n${SAME}`].join(""));
  await page.getByRole("button", { name: "Comparar todos" }).click();

  const result = page.getByRole("region", { name: "Resultado todos contra todos" });
  await expect(result.getByRole("listitem").first()).toHaveText("Ana, Bia");
  await expect(result.getByRole("rowheader", { name: "Ana × Bia" })).toBeVisible();
});

test("o painel por lista é só da chefia (S40-03)", async ({ page }) => {
  await page.goto("/");
  expect((await pageFetch(page, "/api/v1/admin/list-panel?list_number=1")).status).toBe(403);
});

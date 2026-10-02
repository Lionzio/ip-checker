import { expect, type Page, test } from "@playwright/test";
import { pageFetch } from "./pageFetch";

/**
 * Feedback para o aluno (S19-01; FR-30, US-32) com o analisador de verdade e a IA falsa do compose
 * (IPC_LLM_PROVIDER=fake). Roda no projeto "feedback", sozinho: troca o tratamento do
 * desenvolvedor para conferir a apresentação nos três e o devolve no fim.
 */
const NAME = process.env.E2E_NAME ?? "";
const VALID = "x = int(input())\nif x > 0:\n    print(x)\n";
const INVALID = "x = int(input())\nfor i in range(x):\n    print(i)\n";
const FAKE_TEXT =
  "Gostei bastante de como você organizou a leitura dos dados. Como dica, vale testar o programa com outros valores de entrada.";

const PRESENTATIONS = {
  masculino: `sou o monitor ${NAME} e`,
  feminino: `sou a monitora ${NAME} e`,
  neutro: `aqui é ${NAME}, da monitoria, e`,
} as const;

async function verify(page: Page, code: string) {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption("1");
  await page.getByLabel("Código Python").fill(code);
  await page.getByRole("button", { name: "Verificar" }).click();
  return page.getByRole("region", { name: "Feedback para o aluno" });
}

async function generate(page: Page, code: string, student: string) {
  const panel = await verify(page, code);
  await panel.getByLabel("Nome do aluno").fill(student);
  await panel.getByRole("button", { name: "Gerar feedback" }).click();
  const text = panel.getByLabel("Texto do feedback");
  await expect(text).toBeVisible();
  return { panel, text: (await text.inputValue()).trim() };
}

test("o feedback usa a apresentação do tratamento e a frase obrigatória do resultado", async ({ page }) => {
  await page.goto("/");
  const me = await pageFetch(page, "/api/v1/auth/me");
  const original = (me.body as { treatment: keyof typeof PRESENTATIONS }).treatment;
  try {
    for (const treatment of ["masculino", "feminino", "neutro"] as const) {
      const changed = await pageFetch(page, "/api/v1/profile", { method: "PATCH", body: { treatment } });
      expect(changed.status).toBe(200);

      const { panel, text } = await generate(page, VALID, "Isabella Schultz");

      expect(text).toBe(
        `Olá, Isabella Schultz, ${PRESENTATIONS[treatment]} seu código estava muito bom. ` +
          `Sua questão está ótima, não houve nenhuma violação de regras. ${FAKE_TEXT}`,
      );
      await expect(panel).toContainText("Escrito com IA a partir do resultado do IP-Checker.");
    }
  } finally {
    await pageFetch(page, "/api/v1/profile", { method: "PATCH", body: { treatment: original } });
  }
});

test("com violações, a frase obrigatória lista o que o motor encontrou", async ({ page }) => {
  const { text } = await generate(page, INVALID, "Caio Lima");

  expect(text).toContain("seu código precisa de ajustes.");
  expect(text).toContain(
    "Sua questão apresenta problemas, como o uso de for e range() e a falta de if ou operador ternário, portanto ela foi anulada.",
  );
});

test("com erro de sintaxe não há feedback", async ({ page }) => {
  const panel = await verify(page, "if x\n    y = 1\n");

  await expect(panel).toContainText("as permissões não foram verificadas, então não há feedback");
  await expect(panel.getByRole("button", { name: "Gerar feedback" })).toHaveCount(0);
});

test("o texto é editável e o botão Copiar o copia", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const { panel } = await generate(page, VALID, "Duda");
  const field = panel.getByLabel("Texto do feedback");

  await field.press("Control+End");
  await field.pressSequentially(" Até a próxima!");
  await panel.getByRole("button", { name: "Copiar" }).click();

  await expect(panel.getByRole("status")).toHaveText("Copiado.");
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied.endsWith(`${FAKE_TEXT} Até a próxima!`)).toBe(true);
});

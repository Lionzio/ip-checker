import { expect, type Page, test } from "@playwright/test";

/**
 * Marco 1 (Sprint 9): com o compose no ar, quem corrige cola o código, escolhe a Lista 1 e vê o
 * resultado do motor de verdade. Nada aqui é simulado. Desde a Sprint 13, os testes usam a sessão
 * que o projeto "login" abriu (playwright.config.ts).
 */

/** No piloto (pipeline de deploy), a página está na Vercel, que repassa /api/* ao Render. */
const PILOT = process.env.E2E_TARGET === "pilot";

async function verify(page: Page, code: string, list = "1") {
  await page.goto("/");
  await page.getByLabel("Lista").selectOption(list);
  await page.getByLabel("Código Python").fill(code);
  await page.getByRole("button", { name: "Verificar" }).click();
}

const result = (page: Page) => page.getByRole("region", { name: "Resultado da verificação" });

test("a página carrega as listas da API real, sem o aviso de demonstração", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("option", { name: "Lista 1: Comandos condicionais" })).toBeAttached();
  await expect(page.getByRole("option", { name: "Lista 2: Laços de repetição" })).toBeAttached();
  await expect(page.getByRole("option", { name: "Lista 3: Listas e tuplas" })).toBeAttached();
  await expect(page.getByRole("option", { name: "Lista 4: Funções e escopo de variável" })).toBeAttached();
  await expect(page.getByRole("note")).toHaveCount(0);
});

test("Lista 3: lista com append passa, e o append na Lista 2 é da Lista 3", async ({ page }) => {
  const code = "v = input()\nfor c in v:\n    v.append(c)\n";
  await verify(page, "notas = []\nnotas.append(float(input()))\nprint(sum(notas))\n", "3");
  await expect(result(page).getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();

  await verify(page, code, "2");
  const r46 = result(page).getByRole("listitem").filter({ hasText: "R-46" });
  await expect(r46).toContainText("Fora da lista");
  await expect(r46).toContainText("a partir da Lista 3");
});

test("Lista 4: função passa, e função dentro de função não consta (Q-02 f)", async ({ page }) => {
  await verify(page, "def dobro(x):\n    return x * 2\nprint(dobro(3))\n", "4");
  await expect(result(page).getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();

  await verify(page, "def f():\n    def g():\n        return 1\n    return g()\nprint(f())\n", "4");
  const r04 = result(page).getByRole("listitem").filter({ hasText: "R-04" });
  await expect(r04).toContainText("Linha 2, coluna 5");
});

test("Lista 2: zip no cabeçalho do for passa (US-07)", async ({ page }) => {
  await verify(page, "x = input()\ny = input()\nfor a, b in zip(x, y):\n    print(a, b)\n", "2");

  await expect(result(page).getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();
});

test("Lista 2: zip fora do for mostra a R-37 com a condição (US-07)", async ({ page }) => {
  await verify(page, "a = input()\nb = input()\nz = zip(a, b)\nfor par in z:\n    print(par)\n", "2");

  const r37 = result(page).getByRole("listitem").filter({ hasText: "R-37" });
  await expect(r37).toHaveCount(1);
  await expect(r37).toContainText("Linha 3, coluna 5");
  await expect(r37).toContainText("iterável do for");
});

test("código válido na Lista 1 mostra sucesso", async ({ page }) => {
  await verify(page, "nota = float(input())\nif nota >= 7:\n    print('Aprovado')\nelse:\n    print('Reprovado')\n");

  await expect(result(page).getByRole("heading", { name: "Nenhuma violação encontrada" })).toBeVisible();
  await expect(result(page)).toContainText(/Regras 2026\.2\.\d+/);
});

test("for na Lista 1 mostra a R-34 na linha 2", async ({ page }) => {
  await verify(page, "n = int(input())\nfor i in range(n):\n    print(i)\n");

  const panel = result(page);
  // R-34 e R-35 (for e range), mais a R-02: o código não tem if, o assunto da Lista 1.
  await expect(panel.getByRole("heading", { name: "3 violações encontradas" })).toBeVisible();
  const r34 = panel.getByRole("listitem").filter({ hasText: "R-34" });
  await expect(r34).toContainText("Fora da lista");
  await expect(r34).toContainText("Linha 2, coluna 1");
  await expect(r34).toContainText("a partir da Lista 2");
});

test("código sem if na Lista 1 mostra a exigência do assunto da lista (R-02)", async ({ page }) => {
  await verify(page, "n = int(input())\nprint(n * 2)\n");

  const r02 = result(page).getByRole("listitem").filter({ hasText: "R-02" });
  await expect(r02).toContainText("Exigência não atendida");
  await expect(r02).toContainText("Solução inteira");
  await expect(r02).toContainText("assunto da Lista 1");
});

test("erro de sintaxe mostra linha e coluna", async ({ page }) => {
  await verify(page, "x = int(input())\nif x > 0\n    print(x)\n");

  await expect(result(page).getByRole("heading", { name: "Erro de sintaxe" })).toBeVisible();
  await expect(result(page)).toContainText("Linha 2, coluna 9: faltou ':'");
});

test("as proibições gerais anulam a questão", async ({ page }) => {
  await verify(page, "try:\n    x = int(input())\nexcept ValueError:\n    x = 0\n");

  await expect(result(page).getByRole("listitem").filter({ hasText: "R-06" })).toContainText("Anulação imediata");
});

test("a borda envia os cabeçalhos de segurança", async ({ page }) => {
  const response = await page.goto("/");
  const headers = response?.headers() ?? {};

  expect(headers["content-security-policy"]).toContain("script-src 'self'");
  expect(headers["content-security-policy"]).not.toContain("unsafe-inline");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("no-referrer");
  if (PILOT) {
    // Piloto (Vercel, HTTPS): HSTS e a CSP só com a própria origem; a API vem pelo rewrite (NFR-10).
    expect(headers["strict-transport-security"]).toContain("max-age=31536000");
    expect(headers["content-security-policy"]).toContain("connect-src 'self';");
  } else {
    // Compose: a borda é o Caddy, que não se apresenta.
    expect(headers["server"]).toBeUndefined();
  }
});

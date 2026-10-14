/**
 * Roteiro de capturas da página (Sprint 37): entra no compose com a conta do desenvolvedor e
 * fotografa cada tela nos temas claro e escuro, no computador (1280×900) e no celular (375×812).
 * Serve para comparar o antes e o depois de uma mudança visual; as imagens ficam fora do
 * repositório.
 *
 * De frontend/, com o compose no ar (deploy/compose.yaml) e o Chromium do Playwright instalado:
 *
 *   node scripts/capturas.mjs <pasta de saída>
 *
 * Lê E2E_BASE_URL (padrão http://127.0.0.1:8180), E2E_LOGIN (padrão: a conta do desenvolvedor) e
 * E2E_PASSWORD ou, sem ela, o IPC_DEV_INITIAL_PASSWORD do deploy/.env. Gasta 4 verificações e 4
 * comparações da conta (uma por tema e tamanho).
 */
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const output = process.argv[2];
if (!output) {
  console.error("uso: node scripts/capturas.mjs <pasta de saída>");
  process.exit(2);
}

function fromDeployEnv(name) {
  const file = fileURLToPath(new URL("../../deploy/.env", import.meta.url));
  if (!existsSync(file)) return undefined;
  const line = readFileSync(file, "utf-8")
    .split(/\r?\n/)
    .find((entry) => entry.startsWith(`${name}=`));
  return line?.slice(name.length + 1);
}

const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8180";
const login = process.env.E2E_LOGIN ?? "vlacg@cin.ufpe.br";
const password = process.env.E2E_PASSWORD ?? fromDeployEnv("IPC_DEV_INITIAL_PASSWORD");
if (!password) {
  console.error("capturas: defina E2E_PASSWORD ou IPC_DEV_INITIAL_PASSWORD em deploy/.env");
  process.exit(2);
}

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

const PAIR_A = "n = int(input())\nif n > 0:\n    print('positivo')\nelse:\n    print('não positivo')\n";
const PAIR_B = "x = int(input())\nif x > 0:\n    print('positivo')\nelse:\n    print('não positivo')\n";
const CLASS = `=== Ana\n${PAIR_A}=== Bruno\n${PAIR_B}=== Carla\nv = float(input())\nif v >= 7:\n    print('aprovado')\n`;

const SIZES = {
  computador: { width: 1280, height: 900 },
  celular: { width: 375, height: 812 },
};
const THEMES = ["claro", "escuro"];

mkdirSync(output, { recursive: true });
const browser = await chromium.launch();

for (const [size, viewport] of Object.entries(SIZES)) {
  for (const theme of THEMES) {
    const colorScheme = theme === "claro" ? "light" : "dark";
    const name = (screen) => join(output, `${screen}-${size}-${theme}.png`);
    const context = await browser.newContext({ baseURL, viewport, colorScheme });
    const page = await context.newPage();

    // Sem sessão: a tela inicial e o Entrar.
    await page.goto("/");
    await page.getByRole("link", { name: "Entrar" }).waitFor();
    await page.screenshot({ path: name("inicial"), fullPage: true });
    await page.goto("/entrar");
    await page.getByRole("button", { name: "Entrar" }).waitFor();
    await page.screenshot({ path: name("entrar"), fullPage: true });

    await page.getByLabel("Nome ou e-mail institucional").fill(login);
    await page.getByLabel("Senha", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.getByLabel("Código Python").waitFor();
    await page.screenshot({ path: name("verificar-vazio"), fullPage: true });

    // Verificar com sete violações, na Lista 1.
    await page.getByLabel("Lista").selectOption("1");
    await page.getByLabel("Código Python").fill(SEVEN);
    await page.getByRole("button", { name: "Verificar" }).click();
    await page.getByRole("region", { name: "Resultado da verificação" }).getByRole("heading", { name: /violaç/ }).waitFor();
    await page.screenshot({ path: name("verificar-resultado"), fullPage: true });
    await page.screenshot({ path: name("verificar-resultado-1-tela") });

    // Plágio: dois códigos e contra a turma.
    await page.goto("/plagio");
    await page.getByRole("button", { name: "Dois códigos" }).waitFor();
    await page.getByLabel("Código A").fill(PAIR_A);
    await page.getByLabel("Código B").fill(PAIR_B);
    await page.getByRole("button", { name: "Verificar", exact: true }).click();
    await page.getByRole("region", { name: "Resultado da comparação" }).getByText(/%/).first().waitFor();
    await page.screenshot({ path: name("plagio-dois-codigos"), fullPage: true });
    await page.getByRole("button", { name: "Contra a turma" }).click();
    await page.getByLabel("Solução comparada").fill(PAIR_A);
    await page.getByLabel("Soluções da turma").fill(CLASS);
    await page.getByRole("button", { name: "Comparar com a turma" }).click();
    await page.getByRole("region", { name: "Resultado contra a turma" }).getByText(/%/).first().waitFor();
    await page.screenshot({ path: name("plagio-turma"), fullPage: true });

    // Gerenciar e Perfil.
    await page.goto("/gerenciar");
    await page.getByRole("heading", { level: 2 }).first().waitFor();
    await page.screenshot({ path: name("gerenciar"), fullPage: true });
    await page.goto("/perfil");
    await page.getByRole("heading", { level: 2 }).first().waitFor();
    await page.screenshot({ path: name("perfil"), fullPage: true });

    await context.close();
    console.log(`${size}, tema ${theme}: ok`);
  }
}

await browser.close();
console.log(`Capturas em ${output}`);

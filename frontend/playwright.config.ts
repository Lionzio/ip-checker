import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke e2e (S9-02): a página servida pelo Caddy do compose, falando com a API, o analyzer e o banco
 * de verdade. Suba o compose antes (`docker compose -f deploy/compose.yaml up --build -d --wait`).
 *
 * Desde a Sprint 13, tudo exige sessão: o projeto "login" entra pela tela com a conta do
 * desenvolvedor e guarda o cookie em `e2e/.auth/` (fora do Git), que os demais testes reusam. A
 * senha vem de E2E_PASSWORD ou, localmente, do IPC_DEV_INITIAL_PASSWORD do `deploy/.env`.
 */

function fromDeployEnv(name: string): string | undefined {
  const file = fileURLToPath(new URL("../deploy/.env", import.meta.url));
  if (!existsSync(file)) return undefined;
  const line = readFileSync(file, "utf-8")
    .split(/\r?\n/)
    .find((entry) => entry.startsWith(`${name}=`));
  return line?.slice(name.length + 1);
}

process.env.E2E_LOGIN ??= "vlacg@cin.ufpe.br";
process.env.E2E_NAME ??= "Vinícius Leôncio de Andrade Corrêa Gondim";
process.env.E2E_PASSWORD ??= fromDeployEnv("IPC_DEV_INITIAL_PASSWORD") ?? "";

export const STORAGE_STATE = "e2e/.auth/desenvolvedor.json";

/**
 * No piloto (pipeline de deploy), só o que não altera o ambiente de verdade: o smoke e o acesso.
 * Registro, gerenciamento, troca de senha e o limite por conta ficam nos testes do compose.
 */
const PILOT = process.env.E2E_TARGET === "pilot";
const PILOT_ONLY = /(smoke|auth)\.spec\.ts/;

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8180",
    trace: "retain-on-failure",
  },
  projects: PILOT
    ? [
        { name: "login", testMatch: /auth\.setup\.ts/, use: { ...devices["Desktop Chrome"] } },
        {
          name: "chromium",
          use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
          dependencies: ["login"],
          testMatch: PILOT_ONLY,
        },
      ]
    : [
    { name: "login", testMatch: /auth\.setup\.ts/, use: { ...devices["Desktop Chrome"] } },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["login"],
      testIgnore: /(limits|account|feedback|batch|plagiarism-tree)\.spec\.ts/,
    },
    {
      // Uma pausa de 61 s: a janela do limite por conta vira antes dos próximos projetos.
      name: "janela",
      dependencies: ["chromium"],
      testMatch: /window\.setup\.ts/,
    },
    {
      // Sozinho: a troca de senha encerra as outras sessões da conta do desenvolvedor.
      name: "conta",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["janela"],
      testMatch: /account\.spec\.ts/,
      fullyParallel: false,
    },
    {
      // Sozinho também: troca o tratamento do desenvolvedor para conferir os três (S19-01). A correção
      // em lote (S26-02) e o plágio por árvore (S27) vêm junto: cada um gasta o limite por conta.
      name: "feedback",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["conta"],
      testMatch: /(feedback|batch|plagiarism-tree)\.spec\.ts/,
      fullyParallel: false,
    },
    {
      // Por último: o limite é por conta, e todos os testes dividem a do desenvolvedor.
      name: "limite",
      use: { ...devices["Desktop Chrome"], storageState: STORAGE_STATE },
      dependencies: ["feedback"],
      testMatch: /limits\.spec\.ts/,
    },
      ],
});

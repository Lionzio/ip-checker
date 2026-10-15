import AxeBuilder from "@axe-core/playwright";
import { type Browser, expect, type Page, test } from "@playwright/test";
import { verificationLink } from "./mailpit";
import { pageFetch } from "./pageFetch";

/**
 * Gerenciamento da equipe (S15-03; US-27, US-28): o desenvolvedor aprova um cadastro novo, a
 * pessoa entra como monitora sem acesso ao gerenciamento, é removida (vira Ex-monitor e perde a
 * sessão) e é reativada. A tela passa no axe sem violações graves ou críticas.
 */

async function freshPage(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  return context.newPage();
}

async function signIn(page: Page, login: string, password: string) {
  await page.goto("/entrar");
  await page.getByLabel("Nome ou e-mail institucional").fill(login);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
}

function row(page: Page, section: RegExp, name: string) {
  return page.getByRole("region", { name: section }).getByRole("row").filter({ hasText: name });
}

test("aprova, remove e reativa um membro pela tela de gerenciamento", async ({ page, browser, request }) => {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const name = `Monitora E2E ${stamp}`;
  const email = `gerencia.${stamp}@cin.ufpe.br`;
  const password = `Ger-${stamp}!`;

  // Cadastro e confirmação do e-mail, como no registro (S14).
  const person = await freshPage(browser);
  await person.goto("/registrar");
  await person.getByLabel("Nome", { exact: true }).fill(name);
  await person.getByLabel("E-mail institucional", { exact: true }).fill(email);
  await person.getByLabel("Senha", { exact: true }).fill(password);
  await person.getByLabel("Curso", { exact: true }).fill("Ciência da Computação");
  await person.getByLabel(/Neutro/).check();
  await person.getByRole("button", { name: "Registrar" }).click();
  await expect(person.getByRole("heading", { name: "Confirme o seu e-mail" })).toBeVisible();
  const link = await verificationLink(request, email);
  await person.goto(link.pathname + link.search);
  await person.getByRole("button", { name: "Confirmar meu e-mail" }).click();
  await expect(person.getByRole("status")).toContainText("E-mail confirmado");

  // O desenvolvedor aprova como monitor.
  await page.goto("/");
  await page.getByRole("link", { name: "Gerenciar" }).click();
  const pending = row(page, /Pedidos pendentes/, name);
  await expect(pending).toContainText(email);
  await expect(pending).toContainText("E-mail e senha");
  await pending.getByRole("combobox", { name: `Cargo para aprovar ${name}` }).selectOption({ label: "Monitor" });
  await pending.getByRole("button", { name: `Aprovar ${name}` }).click();
  await expect(page.getByRole("status")).toHaveText(`${name} foi aprovado(a) como Monitor.`);
  await expect(row(page, /Membros ativos/, name)).toContainText("Monitor");

  const scan = await new AxeBuilder({ page }).include("main").analyze();
  const serious = scan.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? ""));
  expect(serious.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);

  // A pessoa aprovada entra, verifica código e não gerencia ninguém, nem pela API.
  await signIn(person, email, password);
  await expect(person.getByLabel("Código Python")).toBeVisible();
  // O nome completo e o cargo ficam no menu da conta (S37-04).
  await person.getByRole("button", { name: "Menu da conta" }).click();
  await expect(person.getByRole("banner").locator("p", { hasText: name })).toHaveText(`${name}Monitor`);
  await person.keyboard.press("Escape");
  await expect(person.getByRole("link", { name: "Gerenciar" })).toHaveCount(0);
  const forbidden = await pageFetch(person, "/api/v1/admin/requests");
  expect(forbidden.status).toBe(403);

  // Removida, vira Ex-monitor, perde a sessão e vê a mensagem de conta removida.
  page.once("dialog", (dialog) => {
    expect(dialog.message()).toContain("A conta passa a Ex-monitor");
    void dialog.accept();
  });
  await row(page, /Membros ativos/, name).getByRole("button", { name: `Remover ${name}` }).click();
  await expect(page.getByRole("status")).toHaveText(`${name} foi removido(a) da equipe (Ex-monitor).`);
  await expect(row(page, /Ex-monitores, conselheiros e inativos/, name)).toContainText("Ex-monitor");
  expect((await pageFetch(person, "/api/v1/auth/me")).status).toBe(401);
  const again = await freshPage(browser);
  await signIn(again, email, password);
  await expect(again.getByRole("alert")).toContainText("Esta conta foi removida da equipe");

  // Reativada como monitor, volta a entrar.
  const removed = row(page, /Ex-monitores, conselheiros e inativos/, name);
  await removed.getByRole("combobox", { name: `Cargo para reativar ${name}` }).selectOption({ label: "Monitor" });
  await removed.getByRole("button", { name: `Reativar ${name}` }).click();
  await expect(page.getByRole("status")).toHaveText(`${name} foi reativado(a) como Monitor.`);
  await signIn(again, email, password);
  await expect(again.getByLabel("Código Python")).toBeVisible();

  // O registro de ações (REC-06) mostra as três ações, da mais recente, com quem as fez.
  const log = page.getByRole("region", { name: /Registro de ações/ }).getByRole("row").filter({ hasText: name });
  await expect(log).toHaveText([
    new RegExp(`Reativou ${name}.*Ex-monitor → Ativo \\(Monitor\\)`),
    new RegExp(`Removeu ${name}.*Ativo → Ex-monitor`),
    new RegExp(`Aprovou ${name}.*Pendente → Ativo \\(Monitor\\)`),
  ]);
  await expect(log.first()).toContainText("Monitor e desenvolvedor");
  expect((await pageFetch(again, "/api/v1/admin/log")).status).toBe(403);

  await Promise.all([person.context().close(), again.context().close()]);
});

test("o desenvolvedor aparece em dourado, sem botões, como Monitor e desenvolvedor", async ({ page }) => {
  await page.goto("/gerenciar");

  const developer = row(page, /Membros ativos/, process.env.E2E_NAME ?? "");
  await expect(developer).toContainText("Monitor e desenvolvedor");
  await expect(developer.getByRole("button")).toHaveCount(0);
  await expect(developer.getByText("Monitor e desenvolvedor", { exact: true })).toHaveClass(/amber/);
});

test("o painel por lista mostra só contagens anônimas (S40-03)", async ({ page }) => {
  await page.goto("/gerenciar");

  const panel = page.getByRole("region", { name: "Painel por lista" });
  await panel.getByLabel("Lista do painel").selectOption("1");
  await expect(panel).toContainText(/verificaç(ão|ões)/);
  const answer = await pageFetch(page, "/api/v1/admin/list-panel?list_number=1");
  expect(answer.status).toBe(200);
  expect(Object.keys(answer.body as object).sort()).toEqual(
    ["adoption_pct", "events", "list_number", "semester", "syntax_errors", "top_rules"].sort(),
  );
  await expect(panel).not.toContainText(process.env.E2E_NAME ?? "");
});

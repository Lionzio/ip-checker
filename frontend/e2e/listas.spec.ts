import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";
import { pageFetch } from "./pageFetch";

/**
 * O catálogo das listas (Sprint 50), ponta a ponta: o desenvolvedor cria o token de importação no
 * Perfil, o teste faz o papel da extensão nas rotas /api/v1/import/* e a tela "Listas do período"
 * mostra o que chegou. Uma segunda importação igual não muda a versão. Os textos são inventados.
 */

interface Question {
  question_id: string;
  dikastis_problem_id: string;
  list_kind: "lista";
  list_number: number;
  title: string;
  description: string;
  input_description: string;
  output_description: string;
  samples: { input: string; output: string }[];
  time_limit_ms: number;
  content_hash: string;
}

/** O hash do enunciado (a regra de backend/src/ipc_api/importing/hashing.py); os textos já vêm limpos. */
function hash(q: Omit<Question, "content_hash" | "question_id" | "dikastis_problem_id" | "list_kind" | "list_number" | "time_limit_ms">) {
  const canonical = JSON.stringify({
    description: q.description,
    input_description: q.input_description,
    output_description: q.output_description,
    samples: q.samples,
    title: q.title,
  });
  return createHash("sha256").update(canonical, "utf8").digest("hex");
}

function question(questionId: string, listNumber: number, title: string): Question {
  const texts = {
    title,
    description: `Enunciado inventado da ${questionId}.`,
    input_description: "Um inteiro N.",
    output_description: "O mesmo N.",
    samples: [{ input: "1", output: "1" }],
  };
  return {
    question_id: questionId,
    dikastis_problem_id: `E2E-${questionId}`,
    list_kind: "lista",
    list_number: listNumber,
    time_limit_ms: 1000,
    ...texts,
    content_hash: hash(texts),
  };
}

const QUESTIONS = [question("L1-Q1", 1, "Eco do e2e"), question("L4-Q4", 4, "Aposta do e2e")];
const MANIFEST = {
  period: "2026.2",
  mode: "manual",
  classes: [{ dikastis_org_id: "E2E-TURMA", name: "IP SI UFPE 2026.2", course: "SI" }],
  lists: [1, 4].map((number) => ({
    dikastis_task_id: `E2E-T${number}`,
    class_org_id: "E2E-TURMA",
    kind: "lista",
    number,
    title: `Lista ${number}`,
    starts_at: "2026-10-01T03:00:00Z",
    ends_at: "2026-10-08T02:59:00Z",
    questions: QUESTIONS.filter((q) => q.list_number === number).map((q) => ({
      dikastis_problem_id: q.dikastis_problem_id,
      question_id: q.question_id,
      content_hash: q.content_hash,
    })),
  })),
};

test("o token do Perfil importa o catálogo, e a tela mostra as listas (S50-04 a S50-06)", async ({ page }) => {
  await page.goto("/perfil");
  await page.getByLabel("Onde vai ficar").fill("e2e");
  await page.getByRole("button", { name: "Criar token" }).click();
  const token = (await page.locator("code", { hasText: /^ipc_imp_/ }).textContent()) ?? "";
  expect(token).toMatch(/^ipc_imp_/);
  const auth = { Authorization: `Bearer ${token}` };

  const first = await pageFetch(page, "/api/v1/import/catalog/manifest", { method: "POST", body: MANIFEST, headers: auth });
  expect(first.status).toBe(200);
  const run = first.body as { run_id: string; need: string[] };
  expect(run.need.sort()).toEqual(["E2E-L1-Q1", "E2E-L4-Q4"]);
  const saved = await pageFetch(page, "/api/v1/import/catalog/questions", {
    method: "PUT",
    body: { run_id: run.run_id, period: "2026.2", questions: QUESTIONS },
    headers: auth,
  });
  expect(saved.body).toEqual({ created: 2, updated: 0, unchanged: 0 });

  // A segunda verificação, sem mudança no "Dikastis": nada novo, e a versão continua 1.
  const second = await pageFetch(page, "/api/v1/import/catalog/manifest", { method: "POST", body: MANIFEST, headers: auth });
  expect(second.body).toMatchObject({ need: [], unchanged: 2, missing: [] });

  await page.getByRole("link", { name: "Listas" }).click();
  await expect(page).toHaveURL(/\/listas$/);
  const lista4 = page.getByRole("region", { name: "Lista 4" });
  await expect(lista4.getByRole("row").filter({ hasText: "L4-Q4" })).toContainText("✓ regras");
  const lista1 = page.getByRole("region", { name: "Lista 1" });
  await expect(lista1.getByRole("row").filter({ hasText: "L1-Q1" })).toContainText("✓ gabarito");
  const catalog = await pageFetch(page, "/api/v1/periods/2026.2/catalog");
  const versions = (catalog.body as { lists: { questions: { version: number }[] }[] }).lists.flatMap((l) =>
    l.questions.map((q) => q.version),
  );
  expect(versions).toEqual([1, 1]);
  expect(JSON.stringify(catalog.body)).not.toContain("Enunciado inventado");

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar enunciados (.zip)" }).click();
  expect((await download).suggestedFilename()).toBe("enunciados-2026.2.zip");

  // O token sai como entrou: revogado, ele não abre mais as rotas da extensão.
  await page.goto("/perfil");
  await page.getByRole("list", { name: "Seus tokens de importação" }).getByRole("button", { name: "Revogar" }).first().click();
  await expect(page.getByText("Token “e2e” revogado.")).toBeVisible();
  const refused = await pageFetch(page, "/api/v1/import/catalog/manifest", { method: "POST", body: MANIFEST, headers: auth });
  expect(refused.status).toBe(401);
});

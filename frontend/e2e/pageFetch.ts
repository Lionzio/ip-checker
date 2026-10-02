import { type Page } from "@playwright/test";

/**
 * Chama a API de dentro da página, como o SPA faz. O `page.request` do Playwright não manda o
 * cookie `Secure` por http para 127.0.0.1, e o navegador manda (127.0.0.1 é contexto seguro).
 */
export async function pageFetch(
  page: Page,
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<{ status: number; body: unknown }> {
  return page.evaluate(
    async ({ path, method, body }) => {
      const response = await fetch(path, {
        method,
        headers: body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await response.text();
      return { status: response.status, body: text === "" ? null : (JSON.parse(text) as unknown) };
    },
    { path, method: init.method ?? "GET", body: init.body },
  );
}

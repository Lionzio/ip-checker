import { type APIRequestContext, expect } from "@playwright/test";

/** O Mailpit do compose, que captura os e-mails de verificação (S14-02). */
export const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://127.0.0.1:8125";

interface MailpitSummary {
  ID: string;
}

/** O link do e-mail de verificação mandado para `to`, esperando a mensagem chegar. */
export async function verificationLink(request: APIRequestContext, to: string): Promise<URL> {
  let id: string | undefined;
  await expect
    .poll(
      async () => {
        const search = await request.get(`${MAILPIT}/api/v1/search`, { params: { query: `to:"${to}"` } });
        const body = (await search.json()) as { messages: MailpitSummary[] };
        id = body.messages[0]?.ID;
        return id;
      },
      { message: `o e-mail para ${to} não chegou ao Mailpit`, timeout: 15_000 },
    )
    .toBeTruthy();
  const message = (await (await request.get(`${MAILPIT}/api/v1/message/${id}`)).json()) as {
    Subject: string;
    HTML: string;
  };
  expect(message.Subject).toBe("Confirme o seu cadastro no IP-Checker");
  expect(message.HTML).toContain("Clique aqui para verificar seu acesso.");
  const href = /href="([^"]+\/verificar\?token=[A-Za-z0-9_-]{43})"/.exec(message.HTML)?.[1];
  expect(href, "o HTML do e-mail traz o link de verificação").toBeTruthy();
  return new URL((href ?? "").replaceAll("&amp;", "&"));
}

/** O link do e-mail de "esqueci minha senha" (S24-04) mandado para `to`. */
export async function resetLink(request: APIRequestContext, to: string): Promise<URL> {
  let id: string | undefined;
  await expect
    .poll(
      async () => {
        const query = `to:"${to}" subject:"Redefina a sua senha"`;
        const search = await request.get(`${MAILPIT}/api/v1/search`, { params: { query } });
        const body = (await search.json()) as { messages: MailpitSummary[] };
        id = body.messages[0]?.ID;
        return id;
      },
      { message: `o e-mail de redefinição para ${to} não chegou ao Mailpit`, timeout: 15_000 },
    )
    .toBeTruthy();
  const message = (await (await request.get(`${MAILPIT}/api/v1/message/${id}`)).json()) as { HTML: string };
  const href = /href="([^"]+\/redefinir-senha\?token=[A-Za-z0-9_-]{43})"/.exec(message.HTML)?.[1];
  expect(href, "o HTML do e-mail traz o link de redefinição").toBeTruthy();
  return new URL((href ?? "").replaceAll("&amp;", "&"));
}

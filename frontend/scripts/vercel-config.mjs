/**
 * Configuração da página no piloto (Vercel, Fase 1; S11-02, S16-02, NFR-10), no formato da Build
 * Output API v3 (`.vercel/output/config.json`).
 *
 * Desde a Sprint 16, página e API ficam na mesma origem (ADR-04): a Vercel repassa `/api/*` ao
 * Render por *rewrite*. O cookie da sessão fica na origem da página, o CORS deixa de existir e a
 * CSP só permite falar com a própria origem. O endereço do Render vem de `IPC_API_ORIGIN`, lida só
 * no build, para montar o *rewrite*; ele nunca entra no código da página.
 */

/** Um ano, como na API e na borda do compose. */
export const HSTS = "max-age=31536000; includeSubDomains";

/**
 * Valida o endereço da API e devolve a origem (esquema, host e porta).
 * @param {string | undefined} value
 * @returns {string}
 */
export function parseApiOrigin(value) {
  let url;
  try {
    url = new URL(value ?? "");
  } catch {
    throw new Error(`IPC_API_ORIGIN inválida: ${JSON.stringify(value ?? "")}. Use, por exemplo, https://ip-checker-api.onrender.com`);
  }
  const extra = (url.pathname !== "/" && url.pathname !== "") || url.search || url.hash || url.username;
  if (url.protocol !== "https:" || extra) {
    throw new Error(`IPC_API_ORIGIN inválida: ${JSON.stringify(value)}. Use só a origem HTTPS da API, sem caminho.`);
  }
  return url.origin;
}

/**
 * A página só fala com a própria origem: a API chega pelo *rewrite* de `/api/*`.
 * @returns {string}
 */
export function contentSecurityPolicy() {
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "upgrade-insecure-requests",
  ].join("; ");
}

/**
 * @param {{ apiOrigin: string }} options
 */
export function buildOutputConfig({ apiOrigin }) {
  return {
    version: 3,
    routes: [
      {
        src: "/(.*)",
        headers: {
          "Content-Security-Policy": contentSecurityPolicy(),
          "Strict-Transport-Security": HSTS,
          "X-Content-Type-Options": "nosniff",
          "Referrer-Policy": "no-referrer",
          "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
          "Cross-Origin-Opener-Policy": "same-origin",
        },
        continue: true,
      },
      // Arquivos com hash no nome nunca mudam; o resto é revalidado a cada visita.
      {
        src: "/assets/(.*)",
        headers: { "Cache-Control": "public, max-age=31536000, immutable" },
        continue: true,
      },
      { src: "/version.json", headers: { "Cache-Control": "no-store" }, continue: true },
      // Mesma origem (S16-02): a API no Render atende /api/* pela origem da página. Os cookies e o
      // retorno do Google ficam aqui; o Render vê o IP do cliente no X-Forwarded-For (P-15 b).
      { src: "/api/(.*)", dest: `${apiOrigin}/api/$1` },
      { handle: "filesystem" },
      // Página única: qualquer outro caminho devolve o index.html.
      { src: "/(.*)", dest: "/index.html" },
    ],
  };
}
